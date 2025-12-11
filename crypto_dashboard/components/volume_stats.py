import tkinter as tk
from tkinter import ttk
import websocket
import json
import threading
from ..config import WS_BASE_URL, BG_COLOR, CARD_COLOR, TEXT_COLOR, TEXT_SECONDARY, COLOR_BUY, COLOR_SELL, FONT_SUBTITLE

class VolumeStatsPanel(tk.Frame):
    def __init__(self, parent, symbol):
        # Add border
        super().__init__(parent, bg=CARD_COLOR, padx=10, pady=5, highlightthickness=1, highlightbackground="gray30")
        self.symbol = symbol.lower()
        self.is_active = False
        self.ws = None
        
        # Use grid for internal layout
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        
        # 5m Stats
        self.f5 = tk.Frame(self, bg=CARD_COLOR)
        self.f5.grid(row=0, column=0, padx=10, sticky="nsew")
        self._create_header_box(self.f5, "5m Volume & Ratio")
        
        # 1h Stats
        self.f1 = tk.Frame(self, bg=CARD_COLOR)
        self.f1.grid(row=0, column=1, padx=10, sticky="nsew")
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
        box_color = "#252930"
        f = tk.Frame(parent, bg=box_color, padx=5, pady=5)
        f.pack(fill=tk.X, pady=(0, 10))
        tk.Label(f, text=text, font=("Arial", 9, "bold"), fg=TEXT_SECONDARY, bg=box_color).pack(anchor="w")

    def _create_stat_panel(self, parent, title, var_name, color):
        # Container
        container = tk.Frame(parent, bg=CARD_COLOR)
        container.pack(fill=tk.X, pady=2)
        
        # Box
        box_color = "#252930"
        frame = tk.Frame(container, bg=box_color, padx=10, pady=5)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text=title, font=("Arial", 9), fg=TEXT_SECONDARY, bg=box_color, anchor="w").pack(fill=tk.X)
        tk.Label(frame, textvariable=self.vars[var_name], font=("Arial", 12, "bold"), fg=color, bg=box_color, anchor="w").pack(fill=tk.X)

    def _setup_labels(self, parent, prefix):
        self._create_stat_panel(parent, "BUYS", f"{prefix}_buy", COLOR_BUY)
        self._create_stat_panel(parent, "SELLS", f"{prefix}_sell", COLOR_SELL)
        self._create_stat_panel(parent, "RATIO", f"{prefix}_ratio", TEXT_COLOR)

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
        self.ws.run_forever()

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
