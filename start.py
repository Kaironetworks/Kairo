import os, socket, subprocess, sys
from pathlib import Path

root = Path(__file__).resolve().parent
os.chdir(root)

def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())
    finally:
        s.close()

print("\nKAIRO — shared evidence server")
print("Local: http://127.0.0.1:8000")
try:
    print(f"LAN:   http://{lan_ip()}:8000")
except OSError:
    pass
print("Other laptops on the same Wi-Fi use the LAN address above.")
print("Press Ctrl+C to stop.\n")

subprocess.run([
    sys.executable, "-m", "uvicorn", "backend.main:app",
    "--host", "0.0.0.0", "--port", "8000"
], check=False)
