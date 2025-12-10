import tkinter as tk
from tkinter import ttk
import requests
import pandas as pd
import mplfinance as mpf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import time
from ..config import REST_BASE_URL, BG_COLOR, CARD_COLOR, TEXT_COLOR, COLOR_BUY, COLOR_SELL, FONT_SUBTITLE

class ChartPanel(tk.Frame):
    def __init__(self, parent, symbol):
        super().__init__(parent, bg=CARD_COLOR, padx=10, pady=10)
        self.symbol = symbol.upper()
        
        # Header
        header = tk.Label(self, text=f"{self.symbol} 1H Candlestick", 
                         bg=CARD_COLOR, fg=TEXT_COLOR, 
                         font=FONT_SUBTITLE, anchor="w")
        header.pack(fill=tk.X, pady=(0, 10))
        
        # Matplotlib Figure
        # Set panel color to card color
        self.fig = Figure(figsize=(5, 4), dpi=100, facecolor=CARD_COLOR)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(CARD_COLOR)
        
        # Styling axes
        self.ax.tick_params(axis='x', colors=TEXT_COLOR)
        self.ax.tick_params(axis='y', colors=TEXT_COLOR)
        self.ax.spines['bottom'].set_color(TEXT_COLOR)
        self.ax.spines['top'].set_color(TEXT_COLOR)
        self.ax.spines['left'].set_color(TEXT_COLOR)
        self.ax.spines['right'].set_color(TEXT_COLOR)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.is_active = False
        self.data = pd.DataFrame()
        
    def start(self):
        if self.is_active: return
        self.is_active = True
        
        # Initial fetch
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
        
        # Periodic update (polling for simplicity instead of websocket for full chart rebuild)
        # Using websocket for chart requires managing partial candle updates which is complex with mplfinance
        # Polling every 2s is sufficient for a 1H chart demo
        self.update_loop()
        
    def update_loop(self):
        if not self.is_active: return
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
        self.after(5000, self.update_loop) # Update every 5 seconds
        
    def _fetch_and_update(self):
        try:
            url = f"{REST_BASE_URL}/api/v3/klines"
            params = {
                "symbol": self.symbol,
                "interval": "1h",
                "limit": 50
            }
            resp = requests.get(url, params=params)
            raw = resp.json()
            
            # Parse into DataFrame
            df = pd.DataFrame(raw, columns=['Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close time', 'Quote asset volume', 'Number of trades', 'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'])
            df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
            df.set_index('Open time', inplace=True)
            
            # Convert to float
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = df[col].astype(float)
                
            self.data = df
            
            # Schedule plot on main thread
            self.after(0, self._plot)
            
        except Exception as e:
            print(f"Chart Error: {e}")

    def _plot(self):
        if not self.is_active or self.data.empty: return
        
        self.ax.clear()
        
        # Custom style for mplfinance to match dark theme
        mc = mpf.make_marketcolors(up=COLOR_BUY, down=COLOR_SELL, edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, facecolor=CARD_COLOR, figcolor=CARD_COLOR, gridcolor=TEXT_COLOR, gridstyle=':')
        
        # We use mplfinance plot ability on external axes
        mpf.plot(self.data, type='candle', ax=self.ax, style=s, datetime_format='%H:%M', volume=False)
        # Volume is tricky to add as subplot on existing axes easily without messing specific layouts, 
        # sticking to price only as per request image primarily shows price (though it has volume bars at bottom).
        # To add volume, we'd need another axes. Let's keep it simple first.
        
        self.ax.set_ylabel("") # Remote label to save space
        self.canvas.draw()
        
    def stop(self):
        self.is_active = False

