import tkinter as tk
from tkinter import ttk
import websocket
import json
import threading
from ..config import WS_BASE_URL, BG_COLOR, CARD_COLOR, TEXT_COLOR, TEXT_SECONDARY, COLOR_BUY, COLOR_SELL, FONT_SUBTITLE

class VolumeStatsPanel(tk.Frame):
    def __init__(self, parent, symbol):
        super().__init__(parent, bg=CARD_COLOR, padx=10, pady=10)
        self.symbol = symbol.lower()
        self.is_active = False
        self.ws = None
        
        # Grid layout
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        
        # 5 Mins stats
        self._create_stat_box("5mins Volume & ratio", 0, 0)
        
        # 1 Hour stats
        self._create_stat_box("1HRS Volume & ratio", 0, 1)
        
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
        self._setup_labels(0, "5m")
        self._setup_labels(1, "1h")

    def _create_stat_box(self, title, row, col):
        frame = tk.Frame(self, bg=CARD_COLOR, highlightbackground="gray", highlightthickness=1)
        frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        tk.Label(frame, text=title, bg=CARD_COLOR, fg=TEXT_COLOR, font=("Arial", 12)).pack(anchor="w", padx=5, pady=5)
        return frame

    def _setup_labels(self, col, prefix):
        # We need to access the frame created in _create_stat_box. 
        # Since I didn't save it, let's just create the labels directly in the grid cell
        # Actually proper way:
        frame = self.grid_slaves(row=0, column=col)[0]
        
        tk.Label(frame, text="BUYS:", bg=CARD_COLOR, fg=TEXT_SECONDARY).pack(anchor="w", padx=5)
        l1 = tk.Label(frame, textvariable=self.vars[f"{prefix}_buy"], bg=CARD_COLOR, fg=COLOR_BUY, font=("Arial", 12, "bold"))
        l1.pack(anchor="w", padx=5)
        
        tk.Label(frame, text="SELLS:", bg=CARD_COLOR, fg=TEXT_SECONDARY).pack(anchor="w", padx=5)
        l2 = tk.Label(frame, textvariable=self.vars[f"{prefix}_sell"], bg=CARD_COLOR, fg=COLOR_SELL, font=("Arial", 12, "bold"))
        l2.pack(anchor="w", padx=5)
        
        tk.Label(frame, text="RATIO:", bg=CARD_COLOR, fg=TEXT_SECONDARY).pack(anchor="w", padx=5)
        l3 = tk.Label(frame, textvariable=self.vars[f"{prefix}_ratio"], bg=CARD_COLOR, fg=TEXT_COLOR, font=("Arial", 12, "bold"))
        l3.pack(anchor="w", padx=5)

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
