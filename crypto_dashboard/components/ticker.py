import tkinter as tk
from tkinter import ttk
import websocket
import json
import threading
from ..config import WS_BASE_URL, FONT_TITLE, FONT_SUBTITLE, FONT_NUMBERS, BG_COLOR, CARD_COLOR, TEXT_COLOR, TEXT_SECONDARY, COLOR_BUY, COLOR_SELL, COLOR_NEUTRAL

class CryptoTicker(tk.Frame):
    """
    Header component showing: Last Price | Bids | Asks | 24h High | 24h Low | 24h Vol
    """
    
    def __init__(self, parent, symbol, display_name):
        super().__init__(parent, bg=CARD_COLOR, padx=20, pady=10)
        self.symbol = symbol.lower()
        self.is_active = False
        self.ws = None
        
        # Grid Layout
        for i in range(6): 
            self.columnconfigure(i, weight=1)
        
        # 1. Last Price
        self._create_stat_panel("LAST PRICE", 0, "price_label", TEXT_COLOR, font_val=FONT_TITLE)
        
        # 2. Bids Panel
        self._create_stat_panel("BIDS(BUYS)", 1, "bid_label", COLOR_BUY, font_val=FONT_TITLE)
        
        # 3. Asks Panel
        self._create_stat_panel("ASKS(SELL)", 2, "ask_label", COLOR_SELL, font_val=FONT_TITLE)

        # 4. 24h High
        self._create_stat_panel("24h HIGH", 3, "high_label", TEXT_COLOR, font_val=FONT_SUBTITLE)
        
        # 5. 24h Low
        self._create_stat_panel("24h LOW", 4, "low_label", TEXT_COLOR, font_val=FONT_SUBTITLE)
        
        # 6. 24h Volume
        self._create_stat_panel("24h VOL", 5, "vol_label", TEXT_COLOR, font_val=FONT_SUBTITLE)
        
    def _create_stat_panel(self, title, col, var_name, color, font_val):
        frame = tk.Frame(self, bg=CARD_COLOR)
        frame.grid(row=0, column=col, sticky="w", padx=15)
        
        tk.Label(frame, text=title, font=("Arial", 10, "bold"), fg=TEXT_SECONDARY, bg=CARD_COLOR).pack(anchor="w")
        lbl = tk.Label(frame, text="--", font=font_val, fg=color, bg=CARD_COLOR)
        lbl.pack(anchor="w")
        setattr(self, var_name, lbl)
    
    def start(self):
        if self.is_active: return
        self.is_active = True
        
        # Combined stream: ticker (24h stats) and bookTicker (best bid/ask)
        # ticker stream contains c (close), h (high), l (low), v (volume)
        base = WS_BASE_URL.replace("/ws", "/stream?streams=")
        streams = f"{self.symbol}@ticker/{self.symbol}@bookTicker"
        ws_url = base + streams
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        threading.Thread(target=self.ws.run_forever, daemon=True).start()
    
    def stop(self):
        self.is_active = False
        if self.ws: self.ws.close()
    
    def on_message(self, ws, message):
        if not self.is_active: return
        try:
            data = json.loads(message)
            stream = data.get('stream', '') 
            payload = data.get('data', data)
            
            event_type = payload.get('e')
            
            if event_type == '24hrTicker':
                price = float(payload['c'])
                high = float(payload['h'])
                low = float(payload['l'])
                vol = float(payload['v'])
                
                self.after(0, lambda: self.price_label.config(text=f"${price:,.2f}"))
                self.after(0, lambda: self.high_label.config(text=f"${high:,.2f}"))
                self.after(0, lambda: self.low_label.config(text=f"${low:,.2f}"))
                self.after(0, lambda: self.vol_label.config(text=f"{vol:,.2f}"))
                
            elif event_type == 'bookTicker':
                bid = float(payload['b'])
                ask = float(payload['a'])
                self.after(0, lambda: self.bid_label.config(text=f"${bid:,.2f}"))
                self.after(0, lambda: self.ask_label.config(text=f"${ask:,.2f}"))
                
        except Exception as e:
            print(f"Ticker Error: {e}")

    def on_error(self, ws, error):
        pass 
    
    def on_close(self, ws, status, msg):
        pass
    
    def on_open(self, ws):
        pass
        
    def pack(self, **kwargs):
        super().pack(**kwargs)
    
    def pack_forget(self):
        super().pack_forget()
