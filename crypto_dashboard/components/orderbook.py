import tkinter as tk
from tkinter import ttk
import websocket
import json
import threading
from ..config import WS_BASE_URL, BG_COLOR, CARD_COLOR, TEXT_COLOR, TEXT_SECONDARY, COLOR_BUY, COLOR_SELL, FONT_SUBTITLE, FONT_NUMBERS

class OrderBookPanel(tk.Frame):
    def __init__(self, parent, symbol):
        super().__init__(parent, bg=CARD_COLOR, padx=10, pady=10)
        self.symbol = symbol.lower()
        self.is_active = False
        self.ws = None
        
        # Header
        header = tk.Label(self, text="Order Book Snapshot", 
                         bg=CARD_COLOR, fg=TEXT_COLOR, 
                         font=FONT_SUBTITLE, anchor="w")
        header.pack(fill=tk.X, pady=(0, 10))
        
        # Columns Frame
        cols_frame = tk.Frame(self, bg=CARD_COLOR)
        cols_frame.pack(fill=tk.BOTH, expand=True)
        
        # Bids Column (Left)
        self.bids_frame = tk.Frame(cols_frame, bg=CARD_COLOR)
        self.bids_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Asks Column (Right)
        self.asks_frame = tk.Frame(cols_frame, bg=CARD_COLOR)
        self.asks_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Headers
        tk.Label(self.bids_frame, text="BIDS", fg=COLOR_BUY, bg=CARD_COLOR, font=("Arial", 10, "bold")).pack(anchor="w")
        tk.Label(self.asks_frame, text="ASKS", fg=COLOR_SELL, bg=CARD_COLOR, font=("Arial", 10, "bold")).pack(anchor="w")
        
        # Column Labels
        self._create_header_row(self.bids_frame)
        self._create_header_row(self.asks_frame)
        
        # Rows placeholders
        self.bid_rows = []
        self.ask_rows = []
        
        for _ in range(10): # Top 10
            self.bid_rows.append(self._create_row(self.bids_frame))
            self.ask_rows.append(self._create_row(self.asks_frame))
            
    def _create_header_row(self, parent):
        f = tk.Frame(parent, bg=CARD_COLOR)
        f.pack(fill=tk.X)
        tk.Label(f, text="Price", width=12, anchor="w", bg=CARD_COLOR, fg=TEXT_SECONDARY).pack(side=tk.LEFT)
        tk.Label(f, text="Amount", width=12, anchor="e", bg=CARD_COLOR, fg=TEXT_SECONDARY).pack(side=tk.RIGHT)
        
    def _create_row(self, parent):
        f = tk.Frame(parent, bg=CARD_COLOR)
        f.pack(fill=tk.X, pady=1)
        price_lbl = tk.Label(f, text="-", width=12, anchor="w", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_NUMBERS)
        price_lbl.pack(side=tk.LEFT)
        amt_lbl = tk.Label(f, text="-", width=12, anchor="e", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_NUMBERS)
        amt_lbl.pack(side=tk.RIGHT)
        return (price_lbl, amt_lbl)
        
    def start(self):
        if self.is_active: return
        self.is_active = True
        
        # Helper to run in thread
        threading.Thread(target=self._run_socket, daemon=True).start()
        
    def _run_socket(self):
        # https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams#partial-book-depth-streams
        ws_url = f"{WS_BASE_URL}/{self.symbol}@depth10@100ms"
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=lambda ws, err: print(f"OB Error: {err}"),
            on_close=lambda ws, s, m: print("OB Closed")
        )
        self.ws.run_forever()
        
    def stop(self):
        self.is_active = False
        if self.ws: self.ws.close()
        
    def on_message(self, ws, message):
        if not self.is_active: return
        try:
            data = json.loads(message)
            self.after(0, self.update_ui, data)
        except Exception:
            pass
            
    def update_ui(self, data):
        if not self.is_active: return
        bids = data.get('bids', [])
        asks = data.get('asks', [])
        
        # Update Bids
        for i, (price, qty) in enumerate(bids):
            if i >= len(self.bid_rows): break
            p_lbl, a_lbl = self.bid_rows[i]
            p_lbl.config(text=f"{float(price):.2f}", fg=COLOR_BUY)
            a_lbl.config(text=f"{float(qty):.4f}")
            
        # Update Asks
        for i, (price, qty) in enumerate(asks):
            if i >= len(self.ask_rows): break
            p_lbl, a_lbl = self.ask_rows[i]
            p_lbl.config(text=f"{float(price):.2f}", fg=COLOR_SELL)
            a_lbl.config(text=f"{float(qty):.4f}")
