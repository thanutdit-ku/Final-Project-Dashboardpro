import tkinter as tk
from tkinter import ttk
import websocket
import json
import threading
from datetime import datetime
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
    FONT_SUBTITLE,
    FONT_BODY,
)

class TradesFeedPanel(tk.Frame):
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
        
        # Header
        box_color = CARD_HEADER_BG
        header_frame = tk.Frame(
            self,
            bg=box_color,
            padx=16,
            pady=10,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
        )
        header_frame.pack(fill=tk.X, pady=(0, 8))
        
        header = tk.Label(
            header_frame,
            text="Recent Trades",
            bg=box_color,
            fg=TEXT_COLOR,
            font=("Arial", 12, "bold"),
            anchor="w",
        )  # Bold title
        header.pack(fill=tk.X)
        tk.Frame(header_frame, height=2, bg=ACCENT_COLOR).pack(fill=tk.X, pady=(8, 0))
        
        # Header Columns
        col_frame = tk.Frame(self, bg=CARD_COLOR)
        col_frame.pack(fill=tk.X, padx=12, pady=(0, 6))
        col_frame.grid_columnconfigure(0, weight=1)
        col_frame.grid_columnconfigure(1, weight=1)
        col_frame.grid_columnconfigure(2, weight=1)
        
        tk.Label(col_frame, text="Price", anchor="w", bg=CARD_COLOR, fg=TEXT_SECONDARY).grid(row=0, column=0, sticky="ew")
        tk.Label(col_frame, text="Amount", anchor="e", bg=CARD_COLOR, fg=TEXT_SECONDARY).grid(row=0, column=1, sticky="ew")
        # Increase right padding to prevent overlap with main scrollbar
        tk.Label(col_frame, text="Time", anchor="e", bg=CARD_COLOR, fg=TEXT_SECONDARY).grid(row=0, column=2, sticky="ew", padx=(5, 20))
        
        # Trades List (Canvas or just simplistic labels list for performance)
        # Using a fixed number of rows for simplicity and performance
        self.rows = []
        self.max_rows = 15
        
        self.list_frame = tk.Frame(self, bg=CARD_COLOR)
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        
        for _ in range(self.max_rows):
            row = self._create_row()
            self.rows.append(row)
            
        self.trade_data = [] # Store trade data history
            
    def _create_row(self):
        f = tk.Frame(self.list_frame, bg=CARD_COLOR)
        f.pack(fill=tk.X, pady=1) # Pack once and stay
        f.grid_columnconfigure(0, weight=1)
        f.grid_columnconfigure(1, weight=1)
        f.grid_columnconfigure(2, weight=1)
        
        price = tk.Label(f, text="--", anchor="w", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_BODY)
        price.grid(row=0, column=0, sticky="ew")
        
        amt = tk.Label(f, text="--", anchor="e", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_BODY)
        amt.grid(row=0, column=1, sticky="ew")
        
        time_lbl = tk.Label(f, text="--", anchor="e", bg=CARD_COLOR, fg=TEXT_SECONDARY, font=("Arial", 9))
        time_lbl.grid(row=0, column=2, sticky="ew", padx=(5, 20))
        
        return {"price": price, "amt": amt, "time": time_lbl}

    def start(self):
        if self.is_active: return
        self.is_active = True
        
        ws_url = f"{WS_BASE_URL}/{self.symbol}@trade"
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=lambda ws, err: None,
            on_close=lambda ws, s, m: None
        )
        threading.Thread(target=self._run_forever, daemon=True).start()

    def _run_forever(self):
        if self.ws:
            self.ws.run_forever(sslopt=WS_SSL_OPTIONS)

    def stop(self):
        self.is_active = False
        if self.ws: self.ws.close()

    def on_message(self, ws, message):
        if not self.is_active: return
        try:
            data = json.loads(message)
            self.after(0, self.add_trade, data)
        except Exception:
            pass
            
    def add_trade(self, data):
        if not self.is_active: return
        
        price = float(data['p'])
        qty = float(data['q'])
        is_buyer_maker = data['m'] 
        
        side = "SELL" if is_buyer_maker else "BUY"
        color = COLOR_SELL if side == "SELL" else COLOR_BUY
        time_str = datetime.fromtimestamp(data['T'] / 1000).strftime('%H:%M:%S')
        
        # Add to local history
        self.trade_data.insert(0, {
            "price": f"{price:.2f}",
            "qty": f"{qty:.4f}",
            "time": time_str,
            "color": color
        })
        
        if len(self.trade_data) > self.max_rows:
            self.trade_data.pop()
            
        # Update widgets
        for i, trade in enumerate(self.trade_data):
            if i >= len(self.rows): break
            row = self.rows[i]
            row["price"].config(text=trade["price"], fg=trade["color"])
            row["amt"].config(text=trade["qty"])
            row["time"].config(text=trade["time"])
