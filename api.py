import requests_cache
import random
import string
import datetime
import dukpy

session = requests_cache.CachedSession('cache')

def request(method, endpoint, params):
    try:
        return session.request(method, f"https://orari.units.it/agendaweb/{endpoint}", params=params, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0",
            "Accept": "text/javascript, application/javascript, application/ecmascript, application/x-ecmascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://orari.units.it/agendaweb/index.php",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": f"unitscookieconsent-version=1.0.0; unitscookieconsent=0; unitscookieconsent-categories=%5B%5D; PHPSESSID={''.join([random.choice(string.ascii_lowercase) for _ in range(26)])}"
        })
    except Exception as e:
        print(f"Error in api request: {e!r}")
        return None

def get_all_courses_and_faculties():
    return dukpy.evaljs(request("GET", "combo.php", {
        "page": "corsi",
        "aa": datetime.date.today().year
    }).text + "; [elenco_corsi, elenco_scuole]")

def get_timetable(date, faculty, degree, course):
    return request("POST", "grid_call.php", {
        "view": "easycourse",
        "form-type": "corso",
        "include": "corso",
        "anno": str(datetime.date.today().year),
        "scuola": faculty,
        "corso": degree,
        "date": date,
        "txtcurr": [],
        "anno2": [course],
        "periodo_didattico": "",
        "_lang": ["it"],
        "list": "",
        "week_grid_type": "-1",
        "ar_codes": "",
        "ar_select_": "",
        "col_cells": "0",
        "empty_box": "0",
        "only_grid": "0",
        "highlighted_date": "0",
        "all_events": ["0", "0"],
        "faculty_group": "0",
        "visualizzazione_orario": "cal"
    }).json()


# c = courses[58]
# print(get_timetable("25-09-2023", c["scuola"], c["valore"], [
#     [a["valore"] for a in c["elenco_anni"]][0]
# ]))
courses, faculties = get_all_courses_and_faculties()