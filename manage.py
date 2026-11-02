#!/usr/bin/env python
#Строка выше позволяет проще запустить скрипт (файл) из консоли, игнорируется в Windows

import os #Для работы с ОС (конкретно сейчас для задания переменной окружения)
import sys #Дает Django доступ к аргументам терминала

def main():
    #Очень важная строка
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    #DJANGO_SETTINGS_MODULE - переменная, которая говорит
    #Django идти по пути config.settings когда понадобятся настройки
    #А .setdeafault установит аргументы как значения по умолчанию

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc

    execute_from_command_line(sys.argv) #Из import sys мы передаем Django команды из терминала

if __name__ == "__main__":
    main()