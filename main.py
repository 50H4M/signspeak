import pickle
import cv2
import mediapipe as mp
import numpy as np
import pyttsx3
import tkinter as tk
from tkinter import StringVar, Label, Button, Frame
from PIL import Image, ImageTk
import threading
import time
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# --- High-DPI Fix for Windows (Prevents blurry text) ---
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Load Model
try:
    model_dict = pickle.load(open('./model.p', 'rb'))
    model = model_dict['model']
except FileNotFoundError:
    print("Error: 'model.p' not found. Please ensure your model file is in the same directory.")
    exit()

# Mediapipe setup
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
hands = mp_hands.Hands(static_image_mode=False, min_detection_confidence=0.5, max_num_hands=1)

# Text-to-Speech setup
engine = pyttsx3.init()

# Label mapping
labels_dict = {
    0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F', 6: 'G', 7: 'H', 8: 'I', 9: 'J', 10: 'K', 11: 'L', 12: 'M',
    13: 'N', 14: 'O', 15: 'P', 16: 'Q', 17: 'R', 18: 'S', 19: 'T', 20: 'U', 21: 'V', 22: 'W', 23: 'X', 24: 'Y',
    25: 'Z', 26: '0', 27: '1', 28: '2', 29: '3', 30: '4', 31: '5', 32: '6', 33: '7', 34: '8', 35: '9',
    36: ' ', 37: '.'
}
expected_features = 42

# Initialize buffers and history
stabilization_buffer = []
stable_char = None
word_buffer = ""
sentence = ""

def speak_text(text):
    def tts_thread():
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=tts_thread, daemon=True).start()


# --- GUI Setup ---
root = tk.Tk()
root.title("Sign Speak")

# --- Full Screen Configuration ---
root.attributes('-fullscreen', True)
root.geometry("1400x750") # Fallback size if user exits full screen
root.configure(bg="#ffffff")

# Toggle Full Screen with F11 and Escape with Esc
def toggle_fullscreen(event=None):
    is_fullscreen = root.attributes('-fullscreen')
    root.attributes('-fullscreen', not is_fullscreen)

def exit_fullscreen(event=None):
    root.attributes('-fullscreen', False)

root.bind("<F11>", toggle_fullscreen)
root.bind("<Escape>", exit_fullscreen)

# Theme Colors & Fonts
BG_COLOR = "#ffffff"          # White Background
TEXT_COLOR = "#1f2937"        # Dark Gray Text
ACCENT_BLUE = "#2563eb"       # Modern Blue for Buttons
BUTTON_FG = "#ffffff"         # White text on buttons
FONT_MAIN = ("Helvetica", 24) # Increased font sizes for fullscreen
FONT_BOLD = ("Helvetica", 28, "bold")

# Variables for GUI
current_alphabet = StringVar(value="N/A")
current_word = StringVar(value="N/A")
current_sentence = StringVar(value="N/A")
is_paused = StringVar(value="False")

# --- Layout Frames (Centered for Full Screen) ---
# Outer frame to keep everything centered
center_frame = Frame(root, bg=BG_COLOR)
center_frame.place(relx=0.5, rely=0.5, anchor="center")

header_frame = Frame(center_frame, bg=BG_COLOR)
header_frame.pack(side="top", fill="x", pady=(0, 40))

main_content_frame = Frame(center_frame, bg=BG_COLOR)
main_content_frame.pack(expand=True, fill="both")

left_frame = Frame(main_content_frame, bg=BG_COLOR)
left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 60))

right_frame = Frame(main_content_frame, bg=BG_COLOR)
right_frame.grid(row=0, column=1, sticky="nsew")

button_frame = Frame(right_frame, bg=BG_COLOR)
button_frame.pack(side="bottom", anchor="w", pady=(40, 0))

# --- Titles ---
Label(header_frame, text="Sign Speak", font=("Helvetica", 48, "bold"), fg=ACCENT_BLUE, bg=BG_COLOR).pack()
Label(header_frame, text="Giving voice to every gesture", font=("Helvetica", 20, "italic"), fg="#6b7280", bg=BG_COLOR).pack()

# --- Video Feed ---
# Increased video feed size slightly for full screen
video_container = Frame(left_frame, bg="#e5e7eb", bd=2, relief="flat", width=800, height=600)
video_container.pack()
video_container.pack_propagate(False)
video_label = tk.Label(video_container, bg="#000000")
video_label.pack(expand=True, fill="both")

# --- Right Panel Labels ---
def create_display_section(parent, title_text, string_var):
    Label(parent, text=title_text, font=FONT_MAIN, fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", pady=(20, 5))
    Label(parent, textvariable=string_var, font=FONT_BOLD, fg=ACCENT_BLUE, bg=BG_COLOR, wraplength=700, justify="left").pack(anchor="w")

create_display_section(right_frame, "Current Alphabet:", current_alphabet)
create_display_section(right_frame, "Current Word:", current_word)
create_display_section(right_frame, "Current Sentence:", current_sentence)

# --- Button Functions ---
def reset_sentence():
    global word_buffer, sentence
    word_buffer = ""
    sentence = ""
    current_word.set("N/A")
    current_sentence.set("N/A")
    current_alphabet.set("N/A")

def toggle_pause():
    if is_paused.get() == "False":
        is_paused.set("True")
        pause_button.config(text="Play")
    else:
        is_paused.set("False")
        pause_button.config(text="Pause")

def backspace(event=None): # Added event parameter to allow keyboard binding
    global word_buffer, sentence
    if len(word_buffer) > 0:
        word_buffer = word_buffer[:-1]
        current_word.set(word_buffer if word_buffer else "N/A")
    elif len(sentence) > 0:
        sentence = sentence[:-1]
        current_sentence.set(sentence if sentence else "N/A")

# Bind the physical backspace key to the backspace function
root.bind("<BackSpace>", backspace)

# --- Buttons ---
btn_style = {"font": ("Helvetica", 16, "bold"), "bg": ACCENT_BLUE, "fg": BUTTON_FG, "relief": "flat", "height": 2, "width": 14, "cursor": "hand2"}

speak_button = Button(button_frame, text="Speak", command=lambda: speak_text(current_sentence.get()), **btn_style)
speak_button.grid(row=0, column=0, padx=(0, 15), pady=15)

pause_button = Button(button_frame, text="Pause", command=toggle_pause, **btn_style)
pause_button.grid(row=0, column=1, padx=15, pady=15)

backspace_button = Button(button_frame, text="Backspace", command=backspace, **btn_style)
backspace_button.grid(row=1, column=0, padx=(0, 15), pady=15)

reset_button = Button(button_frame, text="Reset", command=reset_sentence, **btn_style)
reset_button.grid(row=1, column=1, padx=15, pady=15)

# --- Video Capture & Processing ---
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)

last_registered_time = time.time()
registration_delay = 1.5 

def process_frame():
    global stabilization_buffer, stable_char, word_buffer, sentence, last_registered_time

    ret, frame = cap.read()
    if not ret:
        root.after(10, process_frame)
        return

    # Mirror the frame horizontally
    frame = cv2.flip(frame, 1)

    if is_paused.get() == "True":
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img_tk = ImageTk.PhotoImage(image=img)
        video_label.imgtk = img_tk
        video_label.configure(image=img_tk)
        root.after(10, process_frame)
        return

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            data_aux = []
            x_ = []
            y_ = []

            for i in range(len(hand_landmarks.landmark)):
                x = hand_landmarks.landmark[i].x
                y = hand_landmarks.landmark[i].y
                x_.append(x)
                y_.append(y)

            for i in range(len(hand_landmarks.landmark)):
                x = hand_landmarks.landmark[i].x
                y = hand_landmarks.landmark[i].y
                data_aux.append(x - min(x_))
                data_aux.append(y - min(y_))

            if len(data_aux) < expected_features:
                data_aux.extend([0] * (expected_features - len(data_aux)))
            elif len(data_aux) > expected_features:
                data_aux = data_aux[:expected_features]

            prediction = model.predict([np.asarray(data_aux)])
            predicted_character = labels_dict[int(prediction[0])]

            stabilization_buffer.append(predicted_character)
            if len(stabilization_buffer) > 30:
                stabilization_buffer.pop(0)

            if stabilization_buffer.count(predicted_character) > 25:
                current_time = time.time()
                if current_time - last_registered_time > registration_delay:
                    stable_char = predicted_character
                    last_registered_time = current_time
                    current_alphabet.set(stable_char)

                    if stable_char == ' ':
                        if word_buffer.strip():
                            speak_text(word_buffer)
                            sentence += word_buffer + " "
                            current_sentence.set(sentence.strip())
                        word_buffer = ""
                        current_word.set("N/A")
                    elif stable_char == '.':
                        if word_buffer.strip():
                            speak_text(word_buffer)
                            sentence += word_buffer + "."
                            current_sentence.set(sentence.strip())
                        word_buffer = ""
                        current_word.set("N/A")
                    else:
                        word_buffer += stable_char
                        current_word.set(word_buffer)

            # Draw landmarks
            mp_drawing.draw_landmarks(
                frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style()
            )

    # Draw a clean box for the detected alphabet on the video
    cv2.rectangle(frame, (10, 10), (220, 60), (255, 255, 255), -1)
    cv2.putText(frame, f"Detected: {current_alphabet.get()}", (20, 45), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (235, 99, 37), 2)

    # Update GUI video
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(img)
    img_tk = ImageTk.PhotoImage(image=img)
    video_label.imgtk = img_tk
    video_label.configure(image=img_tk)

    root.after(10, process_frame)

# Start loop
process_frame()
root.mainloop()