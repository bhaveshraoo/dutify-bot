#!/usr/bin/env python3
"""
DutyBot - Daily Duties Notification Reminder Bot
Features: Task management, tags, reminders, checklists, SQLite database
"""

import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
# hdeiuhiewuh
from database import Database
from scheduler import ReminderScheduler
from config import BOT_TOKEN, REMINDER_LEAD_TIMES

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
(
    WAITING_TASK_TITLE, WAITING_TASK_DATE, WAITING_TASK_TIME,
    WAITING_TASK_TAG, WAITING_REMINDER_TIME, WAITING_TASK_NOTES,
    WAITING_VIEW_DATE, WAITING_TAG_NAME
) = range(8)

db = Database()
scheduler = ReminderScheduler()


# ─────────────────────────── HELPERS ────────────────────────────

def format_task(task: dict, show_check: bool = True) -> str:
    status = "✅" if task["completed"] else "⬜"
    tag_emoji = get_tag_emoji(task.get("tag", ""))
    tag_str = f" {tag_emoji}#{task['tag']}" if task.get("tag") else ""
    time_str = task.get("task_time", "")
    reminder_str = ""
    if task.get("reminder_minutes"):
        reminder_str = f"\n   🔔 Reminder: {task['reminder_minutes']} min before"
    notes_str = ""
    if task.get("notes"):
        notes_str = f"\n   📝 {task['notes']}"
    prefix = f"{status} " if show_check else "📌 "
    return (
        f"{prefix}*{task['title']}*{tag_str}\n"
        f"   🕐 {time_str}{reminder_str}{notes_str}"
    )


def get_tag_emoji(tag: str) -> str:
    tag_emojis = {
        "exam": "📚", "exams": "📚",
        "meeting": "🤝", "meetings": "🤝",
        "work": "💼", "health": "🏥",
        "personal": "👤", "gym": "💪",
        "study": "📖", "family": "👨‍👩‍👧",
        "finance": "💰", "travel": "✈️",
        "birthday": "🎂", "deadline": "⚠️",
    }
    return tag_emojis.get(tag.lower(), "🏷️") if tag else ""


def parse_date(text: str) -> str | None:
    """Parse various date formats → YYYY-MM-DD"""
    formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y"]
    text = text.strip()
    # Shorthand: "today", "tomorrow"
    if text.lower() == "today":
        return datetime.now().strftime("%Y-%m-%d")
    if text.lower() == "tomorrow":
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_time(text: str) -> str | None:
    """Parse time → HH:MM"""
    formats = ["%H:%M", "%I:%M %p", "%I:%M%p", "%H%M", "%I %p", "%I%p"]
    text = text.strip()
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return None


def build_day_keyboard(tasks: list, date: str) -> InlineKeyboardMarkup:
    buttons = []
    for task in tasks:
        check = "✅" if task["completed"] else "⬜"
        buttons.append([InlineKeyboardButton(
            f"{check} {task['title'][:30]}",
            callback_data=f"toggle_{task['id']}_{date}"
        )])
    buttons.append([
        InlineKeyboardButton("➕ Add Task", callback_data=f"addtask_{date}"),
        InlineKeyboardButton("🗑 Clear Done", callback_data=f"cleardone_{date}"),
    ])
    buttons.append([InlineKeyboardButton("🔙 Main Menu", callback_data="mainmenu")])
    return InlineKeyboardMarkup(buttons)


def build_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Today", callback_data="today"),
            InlineKeyboardButton("📆 Tomorrow", callback_data="tomorrow"),
        ],
        [
            InlineKeyboardButton("🔍 Any Day", callback_data="anydate"),
            InlineKeyboardButton("➕ Add Task", callback_data="addtask_today"),
        ],
        [
            InlineKeyboardButton("📚 Exams List", callback_data="tag_exams"),
            InlineKeyboardButton("🤝 Meetings List", callback_data="tag_meetings"),
        ],
        [
            InlineKeyboardButton("🏷️ Browse Tags", callback_data="browse_tags"),
            InlineKeyboardButton("🔔 My Reminders", callback_data="my_reminders"),
        ],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
    ])


# ─────────────────────────── COMMANDS ────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.ensure_user(user.id, user.first_name)
    welcome = (
        f"👋 *Welcome, {user.first_name}!*\n\n"
        "I'm *DutyBot* — your personal daily duties organizer.\n\n"
        "📌 *What I can do:*\n"
        "• Add tasks with date, time & tags\n"
        "• Send reminders before your tasks\n"
        "• Day-wise checklists (check off tasks)\n"
        "• Tag tasks: #exam #meeting #work…\n"
        "• Quick view of all exams/meetings\n"
        "• Browse tasks for any date\n\n"
        "Use the menu below or type /help for commands."
    )
    await update.message.reply_text(
        welcome, parse_mode="Markdown",
        reply_markup=build_main_menu()
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *DutyBot Commands*\n\n"
        "*/start* — Main menu\n"
        "*/today* — Today's checklist\n"
        "*/tomorrow* — Tomorrow's checklist\n"
        "*/add* — Add a new task\n"
        "*/date DD/MM/YYYY* — View any day\n"
        "*/exams* — All upcoming exams\n"
        "*/meetings* — All upcoming meetings\n"
        "*/tag <tagname>* — Tasks by tag\n"
        "*/stats* — Your task statistics\n"
        "*/reminders* — View pending reminders\n"
        "*/done <id>* — Mark task complete\n"
        "*/delete <id>* — Delete a task\n\n"
        "📅 *Date formats:* today, tomorrow, 25/12/2025, 25-12-2025\n"
        "🕐 *Time formats:* 14:30, 2:30 PM, 0930\n"
        "🏷️ *Tags:* exam, meeting, work, health, gym, study, personal, family, finance, deadline…"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = datetime.now().strftime("%Y-%m-%d")
    await show_day_checklist(update, context, date, "Today")


async def tomorrow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    await show_day_checklist(update, context, date, "Tomorrow")


async def date_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        raw = " ".join(context.args)
        date = parse_date(raw)
        if date:
            label = datetime.strptime(date, "%Y-%m-%d").strftime("%A, %d %b %Y")
            await show_day_checklist(update, context, date, label)
        else:
            await update.message.reply_text("❌ Invalid date. Try: 25/12/2025 or 'tomorrow'")
    else:
        await update.message.reply_text("Usage: /date 25/12/2025")


async def exams_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_tag_list(update, context, "exam", "📚 Upcoming Exams")


async def meetings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_tag_list(update, context, "meeting", "🤝 Upcoming Meetings")


async def tag_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        tag = context.args[0].lstrip("#").lower()
        emoji = get_tag_emoji(tag)
        await show_tag_list(update, context, tag, f"{emoji} #{tag.title()} Tasks")
    else:
        await update.message.reply_text("Usage: /tag exam  or  /tag work")


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_stats(update, context)


async def reminders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    tasks = db.get_upcoming_tasks_with_reminders(uid)
    if not tasks:
        await update.message.reply_text("🔔 No upcoming reminders set.\n\nAdd tasks with /add")
        return
    lines = ["🔔 *Your Upcoming Reminders*\n"]
    for t in tasks[:15]:
        dt = f"{t['task_date']} {t['task_time']}"
        lines.append(
            f"• *{t['title']}* — {dt}\n"
            f"  🔔 {t['reminder_minutes']} min before"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            task_id = int(context.args[0])
            uid = update.effective_user.id
            db.toggle_task(task_id, uid)
            await update.message.reply_text("✅ Task marked as complete!")
        except (ValueError, Exception) as e:
            await update.message.reply_text(f"Error: {e}")
    else:
        await update.message.reply_text("Usage: /done <task_id>")


async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            task_id = int(context.args[0])
            uid = update.effective_user.id
            db.delete_task(task_id, uid)
            await update.message.reply_text("🗑️ Task deleted!")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")
    else:
        await update.message.reply_text("Usage: /delete <task_id>")


# ─────────────────────────── SHOW VIEWS ────────────────────────────

async def show_day_checklist(update, context, date: str, label: str):
    uid = update.effective_user.id
    tasks = db.get_tasks_by_date(uid, date)
    friendly = datetime.strptime(date, "%Y-%m-%d").strftime("%A, %d %b %Y")
    header = f"📋 *{label}* — {friendly}\n"
    if not tasks:
        text = header + "\n_No tasks yet for this day._\n\nTap ➕ to add one!"
    else:
        done = sum(1 for t in tasks if t["completed"])
        text = header + f"_Progress: {done}/{len(tasks)} done_\n\n"
        # Group by tag
        from collections import defaultdict
        grouped = defaultdict(list)
        for t in tasks:
            grouped[t.get("tag") or "General"].append(t)
        for group, gtasks in grouped.items():
            emoji = get_tag_emoji(group)
            text += f"\n{emoji} *{group.title()}*\n"
            for t in gtasks:
                status = "✅" if t["completed"] else "⬜"
                reminder = f" 🔔{t['reminder_minutes']}m" if t.get("reminder_minutes") else ""
                notes = f"\n    📝 _{t['notes']}_" if t.get("notes") else ""
                text += f"  {status} {t['title']} `[{t['task_time']}]`{reminder}{notes}\n"
                text += f"    _ID: {t['id']}_\n"

    msg = update.message if update.message else update.callback_query.message
    await msg.reply_text(
        text, parse_mode="Markdown",
        reply_markup=build_day_keyboard(tasks, date)
    )


async def show_tag_list(update, context, tag: str, title: str):
    uid = update.effective_user.id
    tasks = db.get_tasks_by_tag(uid, tag)
    if not tasks:
        text = f"{title}\n\n_No upcoming tasks with this tag._"
    else:
        text = f"{title}\n\n"
        # Group by date
        from collections import defaultdict
        by_date = defaultdict(list)
        for t in tasks:
            by_date[t["task_date"]].append(t)
        for date in sorted(by_date.keys()):
            friendly = datetime.strptime(date, "%Y-%m-%d").strftime("%a, %d %b %Y")
            text += f"\n📅 *{friendly}*\n"
            for t in by_date[date]:
                status = "✅" if t["completed"] else "⬜"
                text += f"  {status} {t['title']} — `{t['task_time']}`\n"
                if t.get("notes"):
                    text += f"    📝 _{t['notes']}_\n"
                text += f"    _ID: {t['id']}_\n"

    msg = update.message if update.message else update.callback_query.message
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Main Menu", callback_data="mainmenu")
    ]])
    await msg.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def show_stats(update, context):
    uid = update.effective_user.id
    stats = db.get_stats(uid)
    text = (
        "📊 *Your Task Statistics*\n\n"
        f"📝 Total tasks: *{stats['total']}*\n"
        f"✅ Completed: *{stats['completed']}*\n"
        f"⬜ Pending: *{stats['pending']}*\n"
        f"🔔 With reminders: *{stats['with_reminders']}*\n\n"
        "*By Tag:*\n"
    )
    for tag, count in stats.get("by_tag", {}).items():
        emoji = get_tag_emoji(tag)
        text += f"  {emoji} #{tag}: {count}\n"

    msg = update.message if update.message else update.callback_query.message
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Main Menu", callback_data="mainmenu")
    ]])
    await msg.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ─────────────────────────── ADD TASK CONVERSATION ────────────────────────────

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /add command"""
    try:
        logger.info(f"DEBUG: add_start called by user {update.effective_user.id}")
        logger.info(f"DEBUG: Clearing user_data")
        context.user_data.clear()
        logger.info(f"DEBUG: User_data cleared, now empty: {context.user_data}")

        msg = await update.effective_message.reply_text(
            "➕ *Add New Task*\n\nEnter the task title:",
            parse_mode="Markdown"
        )
        
        logger.info(f"DEBUG: Initial message sent with ID: {msg.message_id}")
        logger.info(f"DEBUG: Returning WAITING_TASK_TITLE (constant value = {WAITING_TASK_TITLE})")
        return WAITING_TASK_TITLE
    except Exception as e:
        logger.exception(f"ERROR in add_start: {str(e)}")
        try:
            await update.message.reply_text(f"⚠️ Error: {str(e)}")
        except:
            pass
        return ConversationHandler.END


async def got_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("--- DEBUG: I HAVE ENTERED GOT_TITLE ---")
    try:
        logger.info(f"DEBUG: got_title called")
        logger.info(f"DEBUG: Message text: {update.message.text if update.message else 'NO MESSAGE'}")
        logger.info(f"DEBUG: Update object: {update}")
        logger.info(f"DEBUG: Context user_data: {context.user_data}")
        
        if not update.message or not update.message.text:
            logger.error("DEBUG: No message or text!")
            await update.message.reply_text("Error: No message text received")
            return WAITING_TASK_TITLE
            
        context.user_data["title"] = update.message.text.strip()
        logger.info(f"DEBUG: Title saved: {context.user_data['title']}")
        
        # Simple reply
        msg = await update.message.reply_text("📅 What is the date? (e.g., today, tomorrow, or 25/12/2025)")
        logger.info(f"DEBUG: Reply sent with message ID: {msg.message_id}")
        logger.info(f"DEBUG: Transitioning to WAITING_TASK_DATE")
        return WAITING_TASK_DATE
        
    except Exception as e:
        logger.exception(f"ERROR in got_title: {str(e)}")
        try:
            await update.message.reply_text(f"⚠️ Error: {str(e)}")
        except:
            pass
        return ConversationHandler.END


async def got_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = parse_date(update.message.text)
    if not date:
        await update.message.reply_text("❌ Invalid date. Try: today, tomorrow, 25/12/2025")
        return WAITING_TASK_DATE
    context.user_data["date"] = date
    await update.message.reply_text(
        "🕐 Enter the time:\n_e.g. 14:30, 2:30 PM, 0930_",
        parse_mode="Markdown"
    )
    return WAITING_TASK_TIME


async def got_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time = parse_time(update.message.text)
    if not time:
        await update.message.reply_text("❌ Invalid time. Try: 14:30 or 2:30 PM")
        return WAITING_TASK_TIME
    context.user_data["time"] = time
    # Show tag options
    tag_buttons = [
        [
            InlineKeyboardButton("📚 Exam", callback_data="tag_exam"),
            InlineKeyboardButton("🤝 Meeting", callback_data="tag_meeting"),
            InlineKeyboardButton("💼 Work", callback_data="tag_work"),
        ],
        [
            InlineKeyboardButton("📖 Study", callback_data="tag_study"),
            InlineKeyboardButton("💪 Gym", callback_data="tag_gym"),
            InlineKeyboardButton("🏥 Health", callback_data="tag_health"),
        ],
        [
            InlineKeyboardButton("👨‍👩‍👧 Family", callback_data="tag_family"),
            InlineKeyboardButton("💰 Finance", callback_data="tag_finance"),
            InlineKeyboardButton("⚠️ Deadline", callback_data="tag_deadline"),
        ],
        [
            InlineKeyboardButton("✏️ Custom Tag", callback_data="tag_custom"),
            InlineKeyboardButton("⏭ Skip", callback_data="tag_none"),
        ],
    ]
    await update.message.reply_text(
        "🏷️ Select a tag for this task:",
        reply_markup=InlineKeyboardMarkup(tag_buttons)
    )
    return WAITING_TASK_TAG


async def got_tag_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "tag_custom":
        await query.edit_message_text("✏️ Enter your custom tag name:")
        return WAITING_TAG_NAME
    elif data == "tag_none":
        context.user_data["tag"] = None
    else:
        context.user_data["tag"] = data.replace("tag_", "")

    await query.edit_message_text(
        "🔔 How many minutes *before* the task do you want a reminder?\n\n"
        "_Enter a number, or type 'skip' for no reminder_",
        parse_mode="Markdown"
    )
    return WAITING_REMINDER_TIME


async def got_custom_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tag"] = update.message.text.strip().lower()
    await update.message.reply_text(
        "🔔 How many minutes *before* the task do you want a reminder?\n\n"
        "_Enter a number (e.g. 15, 30, 60), or type 'skip'_",
        parse_mode="Markdown"
    )
    return WAITING_REMINDER_TIME


async def got_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if text == "skip" or text == "0":
        context.user_data["reminder"] = None
    else:
        try:
            mins = int(text)
            if mins < 1 or mins > 10080:
                raise ValueError
            context.user_data["reminder"] = mins
        except ValueError:
            await update.message.reply_text("❌ Enter a number (1-10080) or 'skip'")
            return WAITING_REMINDER_TIME

    await update.message.reply_text(
        "📝 Add notes/description?\n_Type notes or 'skip' to finish_",
        parse_mode="Markdown"
    )
    return WAITING_TASK_NOTES


async def got_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() != "skip":
        context.user_data["notes"] = text
    else:
        context.user_data["notes"] = None

    return await save_task(update, context)


async def save_task(update, context):
    uid = update.effective_user.id
    data = context.user_data
    task_id = db.add_task(
        user_id=uid,
        title=data["title"],
        task_date=data["date"],
        task_time=data["time"],
        tag=data.get("tag"),
        reminder_minutes=data.get("reminder"),
        notes=data.get("notes"),
    )

    # Schedule reminder
    if data.get("reminder"):
        task_dt = datetime.strptime(f"{data['date']} {data['time']}", "%Y-%m-%d %H:%M")
        remind_at = task_dt - timedelta(minutes=data["reminder"])
        if remind_at > datetime.now():
            scheduler.schedule_reminder(
                context.application, uid, task_id,
                data["title"], remind_at, data["time"]
            )

    tag_str = f" #{data.get('tag', '')}" if data.get("tag") else ""
    reminder_str = f"\n🔔 Reminder: {data['reminder']} min before" if data.get("reminder") else ""
    notes_str = f"\n📝 {data['notes']}" if data.get("notes") else ""

    confirm = (
        f"✅ *Task Added!*\n\n"
        f"📌 *{data['title']}*{tag_str}\n"
        f"📅 {data['date']}\n"
        f"🕐 {data['time']}"
        f"{reminder_str}{notes_str}\n\n"
        f"_Task ID: {task_id}_"
    )
    await update.message.reply_text(
        confirm, parse_mode="Markdown",
        reply_markup=build_main_menu()
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Task creation cancelled.")
    else:
        await update.message.reply_text("❌ Cancelled.", reply_markup=build_main_menu())
    return ConversationHandler.END


# ─────────────────────────── CALLBACK HANDLERS ────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "mainmenu":
        await query.edit_message_text(
            "🏠 *Main Menu*\n\nChoose an option:",
            parse_mode="Markdown", reply_markup=build_main_menu()
        )

    elif data == "today":
        date = datetime.now().strftime("%Y-%m-%d")
        await show_day_from_callback(query, context, date, "Today")

    elif data == "tomorrow":
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        await show_day_from_callback(query, context, date, "Tomorrow")

    elif data == "anydate":
        await query.edit_message_text(
            "📅 Enter a date to view:\n_e.g. today, tomorrow, 25/12/2025_",
            parse_mode="Markdown"
        )
        context.user_data["awaiting_date_view"] = True

    elif data.startswith("toggle_"):
        parts = data.split("_")
        task_id = int(parts[1])
        date = parts[2]
        uid = query.from_user.id
        db.toggle_task(task_id, uid)
        await show_day_from_callback(query, context, date, "")

    elif data.startswith("cleardone_"):
        date = data.split("_", 1)[1]
        uid = query.from_user.id
        db.clear_completed_tasks(uid, date)
        await show_day_from_callback(query, context, date, "")

    elif data.startswith("addtask_"):
        date_hint = data.split("_", 1)[1]
        if date_hint == "today":
            context.user_data["prefill_date"] = datetime.now().strftime("%Y-%m-%d")
        elif date_hint == "tomorrow":
            context.user_data["prefill_date"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        # Trigger add flow via message
        await query.edit_message_text(
            "➕ *Add New Task*\n\nEnter the task title:",
            parse_mode="Markdown"
        )
        context.user_data["in_add_flow"] = True
        context.user_data["add_state"] = "title"

    elif data.startswith("tag_") and not data.startswith("tag_exam") and not data.startswith("tag_meeting"):
        # Tag filter
        tag = data.replace("tag_", "")
        emoji = get_tag_emoji(tag)
        uid = query.from_user.id
        tasks = db.get_tasks_by_tag(uid, tag)
        await show_tag_from_callback(query, tasks, f"{emoji} #{tag.title()} Tasks")

    elif data == "tag_exams":
        uid = query.from_user.id
        tasks = db.get_tasks_by_tag(uid, "exam")
        await show_tag_from_callback(query, tasks, "📚 Upcoming Exams")

    elif data == "tag_meetings":
        uid = query.from_user.id
        tasks = db.get_tasks_by_tag(uid, "meeting")
        await show_tag_from_callback(query, tasks, "🤝 Upcoming Meetings")

    elif data == "browse_tags":
        uid = query.from_user.id
        tags = db.get_user_tags(uid)
        if not tags:
            await query.edit_message_text(
                "🏷️ No tags found yet. Add tasks with tags first!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="mainmenu")
                ]])
            )
            return
        btns = []
        for tag in tags:
            emoji = get_tag_emoji(tag)
            btns.append([InlineKeyboardButton(
                f"{emoji} #{tag} ({db.count_tag(uid, tag)})",
                callback_data=f"tag_{tag}"
            )])
        btns.append([InlineKeyboardButton("🔙 Back", callback_data="mainmenu")])
        await query.edit_message_text(
            "🏷️ *Your Tags*\nSelect to view tasks:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    elif data == "my_reminders":
        uid = query.from_user.id
        tasks = db.get_upcoming_tasks_with_reminders(uid)
        if not tasks:
            text = "🔔 No reminders set yet."
        else:
            text = "🔔 *Upcoming Reminders*\n\n"
            for t in tasks[:10]:
                text += f"• *{t['title']}* — {t['task_date']} {t['task_time']}\n  🔔 {t['reminder_minutes']} min before\n\n"
        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="mainmenu")
            ]])
        )

    elif data == "stats":
        uid = query.from_user.id
        stats = db.get_stats(uid)
        text = (
            "📊 *Your Task Statistics*\n\n"
            f"📝 Total tasks: *{stats['total']}*\n"
            f"✅ Completed: *{stats['completed']}*\n"
            f"⬜ Pending: *{stats['pending']}*\n"
            f"🔔 With reminders: *{stats['with_reminders']}*\n\n"
            "*By Tag:*\n"
        )
        for tag, count in stats.get("by_tag", {}).items():
            emoji = get_tag_emoji(tag)
            text += f"  {emoji} #{tag}: {count}\n"
        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="mainmenu")
            ]])
        )


async def show_day_from_callback(query, context, date: str, label: str):
    uid = query.from_user.id
    tasks = db.get_tasks_by_date(uid, date)
    friendly = datetime.strptime(date, "%Y-%m-%d").strftime("%A, %d %b %Y")
    header = f"📋 *{label or friendly}* — {friendly}\n"
    if not tasks:
        text = header + "\n_No tasks yet for this day._"
    else:
        done = sum(1 for t in tasks if t["completed"])
        text = header + f"_Progress: {done}/{len(tasks)} done_\n\n"
        from collections import defaultdict
        grouped = defaultdict(list)
        for t in tasks:
            grouped[t.get("tag") or "General"].append(t)
        for group, gtasks in grouped.items():
            emoji = get_tag_emoji(group)
            text += f"\n{emoji} *{group.title()}*\n"
            for t in gtasks:
                status = "✅" if t["completed"] else "⬜"
                reminder = f" 🔔{t['reminder_minutes']}m" if t.get("reminder_minutes") else ""
                text += f"  {status} {t['title']} `[{t['task_time']}]`{reminder}\n"
                text += f"    _ID: {t['id']}_\n"

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=build_day_keyboard(tasks, date)
    )


async def show_tag_from_callback(query, tasks, title):
    if not tasks:
        text = f"{title}\n\n_No upcoming tasks with this tag._"
    else:
        text = f"{title}\n\n"
        from collections import defaultdict
        by_date = defaultdict(list)
        for t in tasks:
            by_date[t["task_date"]].append(t)
        for date in sorted(by_date.keys()):
            friendly = datetime.strptime(date, "%Y-%m-%d").strftime("%a, %d %b %Y")
            text += f"\n📅 *{friendly}*\n"
            for t in by_date[date]:
                status = "✅" if t["completed"] else "⬜"
                text += f"  {status} {t['title']} — `{t['task_time']}`\n"
                if t.get("notes"):
                    text += f"    📝 _{t['notes']}_\n"
                text += f"    _ID: {t['id']}_\n"

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Main Menu", callback_data="mainmenu")
        ]])
    )
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle free text for date view flow"""
    if context.user_data.get("awaiting_date_view"):
        context.user_data.pop("awaiting_date_view")
        date = parse_date(update.message.text)
        if date:
            label = datetime.strptime(date, "%Y-%m-%d").strftime("%A, %d %b %Y")
            await show_day_checklist(update, context, date, label)
        else:
            await update.message.reply_text("❌ Invalid date. Try: 25/12/2025 or 'tomorrow'")

async def universal_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clears progress and sends user back to the main menu"""
    context.user_data.clear() # Wipe the temporary task data
    
    text = "🚪 **Exit Successful.**\nTask creation discarded. Returning to Home..."
    
    # Send the main menu keyboard so they aren't stuck
    await update.message.reply_text(
        text, 
        parse_mode="Markdown",
        reply_markup=build_main_menu() 
    )
    
    return ConversationHandler.END # This kills the loop


# ─────────────────────────── MAIN ────────────────────────────

def main():
    # Python 3.14 requires explicit event loop setup
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    db.init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # Add task conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("add", add_start),
            CallbackQueryHandler(add_start, pattern="^addtask_")
        ],
        states={
            WAITING_TASK_TITLE: [
                MessageHandler(filters.TEXT, got_title),
            ],
            WAITING_TASK_DATE: [
                MessageHandler(filters.TEXT, got_date),
            ],
            WAITING_TASK_TIME: [
                MessageHandler(filters.TEXT, got_time),
            ],
            WAITING_TASK_TAG: [
                CallbackQueryHandler(got_tag_callback, pattern="^tag_"),
            ],
            WAITING_TAG_NAME: [
                MessageHandler(filters.TEXT, got_custom_tag),
            ],
            WAITING_REMINDER_TIME: [
                MessageHandler(filters.TEXT, got_reminder),
            ],
            WAITING_TASK_NOTES: [
                MessageHandler(filters.TEXT, got_notes),
            ],
            WAITING_TASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(exit|Exit|EXIT)$"), got_title)],
            WAITING_TASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(exit|Exit|EXIT)$"), got_date)],
            WAITING_TASK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(exit|Exit|EXIT)$"), got_time)],
            # ... apply to all text-input states
        },
        fallbacks=[
            CommandHandler("cancel", cancel_add),
            CallbackQueryHandler(cancel_add, pattern="^cancel_add$"),
            MessageHandler(filters.Regex("^(exit|Exit|EXIT)$"), universal_exit),
            CommandHandler("cancel", universal_exit)
        ],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("today", today_cmd))
    app.add_handler(CommandHandler("tomorrow", tomorrow_cmd))
    app.add_handler(CommandHandler("date", date_cmd))
    app.add_handler(CommandHandler("exams", exams_cmd))
    app.add_handler(CommandHandler("meetings", meetings_cmd))
    app.add_handler(CommandHandler("tag", tag_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("reminders", reminders_cmd))
    app.add_handler(CommandHandler("done", done_cmd))
    app.add_handler(CommandHandler("delete", delete_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    async def debug_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Debug handler to log all updates"""
        logger.info(f"DEBUG: Unhandled message received from {update.effective_user.id}: {update.message.text if update.message else 'no message'}")
        
    app.add_handler(MessageHandler(filters.ALL, debug_handler))

    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Exception while handling an update: {context.error}")
        
    app.add_error_handler(error_handler)

    logger.info("🤖 DutyBot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
