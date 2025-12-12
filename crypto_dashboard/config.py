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

# API Settings
REST_BASE_URL = "https://api.binance.com"
WS_BASE_URL = "wss://stream.binance.com:9443/ws"

# Dark Theme Colors
BG_COLOR = "#0b0e11"       # Main background (Very dark)
CARD_COLOR = "#1e2329"     # Card/Panel background
TEXT_COLOR = "#eaecef"     # Primary text (White/Grey)
TEXT_SECONDARY = "#848e9c" # Secondary text (Grey)

# Trading Colors
COLOR_BUY = "#0ecb81"      # Green
COLOR_SELL = "#f6465d"     # Red
COLOR_NEUTRAL = "#eaecef"

# Fonts
FONT_TITLE = ("Arial", 20, "bold")
FONT_SUBTITLE = ("Arial", 14, "bold")
FONT_BODY = ("Arial", 11)
FONT_NUMBERS = ("Courier New", 12, "bold")

# Persistence
PREFS_FILE = "preferences.json"
