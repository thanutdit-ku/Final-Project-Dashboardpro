"""
Configuration file for Cryptocurrency Dashboard
"""

# Window Settings
WINDOW_TITLE = "Crypto Dashboard Pro"
WINDOW_SIZE = "1200x800"

# Symbol Settings
SYMBOLS = [
    {"symbol": "btcusdt", "name": "BTC/USDT"},
    {"symbol": "ethusdt", "name": "ETH/USDT"},
    {"symbol": "solusdt", "name": "SOL/USDT"},
    {"symbol": "bnbusdt", "name": "BNB/USDT"},
    {"symbol": "adausdt", "name": "ADA/USDT"},
]

import ssl

# API Settings
REST_BASE_URL = "https://api.binance.com"
WS_BASE_URL = "wss://stream.binance.com:9443/ws"
# Toggle SSL verification for WebSockets. Set to True to enforce cert checks.
VERIFY_WS_SSL = False
WS_SSL_OPTIONS = None if VERIFY_WS_SSL else {"cert_reqs": ssl.CERT_NONE}

# Dark Theme Colors (logo-inspired accent)
BG_COLOR = "#06090f"          # Main background (deeper slate)
CARD_COLOR = "#141921"        # Card/Panel background
CARD_HEADER_BG = "#1b212d"   # Sub-headers/boxes
SIDEBAR_BG = "#0c1016"       # Sidebar base
SIDEBAR_CARD_BG = "#161c27"  # Sidebar tiles when inactive
BORDER_COLOR = "#252c38"     # Subtle border color
ACCENT_COLOR = "#f0b90b"     # Matches gold logo
TEXT_COLOR = "#f5f7fa"       # Primary text (Warm white)
TEXT_SECONDARY = "#8a95a7"    # Secondary text (Grey)

# Trading Colors
COLOR_BUY = "#0ecb81"      # Green
COLOR_SELL = "#f6465d"     # Red
COLOR_NEUTRAL = "#eaecef"

# Fonts
FONT_TITLE = ("Arial", 20, "bold")
FONT_SUBTITLE = ("Arial", 14, "bold")
FONT_BODY = ("Arial", 11)
FONT_NUMBERS = ("Courier New", 12, "bold")

# Chart settings
CHART_INTERVAL = "1m"  # Use 1-minute candles for smoother updates

# Persistence
PREFS_FILE = "preferences.json"
