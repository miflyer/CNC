# CNC Exchange — учебная биржа на Django

Пользователи регистрируются, получают **10 000 виртуальных долларов** и торгуют
криптовалютами и валютными парами по реальным ценам. Рейтинг игроков,
лимитные заявки, графики свечей.

## Стек

Django 6, SQLite (в разработке), requests (Binance + Frankfurter API),
Lightweight Charts (CDN), polling вместо WebSocket.

## Запуск (разработка)

```bash
python -m venv venv
venv/Scripts/activate            # Windows; в Git Bash: source venv/Scripts/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_assets     # создать активы (BTC, ETH, BNB, SOL, EUR, GBP)
python manage.py update_prices   # загрузить цены и свечи из API

python manage.py runserver       # сайт на http://127.0.0.1:8000
```

Цены не обновляются сами: держи во втором терминале фоновый процесс:

```bash
python manage.py update_prices --loop 60   # каждые 60 секунд
```

Одновременно он исполняет лимитные заявки, когда цена до них доходит.

## Тесты

```bash
python manage.py test
```

## Деплой (Docker)

```bash
docker compose up --build
```

Поднимет веб-сервер (gunicorn) и фоновый обновляль цен.
ВНИМАНИЕ: compose-конфиг с SQLite — демонстрационный. Для настоящего продакшена
замени БД на PostgreSQL, вынеси SECRET_KEY в `.env`, задай `DEBUG = False`
и `ALLOWED_HOSTS`.

## Архитектура

- `accounts` — пользователи, кошелёк (Decimal!), сигнал автосоздания кошелька
- `market` — активы, свечи, загрузка котировок (`services.py`), management-команды
- `trading` — ордера, сделки, позиции; исполнение в `services.py`
- `portfolio` — портфель, история сделок, рейтинг игроков

### Ключевые решения

- **Деньги только `DecimalField`**, никаких float;
- исполнение заявок — внутри `transaction.atomic()` с `select_for_update()`
  (кошелёк и позиция блокируются, двойная трата невозможна);
- лимитные заявки резервируют средства/актив при размещении;
- внешние API недоступны клиентам напрямую — сайт раздаёт свои данные из БД.

## Что осознанно упрощено (и что делать дальше)

1. **Polling вместо WebSocket** (Этап 8) — цены на страницах обновляются
   AJAX-опросом каждые 5–10 секунд. WebSocket-вариант: Django Channels + Redis.
2. **Команда `update_prices` вместо Celery** — для продакшена перенеси
   периодические задачи на Celery + Redis beat.
3. **DRF не используется** — сайт server-rendered; API-эндпоинты отдают JSON
   (свечи, цены), при желании легко переехать на DRF.
4. **SQLite** — до этапа деплоя; миграция на PostgreSQL: поменять `DATABASES`.
5. Собственный стакан и матчинг заявок между пользователями (конец Этапа 7)
   не реализованы — сделки идут против «системы» по рыночной цене.
6. Сезоны-соревнования (Этап 6) не реализованы — рейтинг общий, от стартовых 10 000$.
