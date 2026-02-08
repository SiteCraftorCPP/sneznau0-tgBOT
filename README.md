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

# Создать БД при первом запуске
python3 -c "from database import create_tables; create_tables()"

# Запуск
python3 main.py
```

## Запуск в фоне (screen или systemd)

**Через screen:**
```bash
screen -S bot
source venv/bin/activate
python3 main.py
# Ctrl+A, D — отключиться; screen -r bot — вернуться
```

**Через systemd** — создать `/etc/systemd/system/an26bot.service`:
```ini
[Unit]
Description=AN-26 Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/sneznau0-tgBOT
ExecStart=/root/sneznau0-tgBOT/venv/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload
systemctl enable an26bot
systemctl start an26bot
systemctl status an26bot
```
