# Crypto Dashboard Pro

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)


An unapologetically extra crypto dashboard that feels like a premium trade desk—crafted entirely in Python. Tkinter handles the cinematic UI, Binance WebSockets keep data flowing in real time, and every component is tuned for a flashier market experience.

## 🔥 Why It's Over the Top
- **Cinematic Home Screen** – Hero artwork, glowing CTA button, and gold logomark before you even reach the markets.
- **Realtime Overview** – Price cards, donut volume mix, and mini sparklines powered by Binance streaming plus a REST fallback every 5 seconds.
- **Multi-Panel Market Rows** – Each asset row stacks ticker, depth book, chart (matplotlib/mplfinance), and recent-trade feed in one responsive layout.
- **Smart Sidebar** – Toggle panels, switch symbols, and persist preferences through `preferences.json`.
- **Headless Mode** – No display? Run the CLI snapshot mode and still get 24h stats.

## 🧱 Tech Stack / Libraries
- **Python 3.10+**
- **Tkinter** for the desktop interface
- **websocket-client** + **Binance Stream** for live data
- **requests** for REST snapshots and historical pulls
- **matplotlib / mplfinance / numpy / pandas** for charts, sparklines, and order-book graphics
- **Pillow (PIL)** for splash images, CTA gradients, and logos

## 🗂️ Key Structure
```
crypto_dashboard/
├─ main.py              # Entry point, window layout, sidebar, routing
├─ components/
│  ├─ home_screen.py    # Splash screen + CTA
│  ├─ overview.py       # Realtime overview panel
│  ├─ ticker.py         # Live ticker header
│  ├─ orderbook.py      # Depth/heat map panel
│  ├─ chart.py          # Candlestick/line chart
│  ├─ trades_feed.py    # Live trades list
│  └─ volume_stats.py   # Volume stats card
├─ config.py            # Symbols, theme colors, endpoints, prefs file
└─ requirements.txt
```

## 🚀 Install & Run
1. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Launch the GUI**
   ```bash
   python3 main.py
   ```
4. **Extra launch options**
   ```bash
   python3 main.py --headless       # CLI snapshot mode (no display)
   python3 main.py --force-gui      # Force GUI even if the system looks headless
   python3 -m crypto_dashboard.main # Module-style entry point
   ```

## 💡 Tips & Notes
- Use the sidebar toggles to hide panels or switch symbols for smaller screens.
- The app auto-creates `.matplotlib_cache/` so Matplotlib behaves in sandboxed environments.
- REST fallback (5-second cadence) keeps the Overview data fresh when the socket hiccups.
- Customize `config.py` to add more symbols, recolor the UI, or point to alternate REST/WebSocket endpoints.

Time to hunt some alpha—fire it up! 🟡🚀

---

This project was created by **Thanutdit Jiravichalert (Student ID 6810545662)** as the final project for **Programming 1 (01219114-01219115)**.
