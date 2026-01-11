import face_recognition
import cv2
import numpy as np
import os
import pickle
import speech_recognition as sr
import pyttsx3
import pyautogui
import time
import os
import win32com.client
from datetime import datetime

# ============================
# CONFIGURATION
# ============================
KNOWN_FACES_DIR = "known_faces"  # Folder where your face will be saved
ENCODINGS_FILE = "face_encodings.pickle"
TOLERANCE = 0.5  # Lower = stricter (0.4–0.6 is good)
FRAME_THICKNESS = 3
FONT_THICKNESS = 2
MODEL = "hog"  # Use "cnn" for more accuracy (slower), "hog" for speed

# Initialize TTS
engine = pyttsx3.init('sapi5')
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)  # Female voice
engine.setProperty('rate', 180)

def speak(text):
    print(f"Assistant: {text}")
    engine.say(text)
    engine.runAndWait()

# ============================
# FACE RECOGNITION FUNCTIONS
# ============================
def save_known_face():
    if not os.path.exists(KNOWN_FACES_DIR):
        os.makedirs(KNOWN_FACES_DIR)

    speak("Face registration mode. Look at the camera.")
    video = cv2.VideoCapture(0)
    time.sleep(2)

    print("Taking your photo for registration...")
    speak("Smile! Taking your photo in 3 seconds")

    time.sleep(3)
    ret, frame = video.read()
    if not ret:
        speak("Camera error!")
        return False

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    boxes = face_recognition.face_locations(rgb_frame, model=MODEL)
    
    if len(boxes) == 0:
        speak("No face detected. Try again.")
        video.release()
        return False

    encoding = face_recognition.face_encodings(rgb_frame, boxes)[0]

    # Save encoding
    data = {"name": "owner", "encoding": encoding}
    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump([data], f)

    cv2.putText(frame, "REGISTERED!", (50, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Registration Complete", frame)
    cv2.waitKey(3000)
    cv2.destroyAllWindows()
    video.release()

    speak("Face registered successfully! You can now use face login.")
    return True

def load_known_faces():
    if not os.path.exists(ENCODINGS_FILE):
        return None
    with open(ENCODINGS_FILE, "rb") as f:
        known_faces = pickle.load(f)
    return known_faces

def recognize_face():
    if not os.path.exists(ENCODINGS_FILE):
        speak("No registered face found. Starting first-time registration...")
        if not save_known_face():
            return False
        return recognize_face()  # Retry after registration

    known_faces = load_known_faces()
    if not known_faces:
        speak("Error loading face data.")
        return False

    known_encodings = [face["encoding"] for face in known_faces]
    known_names = [face["name"] for face in known_faces]

    speak("Face login activated. Look at the camera.")
    video = cv2.VideoCapture(0)
    time.sleep(1)

    start_time = time.time()
    authenticated = False

    while time.time() - start_time < 15:  # 15 seconds max
        ret, frame = video.read()
        if not ret:
            continue

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb_frame, model=MODEL)
        encodings = face_recognition.face_encodings(rgb_frame, locations)

        for face_encoding, face_location in zip(encodings, locations):
            results = face_recognition.compare_faces(known_encodings, face_encoding, TOLERANCE)
            if True in results:
                name = known_names[results.index(True)]
                top, right, bottom, left = face_location
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), FRAME_THICKNESS)
                cv2.putText(frame, "ACCESS GRANTED", (left, bottom + 30),
                            cv2.FONT_HERSHEY_COMPLEX, 0.8, (0, 255, 0), FONT_THICKNESS)
                authenticated = True
            else:
                top, right, bottom, left = face_location
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), FRAME_THICKNESS)
                cv2.putText(frame, "UNKNOWN", (left, bottom + 30),
                            cv2.FONT_HERSHEY_COMPLEX, 0.8, (0, 0, 255), FONT_THICKNESS)

        cv2.imshow("Face Login - Look Here", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        if authenticated:
            video.release()
            cv2.destroyAllWindows()
            speak("Welcome back! Face recognized. Voice assistant activated.")
            return True

    video.release()
    cv2.destroyAllWindows()
    speak("Face not recognized. Access denied.")
    return False

# ============================
# YOUR ORIGINAL VOICE COMMANDS (same as before)
# ============================
def lock_windows():
    speak("Locking Windows")
    os.system("rundll32.exe user32.dll,LockWorkStation")

def open_app(app_name):
    speak(f"Opening {app_name}")
    pyautogui.press('win')
    time.sleep(1)
    pyautogui.write(app_name)
    time.sleep(1)
    pyautogui.press('enter')

def switch_desktop(direction="next"):
    speak(f"Switching to {direction} desktop")
    pyautogui.hotkey('ctrl', 'win', 'right' if direction == "next" else 'left')

# Add more from previous code if needed...

def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        r.pause_threshold = 1
        audio = r.listen(source, timeout=5, phrase_time_limit=8)
    try:
        query = r.recognize_google(audio, language='en-in').lower()
        print(f"You: {query}")
        return query
    except:
        return "none"

def process_command(query):
    if "lock" in query:
        lock_windows()
    elif "open " in query:
        app = query.replace("open ", "")
        open_app(app)
    elif "next desktop" in query:
        switch_desktop("next")
    elif "previous desktop" in query:
        switch_desktop("previous")
    elif "exit" in query or "bye" in query:
        speak("Goodbye, Boss!")
        return False
    else:
        speak("Command not recognized.")
    return True

# ============================
# MAIN PROGRAM
# ============================
if __name__ == "__main__":
    speak("Starting Secure Voice Assistant with Face Login")

    if not recognize_face():
        speak("Authentication failed. Closing system.")
        exit()

    # Face login successful → Start voice control
    speak("System unlocked. Say 'hey assistant' to give commands.")

    while True:
        query = listen().lower()
        if "hey assistant" in query or "wake up" in query:
            speak("Yes boss, I'm listening.")
            while True:
                cmd = listen()
                if not process_command(cmd):
                    break