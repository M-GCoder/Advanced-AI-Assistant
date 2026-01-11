import speech_recognition as sr
import pyttsx3
import os
import subprocess
import pyautogui
import time
import psutil
import win32gui
import win32con
import win32com.client
from datetime import datetime

# Initialize text-to-speech engine
engine = pyttsx3.init('sapi5')
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)  # 0 = Male, 1 = Female (change if needed)
engine.setProperty('rate', 180)

def speak(text):
    print(f"Assistant: {text}")
    engine.say(text)
    engine.runAndWait()

def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        r.pause_threshold = 1
        r.energy_threshold = 400
        audio = r.listen(source, timeout=5, phrase_time_limit=10)

    try:
        print("Recognizing...")
        query = r.recognize_google(audio, language='en-in').lower()
        print(f"You said: {query}")         
    except Exception as e:
        speak("Sorry, I didn't catch that.")
        return "none"
    return query

# Windows-specific functions
def lock_windows():
    speak("Locking the computer")
    os.system("rundll32.exe user32.dll,LockWorkStation")

def shutdown():
    speak("Shutting down the computer")
    os.system("shutdown /s /t 1")

def restart():
    speak("Restarting the computer")
    os.system("shutdown /r /t 1")

def sleep_pc():
    speak("Putting computer to sleep")
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

def open_app(app_name):
    speak(f"Opening {app_name}")
    try:
        os.startfile(app_name)
    except:
        pyautogui.press('win')
        time.sleep(1)
        pyautogui.write(app_name)
        time.sleep(1)
        pyautogui.press('enter')

def switch_desktop(direction="next"):
    # Virtual Desktop switching using Ctrl + Win + Left/Right
    speak(f"Switching to {direction} desktop")
    pyautogui.hotkey('ctrl', 'win', 'right' if direction == "next" else 'left')

def volume_up():
    speak("Volume up")
    for _ in range(5): pyautogui.press('volumeup')

def volume_down():
    speak("Volume down")
    for _ in range(5): pyautogui.press('volumedown')

def mute():
    speak("Muting volume")
    pyautogui.press('volumemute')

def take_screenshot():
    speak("Taking screenshot")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pyautogui.screenshot(f"screenshot_{timestamp}.png")

def empty_recycle_bin():
    speak("Emptying recycle bin")
    try:
        import winshell 
        winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
        speak("Recycle bin emptied")
    except ImportError:
        speak("Please install winshell module")

def open_website(site):
    speak(f"Opening {site}")
    import webbrowser
    webbrowser.open(f"https://{site}.com")

# Main command processor
def process_command(query):
    query = query.lower()

    match query:
        case "lock":
            lock_windows()

        case "shutdown" :
            shutdown()

        case "restart":
            restart()

        case "sleep" | "hibernate":
            sleep_pc()

        case "open ":
            app = query.replace("open ", "").strip()
            # Common app mappings
            app_map = {
                "notepad": r"C:\Windows\system32\notepad.exe",
                "calculator": "calc",
                "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                "vscode": r"C:\Users\{}\AppData\Local\Programs\Microsoft VS Code\Code.exe".format(os.getlogin()),
                "paint": "mspaint",
                "command prompt": "cmd",
                "task manager": "taskmgr"
            }
            path = app_map.get(app, app)
            open_app(path)

        case "switch desktop" | "next desktop":
            switch_desktop("next")
        case "previous desktop":
            switch_desktop("previous")

        case "volume up":
            volume_up()
        case "volume down":
            volume_down()
        case "mute":
            mute()

        case "screenshot":
            take_screenshot()

        case "empty recycle bin"  :
            empty_recycle_bin()

        case "open youtube"  :
            open_website("youtube")
        case "open google"  :
            open_website("google")
        case "open github"  :
            open_website("github")

        case "exit"   | "quit"   | "bye"  :
            speak("Goodbye! Have a great day!")
            return False

        case _:
            speak("Sorry, I don't know that command yet.")
    
    return True

# Main loop
if __name__ == "__main__":
    speak("Voice Assistant Activated. Say 'Hey Assistant' to wake me up.")
    
    while True:
        query = listen().lower()

        if "hey assistant" or "hello assistant" or "wake up":
            speak("Yes, I'm here. How can I help you?")
            
            while True:
                query = listen()
                if process_command(query) == False:
                    break