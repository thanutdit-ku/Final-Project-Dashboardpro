import tkinter as tk
from tkinter import ttk
import json
import os
from functools import partial
from .config import WINDOW_TITLE, WINDOW_SIZE, SYMBOLS, BG_COLOR, CARD_COLOR, TEXT_COLOR, TEXT_SECONDARY, FONT_TITLE, PREFS_FILE
from .components.ticker import CryptoTicker
from .components.orderbook import OrderBookPanel
from .components.chart import ChartPanel
from .components.volume_stats import VolumeStatsPanel
from .components.trades_feed import TradesFeedPanel

class CryptoDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(1000, 600)
        self.root.configure(bg=BG_COLOR)
        
        # Configure Grid Layout
        self.root.columnconfigure(0, weight=1) # Main Content (Left)
        self.root.columnconfigure(1, weight=0) # Sidebar (Right)
        self.root.rowconfigure(0, weight=1)
        
        # Main Area Frame (Left)
        # Using a Canvas + Scrollbar for main area since we might stack multiple assets
        self.main_container = tk.Frame(self.root, bg=BG_COLOR)
        self.main_container.grid(row=0, column=0, sticky="nsew")
        
        self.canvas = tk.Canvas(self.main_container, bg=BG_COLOR, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.main_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=BG_COLOR)
        # FIX: Ensure the inner frame's column fills the available width
        self.scrollable_frame.columnconfigure(0, weight=1)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags="frame")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Make scrollable_frame full width
        # Make scrollable_frame full width and handle height expansion
        # Make scrollable_frame full width
        self.main_container.bind('<Configure>', lambda e: self.canvas.itemconfig("frame", width=e.width))
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Sidebar Frame (Right)
        self.sidebar = tk.Frame(self.root, bg="#15191d", width=240)
        self.sidebar.grid(row=0, column=1, sticky="nsew", padx=(1, 0))
        
        # State
        self.active_symbols = set() # Set of symbol strings e.g. "btcusdt"
        self.asset_frames = {} 
        self.asset_components = {}
        self.symbol_buttons = {}
        
        self.panel_vars = {
            "book": tk.BooleanVar(value=True),
            "chart": tk.BooleanVar(value=True),
            "trades": tk.BooleanVar(value=True),
        }
        
        self.load_preferences()
        
        self.setup_sidebar()
        self.setup_main_view()

    def load_preferences(self):
        try:
            if os.path.exists(PREFS_FILE):
                with open(PREFS_FILE, 'r') as f:
                    prefs = json.load(f)
                
                self.active_symbols.clear()
                for s in SYMBOLS:
                    short_name = s['name'].split('/')[0]
                    if prefs.get(short_name, False):
                        self.active_symbols.add(s['symbol'])
                
                if not self.active_symbols:
                     self.active_symbols.add("btcusdt")

                self.panel_vars["book"].set(prefs.get("OrderBook", True))
                self.panel_vars["chart"].set(prefs.get("Chart", True))
                self.panel_vars["trades"].set(prefs.get("RecentTrades", True))
            else:
                self.active_symbols = {"btcusdt"}
                self.panel_vars["book"].set(True)
                self.panel_vars["chart"].set(True)
                self.panel_vars["trades"].set(True)
        except Exception as e:
            print(f"Error loading prefs: {e}")
            self.active_symbols = {"btcusdt"}

    def save_preferences(self):
        try:
            prefs = {}
            for s in SYMBOLS:
                short_name = s['name'].split('/')[0]
                is_active = s['symbol'] in self.active_symbols
                prefs[short_name] = is_active
            
            prefs["OrderBook"] = self.panel_vars["book"].get()
            prefs["Chart"] = self.panel_vars["chart"].get()
            prefs["RecentTrades"] = self.panel_vars["trades"].get()
            
            with open(PREFS_FILE, 'w') as f:
                json.dump(prefs, f, indent=4)
        except Exception as e:
            print(f"Error saving prefs: {e}")
            
    def setup_sidebar(self):
        for widget in self.sidebar.winfo_children():
            widget.destroy()

        tk.Label(self.sidebar, text="CRYPTO\nDASHBOARD", font=("Arial", 16, "bold"), 
                 bg=self.sidebar["bg"], fg="#3498db").pack(pady=(30, 20))
        
        self._add_section_header("MARKETS")
        
        for sym in SYMBOLS:
            self._create_market_card(sym)
            
        tk.Frame(self.sidebar, height=20, bg=self.sidebar["bg"]).pack() 
        self._add_section_header("PANELS")
        
        self._create_panel_toggle("Order Book", "book")
        self._create_panel_toggle("Chart", "chart")
        self._create_panel_toggle("Recent Trades", "trades")

    def _add_section_header(self, text):
        container = tk.Frame(self.sidebar, bg=self.sidebar["bg"])
        container.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        tk.Label(container, text=text, font=("Arial", 10, "bold"), 
                 bg=self.sidebar["bg"], fg=TEXT_SECONDARY).pack(side=tk.LEFT)
        
        tk.Frame(container, bg="#2c3e50", height=1).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

    def _create_market_card(self, sym):
        symbol_key = sym['symbol']
        is_active = symbol_key in self.active_symbols
        
        active_bg = "#3498db"
        inactive_bg = "#252b33"
        hover_bg = "#2c3e50"
        
        bg_color = active_bg if is_active else inactive_bg
        fg_color = "#ffffff" if is_active else "#b0c4de"
        
        card = tk.Frame(self.sidebar, bg=bg_color, cursor="hand2")
        card.pack(fill=tk.X, padx=15, pady=4)
        card.grid_columnconfigure(0, weight=1)
        
        lbl = tk.Label(card, text=sym['name'], font=("Arial", 11, "bold"),
                 bg=bg_color, fg=fg_color, anchor="w")
        lbl.pack(side=tk.LEFT, padx=12, pady=12)
        
        for widget in (card, lbl):
            widget.bind("<Button-1>", lambda e, s=sym: self.toggle_asset(s))
            widget.bind("<Enter>", lambda e, c=card, l=lbl, a=is_active: self._on_hover(c, l, "#2980b9" if a else hover_bg))
            widget.bind("<Leave>", lambda e, c=card, l=lbl, a=is_active: self._on_hover(c, l, active_bg if a else inactive_bg))
                
        self.symbol_buttons[symbol_key] = {"card": card, "label": lbl}

    def _on_hover(self, card, label, color):
        card.config(bg=color)
        label.config(bg=color)

    def toggle_asset(self, symbol_info):
        sym = symbol_info['symbol']
        
        if sym in self.active_symbols:
            # GUARD: Do not allow disabling the last asset
            if len(self.active_symbols) <= 1:
                # Optionally feedback to user? For now just ignore or force re-add
                return

            self.active_symbols.remove(sym)
        else:
            self.active_symbols.add(sym)
            
        self.setup_sidebar()
        self.setup_main_view() # Trigger smart update

    def _create_panel_toggle(self, text, var_key):
        frame = tk.Frame(self.sidebar, bg=self.sidebar["bg"])
        frame.pack(fill=tk.X, padx=15, pady=4)
        
        var = self.panel_vars[var_key]
        def toggle_cb():
            self.setup_main_view()
        cb = tk.Checkbutton(frame, text=text, variable=var, 
                            bg=self.sidebar["bg"], fg=TEXT_COLOR, 
                            selectcolor="#252b33",
                            activebackground=self.sidebar["bg"],
                            activeforeground=TEXT_COLOR,
                            font=("Arial", 11),
                            command=toggle_cb)
        cb.pack(side=tk.LEFT)

    def _create_asset_row(self, symbol_info):
        # Create container
        row_frame = tk.Frame(self.scrollable_frame, bg=BG_COLOR)
        # Grid position will be set by setup_main_view
        
        # Keep track
        if not hasattr(self, 'asset_frames'): self.asset_frames = {}
        self.asset_frames[symbol_info['symbol']] = row_frame
        
        # Layout
        row_frame.columnconfigure(0, weight=3)
        row_frame.columnconfigure(1, weight=4)
        row_frame.columnconfigure(2, weight=3)
        
        # Components Dict
        comps = {}
        
        # Header
        header_frame = tk.Frame(row_frame, bg=BG_COLOR)
        header_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        ticker = CryptoTicker(header_frame, symbol_info['symbol'], symbol_info['name'])
        ticker.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        comps['ticker'] = ticker
        
        # Content Row = 1
        
        # Order Book (Always create, toggle visibility later)
        ob = OrderBookPanel(row_frame, symbol_info['symbol'])
        comps['book'] = ob
        
        # Chart
        chart = ChartPanel(row_frame, symbol_info['symbol'])
        comps['chart'] = chart
        
        # Trades Panel Container
        right_panel = tk.Frame(row_frame, bg=BG_COLOR)
        right_panel.rowconfigure(0, weight=0)
        right_panel.rowconfigure(1, weight=1)
        right_panel.columnconfigure(0, weight=1)
        
        vol = VolumeStatsPanel(right_panel, symbol_info['symbol'])
        vol.grid(row=0, column=0, sticky="ew", pady=(0, 1))
        
        trades = TradesFeedPanel(right_panel, symbol_info['symbol'])
        trades.grid(row=1, column=0, sticky="nsew")
        
        # For the right panel, we treat the CONTAINER as the component to show/hide
        comps['trades_container'] = right_panel
        # Keep refs to children if needed for start/stop
        comps['vol'] = vol
        comps['trades'] = trades

        self.asset_components[symbol_info['symbol']] = comps
        
        # Apply initial visibility
        self._update_row_visibility(symbol_info['symbol'])

    def _update_row_visibility(self, symbol):
        if symbol not in self.asset_components: return
        comps = self.asset_components[symbol]
        
        # Always Start Ticker
        comps['ticker'].start()
        
        # Helper to Start/Grid or Stop/Ungrid
        def manage_comp(key, is_visible, row, col, sticky="nsew"):
            c = comps[key]
            if is_visible:
                c.grid(row=row, column=col, sticky=sticky, padx=1, pady=1)
                if hasattr(c, 'start'): c.start()
                # Special handling for trades container children
                if key == 'trades_container':
                    comps['vol'].start()
                    comps['trades'].start()
            else:
                c.grid_remove()
                if hasattr(c, 'stop'): c.stop()
                if key == 'trades_container':
                    comps['vol'].stop()
                    comps['trades'].stop()

        manage_comp('book', self.panel_vars['book'].get(), 1, 0)
        manage_comp('chart', self.panel_vars['chart'].get(), 1, 1)
        manage_comp('trades_container', self.panel_vars['trades'].get(), 1, 2)

    def setup_main_view(self):
        # 1. REMOVE rows of inactive symbols
        # Use list to avoid runtime error during deletion
        existing_syms = list(self.asset_frames.keys())
        for sym in existing_syms:
            if sym not in self.active_symbols:
                # Disable and Destroy
                comps = self.asset_components.get(sym, {})
                for c in comps.values():
                    if hasattr(c, 'stop'): c.stop()
                
                self.asset_frames[sym].destroy()
                del self.asset_frames[sym]
                del self.asset_components[sym]
        
        # 2. CREATE or UPDATE rows for active symbols
        # Sort by SYMBOLS order
        sorted_active = []
        for s in SYMBOLS:
            if s['symbol'] in self.active_symbols:
                sorted_active.append(s)
                
        for idx, s in enumerate(sorted_active):
            sym = s['symbol']
            
            # If missing, create
            if sym not in self.asset_frames:
                self._create_asset_row(s)
            else:
                # If exists, just update visibility (in case panels toggled)
                self._update_row_visibility(sym)
            
            # Update Grid Position (Safe to re-grid)
            # This ensures correct sorting even if we added out of order
            frame = self.asset_frames[sym]
            frame.grid(row=idx, column=0, sticky="ew", pady=(0, 20))
            
            # Force Layout Update
            # self.scrollable_frame.update_idletasks()

    def on_closing(self):
        print("Closing application...")
        self.save_preferences()
        
        # Stop all components
        if hasattr(self, 'asset_components'):
            for sym, comps in self.asset_components.items():
                for c in comps.values(): # Iterate over values of the component dictionary
                    try:
                        if hasattr(c, 'stop'):
                            c.stop()
                    except Exception as e:
                        print(f"Error stopping component {c} for {sym}: {e}")
                        
        self.root.destroy()
        print("Application closed.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoDashboard(root)
    try:
        root.state('zoomed')
    except:
        try:
            w, h = root.winfo_screenwidth(), root.winfo_screenheight()
            root.geometry(f"{w}x{h}+0+0")
        except:
            pass
            
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
