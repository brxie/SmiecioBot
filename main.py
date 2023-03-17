import datetime
import logging
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

username = getenv("FB_EMAIL")
password = getenv("FB_PASSWORD")
threadId = getenv("THREAD_ID")
debug = getenv("DEBUG", 'false').lower() in ('true', '1', 't')
visible = getenv("UI", 'false').lower() in ('true', '1', 't')
trigger_message_time = getenv("TRIGGER_TIME", "16:00")

ICS_URL = "https://p71-caldav.icloud.com/published/2/MTg0MjE0MzQ0MzE4NDIxNPUuBwTTG2rEEZaB3IqTt-sjB3X-WT2A4qKi9Upx_iZEhgNqVDvPAFRp_3Py3PMMOlEMlZphzr4aBaBde3jzqm0"
COOKIE_BUTTON_XPATH = "//button[@ data-cookiebanner='accept_only_essential_button']"
MESSAGE_TEXT_XPATH = "//div[@aria-label='Wiadomość']"

display = Display(visible=visible)
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
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
        chrome_driver.find_element(By.ID, "email").send_keys(username)
        chrome_driver.find_element(By.ID, "pass").send_keys(password)
        chrome_driver.find_element(By.NAME, "login").click()
    except (NoSuchElementException, TimeoutException):
        logging.exception("failed to login")


def send_message(msg):
    timeout = 300
    chrome_driver.get("https://www.facebook.com/messages/t/" + threadId)
    try:
        WebDriverWait(chrome_driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, MESSAGE_TEXT_XPATH))
        )
    except TimeoutException:
        logging.exception("failed to send message")

    message_field = chrome_driver.find_element(By.XPATH, MESSAGE_TEXT_XPATH)
    for m in msg:
        message_field.send_keys(m)
        message_field.send_keys(Keys.SHIFT, Keys.ENTER)
    message_field.send_keys(Keys.ENTER)

def download_ics():
    logging.info("downloading ics...")
    try:
        f = urlopen(ICS_URL)
    except Exception:
        logging.exception("error loading ics")
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
        fb_msg = ["Tutaj SmiecioBot ♻"]
        fb_msg.append("Wystaw na jutro ☀️ (%s): " % (
            weekDaysPL[events[0]["dtstart"].isoweekday()]
        ))
        for i, evt in enumerate(events):
            evt_text = "➡ %s" % (evt["summary"])
            if evt["description"] is not None:
                evt_text += " (%s)" % evt["description"]
            fb_msg.append(evt_text)

        logging.info("sending message: '%s'" % " ".join(str(x) for x in fb_msg))
        send_message(fb_msg)
    else:
        logging.info("no events today")


if __name__ == "__main__":
    ics = None
    while ics is None:
        ics = download_ics()
        if ics is not None:
            break
        sleep(10)

    login()

    if debug: trigger_message(ics)

    schedule.every().day.at(trigger_message_time).do(trigger_message, ics)
    logging.info("SmiecioBot started!")

    while True:
        schedule.run_pending()
        sleep(60)
