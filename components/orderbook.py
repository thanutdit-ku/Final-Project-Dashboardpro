import threading
import time

import requests
import tkinter as tk

from ..config import (
    CARD_COLOR,
    CARD_HEADER_BG,
    BORDER_COLOR,
    ACCENT_COLOR,
    TEXT_COLOR,
    TEXT_SECONDARY,
    COLOR_BUY,
    COLOR_SELL,
    FONT_SUBTITLE,
    FONT_NUMBERS,
    REST_BASE_URL,
)

class OrderBookPanel(tk.Frame):
    ROW_COUNT = 28
    REFRESH_INTERVAL = 1.0  # seconds between REST snapshots

    def __init__(self, parent, symbol):
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
        self.fetch_thread = None
        
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
            text="Order Book Snapshot",
            bg=box_color,
            fg=TEXT_COLOR,
            font=FONT_SUBTITLE,
            anchor="w",
        )
        header.pack(fill=tk.X)
        tk.Frame(header_frame, height=2, bg=ACCENT_COLOR).pack(fill=tk.X, pady=(8, 0))
        
        # Columns Frame
        cols_frame = tk.Frame(self, bg=CARD_COLOR)
        cols_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(2, 12))
        
        # Bids Column (Left)
        self.bids_frame = tk.Frame(cols_frame, bg=CARD_COLOR)
        self.bids_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Asks Column (Right)
        self.asks_frame = tk.Frame(cols_frame, bg=CARD_COLOR)
        self.asks_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Headers
        tk.Label(
            self.bids_frame,
            text="BIDS",
            fg=COLOR_BUY,
            bg=CARD_COLOR,
            font=("Arial", 10, "bold"),
        ).pack(anchor="w")
        tk.Label(
            self.asks_frame,
            text="ASKS",
            fg=COLOR_SELL,
            bg=CARD_COLOR,
            font=("Arial", 10, "bold"),
        ).pack(anchor="w")
        
        # Column Labels
        self._create_header_row(self.bids_frame)
        self._create_header_row(self.asks_frame)
        
        # Rows placeholders
        self.bid_rows = []
        self.ask_rows = []
        
        for _ in range(self.ROW_COUNT):
            self.bid_rows.append(self._create_row(self.bids_frame))
            self.ask_rows.append(self._create_row(self.asks_frame))
            
    def _create_header_row(self, parent):
        f = tk.Frame(parent, bg=CARD_COLOR)
        f.pack(fill=tk.X)
        f.grid_columnconfigure(0, weight=1)
        f.grid_columnconfigure(1, weight=1)
        
        tk.Label(f, text="Price", anchor="w", bg=CARD_COLOR, fg=TEXT_SECONDARY).grid(row=0, column=0, sticky="ew")
        tk.Label(f, text="Amount", anchor="e", bg=CARD_COLOR, fg=TEXT_SECONDARY).grid(row=0, column=1, sticky="ew")
        
    def _create_row(self, parent):
        f = tk.Frame(parent, bg=CARD_COLOR)
        f.pack(fill=tk.X, pady=1)
        f.grid_columnconfigure(0, weight=1)
        f.grid_columnconfigure(1, weight=1)
        
        price_lbl = tk.Label(f, text="-", anchor="w", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_NUMBERS)
        price_lbl.grid(row=0, column=0, sticky="ew")
        
        amt_lbl = tk.Label(f, text="-", anchor="e", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_NUMBERS)
        amt_lbl.grid(row=0, column=1, sticky="ew")
        
        return (price_lbl, amt_lbl)
        
    def start(self):
        if self.is_active:
            return
        self.is_active = True
        self.fetch_thread = threading.Thread(
            target=self._fetch_loop,
            daemon=True,
        )
        self.fetch_thread.start()

    def stop(self):
        self.is_active = False

    def _fetch_loop(self):
        while self.is_active:
            snapshot = self._fetch_order_book()
            if snapshot:
                self.after(0, self.update_ui, snapshot)
            time.sleep(self.REFRESH_INTERVAL)

    def _fetch_order_book(self):
        try:
            limit = min(max(self.ROW_COUNT, 20), 100)
            resp = requests.get(
                f"{REST_BASE_URL}/api/v3/depth",
                params={"symbol": self.symbol.upper(), "limit": limit},
                timeout=4,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            print(f"Order book fetch failed: {exc}")
            return None

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
