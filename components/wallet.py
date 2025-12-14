import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime

import requests
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Circle

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

        # Single ttk.Style instance keeps the table/progress visuals consistent.
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure(
            "Wallet.Horizontal.TProgressbar",
            troughcolor="#111827",
            background=ACCENT_COLOR,
            bordercolor="#111827",
            lightcolor=ACCENT_COLOR,
            darkcolor=ACCENT_COLOR,
            thickness=6,
        )

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
        self.last_updated_var = tk.StringVar(value="Waiting for update...")
        self.best_asset_var = tk.StringVar(value="--")
        self.best_change_var = tk.StringVar(value="--")
        self.worst_asset_var = tk.StringVar(value="--")
        self.worst_change_var = tk.StringVar(value="--")
        self.diversification_text_var = tk.StringVar(value="--")
        self.diversification_score = tk.DoubleVar(value=0.0)

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

        header_row = tk.Frame(frame, bg=CARD_COLOR)
        header_row.pack(fill="x")
        tk.Label(
            header_row,
            text="My Portfolio",
            font=("Arial", 16, "bold"),
            fg=TEXT_COLOR,
            bg=CARD_COLOR,
        ).pack(side=tk.LEFT, anchor="w")
        tk.Label(
            header_row,
            textvariable=self.last_updated_var,
            font=("Arial", 9),
            fg=TEXT_SECONDARY,
            bg=CARD_COLOR,
        ).pack(side=tk.RIGHT, anchor="e")

        tk.Label(
            frame,
            textvariable=self.summary_value,
            font=("Arial", 34, "bold"),
            fg=ACCENT_COLOR,
            bg=CARD_COLOR,
        ).pack(anchor="w", pady=(10, 2))

        tk.Label(
            frame,
            textvariable=self.summary_hint,
            font=("Arial", 10),
            fg=TEXT_SECONDARY,
            bg=CARD_COLOR,
        ).pack(anchor="w")

        pl_box = tk.Frame(
            frame,
            bg="#0f1624",
            padx=14,
            pady=10,
            highlightthickness=1,
            highlightbackground="#1f2734",
        )
        pl_box.pack(fill="x", pady=(14, 8))
        pl_box.grid_columnconfigure(1, weight=1)
        tk.Label(
            pl_box,
            text="Today P/L",
            font=("Arial", 11, "bold"),
            fg=TEXT_SECONDARY,
            bg="#0f1624",
        ).grid(row=0, column=0, sticky="w")
        self.pl_value_label = tk.Label(
            pl_box,
            textvariable=self.pl_value_var,
            font=("Arial", 16, "bold"),
            fg=TEXT_SECONDARY,
            bg="#0f1624",
        )
        self.pl_value_label.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.pl_percent_label = tk.Label(
            pl_box,
            textvariable=self.pl_percent_var,
            font=("Arial", 11, "bold"),
            fg=TEXT_SECONDARY,
            bg="#0f1624",
        )
        self.pl_percent_label.grid(row=1, column=1, sticky="w", padx=(14, 0))

        self.trend_figure = Figure(figsize=(5, 1.5), facecolor=CARD_COLOR)
        self.trend_ax = self.trend_figure.add_subplot(111)
        self.trend_ax.set_facecolor(CARD_COLOR)
        self.trend_ax.tick_params(axis="both", colors=TEXT_SECONDARY, labelsize=7)
        for spine in self.trend_ax.spines.values():
            spine.set_color(BORDER_COLOR)
        self.trend_canvas = FigureCanvasTkAgg(self.trend_figure, master=frame)
        trend_widget = self.trend_canvas.get_tk_widget()
        trend_widget.configure(highlightthickness=1, highlightbackground="#1b2533")
        trend_widget.pack(fill="x", pady=(8, 4))

        metrics_row = tk.Frame(frame, bg=CARD_COLOR)
        metrics_row.pack(fill="x", pady=(8, 0))
        self._create_metric_card(
            metrics_row,
            "Best Performer",
            self.best_asset_var,
            self.best_change_var,
        )
        self._create_metric_card(
            metrics_row,
            "Lagging Asset",
            self.worst_asset_var,
            self.worst_change_var,
        )
        self.diversification_card = self._create_metric_card(
            metrics_row,
            "Diversification",
            self.diversification_text_var,
            None,
            with_progress=True,
            progress_var=self.diversification_score,
        )

    def _create_metric_card(
        self,
        parent,
        title,
        primary_var,
        secondary_var=None,
        with_progress=False,
        progress_var=None,
    ):
        card = tk.Frame(
            parent,
            bg="#0f1624",
            padx=14,
            pady=12,
            highlightthickness=1,
            highlightbackground="#1f2734",
        )
        card.pack(side=tk.LEFT, expand=True, fill="x", padx=4)
        tk.Label(
            card,
            text=title.upper(),
            font=("Arial", 9, "bold"),
            fg=TEXT_SECONDARY,
            bg="#0f1624",
        ).pack(anchor="w")
        tk.Label(
            card,
            textvariable=primary_var,
            font=("Arial", 14, "bold"),
            fg=TEXT_COLOR,
            bg="#0f1624",
        ).pack(anchor="w", pady=(4, 0))
        if secondary_var:
            tk.Label(
                card,
                textvariable=secondary_var,
                font=("Arial", 10),
                fg=TEXT_SECONDARY,
                bg="#0f1624",
            ).pack(anchor="w")

        progress = None
        if with_progress:
            progress = ttk.Progressbar(
                card,
                maximum=100,
                variable=progress_var,
                style="Wallet.Horizontal.TProgressbar",
            )
            progress.pack(fill="x", pady=(8, 0))

        return {"frame": card, "progress": progress}

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

        table_card = tk.Frame(
            container,
            bg="#090f19",
            padx=10,
            pady=10,
            highlightthickness=1,
            highlightbackground="#1d2535",
        )
        table_card.grid(row=1, column=0, sticky="nsew")
        table_card.columnconfigure(0, weight=1)
        table_card.rowconfigure(2, weight=1)

        header = tk.Frame(table_card, bg="#090f19")
        header.grid(row=0, column=0, sticky="ew")

        self.table_columns = [
            ("asset", "Asset", "w", 3),
            ("amount", "Amount", "center", 2),
            ("price", "Price", "e", 3),
            ("value", "Value", "e", 3),
            ("change", "Change", "e", 2),
        ]

        for idx, (_, title, anchor, weight) in enumerate(self.table_columns):
            header.grid_columnconfigure(idx, weight=weight)
            tk.Label(
                header,
                text=title,
                font=("Arial", 11, "bold"),
                fg=TEXT_SECONDARY,
                bg="#090f19",
                anchor=anchor,
            ).grid(row=0, column=idx, sticky="ew", padx=(0, 6))

        tk.Frame(table_card, bg="#1a2436", height=2).grid(
            row=1, column=0, sticky="ew", pady=(6, 0)
        )

        self.table_body = tk.Frame(table_card, bg="#090f19")
        self.table_body.grid(row=2, column=0, sticky="nsew", pady=(6, 0))
        self.table_body.columnconfigure(0, weight=1)

        self.table_rows = {}
        for idx, asset in enumerate(self.holding_order):
            self._create_table_row(asset, idx)

    def _create_table_row(self, asset, index):
        base_bg = self._row_bg(index)
        row = tk.Frame(
            self.table_body,
            bg=base_bg,
            padx=10,
            pady=8,
            highlightthickness=0,
        )
        row.grid(row=index, column=0, sticky="ew", pady=(0, 4))

        labels = {}
        for idx, (key, _, anchor, weight) in enumerate(self.table_columns):
            row.grid_columnconfigure(idx, weight=weight)
            lbl = tk.Label(
                row,
                text="--",
                font=("Arial", 11),
                fg=TEXT_COLOR if key != "change" else TEXT_SECONDARY,
                bg=base_bg,
                anchor=anchor,
            )
            lbl.grid(row=0, column=idx, sticky="ew", padx=(0, 6))
            labels[key] = lbl

        self.table_rows[asset] = {
            "frame": row,
            "labels": labels,
            "base_bg": base_bg,
        }

        widgets = [row] + list(labels.values())
        for w in widgets:
            w.bind("<Enter>", lambda e, a=asset: self._on_row_enter(a))
            w.bind("<Leave>", lambda e, a=asset: self._on_row_leave(a))

    def _row_bg(self, index):
        return "#0c1522" if index % 2 == 0 else "#0f1a2b"

    def _set_row_bg(self, asset, color):
        info = self.table_rows.get(asset)
        if not info:
            return
        info["frame"].config(bg=color)
        for lbl in info["labels"].values():
            lbl.config(bg=color)

    def _on_row_enter(self, asset):
        self._set_row_bg(asset, "#16243a")

    def _on_row_leave(self, asset):
        info = self.table_rows.get(asset)
        if not info:
            return
        self._set_row_bg(asset, info["base_bg"])

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
        container.rowconfigure(1, weight=1)

        tk.Label(
            container,
            text="Allocation",
            font=("Arial", 12, "bold"),
            fg=TEXT_COLOR,
            bg=CARD_COLOR,
        ).pack(anchor="w")

        # ===== Chart Frame =====
        chart_frame = tk.Frame(container, bg=CARD_COLOR)
        chart_frame.pack(fill="both", expand=True, pady=(6, 4))

        self.figure = Figure(figsize=(4, 3), facecolor=CARD_COLOR)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor(CARD_COLOR)

        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # ===== Legend =====
        legend_wrapper = tk.Frame(
            container,
            bg=CARD_COLOR,
            padx=8,
            pady=6,
        )
        legend_wrapper.pack(fill="x")

        self.legend_body = tk.Frame(
            legend_wrapper,
            bg="#0f1624",
            padx=10,
            pady=10,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
        )
        self.legend_body.pack(fill="x")

        # ===== Insights =====
        insight_frame = tk.Frame(
            container,
            bg="#0f1624",
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
            bg="#0f1624",
        ).pack(anchor="w")

        self.insight_label = tk.Label(
            insight_frame,
            textvariable=self.insights_var,
            justify="left",
            font=("Arial", 9),
            fg=TEXT_SECONDARY,
            bg="#0f1624",
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
            timestamp = datetime.now().strftime("%I:%M:%S %p")
            self.last_updated_var.set(f"Synced {timestamp}")
        else:
            self.summary_value.set("--")
            self.summary_hint.set("Waiting for current prices...")
            self.last_updated_var.set("Waiting for live update...")

        self._update_metrics(rows, total_value)
        self._update_table(rows)
        self._update_allocation_chart(rows)
        self._update_insights(rows, total_value)

        if self.is_active:
            self.refresh_job = self.after(
                self.refresh_interval, self._refresh_prices
            )

    def _update_table(self, rows):
        if not hasattr(self, "table_rows"):
            return

        for idx, row in enumerate(rows):
            asset = row["asset"]
            info = self.table_rows.get(asset)
            if not info:
                continue

            base_bg = self._row_bg(idx)
            info["base_bg"] = base_bg
            self._set_row_bg(asset, base_bg)

            amount_text = f"{row['amount']:.4f}"
            price_text = (
                f"${row['price']:,.2f}" if row["price"] is not None else "--"
            )
            value_text = (
                f"${row['value']:,.2f}" if row["value"] is not None else "--"
            )
            if row["change"] is None:
                change_text = "--"
                change_color = TEXT_SECONDARY
            else:
                change_text = f"{row['change']:+.2f}%"
                if row["change"] > 0:
                    change_color = COLOR_BUY
                elif row["change"] < 0:
                    change_color = COLOR_SELL
                else:
                    change_color = TEXT_SECONDARY

            labels = info["labels"]
            labels["asset"].config(text=asset, fg=TEXT_COLOR)
            labels["amount"].config(text=amount_text, fg="#8fd3ff")
            labels["price"].config(text=price_text, fg=change_color)
            labels["value"].config(text=value_text, fg=change_color)
            labels["change"].config(text=change_text, fg=change_color)

    def _update_metrics(self, rows, total_value):
        valid_change = [r for r in rows if r.get("change") is not None]
        if valid_change:
            best = max(valid_change, key=lambda r: r["change"])
            worst = min(valid_change, key=lambda r: r["change"])
            best_value = (
                f"${best['value']:,.0f}" if best.get("value") is not None else "--"
            )
            worst_value = (
                f"${worst['value']:,.0f}" if worst.get("value") is not None else "--"
            )
            self.best_asset_var.set(best["asset"])
            self.best_change_var.set(f"{best['change']:+.2f}%  |  {best_value}")
            self.worst_asset_var.set(worst["asset"])
            self.worst_change_var.set(f"{worst['change']:+.2f}%  |  {worst_value}")
        else:
            self.best_asset_var.set("--")
            self.best_change_var.set("--")
            self.worst_asset_var.set("--")
            self.worst_change_var.set("--")

        valid_values = [r for r in rows if r.get("value")]
        if valid_values and total_value > 0:
            leader = max(valid_values, key=lambda r: r["value"])
            leader_ratio = leader["value"] / total_value if total_value else 0
            score = max(0, min(100, (1 - leader_ratio) * 100))
            descriptor = (
                "Well distributed"
                if score >= 65
                else "Moderate mix"
                if score >= 35
                else "Highly concentrated"
            )
            self.diversification_text_var.set(descriptor)
            self.diversification_score.set(score)
        else:
            self.diversification_text_var.set("Awaiting allocation data")
            self.diversification_score.set(0)

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
            wedges, texts, autotexts = self.ax.pie(
                values,
                labels=labels,
                autopct="%1.1f%%",
                colors=colors,
                textprops={"color": TEXT_COLOR, "fontsize": 9},
                wedgeprops={
                    "linewidth": 1,
                    "edgecolor": CARD_COLOR,
                    "width": 0.42,
                },
                startangle=120,
                pctdistance=0.78,
            )
            for text in texts + autotexts:
                text.set_color(TEXT_COLOR)
            centre = Circle((0, 0), 0.42, color=CARD_COLOR, zorder=10)
            self.ax.add_artist(centre)

        self.ax.set_aspect("equal")
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
            spine.set_visible(False)
        self.trend_ax.set_xticks([])
        self.trend_ax.set_yticks([])
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
            baseline = sum(self.history_values) / len(self.history_values)
            self.trend_ax.axhline(
                baseline,
                color="#1e2735",
                linewidth=1,
                linestyle="--",
                alpha=0.6,
            )
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
                alpha=0.2,
            )
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
