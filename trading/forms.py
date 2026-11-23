from django import forms

from market.models import Asset

from .models import Order


class TradeForm(forms.Form):
    asset = forms.ModelChoiceField(queryset=Asset.objects.filter(is_active=True))
    side = forms.ChoiceField(choices=Order.Side.choices)
    order_type = forms.ChoiceField(choices=Order.Type.choices)
    quantity = forms.DecimalField(max_digits=20, decimal_places=8, min_value=0)
    limit_price = forms.DecimalField(
        max_digits=20, decimal_places=8, min_value=0, required=False,
        label="Цена (для лимитной)",
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("order_type") == Order.Type.LIMIT and not cleaned_data.get("limit_price"):
            raise forms.ValidationError("Для лимитной заявки укажите цену")
        return cleaned_data
