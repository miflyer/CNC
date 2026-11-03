from django.http import HttpResponse

#View — это обычная функция.
# Правило одно: принимает request (объект с данными запроса) и обязана вернуть ответ.

def index(request):
    return HttpResponse("Привет! Биржа CNC работает.")
