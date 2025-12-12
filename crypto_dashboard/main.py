import tkinter as tk
from tkinter import ttk
from functools import partial
from .config import WINDOW_TITLE, WINDOW_SIZE, SYMBOLS, BG_COLOR, CARD_COLOR, TEXT_COLOR, TEXT_SECONDARY, FONT_TITLE
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
        self.main_area = tk.Frame(self.root, bg=BG_COLOR)
        self.main_area.grid(row=0, column=0, sticky="nsew")
        
        # Sidebar Frame (Right)
        # Using a slightly different color for contrast if desired, or keep as CARD_COLOR
        # User requested "Increase contrast". 
        SIDEBAR_BG = "#161a1e" # Darker than CARD_COLOR (#1e2329) but lighter than BG (#0b0e11)? 
        # actually BG is #0b0e11 (almost black). CARD is #1e2329 (dark grey).
        # Let's make sidebar CARD_COLOR to pop out from BG, or darker. 
        # "Control panel" usually stands out. Let's use BG_COLOR for main, and CARD_COLOR for sidebar, 
        # but maybe add a border?
        self.sidebar = tk.Frame(self.root, bg="#15191d", width=240) # Slightly wider
        self.sidebar.grid(row=0, column=1, sticky="nsew", padx=(1, 0))
        
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
        self.panel_vars = {
            "book": tk.BooleanVar(value=True),
            "chart": tk.BooleanVar(value=True),
            "trades": tk.BooleanVar(value=True),
        }
        
        self.setup_sidebar()
        self.setup_main_view()
        
    def setup_sidebar(self):
        # Clear sidebar first if needed (not needed in init, but good practice if refreshing)
        for widget in self.sidebar.winfo_children():
            widget.destroy()

        # App Title
        tk.Label(self.sidebar, text="CRYPTO\nDASHBOARD", font=("Arial", 16, "bold"), 
                 bg=self.sidebar["bg"], fg="#3498db").pack(pady=(30, 20))
        
        # --- MARKETS SECTION ---
        self._add_section_header("MARKETS")
        
        # Scrollable area for markets could be nice, but list is short.
        # Just use pack for now.
        for sym in SYMBOLS:
            self._create_market_card(sym)
            
        # --- PANELS SECTION ---
        tk.Frame(self.sidebar, height=20, bg=self.sidebar["bg"]).pack() # Spacer
        self._add_section_header("PANELS")
        
        self._create_panel_toggle("Order Book", "book")
        self._create_panel_toggle("Chart", "chart")
        self._create_panel_toggle("Recent Trades", "trades")
        
    def _add_section_header(self, text):
        container = tk.Frame(self.sidebar, bg=self.sidebar["bg"])
        container.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        tk.Label(container, text=text, font=("Arial", 10, "bold"), 
                 bg=self.sidebar["bg"], fg=TEXT_SECONDARY).pack(side=tk.LEFT)
        
        # Optional divider line
        tk.Frame(container, bg="#2c3e50", height=1).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

    def _create_market_card(self, sym):
        symbol_key = sym['symbol']
        is_active = symbol_key == self.current_symbol_info['symbol']
        
        # Card Colors
        active_bg = "#3498db"
        inactive_bg = "#252b33"
        hover_bg = "#2c3e50"
        
        bg_color = active_bg if is_active else inactive_bg
        fg_color = "#ffffff" if is_active else "#b0c4de"
        
        # Card Frame
        card = tk.Frame(self.sidebar, bg=bg_color, cursor="hand2")
        card.pack(fill=tk.X, padx=15, pady=4)
        
        # Inner padding with grid
        card.grid_columnconfigure(0, weight=1)
        
        # Symbol Name (Left)
        lbl = tk.Label(card, text=sym['name'], font=("Arial", 11, "bold"),
                 bg=bg_color, fg=fg_color, anchor="w")
        lbl.pack(side=tk.LEFT, padx=12, pady=12)
        
        # Indicator (Right) - maybe a small dot or arrow
        if is_active:
            tk.Label(card, text="●", fg="white", bg=bg_color).pack(side=tk.RIGHT, padx=10)
            
        # Bind events
        for widget in (card, lbl):
            widget.bind("<Button-1>", lambda e, s=sym: self.switch_symbol(s))
            if not is_active:
                widget.bind("<Enter>", lambda e, c=card, l=lbl: self._on_hover(c, l, hover_bg))
                widget.bind("<Leave>", lambda e, c=card, l=lbl: self._on_hover(c, l, inactive_bg))
                
        self.symbol_buttons[symbol_key] = {"card": card, "label": lbl, "is_active": is_active}

    def _on_hover(self, card, label, color):
        card.config(bg=color)
        label.config(bg=color)

    def _create_panel_toggle(self, text, var_key):
        # Custom Toggle Checkbutton look
        frame = tk.Frame(self.sidebar, bg=self.sidebar["bg"])
        frame.pack(fill=tk.X, padx=15, pady=4)
        
        var = self.panel_vars[var_key]
        
        # Callback to refresh view
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

    def setup_main_view(self):
        # Clear existing components
        for comp in self.components:
            comp.stop()
            try:
                comp.destroy()
            except:
                pass
        self.components = []
        
        # 1. Header Section (Ticker) - Always Visible
        header_frame = tk.Frame(self.main_area, bg=BG_COLOR)
        header_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        
        self.ticker = CryptoTicker(header_frame, self.current_symbol_info['symbol'], self.current_symbol_info['name'])
        self.ticker.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.components.append(self.ticker)
        
        # 2. Main Content Grid Management
        # We need to dynamically adjust grid based on visibility
        
        col_idx = 0
        
        # Order Book
        if self.panel_vars["book"].get():
            self.ob_panel = OrderBookPanel(self.main_area, self.current_symbol_info['symbol'])
            self.ob_panel.grid(row=1, column=col_idx, sticky="nsew", padx=5, pady=(0, 5))
            self.main_area.columnconfigure(col_idx, weight=3)
            self.components.append(self.ob_panel)
            col_idx += 1
        
        # Chart
        if self.panel_vars["chart"].get():
            self.chart_panel = ChartPanel(self.main_area, self.current_symbol_info['symbol'])
            self.chart_panel.grid(row=1, column=col_idx, sticky="nsew", padx=5, pady=(0, 5))
            self.main_area.columnconfigure(col_idx, weight=4)
            self.components.append(self.chart_panel)
            col_idx += 1
            
        # Trades
        if self.panel_vars["trades"].get():
            right_panel = tk.Frame(self.main_area, bg=BG_COLOR)
            right_panel.grid(row=1, column=col_idx, sticky="nsew", padx=5, pady=(0, 5))
            right_panel.rowconfigure(0, weight=0)
            right_panel.rowconfigure(1, weight=1)
            right_panel.columnconfigure(0, weight=1)
            
            self.vol_stats = VolumeStatsPanel(right_panel, self.current_symbol_info['symbol'])
            self.vol_stats.grid(row=0, column=0, sticky="ew", pady=(0, 5))
            self.components.append(self.vol_stats)
            
            self.trades_panel = TradesFeedPanel(right_panel, self.current_symbol_info['symbol'])
            self.trades_panel.grid(row=1, column=0, sticky="nsew")
            self.components.append(self.trades_panel)
            
            self.main_area.columnconfigure(col_idx, weight=3)
            col_idx += 1
            
        # Start all
        for comp in self.components:
            comp.start()
            
    def switch_symbol(self, symbol_info):
        if self.current_symbol_info == symbol_info: return
        
        # Update UI first
        old_sym = self.current_symbol_info['symbol']
        new_sym = symbol_info['symbol']
        self.current_symbol_info = symbol_info
        
        # Refresh sidebar styles
        # Because we rebuilt the sidebar structure entirely, the old set_style helper is obsolete.
        # It's easier to just call setup_sidebar() again or manually update the widgets using the dict.
        # Let's manually update to prevent flickering.
        
        for key, data in self.symbol_buttons.items():
            is_new_active = (key == new_sym)
            data["is_active"] = is_new_active
            
            card = data["card"]
            lbl = data["label"]
            
            active_bg = "#3498db"
            inactive_bg = "#252b33"
            
            bg = active_bg if is_new_active else inactive_bg
            fg = "#ffffff" if is_new_active else "#b0c4de"
            
            card.config(bg=bg)
            lbl.config(bg=bg, fg=fg)
            
            # Re-bind hover
            if is_new_active:
                # Remove hover bindings if possible or just make them no-op 
                card.unbind("<Enter>")
                card.unbind("<Leave>")
                # Remove indicator if present? 
                # (Indicator logic in _create_market_card was one-off, 
                # strictly speaking we should remove/add the dot. 
                # Just re-running setup_sidebar is safer and fast enough for this lightweight UI).
                
        # Actually, simpler:
        self.setup_sidebar() 
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
