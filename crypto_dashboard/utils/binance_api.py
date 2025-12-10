import requests
from ..config import REST_BASE_URL

def get_current_price(symbol):
    """
    Get the current price for a symbol via REST API.
    Useful for initial data before WebSocket connects.
    """
    url = f"{REST_BASE_URL}/api/v3/ticker/price"
    params = {"symbol": symbol.upper()}
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data['price'])
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None

def get_24hr_stats(symbol):
    """
    Get 24-hour statistics for a symbol.
    """
    url = f"{REST_BASE_URL}/api/v3/ticker/24hr"
    params = {"symbol": symbol.upper()}
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching stats for {symbol}: {e}")
        return None
