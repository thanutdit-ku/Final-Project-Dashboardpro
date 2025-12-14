import threading
import tkinter as tk
from tkinter import ttk

import requests
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..config import (
    BG_COLOR,
    CARD_COLOR,
    BORDER_COLOR,
    ACCENT_COLOR,
    TEXT_COLOR,
    TEXT_SECONDARY,
    REST_BASE_URL,
    COLOR_BUY,
    COLOR_SELL,
)


class WalletPanel(tk.Frame):
    """Portfolio view with summary, holdings table, and allocation chart."""

    PIE_COLORS = [
        "#f0b90b",
        "#6ee7b7",
        "#93c5fd",
        "#fda4af",
        "#d8b4fe",
        "#fcd34d",
    ]

    def __init__(
        self,
        parent,
        holdings,
        price_fetcher,
        refresh_interval_ms=8000,
        fallback_prices=None,
    ):
        super().__init__(parent, bg=BG_COLOR, padx=12, pady=12)

        self.holdings = holdings
        self.holding_order = list(holdings.keys())
        self.price_fetcher = price_fetcher
        self.refresh_interval = refresh_interval_ms
        self.fallback_prices = fallback_prices or {}

        self.is_active = False
        self.refresh_job = None
        self.price_cache = {}
        self.change_cache = {}
        self.history_values = []
        self.previous_close_value = None

        self.summary_value = tk.StringVar(value="--")
        self.summary_hint = tk.StringVar(value="Fetching live prices...")
        self.pl_value_var = tk.StringVar(value="--")
        self.pl_percent_var = tk.StringVar(value="--")
        self.insights_var = tk.StringVar(value="Analyzing allocation...")

        self._build_layout()
        self._seed_mock_history()

    # ------------------------
    # UI CONSTRUCTION
    # ------------------------
    def _build_layout(self):
        self.columnconfigure(0, weight=2, uniform="wallet")
        self.columnconfigure(1, weight=1, uniform="wallet")
        self.rowconfigure(1, weight=1)

        self._build_summary_card()
        self._build_table()
        self._build_allocation_chart()

    def _build_summary_card(self):
        frame = tk.Frame(
            self,
            bg=CARD_COLOR,
            padx=18,
            pady=16,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
        )
        frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        header = tk.Label(
            frame,
            text="My Portfolio",
            font=("Arial", 16, "bold"),
            fg=TEXT_COLOR,
            bg=CARD_COLOR,
        )
        header.pack(anchor="w")

        tk.Label(
            frame,
            textvariable=self.summary_value,
            font=("Arial", 28, "bold"),
            fg=ACCENT_COLOR,
            bg=CARD_COLOR,
        ).pack(anchor="w", pady=(8, 0))

        tk.Label(
            frame,
            textvariable=self.summary_hint,
            font=("Arial", 10),
            fg=TEXT_SECONDARY,
            bg=CARD_COLOR,
        ).pack(anchor="w", pady=(6, 0))

        pl_box = tk.Frame(frame, bg=CARD_COLOR)
        pl_box.pack(fill="x", pady=(10, 4))
        tk.Label(
            pl_box,
            text="Today P/L",
            font=("Arial", 10, "bold"),
            fg=TEXT_SECONDARY,
            bg=CARD_COLOR,
        ).grid(row=0, column=0, sticky="w")
        self.pl_value_label = tk.Label(
            pl_box,
            textvariable=self.pl_value_var,
            font=("Arial", 14, "bold"),
            fg=TEXT_SECONDARY,
            bg=CARD_COLOR,
        )
        self.pl_value_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.pl_percent_label = tk.Label(
            pl_box,
            textvariable=self.pl_percent_var,
            font=("Arial", 10, "bold"),
            fg=TEXT_SECONDARY,
            bg=CARD_COLOR,
        )
        self.pl_percent_label.grid(row=1, column=1, sticky="w", padx=(10, 0))

        self.trend_figure = Figure(figsize=(4, 1.2), facecolor=CARD_COLOR)
        self.trend_ax = self.trend_figure.add_subplot(111)
        self.trend_ax.set_facecolor(CARD_COLOR)
        self.trend_ax.tick_params(axis="both", colors=TEXT_SECONDARY, labelsize=7)
        for spine in self.trend_ax.spines.values():
            spine.set_color(BORDER_COLOR)
        self.trend_canvas = FigureCanvasTkAgg(self.trend_figure, master=frame)
        self.trend_canvas.get_tk_widget().pack(fill="x", pady=(8, 0))

    def _build_table(self):
        container = tk.Frame(
            self,
            bg=CARD_COLOR,
            padx=12,
            pady=12,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
        )
        container.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        tk.Label(
            container,
            text="Asset Holdings",
            font=("Arial", 12, "bold"),
            fg=TEXT_COLOR,
            bg=CARD_COLOR,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        style = ttk.Style(container)
        style.theme_use("clam")
        style.configure(
            "Wallet.Treeview",
            background=CARD_COLOR,
            fieldbackground=CARD_COLOR,
            foreground=TEXT_COLOR,
            rowheight=30,
            bordercolor=BORDER_COLOR,
            borderwidth=0,
            highlightthickness=0,
            font=("Arial", 10),
        )
        style.configure(
            "Wallet.Treeview.Heading",
            background="#11161f",
            foreground=TEXT_SECONDARY,
            relief="flat",
            font=("Arial", 10, "bold"),
        )
        style.map("Wallet.Treeview", background=[("selected", "#1f2933")])

        columns = ("asset", "amount", "price", "value", "change")
        self.tree = ttk.Treeview(
            container,
            columns=columns,
            show="headings",
            style="Wallet.Treeview",
            selectmode="none",
        )
        for col, width in zip(columns, (110, 100, 120, 140, 100)):
            self.tree.heading(col, text=col.title(), anchor="w")
            self.tree.column(col, anchor="w", width=width, stretch=True)

        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")

        self.tree.tag_configure("positive", foreground=COLOR_BUY)
        self.tree.tag_configure("negative", foreground=COLOR_SELL)
        self.tree.tag_configure("neutral", foreground=TEXT_COLOR)

    def _build_allocation_chart(self):
        container = tk.Frame(
            self,
            bg=CARD_COLOR,
            padx=12,
            pady=12,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
        )
        container.grid(row=1, column=1, sticky="nsew")

        tk.Label(
            container,
            text="Allocation",
            font=("Arial", 12, "bold"),
            fg=TEXT_COLOR,
            bg=CARD_COLOR,
        ).pack(anchor="w")

        self.figure = Figure(figsize=(4, 3), facecolor=CARD_COLOR)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor(CARD_COLOR)
        self.canvas = FigureCanvasTkAgg(self.figure, master=container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, pady=(8, 0))

        insight_frame = tk.Frame(
            container,
            bg=CARD_COLOR,
            padx=8,
            pady=8,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
        )
        insight_frame.pack(fill="x", pady=(8, 0))
        tk.Label(
            insight_frame,
            text="Wallet Insights",
            font=("Arial", 11, "bold"),
            fg=TEXT_COLOR,
            bg=CARD_COLOR,
        ).pack(anchor="w")
        self.insight_label = tk.Label(
            insight_frame,
            textvariable=self.insights_var,
            justify="left",
            font=("Arial", 9),
            fg=TEXT_SECONDARY,
            bg=CARD_COLOR,
            wraplength=220,
        )
        self.insight_label.pack(anchor="w", pady=(4, 0))

    # ------------------------
    # DATA REFRESH
    # ------------------------
    def start(self):
        if self.is_active:
            return
        self.is_active = True
        self._refresh_prices()

    def stop(self):
        self.is_active = False
        if self.refresh_job:
            try:
                self.after_cancel(self.refresh_job)
            except tk.TclError:
                pass
        self.refresh_job = None

    def _refresh_prices(self):
        if not self.is_active:
            return

        def worker():
            snapshots = {}
            for asset, meta in self.holdings.items():
                symbol = meta["symbol"]
                price = None
                try:
                    price = self.price_fetcher(symbol)
                except Exception as exc:
                    print(f"Wallet price fetch error for {symbol}: {exc}")
                if price is None:
                    fallback = self.fallback_prices.get(symbol.lower())
                    if fallback:
                        price = fallback.get("price")
                change = self._fetch_change_percent(symbol)
                if change is None:
                    fallback = self.fallback_prices.get(symbol.lower())
                    if fallback:
                        change = fallback.get("change")
                snapshots[asset] = {"price": price, "change": change}
            self.after(0, lambda: self._apply_price_data(snapshots))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_price_data(self, price_map):
        if not self.is_active:
            return

        for asset, payload in price_map.items():
            price = payload.get("price") if payload else None
            change = payload.get("change") if payload else None
            if price is not None:
                self.price_cache[asset] = price
            if change is not None:
                self.change_cache[asset] = change

        rows = []
        total_value = 0.0
        for asset in self.holding_order:
            meta = self.holdings[asset]
            amount = meta.get("amount", 0.0)
            price = self.price_cache.get(asset)
            change = self.change_cache.get(asset)
            value = amount * price if price is not None else None
            if value is not None:
                total_value += value
            rows.append(
                {
                    "asset": asset,
                    "amount": amount,
                    "price": price,
                    "value": value,
                    "change": change,
                }
            )

        if total_value > 0:
            self.summary_value.set(f"${total_value:,.2f}")
            self.summary_hint.set("Updated live from Binance REST")
            self._update_performance(total_value)
            self._extend_history(total_value)
        else:
            self.summary_value.set("--")
            self.summary_hint.set("Waiting for current prices...")

        self._update_table(rows)
        self._update_allocation_chart(rows)
        self._update_insights(rows, total_value)

        if self.is_active:
            self.refresh_job = self.after(
                self.refresh_interval, self._refresh_prices
            )

    def _update_table(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            amount = f"{row['amount']:.4f}"
            price = f"${row['price']:,.2f}" if row["price"] is not None else "--"
            value = f"${row['value']:,.2f}" if row["value"] is not None else "--"
            change = (
                f"{row['change']:+.2f}%"
                if row["change"] is not None
                else "--"
            )
            tag = "neutral"
            if row["change"] is not None:
                if row["change"] > 0:
                    tag = "positive"
                elif row["change"] < 0:
                    tag = "negative"
            self.tree.insert(
                "",
                "end",
                values=(row["asset"], amount, price, value, change),
                tags=(tag,),
            )

    def _update_allocation_chart(self, rows):
        self.ax.clear()
        self.ax.set_facecolor(CARD_COLOR)
        self.figure.patch.set_facecolor(CARD_COLOR)

        values = [row["value"] for row in rows if row["value"]]
        labels = [row["asset"] for row in rows if row["value"]]

        if not values:
            self.ax.text(
                0.5,
                0.5,
                "No price data",
                color=TEXT_SECONDARY,
                ha="center",
                va="center",
                fontsize=12,
            )
        else:
            colors = (self.PIE_COLORS * ((len(values) // len(self.PIE_COLORS)) + 1))[
                : len(values)
            ]
            self.ax.pie(
                values,
                labels=labels,
                autopct="%1.1f%%",
                colors=colors,
                textprops={"color": TEXT_COLOR, "fontsize": 10},
                wedgeprops={"linewidth": 1, "edgecolor": BORDER_COLOR},
            )

        self.canvas.draw_idle()

    def _update_performance(self, total_value):
        if self.previous_close_value is None:
            self.previous_close_value = total_value
        delta = total_value - self.previous_close_value
        pct = (
            (delta / self.previous_close_value) * 100
            if self.previous_close_value
            else 0.0
        )
        color = COLOR_BUY if delta >= 0 else COLOR_SELL
        self.pl_value_var.set(f"${delta:+,.2f}")
        self.pl_percent_var.set(f"{pct:+.2f}%")
        self.pl_value_label.config(fg=color)
        self.pl_percent_label.config(fg=color)

    def _extend_history(self, total_value):
        if total_value <= 0:
            return
        if self.history_values:
            self.previous_close_value = self.history_values[-1]
        self.history_values.append(total_value)
        self.history_values = self.history_values[-32:]
        self._update_trend_chart()

    def _update_trend_chart(self):
        self.trend_ax.clear()
        self.trend_ax.set_facecolor(CARD_COLOR)
        for spine in self.trend_ax.spines.values():
            spine.set_color(BORDER_COLOR)
        if len(self.history_values) < 2:
            self.trend_ax.text(
                0.5,
                0.5,
                "No history",
                color=TEXT_SECONDARY,
                ha="center",
                va="center",
                fontsize=9,
            )
        else:
            x = list(range(len(self.history_values)))
            self.trend_ax.plot(
                x,
                self.history_values,
                color=ACCENT_COLOR,
                linewidth=2,
            )
            self.trend_ax.fill_between(
                x,
                self.history_values,
                color=ACCENT_COLOR,
                alpha=0.15,
            )
            self.trend_ax.set_xticks([])
            self.trend_ax.set_yticks([])
        self.trend_canvas.draw_idle()

    def _update_insights(self, rows, total_value):
        if total_value <= 0:
            self.insights_var.set("Awaiting live data to generate insights.")
            return
        valid_rows = [r for r in rows if r["value"]]
        if not valid_rows:
            self.insights_var.set("Awaiting live data to generate insights.")
            return
        sorted_rows = sorted(valid_rows, key=lambda r: r["value"], reverse=True)
        top = sorted_rows[0]
        top_pct = top["value"] / total_value
        lines = [f"{top['asset']} represents {top_pct:.1%} of the wallet."]
        if top_pct > 0.55:
            lines.append("High concentration risk detected—consider rebalancing.")
        else:
            lines.append("Holdings look reasonably diversified.")

        laggard = min(
            valid_rows,
            key=lambda r: r.get("change", 0.0) if r.get("change") is not None else 0.0,
        )
        laggard_change = laggard.get("change")
        if laggard_change is not None and laggard_change < -2:
            lines.append(
                f"{laggard['asset']} is underperforming ({laggard_change:.1f}%)."
            )
        else:
            lines.append("No major asset drawdowns over the last 24h.")
        self.insights_var.set("\n".join(lines))

    def _seed_mock_history(self):
        baseline = self._fallback_total()
        if baseline <= 0:
            baseline = 10000
        deltas = [-0.03, -0.02, -0.01, -0.005, 0.0, 0.01, 0.02]
        self.history_values = [baseline * (1 + d) for d in deltas]
        if self.history_values:
            self.previous_close_value = self.history_values[-1]
        self._update_trend_chart()

    def _fallback_total(self):
        total = 0.0
        for meta in self.holdings.values():
            sym = meta["symbol"].lower()
            fallback = self.fallback_prices.get(sym)
            price = fallback.get("price") if fallback else None
            if price is not None:
                total += meta.get("amount", 0.0) * price
        return total

    def _fetch_change_percent(self, symbol):
        url = f"{REST_BASE_URL}/api/v3/ticker/24hr"
        try:
            resp = requests.get(url, params={"symbol": symbol.upper()}, timeout=5)
            resp.raise_for_status()
            payload = resp.json()
            return float(payload.get("priceChangePercent", 0.0))
        except Exception as exc:
            print(f"Wallet change fetch error for {symbol}: {exc}")
            return None
