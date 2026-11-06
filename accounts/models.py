from django.db import models
from django.conf import settings

# Класс (модель) кошелька
class Wallet(models.Model):
    # Поле пользователя, которому принадлежит кошелек
    user = models.OneToOneField( # OneToOneField — связь «один к одному»: у пользователя ровно один кошелёк
        settings.AUTH_USER_MODEL, # Ссылка на модель пользователя
        on_delete=models.CASCADE, # Каскад удаления, при удалении пользователя удалится кошелек
        related_name="wallet", # Позволит писать user.wallet
    )

    # Поле количества денег в балансе
    balance = models.DecimalField( # Тип данных - точный, без погрешностей
        max_digits=14,
        decimal_places=2,
        default=10000,
    )

    # Поле времени создания кошелька
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Кошелёк {self.user.username}: {self.balance}"

