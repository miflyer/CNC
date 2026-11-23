from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import RegisterForm


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)  # пока НЕ сохраняем в базу
            user.set_password(form.cleaned_data["password"])  # хэшируем пароль
            user.save()
            # Кошелёк создаётся автоматически сигналом accounts/signals.py.
            # Создавать его здесь второй раз нельзя — OneToOne даст IntegrityError.
            login(request, user)  # сразу авторизуем
            return redirect("index")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})
