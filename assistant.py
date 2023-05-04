from __future__ import print_function

import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import pyttsx3
import speech_recognition as sr
import pytz
import subprocess
from googlesearch import search
import platform
import warnings
import openai
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
import requests


warnings.filterwarnings('ignore')
openai.api_key='Enter own'

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
DAY_TRIGGERS=["day is it"]
DATE_TRIGGERS=["is the date","date is it"]
TIME_TRIGGERS=["what is the time","give me the time","the time"]
BOT_TRIGGERS = ["hello", "hey", "hi","how are you"]
TERMINATE_TRIGGERS = ["shutdown","close process","terminate", "close","quit", "okay", "thank you"]
SEARCH_TRIGGERS = ["google","search for","look for"]
NOTE_TRIGGERS = ["take a note","open note","notepad","write","remember","note"]
CALENDAR_TRIGGERS = ["what do i have","schedule","plans","what am i doing","am i busy","am i free","what i have"]
MONTHS = ["january","february","march","april","may","june","july","august","september","october","november","december"]
DAYS = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
SPOTIFY_TRIGGERS = ["play", "listen to", "stream", "start","spotify","song"]
WEATHER_TRIGGERS = ["weather", "temperature", "wind", "climate"]
DAY_EXTENSIONS = ["st","nd","rd","th"]
asked_for_calendar=0
#message list to pass to openai model
messages = [{"role": "system", "content": 'You are a useful virtual assistant. Act as if you were a good helpful friend'}]

def ask_gpt(text):
    prompt = f"{text}"
    response = openai.ChatCompletion.create(
        model="text-davinci-003",
        prompt=prompt,
        temperature=0.5,
        max_tokens=60,
        top_p=0.3,
        frequency_penalty=0.5,
        presence_penalty=0.0
    )
    system_message = response["choices"][0]["text"]
    messages.append(system_message)
    print(system_message)
    speak(str(system_message))

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
            print("")
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


def get_the_time():
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M")
    return current_time

def get_the_day():
    today=datetime.datetime.today()
    day = today.weekday()
    return DAYS[day] 


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


def get_note(sys_flag):
    date=datetime.datetime.now()
    file_name = str(date).replace(":","-")+"-note.txt"
    speak("What would you like me to take a note of?")
    note=get_audio().lower()
    with open(file_name,"w") as f:
        f.write(note)    
    if sys_flag==0:
        subprocess.Popen(["notepad.exe",file_name])
    else:
        subprocess.Popen(["/Applications/TextEdit.app/Contents/MacOS/TextEdit",file_name])


def make_search():
    speak("What would you like to search for?")
    query=get_audio().lower()
    speak(f"here are the top ten results for {query}")
    for i in search(query,tld='com',num=10, stop=10,pause=2):
        print(i)

def play_music(track_name):
    for trigger in SPOTIFY_TRIGGERS:
        track_name = track_name.replace(f'{trigger}','')
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id="Enter own",
                                                   client_secret="Enter own",
                                                   redirect_uri="http://localhost:8000",
                                                   scope="user-read-playback-state,user-modify-playback-state"))
    results = sp.search(q=track_name, type='track')
    if results['tracks']['items']:
        speak(f"now playing {track_name}")
        track_uri = results['tracks']['items'][0]['uri']
        sp.start_playback(uris=[track_uri])
        print(f"Now playing: {results['tracks']['items'][0]['name']} by {results['tracks']['items'][0]['artists'][0]['name']}")
    else:
        print(f"No tracks found matching the name {track_name}")


def get_weather():
    # set up API endpoint and parameters
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": "Bhubaneswar, Odisha",
        "appid": "Enter own",
        "units": "metric"
    }
    
    # send GET request to API endpoint
    response = requests.get(url, params=params)
    
    # check if response is successful (status code 200)
    if response.status_code == 200:
        # extract weather information from response JSON
        data = response.json()
        description = data["weather"][0]["description"]
        temperature = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        
        # format and return weather information as text
        weather_text = f"The current weather in Bhubaneswar, Odisha is {description}, with a temperature of {temperature:.1f}°C (feels like {feels_like:.1f}°C), humidity of {humidity}% and wind speed of {wind_speed} meter per second."
        speak(weather_text)
    else:
        # print error message with status code and reason
        error_text = f"HTTP Error {response.status_code}: {response.reason}"
        print(error_text)
        speak("Sorry, I couldn't retrieve the weather information at this time.")

sys_flag=0
op_sys=platform.platform()
if "mac" in op_sys:
    sys_flag=1
SERVICE = authenticate_google()
speak("How can I help you")
text = get_audio().lower()
while True:
    triggered=0
    for phrase in CALENDAR_TRIGGERS:
        if phrase in text:
            triggered=1
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
            triggered=1
            get_note(sys_flag)
            speak("i made a note of that.")
            break

    for phrase in SEARCH_TRIGGERS:
        if phrase in text:
            triggered=1
            make_search()
            break
    
    for phrase in WEATHER_TRIGGERS:
        if phrase in text:
            get_weather()
            break

    for phrase in BOT_TRIGGERS:
        if phrase in text:
            ask_gpt(text)
            break
    for phrase in SPOTIFY_TRIGGERS:
        if phrase in text:
            subprocess.Popen(["spotify.exe"])
            play_music(text)
            break
    for phrase in TERMINATE_TRIGGERS:
        if phrase in text:
            quit()
    

    listening_prompts = ["I'm all ears.","Listening carefully.","I'm here, what can I help you with?","Go ahead, I'm listening.","What would you like to ask me?","Speak your mind, I'm listening.","Tell me what's on your mind.","I'm ready when you are.","How can I assist you?","I'm here to listen.","Raven is waiting for you, speak up"]

    # start listening loop
    while True:
        # select a random listening prompt from the list
        prompt = random.choice(listening_prompts)
        speak(prompt)

        
        text = get_audio().lower()