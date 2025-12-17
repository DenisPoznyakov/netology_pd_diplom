#!/usr/bin/env python
"""
Утилита командной строки Django для административных задач.

Этот файл является точкой входа для команд manage.py:
- python manage.py runserver — запуск сервера разработки
- python manage.py migrate — применение миграций
- python manage.py test — запуск тестов
- python manage.py createsuperuser — создание администратора
и других команд Django.

Проект использует модуль настроек netology_pd_diplom.settings.
"""
import os
import sys


def main():
    """
    Основная функция запуска утилиты Django.

    Устанавливает переменную окружения DJANGO_SETTINGS_MODULE
    и выполняет команду, переданную через аргументы командной строки.
    """
    # Указываем Django, где искать настройки проекта
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netology_pd_diplom.settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Не удалось импортировать Django. Убедитесь, что Django установлен и "
            "доступен в переменной окружения PYTHONPATH. "
            "Возможно, вы забыли активировать виртуальное окружение?"
        ) from exc

    # Запускаем переданную команду (например, runserver, migrate, test и т.д.)
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()