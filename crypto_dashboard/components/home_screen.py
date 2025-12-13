from pathlib import Path
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFilter

from ..config import BG_COLOR, ACCENT_COLOR, TEXT_SECONDARY, SIDEBAR_BG, WINDOW_SIZE

BACKGROUND_VERTICAL_OFFSET = -0.05  # move hero image slightly upward
CTA_SIZE = (360, 80)
CTA_RADIUS = 26
CTA_SHADOW_OFFSET = 10


class HomeScreen:
    """Splash screen with branded background and CTA."""

    def __init__(self, root, on_enter):
        self.root = root
        self.on_enter = on_enter
        self.frame = None
        self._bg_img = None
        self.background_label = None
        self._resize_binding = None
        self._current_size = None
        self._cta_images = None
        self._cta_canvas = None

    def show(self):
        if self.frame:
            return

        self.frame = tk.Frame(self.root, bg=BG_COLOR)
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._render_background()
        if not self._resize_binding:
            self._resize_binding = self.root.bind("<Configure>", self._on_root_resize)

        cta_container = tk.Frame(self.frame, bg=BG_COLOR, highlightthickness=0, bd=0)
        cta_container.place(relx=0.5, rely=0.88, anchor="center")

        self._cta_canvas = self._create_cta_button(cta_container)
        self._cta_canvas.pack()

        tk.Label(
            cta_container,
            text="Powered by Binance real-time feeds • Python UI",
            font=("Arial", 9),
            fg=TEXT_SECONDARY,
            bg=BG_COLOR,
        ).pack(pady=(14, 0))

        self.root.update_idletasks()

    def destroy(self):
        if self.frame:
            self.frame.destroy()
            self.frame = None
            self._bg_img = None
            self.background_label = None
        if self._resize_binding:
            self.root.unbind("<Configure>", self._resize_binding)
            self._resize_binding = None
        self._current_size = None
        self._cta_canvas = None

    def _render_background(self, width=None, height=None):
        if width is None or height is None:
            width, height = self._target_size()
        if width <= 1 or height <= 1:
            return
        new_size = (width, height)
        if self._current_size == new_size:
            return
        if self.background_label is None:
            self.background_label = tk.Label(self.frame, borderwidth=0)

        bg_path = Path(__file__).resolve().parent.parent / "home.png"
        offset_y = int(height * BACKGROUND_VERTICAL_OFFSET)
        if bg_path.exists():
            try:
                img = Image.open(bg_path)
                img = img.resize((width, height), Image.LANCZOS)
                self._bg_img = ImageTk.PhotoImage(img)
                self.background_label.config(image=self._bg_img, bg=BG_COLOR)
                self.background_label.place(x=0, y=offset_y, width=width, height=height)
                self._current_size = new_size
                return
            except Exception:
                pass
        self.background_label.config(image="", bg=BG_COLOR)
        self.background_label.place(x=0, y=offset_y, width=width, height=height)
        self._current_size = new_size

    def _target_size(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width <= 1 or height <= 1:
            try:
                default_w, default_h = WINDOW_SIZE.split("x")
                width = int(default_w)
                height = int(default_h)
            except Exception:
                width, height = 1200, 800
        return width, height

    def _on_root_resize(self, event):
        if event.widget is self.root:
            width = event.width
            height = event.height
            if width > 0 and height > 0:
                self._render_background(width, height)

    def _create_cta_button(self, parent):
        if not self._cta_images:
            self._cta_images = self._generate_cta_images()
        normal_img, hover_img = self._cta_images
        canvas = tk.Canvas(
            parent,
            width=normal_img.width(),
            height=normal_img.height(),
            highlightthickness=0,
            bd=0,
            bg=BG_COLOR,
            cursor="hand2",
        )
        image_item = canvas.create_image(0, 0, anchor="nw", image=normal_img)
        text_item = canvas.create_text(
            normal_img.width() // 2,
            normal_img.height() // 2,
            text="Enter Market Dashboard",
            font=("Arial", 18, "bold"),
            fill="#0f1015",
        )

        def on_click(event=None):
            self.on_enter()

        def on_enter(event=None):
            canvas.itemconfig(image_item, image=hover_img)
            canvas.itemconfig(text_item, fill="#05060a")

        def on_leave(event=None):
            canvas.itemconfig(image_item, image=normal_img)
            canvas.itemconfig(text_item, fill="#0f1015")

        for seq in ("<Button-1>",):
            canvas.bind(seq, on_click)
        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)

        return canvas

    def _generate_cta_images(self):
        normal = self._create_button_image("#e6ae0a", "#c89b0e")
        hover  = self._create_button_image("#f2cd68", "#e6ae0a")
        return normal, hover

    def _create_button_image(self, start_hex, end_hex):
        width, height = CTA_SIZE
        total_w = width + CTA_SHADOW_OFFSET * 2
        total_h = height + CTA_SHADOW_OFFSET * 2

        img = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

        # Shadow
        shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw_shadow = ImageDraw.Draw(shadow)
        draw_shadow.rounded_rectangle(
            (0, 0, width, height), radius=CTA_RADIUS, fill=(0, 0, 0, 160)
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(16))
        img.paste(shadow, (CTA_SHADOW_OFFSET, CTA_SHADOW_OFFSET), shadow)

        # Gradient button
        gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient)
        start_rgb = self._hex_to_rgb(start_hex)
        end_rgb = self._hex_to_rgb(end_hex)
        for y in range(height):
            ratio = y / max(height - 1, 1)
            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

        mask = Image.new("L", (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle((0, 0, width, height), radius=CTA_RADIUS, fill=255)
        gradient.putalpha(mask)

        img.paste(gradient, (CTA_SHADOW_OFFSET, CTA_SHADOW_OFFSET), gradient)



        return ImageTk.PhotoImage(img)

    @staticmethod
    def _hex_to_rgb(value):
        value = value.lstrip("#")
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))
