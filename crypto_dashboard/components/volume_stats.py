import tkinter as tk
from tkinter import ttk
import websocket
import json
import threading
from ..config import (
    WS_BASE_URL,
    WS_SSL_OPTIONS,
    CARD_COLOR,
    CARD_HEADER_BG,
    BORDER_COLOR,
    ACCENT_COLOR,
    TEXT_COLOR,
    TEXT_SECONDARY,
    COLOR_BUY,
    COLOR_SELL,
)

class VolumeStatsPanel(tk.Frame):
    def __init__(self, parent, symbol):
        # Add border
        super().__init__(
            parent,
            bg=CARD_COLOR,
            padx=1,
            pady=1,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
        )
        self.symbol = symbol.lower()
        self.is_active = False
        self.ws = None
        
        # Use grid for internal layout; spare middle column acts as spacer
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0, minsize=8)
        self.columnconfigure(2, weight=1)
        
        # 5m Stats
        self.f5 = tk.Frame(self, bg=CARD_COLOR)
        self.f5.grid(row=0, column=0, padx=(12, 6), pady=6, sticky="nsew")
        self.f5.grid_columnconfigure(0, weight=1)
        self._create_header_box(self.f5, "5m Volume & Ratio")
        
        # 1h Stats
        self.f1 = tk.Frame(self, bg=CARD_COLOR)
        self.f1.grid(row=0, column=2, padx=(6, 12), pady=6, sticky="nsew")
        self.f1.grid_columnconfigure(0, weight=1)
        self._create_header_box(self.f1, "1h Volume & Ratio")
        
        # Datan Vars
        self.vars = {
            "5m_buy": tk.StringVar(value="--"),
            "5m_sell": tk.StringVar(value="--"),
            "5m_ratio": tk.StringVar(value="--"),
            "1h_buy": tk.StringVar(value="--"),
            "1h_sell": tk.StringVar(value="--"),
            "1h_ratio": tk.StringVar(value="--"),
        }
        
        # Labels mapping for updating
        self.labels = {}
        self._setup_labels(self.f5, "5m")
        self._setup_labels(self.f1, "1h")

    def _create_header_box(self, parent, text):
        box_color = CARD_HEADER_BG
        f = tk.Frame(
            parent,
            bg=box_color,
            padx=14,
            pady=12,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
        )
        f.grid(row=0, column=0, sticky="nsew", padx=8, pady=(0, 8))
        tk.Label(
            f,
            text=text,
            font=("Arial", 9, "bold"),
            fg=TEXT_SECONDARY,
            bg=box_color,
        ).pack(anchor="w", pady=(0, 8))
        tk.Frame(f, height=2, bg=ACCENT_COLOR).pack(fill=tk.X, pady=(4, 0))

    def _create_stat_panel(self, parent, row, title, var_name, color, is_last=False):
        box_color = CARD_HEADER_BG
        frame = tk.Frame(
            parent,
            bg=box_color,
            padx=16,
            pady=12,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
        )
        pady = (0, 0 if is_last else 8)
        frame.grid(row=row, column=0, sticky="nsew", padx=8, pady=pady)
        
        tk.Label(
            frame,
            text=title,
            font=("Arial", 10, "bold"),
            fg=TEXT_SECONDARY,
            bg=box_color,
            anchor="w",
        ).pack(fill=tk.X, pady=(0, 4))
        tk.Label(
            frame,
            textvariable=self.vars[var_name],
            font=("Arial", 14, "bold"),
            fg=color,
            bg=box_color,
            anchor="w",
        ).pack(fill=tk.X)

    def _setup_labels(self, parent, prefix):
        entries = [
            ("BUYS", f"{prefix}_buy", COLOR_BUY),
            ("SELLS", f"{prefix}_sell", COLOR_SELL),
            ("RATIO", f"{prefix}_ratio", TEXT_COLOR),
        ]
        for idx, (title, var_name, color) in enumerate(entries, start=1):
            is_last = idx == len(entries)
            parent.grid_rowconfigure(idx, weight=1)
            self._create_stat_panel(parent, idx, title, var_name, color, is_last)

    def start(self):
        if self.is_active: return
        self.is_active = True
        threading.Thread(target=self._run_socket, daemon=True).start()

    def _run_socket(self):
        # Use aggTrade to calculate volume? or just mock for now?
        # The prompt asks for volume buys/sells. This is complex to calculate from raw streams without heavy processing.
        # Alternatively, use Ticker? Ticker only has total volume.
        # Let's use AggTrade and accumulate in memory for a simplified version.
        # OR use kline data: kline contains 'taker buy base asset volume'.
        # Total Volume - Taker Buy Volume = Taker Sell Volume (approx).
        
        # kline_5m and kline_1h
        ws_url = f"{WS_BASE_URL}/{self.symbol}@kline_5m/{self.symbol}@kline_1h"
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=lambda ws, err: print(f"Vol Error: {err}"),
            on_close=lambda ws, s, m: print("Vol Closed")
        )
        self.ws.run_forever(sslopt=WS_SSL_OPTIONS)

    def stop(self):
        self.is_active = False
        if self.ws: self.ws.close()

    def on_message(self, ws, message):
        if not self.is_active: return
        try:
            data = json.loads(message)
            if 'e' in data and data['e'] == 'kline':
                # kline data
                k = data['k']
                interval = k['i']
                
                vol = float(k['v'])
                buy_vol = float(k['Q']) # Taker buy quote asset volume
                quote_vol = float(k['q']) # Total quote asset volume
                
                # Close enough approximation for "Buys" vs "Sells"
                # Buys = Taker buy volume
                # Sells = Total volume - Taker buy volume
                
                buys = buy_vol
                sells = quote_vol - buy_vol
                
                prefix = "5m" if interval == "5m" else "1h"
                
                self.after(0, self.update_vars, prefix, buys, sells)
                
        except Exception:
            pass

    def update_vars(self, prefix, buys, sells):
        if not self.is_active: return
        ratio = buys / sells if sells > 0 else 0
        
        self.vars[f"{prefix}_buy"].set(f"{buys:,.2f}")
        self.vars[f"{prefix}_sell"].set(f"{sells:,.2f}")
        self.vars[f"{prefix}_ratio"].set(f"{ratio:.3f}")
