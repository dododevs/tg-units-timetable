import os
import psycopg2
from telegram import Update
from ast import literal_eval

PG_DATABASE = os.environ["PG_DATABASE"]
PG_HOST = os.environ["PG_HOST"]
PG_PORT = os.environ["PG_PORT"]
PG_USER = os.environ["PG_USER"]
PG_PASSWORD = os.environ["PG_PASSWORD"]

print("[persistence] Connecting to database...")
db = psycopg2.connect(
    database=PG_DATABASE,
    host=PG_HOST,
    port=PG_PORT,
    user=PG_USER,
    password=PG_PASSWORD
)
cur = db.cursor()

sessions = {}

class Session:
    def __init__(self, chatid, faculty=None, course=None, year=None, is_setting_faculty=False, is_setting_course=False, is_setting_year=False):
        self.chatid = str(chatid)
        self.faculty = faculty
        self.course = course
        self.year = year
        self.is_setting_faculty = is_setting_faculty
        self.is_setting_course = is_setting_course
        self.is_setting_year = is_setting_year

    def reset_selections(self, reset_faculty=False, reset_course=False, reset_year=False):
        if reset_faculty:
            self.faculty = None
        if reset_course:
            self.course = None
        if reset_year:
            self.year = None
        self.is_setting_faculty = False
        self.is_setting_course = False
        self.is_setting_year = False

    def request_set_faculty(self):
        self.reset_selections(reset_faculty=True, reset_course=True)
        self.is_setting_faculty = True
        self.save()

    def request_set_course(self):
        self.reset_selections(reset_faculty=False, reset_course=True)
        self.is_setting_course = True
        self.save()

    def request_set_year(self):
        self.reset_selections(reset_faculty=False, reset_course=False, reset_year=True)
        self.is_setting_year = True
        self.save()

    def has_all_timetable_parameters(self):
        return self.faculty is not None and self.course is not None and self.year is not None

    def terminate(self, ret, msg):
        self.reset_selections(reset_faculty=False, reset_course=False, reset_year=False)
        self.save()
        return (ret, msg)

    def process(self, update: Update, **kwargs):
        courses = kwargs.get("courses")
        faculties = kwargs.get("faculties")
        text = update.message.text.strip()
        if str(update.effective_user.id) != self.chatid:
            return (False, )
        if not courses or not faculties:
            print("[w] courses or faculties null!")
            return (False, )
        if self.is_setting_faculty:
            if text not in [f["label"] for f in faculties]:
                return (True, "No such faculty")
            self.faculty = next(filter(lambda f: f["label"] == text, faculties))
            self.course = None
            self.year = None
            return self.terminate(True, "Good. Now you can set your /course")
        if self.is_setting_course:
            if not self.faculty:
                return (True, "Set your /faculty first")
            if text not in [f'{c["label"]} ({c["tipo"]})' for c in courses]:
                return (True, "No such course")
            c = next(filter(lambda c: f'{c["label"]} ({c["tipo"]})' == text, courses))
            if c["scuola"] != self.faculty["valore"]:
                return (True, "No such course in the faculty you selected")
            self.course = c
            self.year = None
            return self.terminate(True, "Good. Now you can set your /year")
        if self.is_setting_year:
            if not self.course:
                return (True, "Set your /course first")
            if text not in [y["label"] for y in self.course["elenco_anni"]]:
                return (True, "No such year")
            self.year = next(filter(lambda y: y["label"] == text, self.course["elenco_anni"]))
            return self.terminate(True, "Good. Now you can get your /timetable")

        return self.terminate(True, "What?")
    
    def save(self):
        cur.execute("INSERT INTO sessions (chatid, faculty, course, year, setting_faculty, setting_course, setting_year) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (chatid) DO UPDATE SET faculty = %s, course = %s, year = %s, setting_faculty = %s, setting_course = %s, setting_year = %s", (self.chatid, str(self.faculty), str(self.course), str(self.year), 1 if self.is_setting_faculty else 0, 1 if self.is_setting_course else 0, 1 if self.is_setting_year else 0, str(self.faculty), str(self.course), str(self.year), 1 if self.is_setting_faculty else 0, 1 if self.is_setting_course else 0, 1 if self.is_setting_year else 0))
        db.commit()

# print("[persistence] Dropping table (remove in production)...")
# cur.execute("DROP TABLE IF EXISTS sessions")

print("[persistence] Initializing database...")
cur.execute("CREATE TABLE IF NOT EXISTS sessions (chatid TEXT NOT NULL PRIMARY KEY, faculty TEXT, course TEXT, year TEXT, setting_faculty INTEGER NOT NULL DEFAULT 0, setting_course INTEGER NOT NULL DEFAULT 0, setting_year INTEGER NOT NULL DEFAULT 0)")
db.commit()

def retrieve_session(chatid):
    cur.execute("SELECT * FROM sessions WHERE chatid = %s", (str(chatid),))
    s = cur.fetchone()
    if not s:
        return None
    return Session(chatid, literal_eval(s[1]), literal_eval(s[2]), literal_eval(s[3]), s[4] == 1, s[5] == 1, s[6] == 1)

def get_session(chatid):
    if chatid not in sessions:
        sessions[chatid] = retrieve_session(chatid)
    if not sessions[chatid]:
        sessions[chatid] = Session(chatid)
    return sessions[chatid]