import datetime
from os import getenv
from threading import Thread
from time import sleep
from urllib.error import HTTPError
from urllib.request import urlopen

import schedule
from icalendar import Calendar
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

usernam = getenv("FB_EMAIL")
password = getenv("FB_PASSWORD")
threadId = getenv("THREAD_ID")
trigger_message_time = getenv("TRIGGER_TIME", "16:00")
DRY_RUN = False

ICS_URL = "https://p71-caldav.icloud.com/published/2/MTg0MjE0MzQ0MzE4NDIxNPUuBwTTG2rEEZaB3IqTt-sjB3X-WT2A4qKi9Upx_iZEhgNqVDvPAFRp_3Py3PMMOlEMlZphzr4aBaBde3jzqm0"
COOKIE_BUTTON_XPATH = "//button[@ data-cookiebanner='accept_only_essential_button']"
MESSAGE_TEXT_XPATH = "//div[@aria-label='Wiadomość']"

display = Display(visible=0, size=(800, 600))
display.start()

chrome_driver = webdriver.Chrome()

weekDaysPL = (
    "",
    "poniedziałek",
    "wtorek",
    "środa",
    "czwartek",
    "piątek",
    "sobota",
    "niedziela",
)


def login():
    chrome_driver.get("https://www.facebook.com/")
    timeout = 60
    try:
        WebDriverWait(chrome_driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, COOKIE_BUTTON_XPATH))
        )
        chrome_driver.find_element(By.XPATH, COOKIE_BUTTON_XPATH).click()
    except TimeoutException:
        pass

    try:
        WebDriverWait(chrome_driver, timeout).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        chrome_driver.find_element(By.ID, "email").send_keys(usernam)
        chrome_driver.find_element(By.ID, "pass").send_keys(password)
        chrome_driver.find_element(By.NAME, "login").click()
    except (NoSuchElementException, TimeoutException) as e:
        print("failed to login %s" % e)


def send_message(msg):
    timeout = 300
    chrome_driver.get("https://www.facebook.com/messages/t/" + threadId)
    try:
        WebDriverWait(chrome_driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, MESSAGE_TEXT_XPATH))
        )
        chrome_driver.find_element(By.XPATH, MESSAGE_TEXT_XPATH).send_keys(
            msg, Keys.ENTER
        )
    except TimeoutException as e:
        print("%s: failed to send message: %s" % (datetime.datetime.now(), e))


def download_ics():
    print("%s: downloading ics..." % (datetime.datetime.now()))
    try:
        f = urlopen(ICS_URL)
    except Exception as e:
        print("error loading ics, %s" % e)
        return
    return f.read()


def lookup_events(cal):
    events = []
    for component in cal.walk():
        if component.name == "VEVENT":
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            startdt = component.get("dtstart").dt
            if startdt.strftime("%m/%d/%Y") == tomorrow.strftime("%m/%d/%Y"):
                events.append(
                    {
                        "dtstart": startdt,
                        "summary": component.get("summary"),
                        "description": component.get("description"),
                    }
                )
    return events


def trigger_message(ics):
    cal = Calendar().from_ical(ics)
    events = lookup_events(cal)
    if events:
        fb_msg_prefix = "SmiecioBot ♻ > przygotuj na jutro (%s): " % (
            weekDaysPL[events[0]["dtstart"].isoweekday()]
        )
        msg_suffix = ""
        for i, evt in enumerate(events):
            if i > 0:
                msg_suffix += ", "
            msg_suffix += evt["summary"]
            if evt["description"] is not None:
                msg_suffix += " (%s)" % evt["description"]

        fb_msg = fb_msg_prefix + msg_suffix + ". Dziękuję"
        print("%s: sending message: '%s'" % (datetime.datetime.now(), fb_msg))
        if not DRY_RUN:
            send_message(fb_msg)
    else:
        print("%s: no events today" % datetime.datetime.now())


if __name__ == "__main__":
    ics = None
    while ics is None:
        ics = download_ics()
        if ics is not None:
            break
        sleep(10)

    login()

    schedule.every().day.at(trigger_message_time).do(trigger_message, ics)
    print("%s: SmiecioBot started!" % (datetime.datetime.now()))

    while True:
        schedule.run_pending()
        sleep(60)
