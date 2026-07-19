import tkinter as tk
from PIL import Image, ImageTk
import os

class BRXVEngine:
    def __init__(self):
        self.root = None
        self.canvas = None
        self.elements = []
        self.sprites = []
        self.is_open = False

    def init_window(self, width=800, height=600, title="BRX Window", bg="#1a1a2e"):
        if self.root: return
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(f"{width}x{height}")
        self.root.configure(bg=bg)
        self.canvas = tk.Canvas(self.root, width=width, height=height, bg=bg, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.is_open = True
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.is_open = False
        if self.root:
            self.root.destroy()
            self.root = None

    def add_text(self, text, x, y, size=16, color="#FFFFFF"):
        if not self.canvas: return
        self.canvas.create_text(x, y, text=text, font=("Arial", size), fill=color, anchor="nw")

    def add_button(self, text, x, y, w, h, callback=None):
        if not self.root: return
        btn = tk.Button(self.root, text=text, command=callback)
        btn.place(x=x, y=y, width=w, height=h)

    def add_rect(self, x, y, w, h, color="#FFFFFF"):
        if not self.canvas: return
        self.canvas.create_rectangle(x, y, x+w, y+h, fill=color, outline="")

    def add_sprite(self, path, x, y, w=None, h=None, color="#FF0000"):
        if not self.canvas: return
        sprite = {
            'x': x, 'y': y, 'vx': 0, 'vy': 0, 'id': None, 'path': path,
            'w': w or 40, 'h': h or 40, 'color': color
        }
        if path and os.path.exists(path):
            try:
                img = Image.open(path)
                if w and h: img = img.resize((w, h))
                tk_img = ImageTk.PhotoImage(img)
                sprite['tk_img'] = tk_img
                sprite['id'] = self.canvas.create_image(x, y, image=tk_img, anchor="nw")
            except:
                sprite['id'] = self.canvas.create_rectangle(x, y, x+(w or 40), y+(h or 40), fill=color, outline="")
        else:
            sprite['id'] = self.canvas.create_rectangle(x, y, x+(w or 40), y+(h or 40), fill=color, outline="")
        
        self.sprites.append(sprite)
        return sprite

    def update_sprites(self):
        for s in self.sprites:
            s['x'] += s['vx']
            s['y'] += s['vy']
            if self.canvas and s['id']:
                self.canvas.coords(s['id'], s['x'], s['y'])

    def render(self):
        if self.root:
            self.root.update_idletasks()
            self.root.update()

    def wait(self, ms):
        if self.root:
            self.root.after(ms)
            self.render()
