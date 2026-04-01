import pickle
import cv2
import mediapipe as mp
import numpy as np
import pyttsx3
import tkinter as tk
from tkinter import StringVar, Label, Frame
from PIL import Image, ImageTk, ImageDraw
import threading
import time
import warnings
import threading
import time
import warnings
from google import genai
import speech_recognition as sr
from tkinter import messagebox

# --- FIX FOR BLURRY TEXT ON WINDOWS (Native HD Rendering) ---
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

warnings.filterwarnings("ignore", category=UserWarning)

# --- GEMINI AI SETUP ---
GEMINI_API_KEY = "AIzaSyCmpcN4q9huXVtF_VRKSdowhzCk6Jvb5Ag"
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are a Sign Language Teaching Assistant. Your goal is to help users learn sign language (ASL or other varieties).
STRICT RULES:
1. ONLY answer questions related to sign language, deaf culture, or communication for the hearing/speech impaired.
2. If a user asks anything outside this scope, politely decline and redirect them to sign language topics.
3. Keep responses concise, encouraging, and professional.
4. If asked to teach a sign, describe the hand movement, position, and facial expression.
"""

# Initializing chat session with system instruction
chat_session = client.chats.create(
    model='gemini-2.0-flash',
    config={'system_instruction': SYSTEM_PROMPT}
)

model_dict = pickle.load(open('./model.p', 'rb'))
model = model_dict['model']

# Mediapipe setup
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_hands_mesh = mp_hands.Hands(static_image_mode=False, min_detection_confidence=0.5, max_num_hands=1)

# Text-to-Speech setup
engine = pyttsx3.init()

labels_dict = {
    0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F', 6: 'G', 7: 'H', 8: 'I', 9: 'J', 10: 'K', 11: 'L', 12: 'M',
    13: 'N', 14: 'O', 15: 'P', 16: 'Q', 17: 'R', 18: 'S', 19: 'T', 20: 'U', 21: 'V', 22: 'W', 23: 'X', 24: 'Y',
    25: 'Z', 26: '0', 27: '1', 28: '2', 29: '3', 30: '4', 31: '5', 32: '6', 33: '7', 34: '8', 35: '9',
    36: ' ', 37: '.'
}

shortcuts = {
   'A': 'Am',           
        'B': 'Bathroom',      # From: I need to use the bathroom.
        'C': 'Call',          # From: Please call Shreyas.
        'D': 'Doctor',        # From: I need a doctor immediately.
        'E': 'Excuse',        # From: Excuse me.
        'F': 'Food',          # From: I need food, I am hungry.
        'G': 'Good',          # From: Good morning.
        'H': 'Help',         # From: Hello!
        'I': 'I',             # From: I am deaf...
        'J': 'Just',          # From: Just a minute, please.
        'K': 'Know',          # Added to help build sentences
        'L': 'Lets go', 
        'M': 'Me',            # From: My name is...
        'N': 'Need',          # Added to link with Food/Water/Doctor
        'O': 'Okay',          # From: Okay.
        'P': 'Please',        # From: Please.
        'Q': 'Question',      # From: I have a question.
        'R': 'Repeat',        # From: Please repeat that.
        'S': 'Sorry',         # From: My name is Soham.
        'T': 'Thank you',         # From: Thank you very much.
        'U': 'Understand',    # From: I do not understand.
        'V': 'Very',          # From: I am very tired.
        'W': 'Water',         # From: I need water...
        'X': 'Help',          # From: Help me.
        'Y': 'You',           # Added to link with Love/Thank/Are
        'Z': 'Love'           # From: I love you.
}

expected_features = 42
stabilization_buffer = []
stable_char = None
word_buffer = ""
sentence_parts = [] 

def speak_text(text):
    def tts_thread():
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=tts_thread, daemon=True).start()

def get_voice_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            text = recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            return "Could not understand audio"
        except sr.RequestError:
            return "API unavailable"
        except Exception as e:
            return f"Error: {e}"


# --- RESPONSIVE ROUNDED CARD ---
class ResponsiveRoundedCard(tk.Canvas):
    def __init__(self, parent, bg_color, radius, border_color=None, shadow_color=None, **kwargs):
        super().__init__(parent, highlightthickness=0, bg=parent['bg'], **kwargs)
        self.radius = radius
        self.fill_color = bg_color
        self.border_color = border_color
        self.shadow_color = shadow_color
        self.inner_frame = tk.Frame(self, bg=bg_color)
        self.window_id = self.create_window(0, 0, window=self.inner_frame, anchor="nw")
        self.bind('<Configure>', self._on_resize)

    def _draw_rounded(self, x1, y1, x2, y2, r, color, tags):
        r = min(r, (x2-x1)//2, (y2-y1)//2)
        self.create_oval(x1, y1, x1+2*r, y1+2*r, fill=color, outline="", tags=tags)
        self.create_oval(x2-2*r, y1, x2, y1+2*r, fill=color, outline="", tags=tags)
        self.create_oval(x1, y2-2*r, x1+2*r, y2, fill=color, outline="", tags=tags)
        self.create_oval(x2-2*r, y2-2*r, x2, y2, fill=color, outline="", tags=tags)
        self.create_rectangle(x1+r, y1, x2-r, y2, fill=color, outline="", tags=tags)
        self.create_rectangle(x1, y1+r, x2, y2-r, fill=color, outline="", tags=tags)

    def _on_resize(self, event):
        self.delete("bg")
        w, h = event.width, event.height
        if w < 20 or h < 20: return
        r = self.radius

        # Subtle drop shadow
        if self.shadow_color:
            self._draw_rounded(4, 6, w+1, h+1, r, self.shadow_color, "bg")

        # Border ring
        if self.border_color:
            self._draw_rounded(0, 0, w, h, r, self.border_color, "bg")
            bw = 2
            self._draw_rounded(bw, bw, w-bw, h-bw, max(r-bw, 1), self.fill_color, "bg")
        else:
            self._draw_rounded(0, 0, w, h, r, self.fill_color, "bg")

        self.tag_lower("bg")

        # This locks the internal frame so elements can NEVER push past the bottom
        pad = 25
        self.coords(self.window_id, pad, pad)
        self.itemconfig(self.window_id, width=w - (pad*2), height=h - (pad*2))


# --- FIXED HD BUTTONS ---
class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, width=165, height=65, color="#3498db", hover_color="#2980b9", shadow_color="#1A5276", bg_color="#FFFFFF"):
        # Extra padding so the rounded corners are never cropped
        self.pad = 8
        canvas_width = width + (self.pad * 2)
        canvas_height = height + (self.pad * 2)
        
        super().__init__(parent, width=canvas_width, height=canvas_height, bg=bg_color, highlightthickness=0)
        self.command = command
        self.color = color
        self.hover_color = hover_color
        self.shadow_color = shadow_color
        self.is_pressed = False
        self.is_hovered = False
        self._anim_id = None
        self.main_tag = f"main_{id(self)}"
        self.shadow_tag = f"shadow_{id(self)}"
        
        x1, y1 = self.pad, self.pad
        x2, y2 = x1 + width, y1 + height

        self.draw_hd_rounded_rect(x1, y1+5, x2, y2, radius=22, fill_color=shadow_color, tags=self.shadow_tag)
        self.draw_hd_rounded_rect(x1, y1, x2, y2-5, radius=22, fill_color=color, tags=self.main_tag)
        
        self.text_id = self.create_text(x1 + width/2, y1 + (height-5)/2, text=text, fill="#FFFFFF", font=("Segoe UI", 15, "bold"))
        
        self.bind("<ButtonPress-1>", self.on_press)
        self.tag_bind(self.text_id, "<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.tag_bind(self.text_id, "<ButtonRelease-1>", self.on_release)
        self.bind("<Enter>", self.on_hover)
        self.tag_bind(self.text_id, "<Enter>", self.on_hover)
        self.bind("<Leave>", self.on_leave)
        self.tag_bind(self.text_id, "<Leave>", self.on_leave)
        self.config(cursor="hand2")

    def draw_hd_rounded_rect(self, x1, y1, x2, y2, radius, fill_color, tags):
        self.create_oval(x1, y1, x1+2*radius, y1+2*radius, fill=fill_color, outline="", tags=tags)
        self.create_oval(x2-2*radius, y1, x2, y1+2*radius, fill=fill_color, outline="", tags=tags)
        self.create_oval(x1, y2-2*radius, x1+2*radius, y2, fill=fill_color, outline="", tags=tags)
        self.create_oval(x2-2*radius, y2-2*radius, x2, y2, fill=fill_color, outline="", tags=tags)
        self.create_rectangle(x1+radius, y1, x2-radius, y2, fill=fill_color, outline="", tags=tags)
        self.create_rectangle(x1, y1+radius, x2, y2-radius, fill=fill_color, outline="", tags=tags)

    def _lerp_color(self, c1, c2, t):
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _animate_color(self, from_color, to_color, step=0, steps=7):
        if self._anim_id is not None:
            self.after_cancel(self._anim_id)
            self._anim_id = None
        color = self._lerp_color(from_color, to_color, step / steps)
        self.itemconfig(self.main_tag, fill=color)
        if step < steps:
            self._anim_id = self.after(18, lambda: self._animate_color(from_color, to_color, step + 1, steps))

    def on_press(self, event):
        if not self.is_pressed:
            self.is_pressed = True
            self.move(self.main_tag, 0, 4)
            self.move(self.text_id, 0, 4)

    def on_release(self, event):
        if self.is_pressed:
            self.is_pressed = False
            self.move(self.main_tag, 0, -4)
            self.move(self.text_id, 0, -4)
            if self.is_hovered and self.command:
                self.command()

    def on_hover(self, event):
        self.is_hovered = True
        self._animate_color(self.color, self.hover_color)

    def on_leave(self, event):
        self.is_hovered = False
        self._animate_color(self.hover_color, self.color)
        if self.is_pressed:
            self.on_release(event)
            
    def config_text(self, new_text):
        self.itemconfig(self.text_id, text=new_text)

    def config_color(self, main, hover, shadow):
        self.color = main
        self.hover_color = hover
        self.shadow_color = shadow
        self.itemconfig(self.shadow_tag, fill=shadow)
        if not self.is_hovered:
            self.itemconfig(self.main_tag, fill=main)


class TextToggleSwitch(tk.Canvas):
    def __init__(self, parent, command=None, width=320, height=55, bg_color="#FFFFFF", on_color="#1D4ED8", off_color="#3B82F6"):
        self.pad = 8
        canvas_width = width + (self.pad * 2)
        canvas_height = height + (self.pad * 2)
        
        super().__init__(parent, width=canvas_width, height=canvas_height, bg=bg_color, highlightthickness=0)
        self.command = command
        self.is_on = False
        self.on_color = on_color
        self.off_color = off_color
        self.w = width
        self.h = height
        self.bg_tag = f"toggle_bg_{id(self)}"
        
        x1, y1 = self.pad, self.pad
        x2, y2 = x1 + width, y1 + height

        self.draw_hd_rounded_rect(x1, y1, x2, y2, radius=25, fill_color=self.off_color)
        self.knob_radius = height - 12
        self.oval = self.create_oval(x1+6, y1+6, x1+6 + self.knob_radius, y1+6 + self.knob_radius, fill="#FFFFFF", outline="")
        self.text_id = self.create_text(x1 + width/2 + 25, y1 + height/2, text="Spelling Mode", fill="#FFFFFF", font=("Segoe UI", 15, "bold"))
        
        self.bind("<ButtonPress-1>", self.toggle)
        self.tag_bind(self.text_id, "<ButtonPress-1>", self.toggle)
        self.tag_bind(self.bg_tag, "<ButtonPress-1>", self.toggle)
        self.config(cursor="hand2")

    def draw_hd_rounded_rect(self, x1, y1, x2, y2, radius, fill_color):
        self.create_oval(x1, y1, x1+2*radius, y1+2*radius, fill=fill_color, outline="", tags=self.bg_tag)
        self.create_oval(x2-2*radius, y1, x2, y1+2*radius, fill=fill_color, outline="", tags=self.bg_tag)
        self.create_oval(x1, y2-2*radius, x1+2*radius, y2, fill=fill_color, outline="", tags=self.bg_tag)
        self.create_oval(x2-2*radius, y2-2*radius, x2, y2, fill=fill_color, outline="", tags=self.bg_tag)
        self.create_rectangle(x1+radius, y1, x2-radius, y2, fill=fill_color, outline="", tags=self.bg_tag)
        self.create_rectangle(x1, y1+radius, x2, y2-radius, fill=fill_color, outline="", tags=self.bg_tag)

    def toggle(self, event=None):
        self.is_on = not self.is_on
        x1 = self.pad
        
        if self.is_on:
            self.itemconfig(self.bg_tag, fill=self.on_color)
            self.itemconfig(self.text_id, text="Sentence Mode")
            self.coords(self.text_id, x1 + self.w/2 - 25, self.pad + self.h/2)
            target_x = x1 + self.w - self.knob_radius - 6
        else:
            self.itemconfig(self.bg_tag, fill=self.off_color)
            self.itemconfig(self.text_id, text="Spelling Mode")
            self.coords(self.text_id, x1 + self.w/2 + 25, self.pad + self.h/2)
            target_x = x1 + 6
            
        self.coords(self.oval, target_x, self.pad + 6, target_x + self.knob_radius, self.pad + 6 + self.knob_radius)
        if self.command:
            self.command(self.is_on)


# --- GUI SETUP ---
root = tk.Tk()
root.title("SignSpeak")

try:
    root.state('zoomed') 
except tk.TclError:
    root.attributes('-zoomed', True)

BG_MAIN = "#EFF6FF"       # Cool blue-white
CARD_BG = "#FFFFFF"       # Pure white cards
CARD_BORDER = "#BFDBFE"   # Soft blue border
CARD_SHADOW = "#DBEAFE"   # Very soft shadow
TEXT_BLACK = "#0F172A"    # Deep slate (richer than pure black)
TEXT_MED = "#1D4ED8"      # Vibrant blue
TEXT_LIGHT = "#64748B"    # Muted slate for secondary text
PRIMARY_BLUE = "#2563EB"  # Main vibrant blue
ACCENT_PURPLE = "#7C3AED" # Purple accent
ACCENT_TEAL = "#0D9488"   # Teal accent
ACCENT_EMERALD = "#059669" # Emerald green

FONT_TITLE = ("Segoe UI", 56, "bold")
FONT_SUBTITLE = ("Segoe UI", 20, "italic")
FONT_LABEL = ("Segoe UI", 18, "bold")
FONT_VALUE = ("Segoe UI", 30, "bold")

root.configure(bg=BG_MAIN)

current_alphabet = StringVar(value="")
current_word = StringVar(value="")
is_paused = StringVar(value="False")
is_sentence_mode = StringVar(value="False")

# Header
header_frame = Frame(root, bg=BG_MAIN)
header_frame.pack(fill="x", pady=(20, 10))

title_label = Label(header_frame, text="✋ SignSpeak", font=FONT_TITLE, fg=TEXT_BLACK, bg=BG_MAIN)
title_label.pack()

subtitle_label = Label(header_frame, text="Giving voice to every gesture", font=FONT_SUBTITLE, fg=TEXT_LIGHT, bg=BG_MAIN)
subtitle_label.pack()

# Decorative separator line
sep_canvas = tk.Canvas(header_frame, height=4, bg=BG_MAIN, highlightthickness=0, width=260)
sep_canvas.pack(pady=(4, 8))

def _draw_separator(event):
    sep_canvas.delete("all")
    sep_canvas.create_rectangle(0, 0, event.width, 4, fill=PRIMARY_BLUE, outline="")

sep_canvas.bind("<Configure>", _draw_separator)

# --- VIEW SWITCHER LOGIC ---
is_chat_mode = tk.BooleanVar(value=False)

def toggle_view():
    if is_chat_mode.get():
        chat_frame.pack_forget()
        main_frame.pack(expand=True, fill="both")
        toggle_view_btn.config_text("💬 AI Teacher")
        is_chat_mode.set(False)
    else:
        main_frame.pack_forget()
        chat_frame.pack(expand=True, fill="both")
        toggle_view_btn.config_text("📷 Recognition")
        is_chat_mode.set(True)
    root.update_idletasks()

toggle_view_btn = RoundedButton(header_frame, "💬 AI Teacher", toggle_view, width=180, height=50, color=PRIMARY_BLUE, hover_color="#1D4ED8", shadow_color="#1E3A8A", bg_color=BG_MAIN)
toggle_view_btn.pack(pady=10)

# --- VIEW CONTAINER ---
# This ensures that main_frame and chat_frame always occupy the same space
content_container = Frame(root, bg=BG_MAIN)
content_container.pack(expand=True, fill="both", padx=40, pady=(5, 40))

# Main Container
main_frame = Frame(content_container, bg=BG_MAIN)
main_frame.pack(expand=True, fill="both")

main_frame.grid_columnconfigure(0, weight=1) 
main_frame.grid_columnconfigure(1, weight=1) 
main_frame.grid_rowconfigure(0, weight=1)

# --- LEFT BLOCK (Responsive Rounded Video Card) ---
left_card = ResponsiveRoundedCard(main_frame, bg_color=CARD_BG, radius=35, border_color=CARD_BORDER, shadow_color=CARD_SHADOW)
left_card.grid(row=0, column=0, padx=(0, 20), sticky="nsew")

video_container = Frame(left_card.inner_frame, bg=CARD_BG)
video_container.pack(expand=True)

video_label = tk.Label(video_container, bg=CARD_BG)
video_label.pack()

video_width, video_height = 720, 540
rounded_mask = Image.new('L', (video_width, video_height), 0)
mask_draw = ImageDraw.Draw(rounded_mask)
mask_draw.rounded_rectangle((0, 0, video_width, video_height), radius=40, fill=255)

# --- RIGHT BLOCK (Responsive Rounded Content Card) ---
right_card = ResponsiveRoundedCard(main_frame, bg_color=CARD_BG, radius=35, border_color=CARD_BORDER, shadow_color=CARD_SHADOW)
right_card.grid(row=0, column=1, padx=(20, 0), sticky="nsew")

# --- FIXED LAYOUT ORDER (Crucial Fix) ---
# 1. Top Section (Switch)
top_frame = Frame(right_card.inner_frame, bg=CARD_BG)
top_frame.pack(side="top", fill="x", pady=(0, 10))

# 2. Bottom Section (Buttons - Locked to Bottom)
bottom_frame = Frame(right_card.inner_frame, bg=CARD_BG)
bottom_frame.pack(side="bottom", fill="x", pady=(10, 0))

# 3. Middle Section (Text Area - Expands safely between top and bottom)
middle_frame = Frame(right_card.inner_frame, bg=CARD_BG)
middle_frame.pack(side="top", fill="both", expand=True)

# Toggle Switch
def on_mode_toggle(is_on):
    if is_on:
        is_sentence_mode.set("True")
        spelling_frame.pack_forget() 
        dynamic_output_title.config(text="Output:") 
    else:
        is_sentence_mode.set("False")
        spelling_frame.pack(before=output_frame, anchor="w", fill="x") 
        dynamic_output_title.config(text="Current Output:")

toggle = TextToggleSwitch(top_frame, command=on_mode_toggle, bg_color=CARD_BG)
toggle.pack(side="left")

# --- DYNAMIC FRAMES (Inside Middle Section) ---
spelling_frame = Frame(middle_frame, bg=CARD_BG)
spelling_frame.pack(anchor="w", fill="x")

Label(spelling_frame, text="Current Alphabet:", font=FONT_LABEL, fg=TEXT_MED, bg=CARD_BG).pack(anchor="w")
Label(spelling_frame, textvariable=current_alphabet, font=FONT_VALUE, fg=TEXT_BLACK, bg=CARD_BG).pack(anchor="w", pady=(0, 15))

Label(spelling_frame, text="Current Word:", font=FONT_LABEL, fg=TEXT_MED, bg=CARD_BG).pack(anchor="w")
Label(spelling_frame, textvariable=current_word, font=FONT_VALUE, fg=TEXT_BLACK, bg=CARD_BG, wraplength=450, justify="left").pack(anchor="w", pady=(0, 15))
# Output Frame (Scrollable)
output_frame = Frame(middle_frame, bg=CARD_BG)
output_frame.pack(anchor="w", fill="both", expand=True)

dynamic_output_title = Label(output_frame, text="Current Output:", font=FONT_LABEL, fg=TEXT_MED, bg=CARD_BG)
dynamic_output_title.pack(anchor="w")

# The text box will now ONLY take available space and add a scrollbar
sentence_text_widget = tk.Text(output_frame, font=("Segoe UI", 30, "bold"), fg=TEXT_BLACK, bg="#F8FAFF", wrap="word", bd=0, highlightthickness=0, padx=10, pady=8, relief="flat")
text_scroll = tk.Scrollbar(output_frame, command=sentence_text_widget.yview)

sentence_text_widget.pack(side="left", fill="both", expand=True, pady=(5, 0))
text_scroll.pack(side="right", fill="y")
sentence_text_widget.config(yscrollcommand=text_scroll.set, state="disabled")

def update_sentence_ui(text_content):
    sentence_text_widget.config(state="normal")
    sentence_text_widget.delete(1.0, tk.END)
    sentence_text_widget.insert(tk.END, text_content)
    sentence_text_widget.see(tk.END) 
    sentence_text_widget.config(state="disabled")

# --- CORE BUTTON LOGIC ---
def reset_sentence():
    global word_buffer, sentence_parts
    word_buffer = ""
    sentence_parts = []
    current_word.set("")
    current_alphabet.set("")
    update_sentence_ui("")

def toggle_pause():
    if is_paused.get() == "False":
        is_paused.set("True")
        pause_button.config_text("▶ Play")
        pause_button.config_color(main="#94A3B8", hover="#64748B", shadow="#475569")
    else:
        is_paused.set("False")
        pause_button.config_text("⏸ Pause")
        pause_button.config_color(main="#3B82F6", hover="#2563EB", shadow="#1D4ED8")

def backspace():
    global word_buffer, sentence_parts
    if len(word_buffer) > 0:
        word_buffer = word_buffer[:-1]
        current_word.set(word_buffer if word_buffer else "")
    elif len(sentence_parts) > 0:
        sentence_parts.pop() 
        update_sentence_ui("".join(sentence_parts))

# Action Buttons Container (Inside Bottom Section)
bottom_frame.grid_columnconfigure(0, weight=1)
bottom_frame.grid_columnconfigure(1, weight=1)
bottom_frame.grid_columnconfigure(2, weight=1)
bottom_frame.grid_columnconfigure(3, weight=1)

reset_button = RoundedButton(bottom_frame, "🔄 Reset", reset_sentence, width=160, bg_color=CARD_BG, color="#64748B", hover_color="#475569", shadow_color="#334155")
reset_button.grid(row=0, column=0, padx=5, pady=10)

pause_button = RoundedButton(bottom_frame, "⏸ Pause", toggle_pause, width=160, bg_color=CARD_BG, color="#3B82F6", hover_color="#2563EB", shadow_color="#1D4ED8")
pause_button.grid(row=0, column=1, padx=5, pady=10)

backspace_button = RoundedButton(bottom_frame, "⌫ Backspace", backspace, width=175, bg_color=CARD_BG, color=ACCENT_PURPLE, hover_color="#6D28D9", shadow_color="#4C1D95")
backspace_button.grid(row=0, column=2, padx=5, pady=10)

speak_button = RoundedButton(bottom_frame, "🔊 Speak", lambda: speak_text("".join(sentence_parts)), width=160, bg_color=CARD_BG, color=ACCENT_EMERALD, hover_color="#047857", shadow_color="#065F46")
speak_button.grid(row=0, column=3, padx=5, pady=10)

# --- AI CHATBOT FRAME ---
chat_frame = Frame(content_container, bg=BG_MAIN)
# (Hidden by default, shown via toggle_view)

chat_card = ResponsiveRoundedCard(chat_frame, bg_color=CARD_BG, radius=35, border_color=CARD_BORDER, shadow_color=CARD_SHADOW)
chat_card.pack(expand=True, fill="both")

# --- CHAT UI STRUCTURE (Guaranteeing Button Visibility) ---
# We use a container inside chat_card.inner_frame to manage layout
chat_main_container = Frame(chat_card.inner_frame, bg=CARD_BG)
chat_main_container.pack(expand=True, fill="both")

# 1. Header (Top)
chat_header = Frame(chat_main_container, bg=CARD_BG)
chat_header.pack(side="top", fill="x", pady=(0, 10))
Label(chat_header, text="✨ Sign Language AI Teacher", font=("Segoe UI", 24, "bold"), fg=TEXT_MED, bg=CARD_BG).pack(side="left")

# 2. Input Bar (Bottom - Packed FIRST to stay at bottom)
chat_input_frame = Frame(chat_main_container, bg=CARD_BG)
chat_input_frame.pack(side="bottom", fill="x", pady=(10, 0))

# 3. Chat Display (Middle - Takes remaining space)
chat_display_frame = Frame(chat_main_container, bg="#F0F7FF", relief="flat")
chat_display_frame.pack(side="top", expand=True, fill="both", padx=5, pady=5)

chat_history = tk.Text(chat_display_frame, font=("Segoe UI", 12), state="disabled", wrap="word", bg="#F0F7FF", relief="flat", padx=20, pady=20)
chat_history.pack(side="left", fill="both", expand=True)

chat_scroll = tk.Scrollbar(chat_display_frame, command=chat_history.yview)
chat_scroll.pack(side="right", fill="y")
chat_history.config(yscrollcommand=chat_scroll.set)

# Setup tags for styling
chat_history.tag_configure("bold_you", font=("Segoe UI", 13, "bold"), foreground=PRIMARY_BLUE)
chat_history.tag_configure("bold_teacher", font=("Segoe UI", 13, "bold"), foreground=ACCENT_TEAL)
chat_history.tag_configure("bold_system", font=("Segoe UI", 12, "bold"), foreground=TEXT_LIGHT)
chat_history.tag_configure("you", font=("Segoe UI", 12), foreground=TEXT_BLACK)
chat_history.tag_configure("teacher", font=("Segoe UI", 12), foreground=TEXT_BLACK)
chat_history.tag_configure("system", font=("Segoe UI", 11, "italic"), foreground=TEXT_LIGHT)

def add_to_chat(sender, message):
    chat_history.config(state="normal")
    tag = sender.lower()
    chat_history.insert(tk.END, f"◆ {sender}\n", f"bold_{tag}")
    chat_history.insert(tk.END, f"{message}\n\n", tag)
    chat_history.see(tk.END)
    chat_history.config(state="disabled")

def handle_chat_response():
    user_text = chat_entry.get().strip()
    if not user_text: return
    
    chat_entry.delete(0, tk.END)
    add_to_chat("You", user_text)
    
    # Show status
    add_to_chat("System", "Teacher is thinking...")
    
    def ai_thread():
        try:
            response = chat_session.send_message(user_text)
            bot_text = response.text
            
            def update_ui():
                add_to_chat("Teacher", bot_text)
                speak_text(bot_text)
            
            root.after(0, update_ui)
        except Exception as e:
            root.after(0, lambda: add_to_chat("System", f"Error: {e}"))
            
    threading.Thread(target=ai_thread, daemon=True).start()

def handle_voice_chat():
    def voice_thread():
        # Change button state to show recording
        root.after(0, lambda: voice_btn.config_text("🔴 Recording..."))
        root.after(0, lambda: voice_btn.config_color(main="#DC2626", hover="#B91C1C", shadow="#7F1D1D"))
        
        # This will record until a pause is detected
        voice_text = get_voice_input()
        
        # Reset button state
        root.after(0, lambda: voice_btn.config_text("🎙️ Start Voice"))
        root.after(0, lambda: voice_btn.config_color(main=ACCENT_TEAL, hover="#0F766E", shadow="#115E59"))
        
        if voice_text and voice_text not in ["Could not understand audio", "API unavailable"] and not voice_text.startswith("Error"):
            root.after(0, lambda: chat_entry.delete(0, tk.END))
            root.after(0, lambda: chat_entry.insert(0, voice_text))
            root.after(0, handle_chat_response)
        else:
            root.after(0, lambda: add_to_chat("System", "No speech detected. Click 'Start Voice' again."))
            
    threading.Thread(target=voice_thread, daemon=True).start()

# --- INPUT AREA BUTTONS (Guaranteed placement) ---
voice_btn = RoundedButton(chat_input_frame, "🎙️ Start Voice", handle_voice_chat, width=170, height=55, color=ACCENT_TEAL, hover_color="#0F766E", shadow_color="#115E59", bg_color=CARD_BG)
voice_btn.pack(side="right", padx=10)

send_btn = RoundedButton(chat_input_frame, "📤 Send", handle_chat_response, width=130, height=55, color=PRIMARY_BLUE, hover_color="#1D4ED8", shadow_color="#1E3A8A", bg_color=CARD_BG)
send_btn.pack(side="right")

# Styled entry with a colored border frame
chat_entry_frame = Frame(chat_input_frame, bg=CARD_BORDER, padx=2, pady=2)
chat_entry_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
chat_entry = tk.Entry(chat_entry_frame, font=("Segoe UI", 15), relief="flat", bg="#F0F7FF", insertbackground=TEXT_BLACK, fg=TEXT_BLACK)
chat_entry.pack(fill="both", expand=True, ipady=10, padx=6)

chat_entry.bind("<Return>", lambda e: handle_chat_response())

# Initial Welcome Message
add_to_chat("Teacher", "Hello! I am your Sign Language Assistant. Click 'Start Voice' or type below to talk to me.")


# --- OPENCV & PROCESSING ---
cap = cv2.VideoCapture(0)
last_registered_time = time.time()
registration_delay = 1.5 

def process_frame():
    global stabilization_buffer, stable_char, word_buffer, sentence_parts, last_registered_time

    if is_chat_mode.get():
        root.after(100, process_frame)
        return

    ret, frame = cap.read()
    if not ret:
        return

    frame = cv2.resize(frame, (video_width, video_height))

    if is_paused.get() == "True":
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (800, 600), (40, 25, 15), -1) 
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        cv2.putText(frame, "PAUSED", (210, 260), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (255, 255, 255), 7, cv2.LINE_AA)
        cv2.putText(frame, "Press 'Play' to resume", (200, 330), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 230, 255), 2, cv2.LINE_AA)
        
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img)
        img_rounded = Image.new('RGB', img_pil.size, (255, 255, 255)) 
        img_rounded.paste(img_pil, mask=rounded_mask)
        
        img_tk = ImageTk.PhotoImage(image=img_rounded)
        video_label.imgtk = img_tk
        video_label.configure(image=img_tk)
        root.after(10, process_frame)
        return

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = mp_hands_mesh.process(frame_rgb)

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

            features_array = np.asarray(data_aux)
            prediction = model.predict([features_array])
            predicted_character = labels_dict[int(prediction[0])]
            
            try:
                probs = model.predict_proba([features_array])
                confidence = np.max(probs) * 100
            except:
                confidence = 100.0 

            stabilization_buffer.append(predicted_character)
            if len(stabilization_buffer) > 30:
                stabilization_buffer.pop(0)

            if stabilization_buffer.count(predicted_character) > 25:
                current_time = time.time()
                if current_time - last_registered_time > registration_delay:
                    stable_char = predicted_character
                    last_registered_time = current_time 
                    
                    if is_sentence_mode.get() == "True":
                        current_alphabet.set("") 
                        current_word.set("") 
                        
                        if stable_char in shortcuts:
                            phrase = shortcuts[stable_char]
                            sentence_parts.append(phrase + " ") 
                            update_sentence_ui("".join(sentence_parts))
                            speak_text(phrase)
                             
                    else:
                        if stable_char not in [' ', '.']:
                            current_alphabet.set(f"{stable_char}  ({confidence:.0f}%)")
                        else:
                            current_alphabet.set(stable_char)

                        if stable_char == ' ':
                            if word_buffer.strip():
                                speak_text(word_buffer)
                                sentence_parts.append(word_buffer + " ")
                                update_sentence_ui("".join(sentence_parts))
                            word_buffer = ""
                            current_word.set("")
                        elif stable_char == '.':
                            if word_buffer.strip():
                                speak_text(word_buffer)
                                sentence_parts.append(word_buffer + ". ")
                                update_sentence_ui("".join(sentence_parts))
                            word_buffer = ""
                            current_word.set("")
                        else:
                            word_buffer += stable_char
                            current_word.set(word_buffer)

            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                                      mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=3, circle_radius=5),
                                      mp_drawing.DrawingSpec(color=(230, 170, 50), thickness=3, circle_radius=3))

    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(img)
    img_rounded = Image.new('RGB', img_pil.size, (255, 255, 255)) 
    img_rounded.paste(img_pil, mask=rounded_mask)

    img_tk = ImageTk.PhotoImage(image=img_rounded)
    video_label.imgtk = img_tk
    video_label.configure(image=img_tk)

    root.after(10, process_frame)

process_frame()
root.mainloop()
