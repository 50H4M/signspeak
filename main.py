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

def lerp_color(c1, c2, t):
    """Linearly interpolate between two hex colors (t: 0.0 to 1.0)."""
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = max(0, min(255, int(r1 + (r2 - r1) * t)))
    g = max(0, min(255, int(g1 + (g2 - g1) * t)))
    b = max(0, min(255, int(b1 + (b2 - b1) * t)))
    return f"#{r:02x}{g:02x}{b:02x}"

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
    def __init__(self, parent, bg_color, radius, **kwargs):
        super().__init__(parent, highlightthickness=0, bg=parent['bg'], **kwargs)
        self.radius = radius
        self.fill_color = bg_color
        self.inner_frame = tk.Frame(self, bg=bg_color)
        self.window_id = self.create_window(0, 0, window=self.inner_frame, anchor="nw")
        self.bind('<Configure>', self._on_resize)

    def _draw_rounded_rect(self, x1, y1, x2, y2, r, color, tags):
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
        s = 6  # shadow depth

        # Layered shadow for depth (bottom-right offset, soft colors)
        shadow_layers = [
            (s,     "#CBD5EE"),
            (s - 2, "#D8E0F0"),
            (s - 4, "#E4EAF5"),
        ]
        for offset, color in shadow_layers:
            self._draw_rounded_rect(offset, offset, w, h, r, color, "bg")

        # Main card surface
        self._draw_rounded_rect(0, 0, w - s, h - s, r, self.fill_color, "bg")

        self.tag_lower("bg")

        # Inner frame sized to account for shadow offset
        pad = 28
        self.coords(self.window_id, pad, pad)
        self.itemconfig(self.window_id, width=max(1, w - s - pad * 2), height=max(1, h - s - pad * 2))


# --- FIXED HD BUTTONS ---
class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, width=165, height=65, color="#6366F1", hover_color="#4F46E5", shadow_color="#4338CA", bg_color="#FFFFFF"):
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
        self._anim_step = 0
        self._anim_id = None
        self.main_tag = f"main_{id(self)}"
        self.shadow_tag = f"shadow_{id(self)}"
        
        x1, y1 = self.pad, self.pad
        x2, y2 = x1 + width, y1 + height

        self.draw_hd_rounded_rect(x1, y1+5, x2, y2, radius=22, fill_color=shadow_color, tags=self.shadow_tag)
        self.draw_hd_rounded_rect(x1, y1, x2, y2-5, radius=22, fill_color=color, tags=self.main_tag)
        
        self.text_id = self.create_text(x1 + width/2, y1 + (height-5)/2, text=text, fill="#FFFFFF", font=("Segoe UI", 14, "bold"))
        
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

    def _cancel_anim(self):
        if self._anim_id is not None:
            try:
                self.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None

    def _animate_hover(self, target, step, steps=8):
        """Smoothly interpolate button color toward target."""
        if step > steps:
            self.itemconfig(self.main_tag, fill=target)
            return
        source = self.color if target == self.hover_color else self.hover_color
        t = step / steps
        # Ease-in-out
        t = t * t * (3 - 2 * t)
        color = lerp_color(source, target, t)
        self.itemconfig(self.main_tag, fill=color)
        self._anim_id = self.after(16, self._animate_hover, target, step + 1, steps)

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
        self._cancel_anim()
        self._animate_hover(self.hover_color, 0)

    def on_leave(self, event):
        self.is_hovered = False
        self._cancel_anim()
        self._animate_hover(self.color, 0)
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
    def __init__(self, parent, command=None, width=320, height=55, bg_color="#FFFFFF", on_color="#6366F1", off_color="#94A3B8"):
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
        self._anim_id = None
        
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

    def _cancel_anim(self):
        if self._anim_id is not None:
            try:
                self.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None

    def _animate_toggle(self, start_x, end_x, start_color, end_color, step, steps=10):
        if step > steps:
            self.coords(self.oval, end_x, self.pad + 6, end_x + self.knob_radius, self.pad + 6 + self.knob_radius)
            self.itemconfig(self.bg_tag, fill=end_color)
            return
        t = step / steps
        # Ease-out cubic for snappy feel
        t_eased = 1 - (1 - t) ** 3
        x = start_x + (end_x - start_x) * t_eased
        self.coords(self.oval, x, self.pad + 6, x + self.knob_radius, self.pad + 6 + self.knob_radius)
        color = lerp_color(start_color, end_color, t)
        self.itemconfig(self.bg_tag, fill=color)
        self._anim_id = self.after(14, self._animate_toggle, start_x, end_x, start_color, end_color, step + 1, steps)

    def toggle(self, event=None):
        self.is_on = not self.is_on
        x1 = self.pad
        
        if self.is_on:
            self.itemconfig(self.text_id, text="Sentence Mode")
            self.coords(self.text_id, x1 + self.w/2 - 25, self.pad + self.h/2)
            start_x = x1 + 6
            end_x = x1 + self.w - self.knob_radius - 6
            start_color, end_color = self.off_color, self.on_color
        else:
            self.itemconfig(self.text_id, text="Spelling Mode")
            self.coords(self.text_id, x1 + self.w/2 + 25, self.pad + self.h/2)
            start_x = x1 + self.w - self.knob_radius - 6
            end_x = x1 + 6
            start_color, end_color = self.on_color, self.off_color

        self._cancel_anim()
        self._animate_toggle(start_x, end_x, start_color, end_color, 0)

        if self.command:
            self.command(self.is_on)


# --- GUI SETUP ---
root = tk.Tk()
root.title("SignSpeak")

try:
    root.state('zoomed') 
except tk.TclError:
    root.attributes('-zoomed', True)

BG_MAIN = "#F0F2FA"        # Soft indigo-tinted background
BG_MAIN_RGB = (0xF0, 0xF2, 0xFA)   # Pre-converted RGB for image operations
CARD_BG = "#FFFFFF"         # Pure white cards
TEXT_BLACK = "#1E1B4B"      # Deep indigo-black (replaces pure black)
TEXT_MED = "#6366F1"        # Indigo for medium-emphasis text
PRIMARY_BLUE = "#6366F1"    # Indigo primary (replaces old blue)
PRIMARY_BLUE_HOVER = "#4F46E5"   # Darker indigo for hover
PRIMARY_BLUE_SHADOW = "#4338CA"  # Darkest indigo for shadow

# Extended palette for button variety
BTN_SKY = "#0EA5E9"
BTN_SKY_HOVER = "#0284C7"
BTN_SKY_SHADOW = "#0369A1"
BTN_VIOLET = "#8B5CF6"
BTN_VIOLET_HOVER = "#7C3AED"
BTN_VIOLET_SHADOW = "#6D28D9"
BTN_EMERALD = "#10B981"
BTN_EMERALD_HOVER = "#059669"
BTN_EMERALD_SHADOW = "#047857"
BTN_CORAL = "#F43F5E"
BTN_CORAL_HOVER = "#E11D48"
BTN_CORAL_SHADOW = "#BE123C"

FONT_TITLE = ("Segoe UI", 54, "bold")
FONT_SUBTITLE = ("Segoe UI", 20, "italic")
FONT_LABEL = ("Segoe UI", 17, "bold")
FONT_VALUE = ("Segoe UI", 26, "bold")

root.configure(bg=BG_MAIN)

current_alphabet = StringVar(value="")
current_word = StringVar(value="")
is_paused = StringVar(value="False")
is_sentence_mode = StringVar(value="False")

# Header
header_frame = Frame(root, bg=BG_MAIN)
header_frame.pack(fill="x", pady=(22, 8))

# Decorative accent row above title
accent_row = Frame(header_frame, bg=BG_MAIN)
accent_row.pack()
Label(accent_row, text="✋", font=("Segoe UI", 28), bg=BG_MAIN, fg=PRIMARY_BLUE).pack(side="left", padx=(0, 8))
Label(accent_row, text="ASL · SIGN RECOGNITION", font=("Segoe UI", 11, "bold"), fg=BTN_VIOLET, bg=BG_MAIN, padx=12, pady=4).pack(side="left")
Label(accent_row, text="✋", font=("Segoe UI", 28), bg=BG_MAIN, fg=PRIMARY_BLUE).pack(side="left", padx=(8, 0))

title_label = Label(header_frame, text="SignSpeak", font=FONT_TITLE, fg=TEXT_BLACK, bg=BG_MAIN)
title_label.pack(pady=(4, 0))

subtitle_label = Label(header_frame, text="Giving voice to every gesture", font=FONT_SUBTITLE, fg=TEXT_MED, bg=BG_MAIN)
subtitle_label.pack()

# Thin decorative divider under subtitle
divider_canvas = tk.Canvas(header_frame, width=120, height=4, bg=BG_MAIN, highlightthickness=0)
divider_canvas.pack(pady=(6, 0))
divider_canvas.create_rectangle(0, 1, 40, 4, fill=BTN_VIOLET, outline="")
divider_canvas.create_rectangle(44, 1, 76, 4, fill=PRIMARY_BLUE, outline="")
divider_canvas.create_rectangle(80, 1, 120, 4, fill=BTN_SKY, outline="")

# --- VIEW SWITCHER LOGIC ---
is_chat_mode = tk.BooleanVar(value=False)

def toggle_view():
    if is_chat_mode.get():
        chat_frame.pack_forget()
        main_frame.pack(expand=True, fill="both")
        toggle_view_btn.config_text("💬 AI Teacher")
        toggle_view_btn.config_color(main=BTN_VIOLET, hover=BTN_VIOLET_HOVER, shadow=BTN_VIOLET_SHADOW)
        is_chat_mode.set(False)
    else:
        main_frame.pack_forget()
        chat_frame.pack(expand=True, fill="both")
        toggle_view_btn.config_text("📷 Recognition")
        toggle_view_btn.config_color(main=BTN_SKY, hover=BTN_SKY_HOVER, shadow=BTN_SKY_SHADOW)
        is_chat_mode.set(True)
    root.update_idletasks()

toggle_view_btn = RoundedButton(header_frame, "💬 AI Teacher", toggle_view, width=190, height=48, color=BTN_VIOLET, hover_color=BTN_VIOLET_HOVER, shadow_color=BTN_VIOLET_SHADOW, bg_color=BG_MAIN)
toggle_view_btn.pack(pady=(10, 0))

# --- VIEW CONTAINER ---
# This ensures that main_frame and chat_frame always occupy the same space
content_container = Frame(root, bg=BG_MAIN)
content_container.pack(expand=True, fill="both", padx=35, pady=(5, 35))

# Main Container
main_frame = Frame(content_container, bg=BG_MAIN)
main_frame.pack(expand=True, fill="both")

main_frame.grid_columnconfigure(0, weight=1) 
main_frame.grid_columnconfigure(1, weight=1) 
main_frame.grid_rowconfigure(0, weight=1)

# --- LEFT BLOCK (Responsive Rounded Video Card) ---
left_card = ResponsiveRoundedCard(main_frame, bg_color=CARD_BG, radius=35)
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
right_card = ResponsiveRoundedCard(main_frame, bg_color=CARD_BG, radius=35)
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
sentence_text_widget = tk.Text(output_frame, font=("Segoe UI", 30, "bold"), fg=TEXT_BLACK, bg=CARD_BG, wrap="word", bd=0, highlightthickness=0, padx=5, pady=8, spacing1=4, spacing3=4)
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
        pause_button.config_color(main=BTN_SKY, hover=BTN_SKY_HOVER, shadow=BTN_SKY_SHADOW)
    else:
        is_paused.set("False")
        pause_button.config_text("⏸ Pause")
        pause_button.config_color(main=PRIMARY_BLUE, hover=PRIMARY_BLUE_HOVER, shadow=PRIMARY_BLUE_SHADOW)

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

reset_button = RoundedButton(bottom_frame, "🔄 Reset", reset_sentence, width=160, bg_color=CARD_BG, color=BTN_SKY, hover_color=BTN_SKY_HOVER, shadow_color=BTN_SKY_SHADOW)
reset_button.grid(row=0, column=0, padx=5, pady=10)

pause_button = RoundedButton(bottom_frame, "⏸ Pause", toggle_pause, width=160, bg_color=CARD_BG, color=PRIMARY_BLUE, hover_color=PRIMARY_BLUE_HOVER, shadow_color=PRIMARY_BLUE_SHADOW)
pause_button.grid(row=0, column=1, padx=5, pady=10)

backspace_button = RoundedButton(bottom_frame, "⌫ Backspace", backspace, width=175, bg_color=CARD_BG, color=BTN_VIOLET, hover_color=BTN_VIOLET_HOVER, shadow_color=BTN_VIOLET_SHADOW)
backspace_button.grid(row=0, column=2, padx=5, pady=10)

speak_button = RoundedButton(bottom_frame, "🔊 Speak", lambda: speak_text("".join(sentence_parts)), width=160, bg_color=CARD_BG, color=BTN_EMERALD, hover_color=BTN_EMERALD_HOVER, shadow_color=BTN_EMERALD_SHADOW)
speak_button.grid(row=0, column=3, padx=5, pady=10)

# --- AI CHATBOT FRAME ---
chat_frame = Frame(content_container, bg=BG_MAIN)
# (Hidden by default, shown via toggle_view)

chat_card = ResponsiveRoundedCard(chat_frame, bg_color=CARD_BG, radius=35)
chat_card.pack(expand=True, fill="both")

# --- CHAT UI STRUCTURE (Guaranteeing Button Visibility) ---
# We use a container inside chat_card.inner_frame to manage layout
chat_main_container = Frame(chat_card.inner_frame, bg=CARD_BG)
chat_main_container.pack(expand=True, fill="both")

# 1. Header (Top)
chat_header = Frame(chat_main_container, bg=CARD_BG)
chat_header.pack(side="top", fill="x", pady=(0, 10))
Label(chat_header, text="✨ Sign Language AI Teacher", font=("Segoe UI", 22, "bold"), fg=TEXT_BLACK, bg=CARD_BG).pack(side="left")
Label(chat_header, text="Powered by Gemini", font=("Segoe UI", 11), fg=BTN_VIOLET, bg=CARD_BG).pack(side="left", padx=(12, 0), pady=(4, 0))

# 2. Input Bar (Bottom - Packed FIRST to stay at bottom)
chat_input_frame = Frame(chat_main_container, bg=CARD_BG)
chat_input_frame.pack(side="bottom", fill="x", pady=(10, 0))

# 3. Chat Display (Middle - Takes remaining space)
chat_display_frame = Frame(chat_main_container, bg="#F5F4FF", relief="flat")
chat_display_frame.pack(side="top", expand=True, fill="both", padx=5, pady=5)

chat_history = tk.Text(chat_display_frame, font=("Segoe UI", 12), state="disabled", wrap="word", bg="#F5F4FF", relief="flat", padx=20, pady=16, spacing1=4, spacing2=2, spacing3=8)
chat_history.pack(side="left", fill="both", expand=True)

chat_scroll = tk.Scrollbar(chat_display_frame, command=chat_history.yview)
chat_scroll.pack(side="right", fill="y")
chat_history.config(yscrollcommand=chat_scroll.set)

# Setup tags for styling
chat_history.tag_configure("bold_you", font=("Segoe UI", 13, "bold"), foreground=PRIMARY_BLUE)
chat_history.tag_configure("bold_teacher", font=("Segoe UI", 13, "bold"), foreground=BTN_EMERALD)
chat_history.tag_configure("bold_system", font=("Segoe UI", 11, "bold"), foreground=BTN_VIOLET)
chat_history.tag_configure("you", font=("Segoe UI", 12), foreground="#1E1B4B")
chat_history.tag_configure("teacher", font=("Segoe UI", 12), foreground="#1E1B4B")
chat_history.tag_configure("system", font=("Segoe UI", 10, "italic"), foreground="#94A3B8")

def add_to_chat(sender, message):
    chat_history.config(state="normal")
    tag = sender.lower()
    chat_history.insert(tk.END, f"● {sender}\n", f"bold_{tag}")
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
        root.after(0, lambda: voice_btn.config_color(main=BTN_CORAL, hover=BTN_CORAL_HOVER, shadow=BTN_CORAL_SHADOW))
        
        # This will record until a pause is detected
        voice_text = get_voice_input()
        
        # Reset button state
        root.after(0, lambda: voice_btn.config_text("🎙️ Start Voice"))
        root.after(0, lambda: voice_btn.config_color(main=BTN_EMERALD, hover=BTN_EMERALD_HOVER, shadow=BTN_EMERALD_SHADOW))
        
        if voice_text and voice_text not in ["Could not understand audio", "API unavailable"] and not voice_text.startswith("Error"):
            root.after(0, lambda: chat_entry.delete(0, tk.END))
            root.after(0, lambda: chat_entry.insert(0, voice_text))
            root.after(0, handle_chat_response)
        else:
            root.after(0, lambda: add_to_chat("System", "No speech detected. Click 'Start Voice' again."))
            
    threading.Thread(target=voice_thread, daemon=True).start()

# --- INPUT AREA BUTTONS (Guaranteed placement) ---
voice_btn = RoundedButton(chat_input_frame, "🎙️ Start Voice", handle_voice_chat, width=170, height=55, color=BTN_EMERALD, hover_color=BTN_EMERALD_HOVER, shadow_color=BTN_EMERALD_SHADOW, bg_color=CARD_BG)
voice_btn.pack(side="right", padx=10)

send_btn = RoundedButton(chat_input_frame, "📤 Send", handle_chat_response, width=130, height=55, color=PRIMARY_BLUE, hover_color=PRIMARY_BLUE_HOVER, shadow_color=PRIMARY_BLUE_SHADOW, bg_color=CARD_BG)
send_btn.pack(side="right")

chat_entry = tk.Entry(chat_input_frame, font=("Segoe UI", 15), relief="flat", bg="#EDEDF8", insertbackground=TEXT_BLACK, fg=TEXT_BLACK)
chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=10)

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
        img_rounded = Image.new('RGB', img_pil.size, BG_MAIN_RGB)
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
    img_rounded = Image.new('RGB', img_pil.size, BG_MAIN_RGB)
    img_rounded.paste(img_pil, mask=rounded_mask)

    img_tk = ImageTk.PhotoImage(image=img_rounded)
    video_label.imgtk = img_tk
    video_label.configure(image=img_tk)

    root.after(10, process_frame)

process_frame()
root.mainloop()
