import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk

from ..config import (
    BG_COLOR,
    ACCENT_COLOR,
    COLOR_SELL,
    TEXT_COLOR,
    TEXT_SECONDARY,
)


class HomeScreen:
    """Standalone landing screen overlay shown before dashboard loads."""

    def __init__(self, root, on_enter):
        self.root = root
        self.on_enter = on_enter
        self.frame = tk.Frame(self.root, bg=BG_COLOR)
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.logo_photo = None
        self._build_layout()

    def _build_layout(self):
        top_bar = tk.Frame(self.frame, bg="#060b16", height=60)
        top_bar.pack(fill="x", side="top")
        top_bar.pack_propagate(False)
        tk.Label(
            top_bar,
            text="CRYPTO DASHBOARD • ALPHA ACCESS",
            font=("Arial", 11, "bold"),
            fg="#f7f9fb",
            bg="#060b16",
            anchor="center",
        ).pack(fill="both")

        self.frame.configure(bg="#03050b")
        hero_surface = tk.Frame(self.frame, bg="#04060f")
        hero_surface.pack(fill="both", expand=True)
        hero_surface.columnconfigure(0, weight=3)
        hero_surface.columnconfigure(1, weight=2)
        hero_surface.rowconfigure(0, weight=1)

        left_bg = tk.Frame(hero_surface, bg="#0c1429", padx=50, pady=50)
        left_bg.grid(row=0, column=0, sticky="nsew", padx=(50, 25), pady=(40, 20))
        left_bg.columnconfigure(0, weight=1)

        hero = left_bg
        hero.columnconfigure(0, weight=1)

        logo_path = Path(__file__).resolve().parent.parent / "crypto-Photoroom.png"
        if logo_path.exists():
            try:
                img = Image.open(logo_path)
                img.thumbnail((200, 180), Image.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(img)
                tk.Label(hero, image=self.logo_photo, bg="#0b1220").pack(pady=(0, 20))
            except Exception:
                tk.Label(
                    hero,
                    text="CRYPTO\nDASHBOARD",
                    font=("Arial", 26, "bold"),
                    fg=ACCENT_COLOR,
                    bg="#0b1220",
                ).pack(pady=(0, 20))
        else:
            tk.Label(
                hero,
                text="CRYPTO\nDASHBOARD",
                font=("Arial", 26, "bold"),
                fg=ACCENT_COLOR,
                bg="#0b1220",
            ).pack(pady=(0, 20))

        tk.Label(
            hero,
            text="Premium Quant Terminal",
            font=("Arial", 18, "bold"),
            fg=TEXT_COLOR,
            bg="#0b1220",
        ).pack()
        tk.Label(
            hero,
            text="Monitor spot majors, macro sentiment, and curated flows\nbefore committing capital.",
            font=("Arial", 11),
            fg=TEXT_SECONDARY,
            bg="#0b1220",
            justify="center",
        ).pack(pady=(10, 25))

        cta = tk.Button(
            hero,
            text="Launch Trading Desk",
            font=("Arial", 12, "bold"),
            bg=ACCENT_COLOR,
            fg="#0c1016",
            activebackground="#ffd84d",
            activeforeground="#0c1016",
            relief="flat",
            padx=60,
            pady=14,
            command=self._handle_enter,
        )
        cta.pack(pady=(20, 10))

        tk.Label(
            hero,
            text="Live Binance feeds • Last refreshed just now",
            font=("Arial", 9),
            fg=TEXT_SECONDARY,
            bg="#0b1220",
        ).pack()

        stats_panel = tk.Frame(hero_surface, bg="#04060f")
        stats_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 50), pady=(40, 20))
        stats_panel.columnconfigure((0, 1), weight=1)
        stats_panel.rowconfigure((0, 1), weight=1)

        stat_data = [
            ("BTC/USD", "$90,418", "+0.42%", ACCENT_COLOR),
            ("ETH/USD", "$3,114", "-1.86%", COLOR_SELL),
            ("Solana Heat", "78%", "Momentum", "#7dd3fc"),
            ("Fear & Greed", "61", "Greed", "#a78bfa"),
        ]

        for idx, (title, value, change, color) in enumerate(stat_data):
            frame = tk.Frame(
                stats_panel,
                bg="#0e1524",
                padx=18,
                pady=16,
                highlightthickness=1,
                highlightbackground="#1c2434",
            )
            frame.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=10, pady=10)
            stats_panel.rowconfigure(idx // 2, weight=1)
            tk.Label(
                frame,
                text=title,
                font=("Arial", 10, "bold"),
                fg=TEXT_SECONDARY,
                bg="#0e1524",
            ).pack(anchor="w")
            tk.Label(
                frame,
                text=value,
                font=("Arial", 18, "bold"),
                fg=TEXT_COLOR,
                bg="#0e1524",
            ).pack(anchor="w", pady=(4, 0))
            tk.Label(
                frame,
                text=change,
                font=("Arial", 10, "bold"),
                fg=color,
                bg="#0e1524",
            ).pack(anchor="w", pady=(2, 0))

        ticker = tk.Frame(self.frame, bg="#05070f", pady=8)
        ticker.pack(fill="x", side="bottom")
        ticker_items = [
            ("DXY", "102.4", "-0.32%"),
            ("S&P Fut", "4,832", "+0.25%"),
            ("BTC Dom", "59.3%", "+0.14%"),
            ("Alt Heat", "1.18", "-1.02%"),
        ]
        for item in ticker_items:
            block = tk.Frame(ticker, bg="#05070f", padx=18)
            block.pack(side="left")
            tk.Label(block, text=item[0], font=("Arial", 9, "bold"), fg=TEXT_SECONDARY, bg="#05070f").pack(anchor="w")
            tk.Label(block, text=item[1], font=("Arial", 12, "bold"), fg=TEXT_COLOR, bg="#05070f").pack(anchor="w")
            tk.Label(block, text=item[2], font=("Arial", 9, "bold"), fg=ACCENT_COLOR if "+" in item[2] else COLOR_SELL, bg="#05070f").pack(anchor="w")

        strip = tk.Frame(self.frame, bg="#03040a")
        strip.pack(fill="x", side="bottom")
        canvas = tk.Canvas(strip, height=140, bg="#03040a", highlightthickness=0)
        canvas.pack(fill="x", padx=40, pady=(0, 10))
        width = 1200
        candles = 30
        spacing = width / candles
        for i in range(candles):
            x = 20 + i * spacing
            high = 20 + (i % 5) * 5
            low = high + 50 + (i % 3) * 8
            open_y = high + 10
            close_y = low - 10
            bullish = i % 3 != 0
            color = "#34d399" if bullish else "#f87171"
            canvas.create_line(x, high, x, low, fill=color, width=2)
            canvas.create_rectangle(x - 5, open_y, x + 5, close_y, fill=color, outline=color)

    def _handle_enter(self):
        if callable(self.on_enter):
            self.on_enter()

    def destroy(self):
        if self.frame:
            self.frame.destroy()
            self.frame = None
