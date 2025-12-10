import tkinter as tk
from tkinter import ttk
import websocket
import json
import threading
from datetime import datetime
from ..config import WS_BASE_URL, BG_COLOR, CARD_COLOR, TEXT_COLOR, TEXT_SECONDARY, COLOR_BUY, COLOR_SELL, FONT_SUBTITLE, FONT_BODY

class TradesFeedPanel(tk.Frame):
    def __init__(self, parent, symbol):
        super().__init__(parent, bg=CARD_COLOR, padx=10, pady=10)
        self.symbol = symbol.lower()
        self.is_active = False
        self.ws = None
        
        # Header
        header = tk.Label(self, text="Recent Trades", 
                         bg=CARD_COLOR, fg=TEXT_COLOR, 
                         font=FONT_SUBTITLE, anchor="w")
        header.pack(fill=tk.X, pady=(0, 5))
        
        # Header Columns
        col_frame = tk.Frame(self, bg=CARD_COLOR)
        col_frame.pack(fill=tk.X)
        tk.Label(col_frame, text="Price", width=10, anchor="w", bg=CARD_COLOR, fg=TEXT_SECONDARY).pack(side=tk.LEFT)
        tk.Label(col_frame, text="Amount", width=10, anchor="e", bg=CARD_COLOR, fg=TEXT_SECONDARY).pack(side=tk.RIGHT)
        tk.Label(col_frame, text="Time", width=8, anchor="center", bg=CARD_COLOR, fg=TEXT_SECONDARY).pack(side=tk.RIGHT, padx=5)
        
        # Trades List (Canvas or just simplistic labels list for performance)
        # Using a fixed number of rows for simplicity and performance
        self.rows = []
        self.max_rows = 15
        
        self.list_frame = tk.Frame(self, bg=CARD_COLOR)
        self.list_frame.pack(fill=tk.BOTH, expand=True)
        
        for _ in range(self.max_rows):
            row = self._create_row()
            self.rows.append(row)
            
    def _create_row(self):
        f = tk.Frame(self.list_frame, bg=CARD_COLOR)
        # Don't pack yet, we pack them as data comes in or pre-pack empty?
        # Let's pack them all empty
        f.pack(fill=tk.X, pady=1)
        
        price = tk.Label(f, text="", width=10, anchor="w", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_BODY)
        price.pack(side=tk.LEFT)
        
        amt = tk.Label(f, text="", width=10, anchor="e", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_BODY)
        amt.pack(side=tk.RIGHT)
        
        time_lbl = tk.Label(f, text="", width=8, anchor="center", bg=CARD_COLOR, fg=TEXT_SECONDARY, font=("Arial", 9))
        time_lbl.pack(side=tk.RIGHT, padx=5)
        
        return {"frame": f, "price": price, "amt": amt, "time": time_lbl}

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
        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def stop(self):
        self.is_active = False
        if self.ws: self.ws.close()

    def on_message(self, ws, message):
        if not self.is_active: return
        try:
            data = json.loads(message)
            # Schedule update
            self.after(0, self.add_trade, data)
        except Exception:
            pass
            
    def add_trade(self, data):
        if not self.is_active: return
        
        price = float(data['p'])
        qty = float(data['q'])
        is_buyer_maker = data['m'] # True if seller is maker -> Buyer is taker (Buy) ? No. 
        # m: Is the buyer the market maker?
        # If true, buyer is maker (limit order sitting in book), seller is taker (market sell). -> SELL
        # If false, buyer is taker (market buy), seller is maker. -> BUY
        
        side = "SELL" if is_buyer_maker else "BUY"
        color = COLOR_SELL if side == "SELL" else COLOR_BUY
        
        time_str = datetime.fromtimestamp(data['T'] / 1000).strftime('%H:%M:%S')
        
        # Logic: Shift all rows down, update top row?
        # Simpler: Rotate the data values visually?
        # Let's effectively shift.
        
        # Move values from i to i+1
        # Actually in a fixed list, typically newest is top.
        
        # We need to maintain a list of trade data memory and render it.
        # But manipulating config of 15 widgets every message (high freq) is heavy.
        # Trades can be 100/sec.
        # Optimization: Buffer updates? Or just update UI. Tkinter might lag.
        
        # For this standard project, let's just update the top widget and re-pack?
        # NO, re-packing is expensive.
        
        # Let's just cycle the widgets?
        # Pop last row, move to top, update content.
        
        last_row = self.rows.pop() # Remove from end
        last_row["frame"].pack_forget() # Hide
        
        # Update content
        last_row["price"].config(text=f"{price:.2f}", fg=color)
        last_row["amt"].config(text=f"{qty:.4f}")
        last_row["time"].config(text=time_str)
        
        # Pack at top
        last_row["frame"].pack(side=tk.TOP, fill=tk.X, pady=1, before=self.list_frame.winfo_children()[0] if self.list_frame.winfo_children() else None)
        
        self.rows.insert(0, last_row) # Add to front
