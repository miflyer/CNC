from django.shortcuts import render

#View — это обычная функция.
# Правило одно: принимает request (объект с данными запроса) и обязана вернуть ответ.

def index(request):
    # Пока данные захардкожены прямо тут.
    # На Этапе 2 заменим это на данные из базы и внешнего API.
    fake_assets = [
        {"name": "Bitcoin", "price": "97 000"},
        {"name": "Ethereum", "price": "3 400"},
        {"name": "Акции Сбера", "price": "310"},
    ]
    context = {
        "title": "Биржа CNC",
        "assets": fake_assets,
    }
    return render(request, "market/index.html", context)

