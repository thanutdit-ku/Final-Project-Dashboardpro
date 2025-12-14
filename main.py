import argparse
import json
import os
import sys
from pathlib import Path
from functools import partial

import requests
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# Allow running both as `python -m crypto_dashboard.main` and `python main.py`.
if __package__ is None or __package__ == "":
    current_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(current_dir.parent))
    __package__ = current_dir.name

# Matplotlib needs a writable cache (home is read-only in Codex sandbox).
MPL_CACHE_DIR = Path(__file__).resolve().parent / ".matplotlib_cache"
if "MPLCONFIGDIR" not in os.environ:
    os.environ["MPLCONFIGDIR"] = str(MPL_CACHE_DIR)
MPL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

from .config import (
    WINDOW_TITLE,
    WINDOW_SIZE,
    SYMBOLS,
    BG_COLOR,
    SIDEBAR_BG,
    SIDEBAR_CARD_BG,
    BORDER_COLOR,
    ACCENT_COLOR,
    TEXT_COLOR,
    TEXT_SECONDARY,
    FONT_TITLE,
    PREFS_FILE,
    REST_BASE_URL,
)
from .components.ticker import CryptoTicker
from .components.orderbook import OrderBookPanel
from .components.chart import ChartPanel
from .components.volume_stats import VolumeStatsPanel
from .components.trades_feed import TradesFeedPanel
from .components.overview import OverviewPanel
from .components.home_screen import HomeScreen
from .components.wallet import WalletPanel
from .utils.binance_api import get_current_price

OVERVIEW_KEY = "overview"
WALLET_KEY = "wallet"

# Offline-friendly sample snapshot so headless mode still shows useful info.
HEADLESS_SAMPLE_DATA = {
    "btcusdt": {"price": 90343.38, "change": 1.05, "volume": 135_000_000},
    "ethusdt": {"price": 3188.42, "change": -0.86, "volume": 78_000_000},
    "solusdt": {"price": 182.15, "change": 2.34, "volume": 41_000_000},
    "bnbusdt": {"price": 615.08, "change": 0.52, "volume": 22_000_000},
    "adausdt": {"price": 0.83, "change": -1.67, "volume": 15_000_000},
}


def _run_headless_dashboard():
    """Fetch a lightweight market snapshot for CLI environments."""
    print("Crypto Dashboard (headless mode)")
    print("Fetching 24h ticker data from Binance REST API...\n")

    rows = []
    for sym in SYMBOLS:
        symbol_code = sym["symbol"].upper()
        url = f"{REST_BASE_URL}/api/v3/ticker/24hr"
        try:
            resp = requests.get(url, params={"symbol": symbol_code}, timeout=10)
            resp.raise_for_status()
            payload = resp.json()
            rows.append(
                {
                    "pair": sym["name"],
                    "price": float(payload["lastPrice"]),
                    "change": float(payload["priceChangePercent"]),
                    "volume": float(payload.get("quoteVolume", 0)),
                }
            )
        except Exception as exc:
            fallback = HEADLESS_SAMPLE_DATA.get(sym["symbol"])
            if fallback:
                rows.append(
                    {
                        "pair": sym["name"],
                        "price": fallback["price"],
                        "change": fallback["change"],
                        "volume": fallback["volume"],
                        "note": f"offline sample ({exc})",
                    }
                )
            else:
                rows.append(
                    {
                        "pair": sym["name"],
                        "price": None,
                        "change": None,
                        "volume": None,
                        "error": str(exc),
                    }
                )

    header = f"{'PAIR':<10} {'PRICE (USDT)':>16} {'24H%':>8} {'QUOTE VOL':>15}"
    print(header)
    print("-" * len(header))
    for row in rows:
        note = row.get("note")
        if row.get("error"):
            print(f"{row['pair']:<10} ERROR: {row['error']}")
            continue
        print(
            f"{row['pair']:<10}"
            f" {row['price']:>16,.2f}"
            f" {row['change']:>8.2f}%"
            f" {row['volume']:>15,.0f}"
        )
        if note:
            print(f"{'':<10} note: {note}")

    print(
        "\nGUI mode is unavailable in this environment. Run without --headless on a desktop "
        "session to launch the full dashboard."
    )


def _parse_cli_args():
    parser = argparse.ArgumentParser(description="Crypto Dashboard launcher")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Force console mode even when a GUI is available.",
    )
    parser.add_argument(
        "--force-gui",
        action="store_true",
        help="Force GUI mode even if the environment looks headless.",
    )
    return parser.parse_args()


def _should_use_headless(args):
    if args.force_gui:
        return False
    if args.headless:
        return True
    return os.environ.get("CODEX_SANDBOX") == "seatbelt"

class CryptoDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(1000, 600)
        self.root.configure(bg=BG_COLOR)
        
        self.dashboard_initialized = False
        self.home_screen = HomeScreen(self.root, self.enter_dashboard)
        self.sidebar = None
        self.main_container = None
        self.scrollable_frame = None
        self.loading_overlay = None
        self.loading_progress = None
        self.initial_view_loaded = False
        
        # State
        self.active_symbol = None  # Currently selected symbol string e.g. "btcusdt"
        self.asset_frames = {} 
        self.asset_components = {}
        self.symbol_buttons = {}
        self.overview_panel = None
        self.wallet_panel = None
        
        self.panel_vars = {
            "book": tk.BooleanVar(value=True),
            "chart": tk.BooleanVar(value=True),
            "trades": tk.BooleanVar(value=True),
        }
        self.panel_trace_ids = {}
        self.wallet_holdings = {
            "BTC": {"symbol": "btcusdt", "amount": 0.42},
            "ETH": {"symbol": "ethusdt", "amount": 3.1},
            "SOL": {"symbol": "solusdt", "amount": 55},
            "BNB": {"symbol": "bnbusdt", "amount": 12},
            "ADA": {"symbol": "adausdt", "amount": 1500},
        }
        
        self.load_preferences()
        
        self.home_screen.show()

    def enter_dashboard(self):
        if not self.dashboard_initialized:
            self._setup_dashboard_ui()
        if self.home_screen:
            self.home_screen.destroy()

    def _setup_dashboard_ui(self):
        if self.dashboard_initialized:
            return
        # Configure Grid Layout
        self.root.columnconfigure(0, weight=1)  # Main Content (Left)
        self.root.columnconfigure(1, weight=0)  # Sidebar (Right)
        self.root.rowconfigure(0, weight=1)

        # Main Area Frame (Left)
        self.main_container = tk.Frame(self.root, bg=BG_COLOR)
        self.main_container.grid(row=0, column=0, sticky="nsew")

        self.scrollable_frame = tk.Frame(self.main_container, bg=BG_COLOR)
        self.scrollable_frame.columnconfigure(0, weight=1)
        self.scrollable_frame.rowconfigure(0, weight=1)
        self.scrollable_frame.pack(fill="both", expand=True)

        # Sidebar Frame (Right)
        self.sidebar = tk.Frame(
            self.root,
            bg=SIDEBAR_BG,
            width=250,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
        )
        self.sidebar.grid(row=0, column=1, sticky="nsew", padx=(1, 0))
        self.sidebar.grid_propagate(False)

        self.dashboard_initialized = True
        self.setup_sidebar()
        self._show_initial_loading()
        self.setup_main_view()

    def load_preferences(self):
        try:
            if os.path.exists(PREFS_FILE):
                with open(PREFS_FILE, 'r') as f:
                    prefs = json.load(f)
                
                saved_selection = prefs.get("ActiveSelection")
                valid_symbols = {s['symbol'] for s in SYMBOLS}
                if saved_selection == OVERVIEW_KEY:
                    self.active_symbol = OVERVIEW_KEY
                elif saved_selection == WALLET_KEY:
                    self.active_symbol = WALLET_KEY
                elif saved_selection in valid_symbols:
                    self.active_symbol = saved_selection
                else:
                    self.active_symbol = None
                    for s in SYMBOLS:
                        short_name = s['name'].split('/')[0]
                        if prefs.get(short_name, False):
                            self.active_symbol = s['symbol']
                            break
                
                if not self.active_symbol:
                     self.active_symbol = "btcusdt"

                self.panel_vars["book"].set(prefs.get("OrderBook", True))
                self.panel_vars["chart"].set(prefs.get("Chart", True))
                self.panel_vars["trades"].set(prefs.get("RecentTrades", True))
            else:
                self.active_symbol = "btcusdt"
                self.panel_vars["book"].set(True)
                self.panel_vars["chart"].set(True)
                self.panel_vars["trades"].set(True)
        except Exception as e:
            print(f"Error loading prefs: {e}")
            self.active_symbol = "btcusdt"

    def save_preferences(self):
        try:
            prefs = {}
            for s in SYMBOLS:
                short_name = s['name'].split('/')[0]
                is_active = s['symbol'] == self.active_symbol
                prefs[short_name] = is_active
            
            prefs["ActiveSelection"] = self.active_symbol
            
            prefs["OrderBook"] = self.panel_vars["book"].get()
            prefs["Chart"] = self.panel_vars["chart"].get()
            prefs["RecentTrades"] = self.panel_vars["trades"].get()
            
            with open(PREFS_FILE, 'w') as f:
                json.dump(prefs, f, indent=4)
        except Exception as e:
            print(f"Error saving prefs: {e}")
    
    def _show_initial_loading(self):
        if self.loading_overlay or not self.main_container:
            return
        self.loading_overlay = tk.Frame(
            self.main_container,
            bg=BG_COLOR,
        )
        self.loading_overlay.place(relx=0.5, rely=0.5, anchor="center")

        label = tk.Label(
            self.loading_overlay,
            text="Preparing real-time dashboard...",
            font=("Arial", 13, "bold"),
            fg=TEXT_COLOR,
            bg=BG_COLOR,
        )
        label.pack(pady=(0, 8))

        self.loading_progress = ttk.Progressbar(
            self.loading_overlay,
            mode="indeterminate",
            length=220,
        )
        self.loading_progress.pack()
        try:
            self.loading_progress.start(12)
        except tk.TclError:
            pass

    def _hide_initial_loading(self):
        if self.loading_progress:
            try:
                self.loading_progress.stop()
            except tk.TclError:
                pass
            self.loading_progress = None
        if self.loading_overlay:
            self.loading_overlay.destroy()
            self.loading_overlay = None
    
    def _initial_load_complete(self):
        if not self.initial_view_loaded:
            self.initial_view_loaded = True
            self._hide_initial_loading()
            
    def setup_sidebar(self):
        for widget in self.sidebar.winfo_children():
            widget.destroy()

        logo_path = Path(__file__).resolve().parent / "components" / "crypto-Photoroom.png"
        if logo_path.exists():
            try:
                img = Image.open(logo_path)
                max_width, max_height = 140, 120
                img.thumbnail((max_width, max_height), Image.LANCZOS)
                self.sidebar_logo = ImageTk.PhotoImage(img)
                tk.Label(self.sidebar, image=self.sidebar_logo, bg=self.sidebar["bg"]).pack(
                    pady=(25, 20)
                )
            except Exception as e:
                print(f"Error loading logo: {e}")
                tk.Label(
                    self.sidebar,
                    text="CRYPTO\nDASHBOARD",
                    font=("Arial", 16, "bold"),
                    bg=self.sidebar["bg"],
                    fg=ACCENT_COLOR,
                ).pack(pady=(30, 20))
        else:
            tk.Label(
                self.sidebar,
                text="CRYPTO\nDASHBOARD",
                font=("Arial", 16, "bold"),
                bg=self.sidebar["bg"],
                fg=ACCENT_COLOR,
            ).pack(pady=(30, 20))
        
        self._add_section_header("OVERVIEW")
        self._create_overview_tab()
        self._create_wallet_tab()
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
        container.pack(fill=tk.X, padx=18, pady=(12, 4))

        tk.Label(
            container,
            text=text,
            font=("Arial", 10, "bold"),
            bg=self.sidebar["bg"],
            fg=TEXT_SECONDARY,
        ).pack(side=tk.LEFT)

        tk.Frame(container, bg=BORDER_COLOR, height=1).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0)
        )

    def _create_overview_tab(self):
        is_active = self.active_symbol == OVERVIEW_KEY
        container = tk.Frame(self.sidebar, bg=self.sidebar["bg"])
        container.pack(fill=tk.X, padx=18, pady=(4, 8))

        bg_color = ACCENT_COLOR if is_active else SIDEBAR_CARD_BG
        fg_color = SIDEBAR_BG if is_active else TEXT_COLOR
        border_color = ACCENT_COLOR if is_active else BORDER_COLOR

        tab = tk.Frame(
            container,
            bg=bg_color,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=border_color,
            padx=16,
            pady=10,
        )
        tab.pack(fill=tk.X)

        title = tk.Label(
            tab,
            text="OVERVIEW",
            font=("Arial", 12, "bold"),
            bg=bg_color,
            fg=fg_color,
            anchor="w",
        )
        title.pack(fill=tk.X)

        subtitle = tk.Label(
            tab,
            text="Market Snapshot",
            font=("Arial", 9),
            bg=bg_color,
            fg=SIDEBAR_BG if is_active else TEXT_SECONDARY,
            anchor="w",
        )
        subtitle.pack(fill=tk.X, pady=(2, 0))

        def on_click(event=None):
            if self.active_symbol == OVERVIEW_KEY:
                return
            self.active_symbol = OVERVIEW_KEY
            self.setup_sidebar()
            self.setup_main_view()

        widgets = (tab, title, subtitle)
        for w in widgets:
            w.bind("<Button-1>", on_click)

    def _create_wallet_tab(self):
        is_active = self.active_symbol == WALLET_KEY
        container = tk.Frame(self.sidebar, bg=self.sidebar["bg"])
        container.pack(fill=tk.X, padx=18, pady=(0, 8))

        bg_color = ACCENT_COLOR if is_active else SIDEBAR_CARD_BG
        fg_color = SIDEBAR_BG if is_active else TEXT_COLOR
        border_color = ACCENT_COLOR if is_active else BORDER_COLOR

        tab = tk.Frame(
            container,
            bg=bg_color,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=border_color,
            padx=16,
            pady=10,
        )
        tab.pack(fill=tk.X)

        title = tk.Label(
            tab,
            text="WALLET",
            font=("Arial", 12, "bold"),
            bg=bg_color,
            fg=fg_color,
            anchor="w",
        )
        title.pack(fill=tk.X)

        subtitle = tk.Label(
            tab,
            text="Portfolio Overview",
            font=("Arial", 9),
            bg=bg_color,
            fg=SIDEBAR_BG if is_active else TEXT_SECONDARY,
            anchor="w",
        )
        subtitle.pack(fill=tk.X, pady=(2, 0))

        def on_click(event=None):
            if self.active_symbol == WALLET_KEY:
                return
            self.active_symbol = WALLET_KEY
            self.setup_sidebar()
            self.setup_main_view()

        widgets = (tab, title, subtitle)
        for w in widgets:
            w.bind("<Button-1>", on_click)
    def _create_market_card(self, sym):
        symbol_key = sym['symbol']
        is_active = symbol_key == self.active_symbol
        
        active_bg = ACCENT_COLOR
        inactive_bg = SIDEBAR_CARD_BG
        hover_bg = "#222a39"
        
        bg_color = active_bg if is_active else inactive_bg
        fg_color = SIDEBAR_BG if is_active else "#d7dee9"
        
        # Outer container for drop-shadow effect
        card_container = tk.Frame(self.sidebar, bg=self.sidebar["bg"])
        card_container.pack(fill=tk.X, padx=18, pady=4)

        border_color = ACCENT_COLOR if is_active else BORDER_COLOR
        card = tk.Frame(
            card_container,
            bg=bg_color,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=border_color,
        )
        card.pack(fill=tk.X)
        card.grid_columnconfigure(1, weight=1)
        card.grid_rowconfigure(0, weight=1)

        accent = tk.Frame(
            card,
            width=6,
            bg=ACCENT_COLOR if is_active else BORDER_COLOR,
        )
        accent.grid(row=0, column=0, sticky="ns")

        text_frame = tk.Frame(card, bg=bg_color)
        text_frame.grid(row=0, column=1, sticky="nsew", padx=14, pady=10)

        lbl = tk.Label(
            text_frame,
            text=sym['name'],
            font=("Arial", 12, "bold"),
            bg=bg_color,
            fg=fg_color,
            anchor="w",
        )
        lbl.pack(fill=tk.X)

        sub_fg = SIDEBAR_BG if is_active else TEXT_SECONDARY
        sub_lbl = tk.Label(
            text_frame,
            text="SPOT MARKET",
            font=("Arial", 9),
            bg=bg_color,
            fg=sub_fg,
            anchor="w",
        )
        sub_lbl.pack(fill=tk.X, pady=(2, 0))

        def on_enter(e, sym_info=sym, active=is_active):
            new_bg = "#f9d34b" if active else hover_bg
            for widget in (card, text_frame, lbl, sub_lbl):
                widget.config(bg=new_bg)
            if not active:
                lbl.config(fg=TEXT_COLOR)
                sub_lbl.config(fg="#aeb7c7")
                card.config(highlightbackground="#3a4251")
            accent.config(bg=ACCENT_COLOR if active else "#2e3442")

        def on_leave(e, sym_info=sym, active=is_active):
            base_bg = active_bg if active else inactive_bg
            for widget in (card, text_frame, lbl, sub_lbl):
                widget.config(bg=base_bg)
            lbl.config(fg=SIDEBAR_BG if active else "#d7dee9")
            sub_lbl.config(fg=SIDEBAR_BG if active else TEXT_SECONDARY)
            card.config(highlightbackground=ACCENT_COLOR if active else BORDER_COLOR)
            accent.config(bg=ACCENT_COLOR if active else BORDER_COLOR)

        widgets_to_bind = (card, text_frame, lbl, sub_lbl, accent)
        for widget in widgets_to_bind:
            widget.bind("<Button-1>", lambda e, s=sym: self.toggle_asset(s))
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
                
        self.symbol_buttons[symbol_key] = {"card": card, "label": lbl}

    def toggle_asset(self, symbol_info):
        sym = symbol_info['symbol']
        
        if sym == self.active_symbol:
            return

        self.active_symbol = sym
        self.setup_sidebar()
        self.setup_main_view() # Trigger smart update

    def _create_panel_toggle(self, text, var_key):
        var = self.panel_vars[var_key]
        container = tk.Frame(self.sidebar, bg=self.sidebar["bg"])
        container.pack(fill=tk.X, padx=18, pady=1)

        card = tk.Frame(
            container,
            bg=SIDEBAR_CARD_BG,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
            padx=6,
            pady=3,
        )
        card.pack(fill=tk.X)
        card.grid_columnconfigure(1, weight=1)

        indicator = tk.Canvas(card, width=16, height=16, bg=SIDEBAR_CARD_BG, highlightthickness=0)
        indicator.grid(row=0, column=0, rowspan=2, sticky="w")
        indicator_circle = indicator.create_oval(2, 2, 14, 14, fill=SIDEBAR_BG, outline=BORDER_COLOR, width=2)
        indicator_check = indicator.create_text(8, 8, text="✓", font=("Arial", 9, "bold"))

        text_frame = tk.Frame(card, bg=SIDEBAR_CARD_BG)
        text_frame.grid(row=0, column=1, sticky="w", padx=(6, 0))

        title = tk.Label(
            text_frame,
            text=text.upper(),
            font=("Arial", 10, "bold"),
            bg=SIDEBAR_CARD_BG,
            fg=TEXT_COLOR,
            anchor="w",
        )
        title.pack(fill=tk.X)

        subtitle = tk.Label(
            text_frame,
            text=f"Show {text}",
            font=("Arial", 7),
            bg=SIDEBAR_CARD_BG,
            fg=TEXT_SECONDARY,
            anchor="w",
        )
        subtitle.pack(fill=tk.X)

        def refresh():
            if not card.winfo_exists():
                return
            active = var.get()
            bg_color = "#1f2735" if active else SIDEBAR_CARD_BG
            border = ACCENT_COLOR if active else BORDER_COLOR
            title_fg = TEXT_COLOR
            subtitle_fg = TEXT_SECONDARY

            card.config(bg=bg_color, highlightbackground=border)
            indicator.config(bg=bg_color)
            text_frame.config(bg=bg_color)
            title.config(bg=bg_color, fg=title_fg)
            subtitle.config(bg=bg_color, fg=subtitle_fg)

            indicator.itemconfig(
                indicator_circle,
                fill=ACCENT_COLOR if active else SIDEBAR_BG,
                outline=border,
            )
            indicator.itemconfig(
                indicator_check,
                fill=SIDEBAR_BG if active else SIDEBAR_BG,
                state="normal" if active else "hidden",
            )

        def toggle_panel(event=None):
            current_value = var.get()
            if current_value:
                active_count = sum(1 for v in self.panel_vars.values() if v.get())
                if active_count <= 1:
                    return
            var.set(not current_value)
            refresh()
            self.setup_main_view()

        def on_enter(event=None):
            card.config(bg="#252f40")
            indicator.config(bg="#252f40")
            text_frame.config(bg="#252f40")

        def on_leave(event=None):
            refresh()

        refresh()

        if var_key in self.panel_trace_ids:
            try:
                var.trace_remove("write", self.panel_trace_ids[var_key])
            except tk.TclError:
                pass
        trace_id = var.trace_add("write", lambda *args: refresh())
        self.panel_trace_ids[var_key] = trace_id

        widgets = (card, indicator, text_frame, title, subtitle)
        for widget in widgets:
            widget.bind("<Button-1>", toggle_panel)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

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
        row_frame.rowconfigure(1, weight=1)
        
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
        
        def manage_comp(key, position, sticky="nsew"):
            c = comps[key]
            if position is not None:
                row, col = position
                c.grid(row=row, column=col, sticky=sticky, padx=8, pady=8)
                if hasattr(c, 'start'):
                    c.start()
                if key == 'trades_container':
                    comps['vol'].start()
                    comps['trades'].start()
            else:
                c.grid_remove()
                if hasattr(c, 'stop'):
                    c.stop()
                if key == 'trades_container':
                    comps['vol'].stop()
                    comps['trades'].stop()

        panel_order = [
            ('book', self.panel_vars['book'].get()),
            ('chart', self.panel_vars['chart'].get()),
            ('trades_container', self.panel_vars['trades'].get()),
        ]
        positions = {}
        current_col = 0
        for key, visible in panel_order:
            if visible:
                positions[key] = (1, current_col)
                current_col += 1
            else:
                positions[key] = None

        row_frame = self.asset_frames.get(symbol)
        if row_frame:
            for idx in range(3):
                weight = 1 if idx < current_col else 0
                row_frame.columnconfigure(idx, weight=weight)

        for key, _ in panel_order:
            manage_comp(key, positions[key])

    def _show_overview_view(self):
        if not self.overview_panel:
            self.overview_panel = OverviewPanel(self.scrollable_frame)
        self.overview_panel.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.scrollable_frame.rowconfigure(0, weight=1)
        self.overview_panel.start()

    def _hide_overview_view(self):
        if self.overview_panel:
            self.overview_panel.grid_remove()
            self.overview_panel.stop()

    def _show_wallet_view(self):
        if not self.wallet_panel:
            self.wallet_panel = WalletPanel(
                self.scrollable_frame,
                holdings=self.wallet_holdings,
                price_fetcher=get_current_price,
                fallback_prices=HEADLESS_SAMPLE_DATA,
            )
        self.wallet_panel.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.scrollable_frame.rowconfigure(0, weight=1)
        self.wallet_panel.start()

    def _hide_wallet_view(self):
        if self.wallet_panel:
            self.wallet_panel.grid_remove()
            self.wallet_panel.stop()

    def setup_main_view(self):
        # 1. REMOVE rows of inactive symbols
        # Use list to avoid runtime error during deletion
        active_set = {self.active_symbol} if self.active_symbol else set()
        existing_syms = list(self.asset_frames.keys())
        for sym in existing_syms:
            if sym not in active_set:
                # Disable and Destroy
                comps = self.asset_components.get(sym, {})
                for c in comps.values():
                    if hasattr(c, 'stop'): c.stop()
                
                self.asset_frames[sym].destroy()
                del self.asset_frames[sym]
                del self.asset_components[sym]
        
        if self.active_symbol == OVERVIEW_KEY:
            self._hide_wallet_view()
            self._show_overview_view()
            self._initial_load_complete()
            return
        elif self.active_symbol == WALLET_KEY:
            self._hide_overview_view()
            self._show_wallet_view()
            self._initial_load_complete()
            return
        else:
            self._hide_overview_view()
            self._hide_wallet_view()
        
        # 2. CREATE or UPDATE rows for active symbols
        # Sort by SYMBOLS order
        current_symbol_info = None
        if self.active_symbol:
            for s in SYMBOLS:
                if s['symbol'] == self.active_symbol:
                    current_symbol_info = s
                    break
        
        if current_symbol_info:
            sym = current_symbol_info['symbol']
            if sym not in self.asset_frames:
                self._create_asset_row(current_symbol_info)
            else:
                self._update_row_visibility(sym)
            
            frame = self.asset_frames[sym]
            frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
            self.scrollable_frame.rowconfigure(0, weight=1)

        self._initial_load_complete()

    def on_closing(self):
        print("Closing application...")
        self.save_preferences()
        
        if self.overview_panel:
            try:
                self.overview_panel.stop()
            except Exception:
                pass
        if self.wallet_panel:
            try:
                self.wallet_panel.stop()
            except Exception:
                pass
        
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
    args = _parse_cli_args()
    if _should_use_headless(args):
        _run_headless_dashboard()
        sys.exit(0)

    try:
        root = tk.Tk()
    except Exception as exc:
        print(f"Unable to start Tkinter GUI ({exc}). Falling back to headless mode.")
        _run_headless_dashboard()
        sys.exit(1)

    app = CryptoDashboard(root)
    try:
        root.state('zoomed')
    except Exception:
        try:
            w, h = root.winfo_screenwidth(), root.winfo_screenheight()
            root.geometry(f"{w}x{h}+0+0")
        except Exception:
            pass

    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
