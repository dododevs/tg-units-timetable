from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes

from dotenv import load_dotenv
load_dotenv()

from datetime import date, datetime, timedelta
import os
import api
from persistence import Session, get_session
from utils import escape_markdown_message

async def select_faculty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    courses, faculties = api.get_all_courses_and_faculties()
    session: Session = get_session(update.effective_user.id)
    session.request_set_faculty()
    await update.message.reply_text(
        "Choose your faculty from the list",
        reply_markup=ReplyKeyboardMarkup(
            [[f["label"]] for f in faculties],
            one_time_keyboard=True,
            input_field_placeholder="Faculty?"
        )
    )

async def select_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    courses, faculties = api.get_all_courses_and_faculties()
    session: Session = get_session(update.effective_user.id)
    if not session.faculty:
        return await update.message.reply_text(
            "Select your /faculty first",
            reply_markup=ReplyKeyboardRemove()
        )
    session.request_set_course()
    await update.message.reply_text(
        "Choose your course from the list",
        reply_markup=ReplyKeyboardMarkup(
            [[f'{c["label"]} ({c["tipo"]})'] for c in courses if c["scuola"] == session.faculty["valore"]],
            one_time_keyboard=True,
            input_field_placeholder="Course?"
        )
    )

async def select_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session: Session = get_session(update.effective_user.id)
    if not session.course:
        return await update.message.reply_text(
            "Select your /course first",
            reply_markup=ReplyKeyboardRemove()
        )
    session.request_set_year()
    await update.message.reply_text(
        "Choose your year from the list",
        reply_markup=ReplyKeyboardMarkup(
            [[y["label"]] for y in session.course["elenco_anni"]],
            one_time_keyboard=True,
            input_field_placeholder="Year?"
        )
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session: Session = get_session(update.effective_user.id)
    session.reset_selections(reset_faculty=False, reset_course=False, reset_year=False)
    await update.message.reply_text("Cancelled, all good", reply_markup=ReplyKeyboardRemove())

def timetable(mode):
    async def tt(update: Update, context: ContextTypes.DEFAULT_TYPE):
        session: Session = get_session(update.effective_user.id)
        if not session.has_all_timetable_parameters():
            await update.message.reply_text(
                "Select your /faculty, /course and /year first",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            if mode == "tomorrow":
                tt = api.get_timetable(
                    (date.today() + timedelta(days=1)).strftime("%d-%m-%Y"),
                    session.faculty["valore"],
                    session.course["valore"],
                    session.year["valore"]
                )
            else:
                tt = api.get_timetable(
                    date.today().strftime("%d-%m-%Y"),
                    session.faculty["valore"],
                    session.course["valore"],
                    session.year["valore"]
                )
            if mode == "timetable":
                return await update.message.reply_markdown_v2(
                    "Get your lecture timetable for\n" + 
                    "\- right /now, at this very moment\n" +
                    "\- the entire day of /today\n" +
                    "\- the entire day of /tomorrow"
                )
            if mode == "today":
                now = datetime.now()
                lectures = [{
                    "time": (t["ora_inizio"], t["ora_fine"]),
                    "room": escape_markdown_message(t["aula"]),
                    "course": escape_markdown_message(t["nome_insegnamento"]),
                    "lecturer": escape_markdown_message(t["docente"]),
                    "cancelled": t["Annullato"] != "0",
                    "over": now > datetime.combine(date.today(), datetime.strptime(t["ora_fine"], "%H:%M").time())
                } for t in tt["celle"] if t["data"] == date.today().strftime("%d-%m-%Y")]
                if len(lectures) == 0:
                    return await update.message.reply_text("No lecture found for today")
            elif mode == "tomorrow":
                lectures = [{
                    "time": (t["ora_inizio"], t["ora_fine"]),
                    "room": escape_markdown_message(t["aula"]),
                    "course": escape_markdown_message(t["nome_insegnamento"]),
                    "lecturer": escape_markdown_message(t["docente"]),
                    "cancelled": t["Annullato"] != "0",
                    "over": False
                } for t in tt["celle"] if t["data"] == (date.today() + timedelta(days=1)).strftime("%d-%m-%Y")]
                if len(lectures) == 0:
                    return await update.message.reply_text("No lecture found for tomorrow")
            elif mode == "now":
                now = datetime.now()
                lectures = [{
                    "time": (t["ora_inizio"], t["ora_fine"]),
                    "room": t["aula"].replace("-", "\\-").replace(".", "\\."),
                    "course": t["nome_insegnamento"].replace("-", "\\-").replace(".", "\\."),
                    "lecturer": t["docente"].replace("-", "\\").replace(".", "\\."),
                    "cancelled": t["Annullato"] != "0",
                    "over": False
                } for t in tt["celle"] if t["data"] == date.today().strftime("%d-%m-%Y") and datetime.combine(date.today(), datetime.strptime(t["ora_inizio"], "%H:%M").time()) <= now <= datetime.combine(date.today(), datetime.strptime(t["ora_fine"], "%H:%M").time())]
                if len(lectures) == 0:
                    return await update.message.reply_text("No lecture found for right now")
            await update.message.reply_markdown_v2("\n\n".join([
                "\U0000274C" if lecture["cancelled"] else ("\U00002705" if lecture["over"] else "\U0001F449") + 
                f' {"Past" if lecture["over"] else "Planned"}{" cancelled" if lecture["cancelled"] else ""} lecture\n'
                f'{"~" if lecture["over"] or lecture["cancelled"] else ""}' +
                f'_*{lecture["course"]}*_\n' +
                f'\U0001F552 {lecture["time"][0]} \- {lecture["time"][1]}\n' +
                f'\U0001F4CD {lecture["room"]}{"~" if lecture["over"] or lecture["cancelled"] else ""}' for lecture in lectures
            ]))
    return tt

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    courses, faculties = api.get_all_courses_and_faculties()
    session: Session = get_session(update.effective_user.id)
    ret, msg = session.process(update, courses=courses, faculties=faculties)
    if ret:
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

app = Application.builder().token(os.environ["TELEGRAM_BOT_API_KEY"]).build()
app.add_handler(CommandHandler("cancel", cancel))
app.add_handler(CommandHandler("faculty", select_faculty))
app.add_handler(CommandHandler("course", select_course))
app.add_handler(CommandHandler("year", select_year))
app.add_handler(CommandHandler("timetable", timetable("timetable")))
app.add_handler(CommandHandler("today", timetable("today")))
app.add_handler(CommandHandler("tomorrow", timetable("tomorrow")))
app.add_handler(CommandHandler("now", timetable("now")))
app.add_handler(MessageHandler(None, message))
app.run_polling(allowed_updates=Update.ALL_TYPES)