import requests
import websocket
import json
import threading
import time
from config import REST_BASE_URL, WS_BASE_URL, WS_SSL_OPTIONS

def test_rest_api():
    print(f"Testing REST API ({REST_BASE_URL})...")
    url = f"{REST_BASE_URL}/api/v3/ticker/price"
    params = {"symbol": "BTCUSDT"}
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        print(f"✅ REST API Success: BTC Price = {data['price']}")
        return True
    except Exception as e:
        print(f"❌ REST API Failed: {e}")
        return False

def test_websocket():
    print(f"Testing WebSocket ({WS_BASE_URL})...")
    ws_url = f"{WS_BASE_URL}/btcusdt@ticker"
    
    received = False
    
    def on_message(ws, message):
        nonlocal received
        data = json.loads(message)
        print(f"✅ WebSocket Success: Received tick for {data['s']} at {data['c']}")
        received = True
        ws.close()
        
    def on_error(ws, error):
        print(f"❌ WebSocket Error: {error}")
        
    ws = websocket.WebSocketApp(ws_url, on_message=on_message, on_error=on_error)
    
    # Run in thread
    t = threading.Thread(target=lambda: ws.run_forever(sslopt=WS_SSL_OPTIONS))
    t.start()
    
    # Wait max 5 seconds
    timeout = 5
    start_time = time.time()
    while not received and time.time() - start_time < timeout:
        time.sleep(0.1)
        
    if not received:
        print("❌ WebSocket Timeout: No data received in 5 seconds")
        ws.close()
        
    t.join(timeout=1)
    return received

if __name__ == "__main__":
    rest_ok = test_rest_api()
    print("-" * 20)
    ws_ok = test_websocket()
    
    if rest_ok and ws_ok:
        print("\n🎉 All connectivity tests passed!")
    else:
        print("\n⚠️ Some tests failed. Check internet connection.")
