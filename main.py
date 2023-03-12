from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from time import sleep
from selenium.webdriver.common.keys import Keys
from urllib.request import urlopen
from urllib.error import HTTPError
from icalendar import Calendar
import datetime
from pyvirtualdisplay import Display
from threading import Thread
import schedule
from os import getenv


usernam = getenv('FB_EMAIL')
password = getenv('FB_PASSWORD')
threadId = getenv('THREAD_ID')
trigger_message_time = getenv('TRIGGER_TIME', "12:00")
dry_run = False

ics_url = "https://p71-caldav.icloud.com/published/2/MTg0MjE0MzQ0MzE4NDIxNPUuBwTTG2rEEZaB3IqTt-sjB3X-WT2A4qKi9Upx_iZEhgNqVDvPAFRp_3Py3PMMOlEMlZphzr4aBaBde3jzqm0"
cookie_button_xpath = "//button[@ data-cookiebanner='accept_only_essential_button']"
message_text_xpath = "//div[@aria-label='Wiadomość']"

display = Display(visible=0, size=(800, 600))
display.start()

chrome_driver = webdriver.Chrome()

weekDaysPL = ("","poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela")

def login():
    chrome_driver.get('https://www.facebook.com/')
    try:
        chrome_driver.find_element("xpath", cookie_button_xpath).click()
    except NoSuchElementException as e:
        pass    
    
    try:
        chrome_driver.find_element("xpath", cookie_button_xpath).click()
        chrome_driver.find_element("id", "email").send_keys(usernam)
        chrome_driver.find_element("id", 'pass').send_keys(password)
        chrome_driver.find_element("name", "login").click()
        sleep(5)
    except NoSuchElementException as e:
        print("failed to login %s" % e)    

def send_message(msg):
    try:
        chrome_driver.get('https://www.facebook.com/messages/t/'+threadId)
        sleep (60)
        chrome_driver.find_element("xpath", message_text_xpath).send_keys(msg, Keys.ENTER)
    except NoSuchElementException as e:
        print("%s: failed to send message: %s" % (datetime.datetime.now(), e))

def download_ics():
    print("%s: downloading ics..." % (datetime.datetime.now()))
    try: 
        f = urlopen(ics_url)
    except Exception as e:
        print("error loading ics, %s" % e)
        return
    else:
        return f.read()
            

def lookup_events(cal):
    events = []
    for component in cal.walk():
        if component.name == "VEVENT":
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            startdt = component.get('dtstart').dt
            if startdt.strftime("%m/%d/%Y") == tomorrow.strftime("%m/%d/%Y"):
                events.append({
                    "dtstart": startdt,
                    "summary": component.get('summary'),
                    "description": component.get('description')
                })
    return events

def trigger_message(ics):
    cal = Calendar().from_ical(ics)
    events = lookup_events(cal)
    if events:
        fb_msg_prefix = "SmiecioBot ♻ > przygotuj na jutro (%s): " % (weekDaysPL[events[0]["dtstart"].isoweekday()])
        msg_suffix = ""
        for i, evt in enumerate(events):
            if i > 0:
                msg_suffix += ", "    
            msg_suffix += evt["summary"]
            if evt["description"] is not None:
                msg_suffix += " (%s)" % evt["description"]

        fb_msg = fb_msg_prefix + msg_suffix + ". Dziękuję"
        print("%s: sending message: '%s'" % (datetime.datetime.now(), fb_msg))
        if not dry_run:
            send_message(fb_msg)
    else:
        print("%s: no events today" % datetime.datetime.now())

if __name__ == "__main__":
    ics = None
    while ics == None:
        ics = download_ics()
        if ics != None:
            break
        sleep(10)

    login()

    schedule.every().day.at(trigger_message_time).do(trigger_message, ics)
    print("%s: SmiecioBot started!" % (datetime.datetime.now()))

    while True:
        schedule.run_pending()
        sleep(60)