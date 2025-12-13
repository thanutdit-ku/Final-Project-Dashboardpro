import tkinter as tk
from tkinter import ttk
import threading
import json
from datetime import datetime

import requests
import websocket
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..config import (
    SYMBOLS,
    WS_BASE_URL,
    WS_SSL_OPTIONS,
    REST_BASE_URL,
    COLOR_BUY,
    COLOR_SELL,
)


# =========================
# 🎨 PASTEL PREMIUM THEME
# =========================
BG_COLOR = "#0E1117"
CARD_COLOR = "#151A23"
BORDER_COLOR = "#1F2937"

TEXT_COLOR = "#E5E7EB"
TEXT_SECONDARY = "#9CA3AF"

PASTEL_CHART_COLORS = [
    "#FCD34D",  # BTC
    "#6EE7B7",  # ETH
    "#93C5FD",  # SOL
    "#FCA5A5",  # BNB
    "#D8B4FE",  # ADA
]


class OverviewPanel(tk.Frame):
    """Premium overview dashboard panel"""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR, padx=8, pady=8)

        self.symbols = [s["symbol"] for s in SYMBOLS]
        self.ws = None
        self.is_active = False

        self.card_vars = {}
        self.volume_data = {s: 0 for s in self.symbols}
        self.change_data = {s: 0.0 for s in self.symbols}

        self.historical_prices = {}
        self.history_dates = []
        self.sparkline_cards = {}
        self.has_ws_data = False
        self.has_history_data = False
        self.loading_overlay = None

        self.chart_colors = PASTEL_CHART_COLORS

        self._build_cards()
        self._build_visuals()
        self._show_loading_overlay()

    # =========================
    # TOP CARDS
    # =========================
    def _build_cards(self):
        frame = tk.Frame(self, bg=BG_COLOR)
        frame.pack(fill=tk.X)

        for idx, sym in enumerate(self.symbols):
            frame.columnconfigure(idx, weight=1, uniform="cards")

            card = tk.Frame(
                frame,
                bg=CARD_COLOR,
                padx=14,
                pady=12,
                highlightthickness=1,
                highlightbackground=BORDER_COLOR,
            )
            card.grid(row=0, column=idx, sticky="nsew", padx=6)

            tk.Frame(card, height=1, bg=BORDER_COLOR).pack(fill=tk.X, pady=(0, 10))

            name = sym.upper().replace("USDT", "/USDT")
            tk.Label(
                card,
                text=name,
                font=("Arial", 11, "bold"),
                fg=TEXT_COLOR,
                bg=CARD_COLOR,
            ).pack(anchor="w")

            price_var = tk.StringVar(value="--")
            tk.Label(
                card,
                textvariable=price_var,
                font=("Arial", 16, "bold"),
                fg=TEXT_COLOR,
                bg=CARD_COLOR,
            ).pack(anchor="w", pady=(6, 2))

            change_var = tk.StringVar(value="--")
            change_label = tk.Label(
                card,
                textvariable=change_var,
                font=("Arial", 10, "bold"),
                fg=TEXT_SECONDARY,
                bg=CARD_COLOR,
            )
            change_label.pack(anchor="w")

            vol_var = tk.StringVar(value="Vol --")
            tk.Label(
                card,
                textvariable=vol_var,
                font=("Arial", 9),
                fg=TEXT_SECONDARY,
                bg=CARD_COLOR,
            ).pack(anchor="w", pady=(6, 0))

            self.card_vars[sym] = {
                "price": price_var,
                "change": change_var,
                "change_label": change_label,
                "vol": vol_var,
            }

    # =========================
    # VISUAL SECTION
    # =========================
    def _build_visuals(self):
        visuals = tk.Frame(self, bg=BG_COLOR)
        visuals.pack(fill=tk.BOTH, expand=True, pady=(14, 0))
        visuals.columnconfigure(0, weight=1)
        visuals.columnconfigure(1, weight=1)

        # -------- Donut --------
        donut_card = tk.Frame(
            visuals,
            bg=CARD_COLOR,
            padx=14,
            pady=14,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
        )
        donut_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        donut_header = tk.Frame(donut_card, bg=CARD_COLOR)
        donut_header.pack(fill=tk.X)
        tk.Label(
            donut_header,
            text="24h Volume Mix",
            font=("Arial", 12, "bold"),
            bg=CARD_COLOR,
            fg=TEXT_COLOR,
        ).pack(anchor="w")
        tk.Label(
            donut_header,
            text="Live volume share across tracked markets",
            font=("Arial", 9),
            bg=CARD_COLOR,
            fg=TEXT_SECONDARY,
        ).pack(anchor="w")

        self.donut_fig = Figure(figsize=(4.6, 3.2), dpi=120)
        self.donut_ax = self.donut_fig.add_subplot(111)
        self.donut_fig.patch.set_facecolor(CARD_COLOR)
        self.donut_ax.set_facecolor(CARD_COLOR)

        self.donut_canvas = FigureCanvasTkAgg(self.donut_fig, master=donut_card)
        self.donut_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=(8, 2))

        # Sector list container (ใต้ donut)
        self.sector_frame = tk.Frame(donut_card, bg=CARD_COLOR)
        self.sector_frame.pack(fill=tk.X, pady=(6, 0))

        # -------- Sparkline Grid --------
        chart_card = tk.Frame(
            visuals,
            bg=CARD_COLOR,
            padx=14,
            pady=14,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
        )
        chart_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        tk.Label(
            chart_card,
            text="Mini Performance Charts",
            font=("Arial", 11, "bold"),
            bg=CARD_COLOR,
            fg=TEXT_COLOR,
        ).pack(anchor="w")

        self.sparkline_container = tk.Frame(chart_card, bg=CARD_COLOR)
        self.sparkline_container.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        columns = 2
        for col in range(columns):
            self.sparkline_container.columnconfigure(col, weight=1, uniform="sparkcols")

        for idx, sym in enumerate(self.symbols):
            row = idx // columns
            col = idx % columns
            outer = tk.Frame(self.sparkline_container, bg=CARD_COLOR)
            outer.grid(row=row, column=col, sticky="nsew", padx=6, pady=8)
            card = tk.Frame(
                outer,
                bg="#111623",
                highlightthickness=1,
                highlightbackground="#1f2733",
                padx=12,
                pady=10,
            )
            card.pack(fill=tk.BOTH, expand=True)

            header = tk.Frame(card, bg="#111623")
            header.pack(fill=tk.X, pady=(0, 6))
            tk.Label(
                header,
                text=sym.upper().replace("USDT", "/USDT"),
                font=("Arial", 10, "bold"),
                fg=TEXT_COLOR,
                bg="#111623",
            ).pack(side=tk.LEFT)
            price_var = tk.StringVar(value="--")
            tk.Label(
                header,
                textvariable=price_var,
                font=("Arial", 10, "bold"),
                fg=TEXT_COLOR,
                bg="#111623",
            ).pack(side=tk.RIGHT, padx=(0, 6))
            change_var = tk.StringVar(value="--")
            change_label = tk.Label(
                header,
                textvariable=change_var,
                font=("Arial", 9, "bold"),
                fg=TEXT_SECONDARY,
                bg="#111623",
            )
            change_label.pack(side=tk.RIGHT)

            fig = Figure(figsize=(2.4, 1.2), dpi=120)
            ax = fig.add_subplot(111)
            fig.patch.set_facecolor("#111623")
            ax.set_facecolor("#111623")
            fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.05)
            ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
            for spine in ax.spines.values():
                spine.set_visible(False)

            canvas = FigureCanvasTkAgg(fig, master=card)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            self.sparkline_cards[sym] = {
                "ax": ax,
                "canvas": canvas,
                "change_var": change_var,
                "change_label": change_label,
                "price_var": price_var,
            }
    def _show_loading_overlay(self):
        if self.loading_overlay:
            return
        overlay = tk.Frame(self, bg="#060a11")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Label(
            overlay,
            text="Loading Overview…",
            font=("Arial", 12, "bold"),
            fg=TEXT_COLOR,
            bg="#060a11",
        ).pack(pady=(40, 12))
        tk.Label(
            overlay,
            text="Fetching live metrics and history",
            font=("Arial", 10),
            fg=TEXT_SECONDARY,
            bg="#060a11",
        ).pack()
        progress = ttk.Progressbar(overlay, mode="indeterminate", length=200)
        progress.pack(pady=(20, 0))
        progress.start(10)
        self.loading_overlay = (overlay, progress)

    def _hide_loading_overlay(self):
        if not self.loading_overlay:
            return
        overlay, progress = self.loading_overlay
        progress.stop()
        overlay.destroy()
        self.loading_overlay = None

    def _maybe_hide_loading(self):
        if self.has_ws_data and self.has_history_data:
            self._hide_loading_overlay()

    # =========================
    # SOCKET
    # =========================
    def start(self):
        if self.is_active:
            return
        self.is_active = True

        base = WS_BASE_URL.replace("/ws", "/stream?streams=")
        stream = "/".join(f"{s}@ticker" for s in self.symbols)
        url = base + stream

        self.ws = websocket.WebSocketApp(url, on_message=self._on_message)

        threading.Thread(
            target=self.ws.run_forever,
            kwargs={"sslopt": WS_SSL_OPTIONS},
            daemon=True,
        ).start()

        threading.Thread(target=self._fetch_history, daemon=True).start()

    def stop(self):
        self.is_active = False
        if self.ws:
            self.ws.close()

    # =========================
    # UPDATE LOGIC
    # =========================
    def _on_message(self, ws, msg):
        data = json.loads(msg).get("data", {})
        sym = data.get("s", "").lower()
        if sym not in self.card_vars:
            return

        price = float(data["c"])
        change = float(data["P"])
        vol = float(data.get("q", 0))

        self.after(0, self._update_card, sym, price, change, vol)

    def _update_card(self, sym, price, change, vol):
        c = self.card_vars[sym]
        c["price"].set(f"${price:,.2f}")
        c["change"].set(f"{change:+.2f}%")
        c["vol"].set(f"Vol {vol:,.0f}")

        c["change_label"].config(
            fg=COLOR_BUY if change >= 0 else COLOR_SELL
        )

        self.volume_data[sym] = vol
        self.change_data[sym] = change

        self._render_donut()
        self._render_sector_list()
        if not self.has_ws_data:
            self.has_ws_data = True
            self._maybe_hide_loading()

    # =========================
    # DONUT
    # =========================
    def _render_donut(self):
        vols = list(self.volume_data.values())
        total = sum(vols)
        if total <= 0:
            return

        self.donut_ax.clear()
        self.donut_ax.set_facecolor(CARD_COLOR)

        shares = [v / total for v in vols]
        top_idx = vols.index(max(vols))
        explode = [0.04 if i == top_idx else 0.015 for i in range(len(vols))]

        self.donut_ax.pie(
            shares,
            colors=self.chart_colors,
            startangle=90,
            counterclock=False,
            wedgeprops=dict(width=0.32, edgecolor=CARD_COLOR, linewidth=3),
            explode=explode,
        )

        outer_ring = Circle((0, 0), 0.74, facecolor="none", edgecolor=BORDER_COLOR, linewidth=1)
        self.donut_ax.add_patch(outer_ring)
        self.donut_ax.add_patch(
            Circle((0, 0), 0.56, facecolor=CARD_COLOR, edgecolor=BORDER_COLOR, linewidth=1.2)
        )

        top_symbol = self.symbols[top_idx].upper().replace("USDT", "")
        top_share = shares[top_idx] * 100

        self.donut_ax.text(
            0,
            0,
            f"${total/1_000_000_000:.2f}B",
            color=TEXT_COLOR,
            fontsize=20,
            fontweight="bold",
            ha="center",
        )
        self.donut_ax.text(
            0,
            0.26,
            "24h Volume",
            color=TEXT_SECONDARY,
            fontsize=10,
            fontweight="bold",
            ha="center",
        )
        self.donut_ax.text(
            0,
            -0.22,
            f"Top: {top_symbol}  ({top_share:.1f}%)",
            color=self.chart_colors[top_idx],
            fontsize=10,
            fontweight="bold",
            ha="center",
        )

        self.donut_ax.axis("equal")
        self.donut_canvas.draw_idle()

    # =========================
    # SECTOR LIST (ใต้ donut)
    # =========================
    def _render_sector_list(self):
        for w in self.sector_frame.winfo_children():
            w.destroy()

        total_vol = sum(self.volume_data.values()) or 1
        sorted_syms = sorted(
            self.symbols,
            key=lambda s: self.volume_data.get(s, 0),
            reverse=True,
        )

        for sym in sorted_syms:
            change = self.change_data.get(sym, 0)
            vol = self.volume_data.get(sym, 0)
            share_ratio = vol / total_vol
            share_pct = share_ratio * 100
            accent = self.chart_colors[self.symbols.index(sym)]
            trend_color = COLOR_BUY if change >= 0 else COLOR_SELL

            row = tk.Frame(
                self.sector_frame,
                bg=CARD_COLOR,
                highlightthickness=1,
                highlightbackground=BORDER_COLOR,
                padx=9,
                pady=5,
            )
            row.pack(fill=tk.X, pady=3)

            left = tk.Frame(row, bg=CARD_COLOR)
            left.pack(fill=tk.X)
            tk.Label(left, text="●", fg=accent, bg=CARD_COLOR, font=("Arial", 12)).pack(
                side=tk.LEFT
            )
            tk.Label(
                left,
                text=sym.upper().replace("USDT", ""),
                fg=TEXT_COLOR,
                bg=CARD_COLOR,
                font=("Arial", 11, "bold"),
                width=6,
                anchor="w",
            ).pack(side=tk.LEFT, padx=(6, 0))
            tk.Label(
                left,
                text=f"{share_pct:>4.1f}%",
                fg=TEXT_SECONDARY,
                bg=CARD_COLOR,
                font=("Arial", 9),
            ).pack(side=tk.LEFT, padx=(4, 0))
            tk.Label(
                left,
                text=f"{change:+.2f}%",
                fg=trend_color,
                bg=CARD_COLOR,
                font=("Arial", 10, "bold"),
            ).pack(side=tk.RIGHT)

            bar_bg = tk.Frame(row, bg="#0B111A", height=8)
            bar_bg.pack(fill=tk.X, pady=(6, 0))
            bar_bg.pack_propagate(False)

            bar_fill = tk.Frame(bar_bg, bg=accent)
            bar_fill.place(relheight=1, relwidth=min(1.0, max(0.04, share_ratio)))

    # =========================
    # SPARKLINE CHARTS
    # =========================
    def _fetch_history(self):
        url = f"{REST_BASE_URL}/api/v3/klines"
        for sym in self.symbols:
            r = requests.get(
                url,
                params={"symbol": sym.upper(), "interval": "1d", "limit": 120},
                timeout=10,
            )
            data = r.json()
            closes = [float(x[4]) for x in data]
            self.historical_prices[sym] = closes
            if not self.history_dates and data:
                self.history_dates = [
                    datetime.utcfromtimestamp(x[0] / 1000).strftime("%d %b")
                    for x in data
                ]

        self.after(0, self._render_sparklines)

    def _render_sparklines(self):
        for sym, card in self.sparkline_cards.items():
            ax = card["ax"]
            canvas = card["canvas"]
            ax.clear()
            ax.set_facecolor("#111623")
            ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
            for spine in ax.spines.values():
                spine.set_visible(False)

            prices = self.historical_prices.get(sym, [])
            if not prices:
                canvas.draw_idle()
                continue

            x = list(range(len(prices)))
            color = self.chart_colors[self.symbols.index(sym)]
            ax.plot(x, prices, color=color, linewidth=2.2)
            ax.fill_between(x, prices, color=color, alpha=0.18)
            if len(x) > 1:
                ax.set_xlim(x[0], x[-1])
            ymin = min(prices)
            ymax = max(prices)
            if ymin == ymax:
                ymin *= 0.98
                ymax *= 1.02
            ax.set_ylim(ymin * 0.995, ymax * 1.005)
            ax.scatter(x[-1], prices[-1], color=color, s=18)

            change = 0.0
            if len(prices) >= 2 and prices[0] != 0:
                change = (prices[-1] - prices[0]) / prices[0] * 100
            card["price_var"].set(f"${prices[-1]:,.2f}")
            card["change_var"].set(f"{change:+.2f}%")
            card["change_label"].config(
                fg=COLOR_BUY if change >= 0 else COLOR_SELL
            )

            canvas.draw_idle()
        if not self.has_history_data:
            self.has_history_data = True
            self._maybe_hide_loading()
