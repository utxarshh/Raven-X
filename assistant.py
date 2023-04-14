from __future__ import print_function

import datetime
import os.path
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import time
import pyttsx3
import speech_recognition as sr
import pytz
import subprocess
from googlesearch import search

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
BOT_TRIGGERS = ["hello", "hey", "hi","how are you"]
TERMINATE_TRIGGERS = ["shut down","close process","terminate"]
SEARCH_TRIGGERS = ["google","search for","look for"]
NOTE_TRIGGERS = ["take a note","open note","notepad","write","remember"]
CALENDAR_TRIGGERS = ["what do i have","schedule","plans","what am i doing","am i busy","am i free","what i have"]
MONTHS = ["january","february","march","april","may","june","july","august","september","october","november","december"]
DAYS = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
DAY_EXTENSIONS = ["st","nd","rd","th"]
asked_for_calendar=0

def speak(text):
    engine=pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def get_audio():
    r=sr.Recognizer()
    with sr.Microphone() as source:
        audio=r.listen(source)
        said=""

        try:
            said= r.recognize_google(audio)
            print(said)
        except Exception as e:
            print("Exception: "+str(e))
    return said


def authenticate_google():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    return service

def get_events(day,service):
        # Call the Calendar API
    date = datetime.datetime.combine(day,datetime.datetime.min.time())
    end_date = datetime.datetime.combine(day,datetime.datetime.max.time())
    utc= pytz.UTC
    date=date.astimezone(utc)
    end_date=end_date.astimezone(utc)
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    print('Getting the upcoming events')
    events_result = service.events().list(calendarId='primary', timeMin=date.isoformat(),timeMax=end_date.isoformat(),
                                            singleEvents=True,
                                            orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        speak('No upcoming events found.')
        return

        # Prints the start and name of the next n events
    for event in events:
        plural="events"
        if(len(events)==1):
            plural="event"
        speak(f'You have {len(events)} {plural} on this day.')
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])
        start_time = str(start.split("T")[1].split("-")[0])
        if int(start_time.split(":")[0]) < 12:
            if int(start_time.split(":")[0]) == 0:
                start_time = str(int(start_time.split(":")[0]+12)) + start_time.split(":")[1]
            start_time = start_time+"am"
        else:
            start_time = str(int(start_time.split(":")[0]-12)) + start_time.split(":")[1]
            start_time = start_time+"pm"
        
        speak(event["summmary"]+" at "+start_time)



def get_date(text):
    text=text.lower()
    today = datetime.date.today()

    if text.count("today")>0:
        return today
    if text.count("tomorrow")>0:
        return today+datetime.timedelta(1)
    if text.count("day after")>0:
        return today+datetime.timedelta(2)
    day=-1
    day_of_week=-1
    month=-1
    year=today.year

    for word in text.split():
        if word in MONTHS:
            month = MONTHS.index(word)+1
        elif word in DAYS:
            day_of_week=DAYS.index(word)
        elif word.isdigit():
            day = int(word)
        else:
            for ext in DAY_EXTENSIONS:
                found = word.find(ext)
                if found > 0:
                    try:
                        day=int(word[:found])
                    except:
                        pass
    
    if month<today.month and month != -1:
        year = year+1
    if day<today.day and month == -1 and day != -1:
        month = month+1
    if month == -1 and day == -1 and day_of_week != -1:
        current_day_of_week = today.weekday()
        dif = current_day_of_week-day_of_week
        if dif < 0:
            dif +=7
        if text.count("next")>=1:
            dif += 7
        return today+datetime.timedelta(dif)
    if month==-1 or day==-1:
        return None
    return datetime.date(day=day,month=month,year=year)


def get_note():
    date=datetime.datetime.now()
    file_name = str(date).replace(":","-")+"-note.txt"
    speak("What would you like me to take a note of?")
    note=get_audio().lower()
    with open(file_name,"w") as f:
        f.write(note)
    subprocess.Popen(["notepad.exe",file_name])


def make_search():
    speak("What would you like to search for?")
    query=get_audio().lower()
    speak(f"here are the top ten results for {query}")
    for i in search(query,tld='com',num=10, stop=10,pause=2):
        print(i)


SERVICE = authenticate_google()
speak("How can I help you")
text = get_audio().lower()

while True:

    for phrase in CALENDAR_TRIGGERS:
        if phrase in text:
            asked_for_calendar=1
            break
    if asked_for_calendar==1:
        asked_for_calendar=0
        date=get_date(text)
        if date:
            get_events(date,SERVICE)
        else:
            speak("i did not quite get that.")


    for phrase in NOTE_TRIGGERS:
        if phrase in text:
            get_note()
            speak("i made a note of that.")
            break

    for phrase in SEARCH_TRIGGERS:
        if phrase in text:
            make_search()
            break
    
    for phrase in TERMINATE_TRIGGERS:
        if phrase in text:
            quit()

    speak("i'm listening.")
    text = get_audio().lower()