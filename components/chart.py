import tkinter as tk
from tkinter import ttk
import requests
import pandas as pd
import mplfinance as mpf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import time
import websocket
import json
from ..config import (
    REST_BASE_URL,
    WS_BASE_URL,
    WS_SSL_OPTIONS,
    CARD_COLOR,
    CARD_HEADER_BG,
    BORDER_COLOR,
    ACCENT_COLOR,
    TEXT_COLOR,
    COLOR_BUY,
    COLOR_SELL,
    FONT_SUBTITLE,
    CHART_INTERVAL,
)

class ChartPanel(tk.Frame):
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
        
        self.interval = CHART_INTERVAL.lower()
        interval_label = self.interval.upper()
        tk.Label(
            header_frame,
            text=f"{symbol.upper()} {interval_label} Candlestick",
            font=("Arial", 12, "bold"),
            bg=box_color,
            fg=TEXT_COLOR,
            anchor="w",
        ).pack(fill=tk.X)
        tk.Frame(header_frame, height=2, bg=ACCENT_COLOR).pack(fill=tk.X, pady=(8, 0))
                 
        # Matplotlib Figure
        # Set panel color to card color
        self.fig = Figure(figsize=(5, 4), dpi=100, facecolor=CARD_COLOR)
        
        # Adjust margins to show axis labels while keeping it tight
        self.fig.subplots_adjust(left=0.15, right=0.95, top=0.95, bottom=0.2)
        
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(CARD_COLOR)
        
        # Styling axes
        self.ax.tick_params(axis="x", colors=TEXT_COLOR)
        self.ax.tick_params(axis="y", colors=TEXT_COLOR)
        for side in ("bottom", "top", "left", "right"):
            self.ax.spines[side].set_color(BORDER_COLOR)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.is_active = False
        self.data = pd.DataFrame()
        
    def start(self):
        if self.is_active: return
        self.is_active = True
        self.last_draw_time = 0
        self.draw_interval = 0.2 # Max 5 FPS
        
        # Initial fetch
        threading.Thread(target=self._fetch_initial_history, daemon=True).start()
        
    def _fetch_initial_history(self):
        try:
            url = f"{REST_BASE_URL}/api/v3/klines"
            
            # Debug symbol
            sym = self.symbol.strip().upper()
            
            # Binance REST API usually prefers uppercase e.g. BTCUSDT
            params = {
                "symbol": sym,
                "interval": self.interval,
                "limit": 50
            }
            resp = requests.get(url, params=params)
            raw = resp.json()
            
            # Check if valid list
            if not isinstance(raw, list):
                print(f"Chart API Error: {raw}")
                return

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
            
            # Start WebSocket for live updates AFTER initial fetch
            threading.Thread(target=self._run_socket, daemon=True).start()
            
        except Exception as e:
            print(f"Chart Error: {e}")

    # ADDED: WebSocket kline handler
    def _run_socket(self):
        ws_url = f"{WS_BASE_URL}/{self.symbol}@kline_{self.interval}"
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=lambda ws, err: print(f"Chart WS Error: {err}"),
            on_close=lambda ws, s, m: print(f"Chart WS Closed {self.symbol}"),
            on_open=lambda ws: print(f"Chart WS Open {self.symbol}")
        )
        self.ws.run_forever(sslopt=WS_SSL_OPTIONS)

    # MODIFIED: chart update logic with throttling
    def on_message(self, ws, message):
        if not self.is_active: return
        try:
            data = json.loads(message)
            if data.get('e') == 'kline':
                k = data['k']
                
                # Parse candle data
                t = pd.to_datetime(k['t'], unit='ms')
                o = float(k['o'])
                h = float(k['h'])
                l = float(k['l'])
                c = float(k['c'])
                v = float(k['v'])
                
                # Update DataFrame (CURRENT candle update)
                if t in self.data.index:
                    # Update existing row using .at for scalar access (safer/faster)
                    self.data.at[t, 'Open'] = o
                    self.data.at[t, 'High'] = h
                    self.data.at[t, 'Low'] = l
                    self.data.at[t, 'Close'] = c
                    self.data.at[t, 'Volume'] = v
                else:
                    # New candle - Append
                    new_row_data = {
                        'Open': o, 'High': h, 'Low': l, 'Close': c, 'Volume': v
                    }
                    # Construct DataFrame aligned with existing columns
                    # We create a single-row DataFrame
                    new_df = pd.DataFrame(new_row_data, index=[t])
                    # Reindex to match self.data columns, filling missing with 0
                    new_df = new_df.reindex(columns=self.data.columns, fill_value=0)
                    
                    self.data = pd.concat([self.data, new_df])
                
                # Prune old data
                if len(self.data) > 60:
                     self.data = self.data.iloc[-50:]
                
                # Throttling to prevent GUI freeze
                current_time = time.time()
                if current_time - self.last_draw_time > self.draw_interval:
                    self.last_draw_time = current_time
                    self.after(0, self._plot)
                
        except Exception as e:
            print(f"Chart Message Error: {e}")

    def _plot(self):
        try:
            if not self.is_active or self.data.empty: return
            
            # Efficiently clear and replot
            self.ax.clear()
            
            # Custom style for mplfinance to match dark theme
            mc = mpf.make_marketcolors(
                up=COLOR_BUY, down=COLOR_SELL, edge="inherit", wick="inherit", volume="in"
            )
            s = mpf.make_mpf_style(
                marketcolors=mc,
                facecolor=CARD_COLOR,
                figcolor=CARD_COLOR,
                gridcolor=BORDER_COLOR,
                gridstyle=":",
            )
            
            # Plot only OHLCV data to avoid column mismatch errors
            plot_data = self.data[['Open', 'High', 'Low', 'Close', 'Volume']]
            
            mpf.plot(plot_data, type='candle', ax=self.ax, style=s, datetime_format='%H:%M', volume=False, warn_too_much_data=1000)
            
            self.ax.set_ylabel("")
            self.canvas.draw()
            
        except Exception as e:
            print(f"Plot Error: {e}")
        
    def stop(self):
        self.is_active = False
        if self.ws: self.ws.close()
