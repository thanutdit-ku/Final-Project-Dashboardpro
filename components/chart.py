import tkinter as tk
from tkinter import ttk
import requests
from datetime import datetime
import websocket
import json
import pandas as pd
import mplfinance as mpf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import time
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
        self.poll_thread = None
        self.ws_thread = None
        self.ws = None
        self.ws_failed = False
        
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
        self.poll_interval = 6  # seconds between REST refreshes
        self.last_draw_time = 0
        self.draw_interval = 0.25
        
    def start(self):
        if self.is_active:
            return
        self.is_active = True
        self.ws_failed = False
        self.ws_thread = None
        
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
            df['Open time'] = pd.to_datetime(df['Open time'], unit='ms', utc=True)
            df.set_index('Open time', inplace=True)
            df.index = self._localize_index(df.index)
            
            # Convert to float
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = df[col].astype(float)
                
            self.data = df
            
            # Schedule plot on main thread
            self.after(0, self._plot)
            
            if not self.ws_failed:
                self._start_websocket()
            else:
                self._ensure_polling()
            
        except Exception as e:
            print(f"Chart Error: {e}")

    def _poll_loop(self):
        while self.is_active:
            self._fetch_latest_snapshot()
            time.sleep(self.poll_interval)
    
    def _ensure_polling(self):
        if self.poll_thread and self.poll_thread.is_alive():
            return
        print("Chart REST poller engaged.")
        self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.poll_thread.start()

    def _fetch_latest_snapshot(self):
        if not self.is_active:
            return
        try:
            url = f"{REST_BASE_URL}/api/v3/klines"
            sym = self.symbol.strip().upper()
            params = {"symbol": sym, "interval": self.interval, "limit": 60}
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            raw = resp.json()
            if not isinstance(raw, list):
                return
            df = pd.DataFrame(
                raw,
                columns=[
                    "Open time",
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume",
                    "Close time",
                    "Quote asset volume",
                    "Number of trades",
                    "Taker buy base asset volume",
                    "Taker buy quote asset volume",
                    "Ignore",
                ],
            )
            df["Open time"] = pd.to_datetime(df["Open time"], unit="ms", utc=True)
            df.set_index("Open time", inplace=True)
            df.index = self._localize_index(df.index)
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                df[col] = df[col].astype(float)
            self.data = df
            self.after(0, self._plot)
        except Exception as exc:
            print(f"Chart REST update failed: {exc}")
    
    def _localize_index(self, index):
        try:
            local_tz = datetime.now().astimezone().tzinfo
            if getattr(index, "tz", None) is None:
                index = index.tz_localize("UTC")
            if local_tz is not None:
                index = index.tz_convert(local_tz)
            return index.tz_localize(None)
        except Exception:
            try:
                return index.tz_localize(None)
            except Exception:
                return index
    
    def _start_websocket(self):
        if self.ws_failed:
            self._ensure_polling()
            return
        if self.ws_thread and self.ws_thread.is_alive():
            return
        self.ws_thread = threading.Thread(target=self._run_socket, daemon=True)
        self.ws_thread.start()

    def _run_socket(self):
        ws_url = f"{WS_BASE_URL}/{self.symbol}@kline_{self.interval}"
        print(f"Chart WS connecting to {ws_url}")
        try:
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self.on_message,
                on_error=self._ws_error,
                on_close=self._ws_close,
                on_open=self._ws_open,
            )
            self.ws.run_forever(sslopt=WS_SSL_OPTIONS)
        except Exception as exc:
            self._ws_error(self.ws, exc)

    def _ws_open(self, ws):
        print(f"Chart WS Open {self.symbol.upper()}")

    def _ws_close(self, ws, status, msg):
        print(f"Chart WS Closed {self.symbol.upper()} status={status} msg={msg}")
        self.ws_thread = None
        self._schedule_rest_fallback()

    def _ws_error(self, ws, err):
        print(f"Chart WS Error {self.symbol.upper()}: {err}")
        self.ws_thread = None
        self._schedule_rest_fallback()

    def _schedule_rest_fallback(self):
        if not self.ws_failed:
            print("Falling back to REST polling for chart updates.")
        self.ws_failed = True
        self.ws = None
        self.ws_thread = None
        self._ensure_polling()

    def on_message(self, ws, message):
        if not self.is_active:
            return
        try:
            payload = json.loads(message)
            if payload.get("e") != "kline":
                return
            kline = payload.get("k")
            if not kline:
                return
            t = pd.to_datetime(kline["t"], unit="ms", utc=True)
            t = self._localize_index(pd.DatetimeIndex([t]))[0]
            o = float(kline["o"])
            h = float(kline["h"])
            l = float(kline["l"])
            c = float(kline["c"])
            v = float(kline["v"])

            if t in self.data.index:
                self.data.at[t, "Open"] = o
                self.data.at[t, "High"] = h
                self.data.at[t, "Low"] = l
                self.data.at[t, "Close"] = c
                self.data.at[t, "Volume"] = v
            else:
                new_df = pd.DataFrame(
                    {"Open": o, "High": h, "Low": l, "Close": c, "Volume": v},
                    index=[t],
                )
                new_df.index = self._localize_index(new_df.index)
                new_df = new_df.reindex(columns=self.data.columns, fill_value=0)
                self.data = pd.concat([self.data, new_df])

            if len(self.data) > 60:
                self.data = self.data.iloc[-60:]

            now = time.time()
            if now - self.last_draw_time > self.draw_interval:
                self.last_draw_time = now
                self.after(0, self._plot)
        except Exception as exc:
            print(f"Chart WS message parse failed: {exc}")

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
        self.poll_thread = None
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        self.ws = None
        self.ws_thread = None
