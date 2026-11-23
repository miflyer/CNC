import time

from django.core.management.base import BaseCommand

from market.services import update_market_data


class Command(BaseCommand):
    help = "Обновляет котировки и свечи из внешних API, исполняет лимитные заявки"

    def add_arguments(self, parser):
        parser.add_argument(
            "--loop",
            type=int,
            default=0,
            metavar="SECONDS",
            help="Перезапускать каждые N секунд (0 = выполнить один раз)",
        )

    def handle(self, *args, **options):
        while True:
            errors = update_market_data()
            for error in errors:
                self.stderr.write(self.style.ERROR(f"Ошибка: {error}"))
            if not errors:
                self.stdout.write(self.style.SUCCESS("Цены обновлены"))

            # После обновления цен проверяем лимитные заявки (Этап 7)
            from trading.services import process_pending_limit_orders

            executed = process_pending_limit_orders()
            if executed:
                self.stdout.write(self.style.SUCCESS(f"Исполнено лимитных заявок: {executed}"))

            if not options["loop"]:
                break
            time.sleep(options["loop"])
