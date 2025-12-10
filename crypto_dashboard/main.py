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
        
        self.setup_sidebar()
        self.setup_main_view()
        
    def setup_sidebar(self):
        tk.Label(self.sidebar, text="MARKETS", font=FONT_TITLE, bg=CARD_COLOR, fg=TEXT_COLOR).pack(pady=20)
        
        for sym in SYMBOLS:
            btn = tk.Button(self.sidebar, text=sym['name'], 
                            bg=BG_COLOR, fg=TEXT_COLOR, 
                            bd=0, font=("Arial", 12),
                            command=partial(self.switch_symbol, sym))
            btn.pack(fill=tk.X, pady=5, padx=10)
            
    def setup_main_view(self):
        # Clear existing components
        for comp in self.components:
            comp.stop()
            comp.destroy()
        self.components = []
        
        # 1. Header Section (Ticker + Stats)
        header_frame = tk.Frame(self.main_area, bg=BG_COLOR)
        header_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        
        # Ticker Component 
        self.ticker = CryptoTicker(header_frame, self.current_symbol_info['symbol'], self.current_symbol_info['name'])
        self.ticker.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.components.append(self.ticker)
        
        # Volume Stats
        self.vol_stats = VolumeStatsPanel(header_frame, self.current_symbol_info['symbol'])
        self.vol_stats.pack(side=tk.RIGHT, padx=10)
        self.components.append(self.vol_stats)
        
        # 2. Main Content
        # Left: Order Book
        self.ob_panel = OrderBookPanel(self.main_area, self.current_symbol_info['symbol'])
        self.ob_panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 10))
        self.components.append(self.ob_panel)
        
        # Center: Chart
        self.chart_panel = ChartPanel(self.main_area, self.current_symbol_info['symbol'])
        self.chart_panel.grid(row=1, column=1, sticky="nsew", padx=5, pady=(0, 10))
        self.components.append(self.chart_panel)
        
        # Right: Trades Feed
        self.trades_panel = TradesFeedPanel(self.main_area, self.current_symbol_info['symbol'])
        self.trades_panel.grid(row=1, column=2, sticky="nsew", padx=5, pady=(0, 10))
        self.components.append(self.trades_panel)
        
        # Start all
        for comp in self.components:
            comp.start()
            
    def switch_symbol(self, symbol_info):
        if self.current_symbol_info == symbol_info: return
        print(f"Switching to {symbol_info['name']}")
        self.current_symbol_info = symbol_info
        
        # Rebuild view (easiest way to ensure clean state)
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
