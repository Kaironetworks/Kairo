import os, socket, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parent
os.chdir(root)
print('KAIRO — starting shared demo server')
print('Local: http://localhost:8000')
try:
    ip=socket.gethostbyname(socket.gethostname())
    print('LAN:   http://%s:8000'%ip)
except: pass
print('Press Ctrl+C to stop. Other laptops on the same Wi-Fi can open the LAN address.')
subprocess.run([sys.executable,'-m','uvicorn','backend.main:app','--host','0.0.0.0','--port','8000'])
