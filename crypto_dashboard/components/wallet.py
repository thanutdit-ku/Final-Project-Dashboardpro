import threading
import tkinter as tk
from tkinter import ttk

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..config import (
    BG_COLOR,
    CARD_COLOR,
    BORDER_COLOR,
    ACCENT_COLOR,
    TEXT_COLOR,
    TEXT_SECONDARY,
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

        self.summary_value = tk.StringVar(value="--")
        self.summary_hint = tk.StringVar(value="Fetching live prices...")

        self._build_layout()

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

        columns = ("asset", "amount", "price", "value")
        self.tree = ttk.Treeview(
            container,
            columns=columns,
            show="headings",
            style="Wallet.Treeview",
            selectmode="none",
        )
        for col, width in zip(columns, (110, 100, 120, 140)):
            self.tree.heading(col, text=col.title(), anchor="w")
            self.tree.column(col, anchor="w", width=width, stretch=True)

        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")

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
                snapshots[asset] = price
            self.after(0, lambda: self._apply_price_data(snapshots))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_price_data(self, price_map):
        if not self.is_active:
            return

        for asset, price in price_map.items():
            if price is not None:
                self.price_cache[asset] = price

        rows = []
        total_value = 0.0
        for asset in self.holding_order:
            meta = self.holdings[asset]
            amount = meta.get("amount", 0.0)
            price = self.price_cache.get(asset)
            value = amount * price if price is not None else None
            if value is not None:
                total_value += value
            rows.append(
                {
                    "asset": asset,
                    "amount": amount,
                    "price": price,
                    "value": value,
                }
            )

        if total_value > 0:
            self.summary_value.set(f"${total_value:,.2f}")
            self.summary_hint.set("Updated live from Binance REST")
        else:
            self.summary_value.set("--")
            self.summary_hint.set("Waiting for current prices...")

        self._update_table(rows)
        self._update_allocation_chart(rows)

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
            self.tree.insert(
                "",
                "end",
                values=(row["asset"], amount, price, value),
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
