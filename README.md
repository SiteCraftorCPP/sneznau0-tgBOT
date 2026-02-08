# AN-26 Equipment Bot

Телеграм-бот по разделу оборудования AN-26 (4.1, 4.2, 4.3).

## Установка на VPS (Ubuntu/Debian)

```bash
# Установить Python 3 и pip (если нет)
apt update && apt install -y python3 python3-pip python3-venv

# Перейти в папку проекта
cd sneznau0-tgBOT

# Создать виртуальное окружение (рекомендуется)
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Настроить .env (токен бота, ID админа, пароль)
nano .env

# Создать БД и заполнить подразделы (4.1, 4.2, 4.3 — названия пунктов)
python3 -c "from database import create_tables; create_tables()"
python3 seed_subsections.py

# Запуск
python3 main.py
```

## Автозапуск (systemd) — бот всегда работает

На VPS после установки проекта:

```bash
cd ~/sneznau0-tgBOT
# Подключить юнит (путь к проекту — /root/sneznau0-tgBOT)
sudo cp an26bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable an26bot
sudo systemctl start an26bot
sudo systemctl status an26bot
```

Дальше бот:
- стартует при загрузке сервера;
- перезапускается при падении (Restart=always, через 5 сек);
- логи: `journalctl -u an26bot -f`

Если проект лежит не в `/root/sneznau0-tgBOT`, отредактируй пути в `an26bot.service` (WorkingDirectory и ExecStart) или создай юнит вручную с нужным путём.
