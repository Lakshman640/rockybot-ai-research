import uvicorn
import webbrowser
import threading
import time

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" 🌟 RockyBot AI - News & Financial Research Web Engine 🌟 ")
    print("=" * 60)
    print(" Launching server at: http://localhost:8000")
    print(" Press Ctrl+C to terminate.")
    print("=" * 60 + "\n")
    
    # Auto-open browser in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
