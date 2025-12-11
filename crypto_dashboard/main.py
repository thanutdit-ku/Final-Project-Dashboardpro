import tkinter as tk
from tkinter import ttk
from functools import partial
from .config import WINDOW_TITLE, WINDOW_SIZE, SYMBOLS, BG_COLOR, CARD_COLOR, TEXT_COLOR, FONT_TITLE
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
        self.root.minsize(1000, 600) # Prevent making it too small
        self.root.configure(bg=BG_COLOR)
        
        # Configure Grid Layout
        self.root.columnconfigure(0, weight=0) # Sidebar
        self.root.columnconfigure(1, weight=1) # Main Content
        self.root.rowconfigure(0, weight=1)
        
        # Sidebar Frame
        self.sidebar = tk.Frame(self.root, bg=CARD_COLOR, width=200)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
        
        # Main Area Frame (Use grid inside here)
        self.main_area = tk.Frame(self.root, bg=BG_COLOR)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        
        # Configure Main Area Grid
        self.main_area.columnconfigure(0, weight=3) # Order Book
        self.main_area.columnconfigure(1, weight=4) # Chart
        self.main_area.columnconfigure(2, weight=3) # Trades
        self.main_area.rowconfigure(0, weight=0) # Header
        self.main_area.rowconfigure(1, weight=1) # Content
        
        # State
        self.current_symbol_info = SYMBOLS[0]
        self.components = []
        self.symbol_buttons = {}
        
        self.setup_sidebar()
        self.setup_main_view()
        
    def setup_sidebar(self):
        # App Title in Sidebar
        tk.Label(self.sidebar, text="Crypto\nDashboard", font=("Arial", 18, "bold"), bg=CARD_COLOR, fg="#4fa3ff").pack(pady=(20, 10))
        
        # Section Title
        tk.Label(self.sidebar, text="MARKETS", font=("Arial", 14, "bold"), bg=CARD_COLOR, fg=TEXT_COLOR).pack(pady=10)
        
        for sym in SYMBOLS:
            symbol_key = sym['symbol']
            # Determine initial color - Use a distinct color for active, and a lighter dark for inactive to be visible
            is_active = symbol_key == self.current_symbol_info['symbol']
            
            # Button Styling
            # User wanted "visible frame". We use relief and border.
            bg_color = "#2b3139" if is_active else "#161a1e"
            fg_color = "#ffffff" if is_active else "#848e9c"
            
            # Using a Frame to create a "box" effect if standard button border isn't enough, 
            # but standard button with bd=2 and relief should work.
            btn = tk.Button(self.sidebar, text=sym['name'], 
                            bg=bg_color, fg=fg_color,
                            activebackground="#2b3139", activeforeground="#ffffff",
                            bd=2, relief="groove", # Visible frame
                            font=("Arial", 12, "bold"),
                            cursor="hand2",
                            command=partial(self.switch_symbol, sym))
            btn.pack(fill=tk.X, pady=5, padx=15, ipady=5) # ipady for taller buttons
            self.symbol_buttons[symbol_key] = btn
            
    def setup_main_view(self):
        # Clear existing components
        for comp in self.components:
            comp.stop()
            comp.destroy()
        self.components = []
        
        # 1. Header Section (Ticker + Stats)
        header_frame = tk.Frame(self.main_area, bg=BG_COLOR)
        header_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        
        # Ticker Component 
        self.ticker = CryptoTicker(header_frame, self.current_symbol_info['symbol'], self.current_symbol_info['name'])
        self.ticker.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.components.append(self.ticker)
        
        # Volume Stats
        self.vol_stats = VolumeStatsPanel(header_frame, self.current_symbol_info['symbol'])
        self.vol_stats.pack(side=tk.RIGHT, padx=5)
        self.components.append(self.vol_stats)
        
        # 2. Main Content
        # Left: Order Book
        self.ob_panel = OrderBookPanel(self.main_area, self.current_symbol_info['symbol'])
        self.ob_panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        self.components.append(self.ob_panel)
        
        # Center: Chart
        self.chart_panel = ChartPanel(self.main_area, self.current_symbol_info['symbol'])
        self.chart_panel.grid(row=1, column=1, sticky="nsew", padx=5, pady=(0, 5))
        self.components.append(self.chart_panel)
        
        # Right: Trades Feed
        self.trades_panel = TradesFeedPanel(self.main_area, self.current_symbol_info['symbol'])
        self.trades_panel.grid(row=1, column=2, sticky="nsew", padx=5, pady=(0, 5))
        self.components.append(self.trades_panel)
        
        # Start all
        for comp in self.components:
            comp.start()
            
    def switch_symbol(self, symbol_info):
        if self.current_symbol_info == symbol_info: return
        print(f"Switching to {symbol_info['name']}")
        
        # Update buttons
        old_sym = self.current_symbol_info['symbol']
        new_sym = symbol_info['symbol']
        
        if old_sym in self.symbol_buttons:
            self.symbol_buttons[old_sym].config(bg="#161a1e", fg="#848e9c")
        if new_sym in self.symbol_buttons:
            self.symbol_buttons[new_sym].config(bg="#2b3139", fg="#ffffff")
            
        self.current_symbol_info = symbol_info
        
        # Rebuild view
        self.setup_main_view()
            
    def on_closing(self):
        print("Closing application...")
        for comp in self.components:
            comp.stop()
        self.root.destroy()
        print("Application closed.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoDashboard(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
