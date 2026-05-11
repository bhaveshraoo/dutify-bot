# 🤖 DutyBot — Daily Duties Notification Reminder

A fully-featured Telegram bot for managing daily tasks, duties, and reminders — with tags, checklists, and smart scheduling. Powered by SQLite.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📋 Day-wise Checklist | View and check off tasks for any date |
| ➕ Add Tasks | Title, date, time, tag, reminder, notes |
| 🔔 Smart Reminders | Set X minutes before the task fires |
| 🏷️ Tags | Categorize tasks: #exam, #meeting, #work, etc. |
| 📚 Exam/Meeting List | Dedicated commands for grouped tag views |
| 📅 Any Date View | Browse tasks for past or future dates |
| 📊 Stats | Completion rates and tag breakdowns |
| 🗑️ Cleanup | Clear completed tasks from a day |
| 🔄 Auto-Restore | Reminders survive bot restarts |

---

## 🚀 Quick Setup

### 1. Clone / Download
```bash
git clone <your-repo>
cd duty_bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Create Your Bot
1. Open Telegram → search `@BotFather`
2. Send `/newbot`
3. Follow prompts → copy your **Bot Token**

### 4. Set Token
**Option A — Environment variable (recommended):**
```bash
export TELEGRAM_BOT_TOKEN="your_token_here"
```

**Option B — Edit config.py:**
```python
BOT_TOKEN = "your_token_here"
```

### 5. Run the Bot
```bash
python bot.py
```

---

## 📱 Commands Reference

| Command | Description |
|---|---|
| `/start` | Main menu |
| `/help` | Full command reference |
| `/today` | Today's checklist |
| `/tomorrow` | Tomorrow's checklist |
| `/add` | Start add-task wizard |
| `/date 25/12/2025` | View tasks for a specific date |
| `/exams` | All upcoming exam tasks |
| `/meetings` | All upcoming meeting tasks |
| `/tag <name>` | Tasks by any tag (e.g. `/tag work`) |
| `/stats` | Your task statistics |
| `/reminders` | View all pending reminders |
| `/done <id>` | Mark a task as complete |
| `/delete <id>` | Delete a task |
| `/cancel` | Cancel current operation |

---

## 🏷️ Available Tags

| Tag | Emoji | Tag | Emoji |
|---|---|---|---|
| exam | 📚 | meeting | 🤝 |
| work | 💼 | health | 🏥 |
| study | 📖 | gym | 💪 |
| family | 👨‍👩‍👧 | finance | 💰 |
| deadline | ⚠️ | travel | ✈️ |
| birthday | 🎂 | personal | 👤 |

You can also create **custom tags** during task creation!

---

## ⏰ Reminder Options

When adding a task, you can set a reminder (in minutes before the task):

- `5` → 5 minutes before
- `15` → 15 minutes before
- `30` → 30 minutes before
- `60` → 1 hour before
- `120` → 2 hours before
- `1440` → 1 day before
- Any custom number (1 – 10080 minutes)

---

## 📅 Date Formats Accepted

```
today           → current date
tomorrow        → next day
25/12/2025      → DD/MM/YYYY
25-12-2025      → DD-MM-YYYY
2025-12-25      → YYYY-MM-DD
25 Dec 2025     → DD Mon YYYY
```

## 🕐 Time Formats Accepted

```
14:30           → 24-hour
2:30 PM         → 12-hour with AM/PM
2:30PM          → no space
0930            → compact 24-hour
```

---

## 🗄️ Database Schema

SQLite database (`dutybot.db`) with 3 tables:

### `users`
| Column | Type | Description |
|---|---|---|
| user_id | INTEGER PK | Telegram user ID |
| name | TEXT | User's first name |
| created_at | TEXT | Registration time |
| timezone | TEXT | User timezone |

### `tasks`
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| user_id | INTEGER FK | Owner |
| title | TEXT | Task title |
| task_date | TEXT | YYYY-MM-DD |
| task_time | TEXT | HH:MM |
| tag | TEXT | Category tag |
| reminder_minutes | INTEGER | Minutes before to remind |
| notes | TEXT | Optional notes |
| completed | INTEGER | 0=pending, 1=done |

### `reminder_log`
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| task_id | INTEGER FK | Related task |
| sent_at | TEXT | When reminder was sent |
| status | TEXT | sent / failed |

---

## 🏗️ Project Structure

```
duty_bot/
├── bot.py          # Main bot logic, commands, handlers
├── database.py     # SQLite database layer
├── scheduler.py    # APScheduler reminder engine
├── config.py       # Token and settings
├── requirements.txt
├── README.md
└── dutybot.db      # Created automatically on first run
```

---

## 🔧 Advanced Configuration

Edit `config.py`:

```python
# Timezone
DEFAULT_TIMEZONE = "Asia/Kolkata"  # Change for your region

# Daily summary time
DAILY_SUMMARY_HOUR = 8    # 8 AM
DAILY_SUMMARY_MINUTE = 0
```

---

## 🐳 Docker (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV TELEGRAM_BOT_TOKEN=your_token_here
CMD ["python", "bot.py"]
```

```bash
docker build -t dutybot .
docker run -d --name dutybot -e TELEGRAM_BOT_TOKEN=xxx dutybot
```

---

## 🔁 Run as System Service (Linux)

Create `/etc/systemd/system/dutybot.service`:
```ini
[Unit]
Description=DutyBot Telegram Bot
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/duty_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
Environment=TELEGRAM_BOT_TOKEN=your_token_here

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable dutybot
sudo systemctl start dutybot
sudo systemctl status dutybot
```

---

## 📝 Notes

- The bot uses **polling** mode (no webhook needed)
- Reminders are **in-memory** (via APScheduler) and restored from DB on restart
- All times are stored in **local time** (default: Asia/Kolkata)
- SQLite supports concurrent reads fine for personal/small group bots