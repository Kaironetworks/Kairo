"""Static release gate for the KAIRO source package.
Run from the repository root with Python 3.11+.
This gate never calls the network and never marks Fabric as live.
"""
from pathlib import Path
import ast
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
required = [
    "README.md", "docker-compose.yml", "START_KAIRO.ps1", "STOP_KAIRO.ps1", "BUILD_KAIRO.ps1",
    "backend/app/main.py", "backend/app/models.py", "backend/app/security.py", "backend/requirements.txt",
    "frontend/package.json", "frontend/package-lock.json", "frontend/src/App.jsx", "frontend/src/api.js",
    "frontend/src/main.jsx", "frontend/src/styles.css", "frontend/public/kairo-logo.png",
    "blockchain-gateway/server.js", "blockchain-gateway/package.json",
    "fabric/chaincode/kairo-trust/chaincode.js", "fabric/scripts/bootstrap.sh", "final_tools/live_api_smoke.py",
]
errors=[]
for rel in required:
    if not (ROOT/rel).exists(): errors.append(f"missing: {rel}")

for bad in [".env", "frontend/node_modules", "backend/__pycache__", "backend/app/__pycache__"]:
    if (ROOT/bad).exists(): errors.append(f"release artifact must not contain: {bad}")

for py in (ROOT/"backend"/"app").glob("*.py"):
    try: ast.parse(py.read_text(encoding="utf-8"))
    except Exception as e: errors.append(f"python parse failure {py}: {e}")

app=(ROOT/"frontend"/"src"/"App.jsx").read_text(encoding="utf-8")
for pattern in [r"fabricbric", r"React\.Component", r"export default function App\(\).*export default"]:
    if re.search(pattern, app): errors.append(f"frontend bad pattern: {pattern}")

main=(ROOT/"backend"/"app"/"main.py").read_text(encoding="utf-8")
if main.count("def require_case_access") != 1: errors.append("case authorization helper count is not exactly one")
if "case_members" not in main: errors.append("case membership enforcement missing")
if "pg_advisory_xact_lock" not in main: errors.append("document version serialization missing")
if "kairo_document_number_seq" not in main: errors.append("document number sequence missing")

print("KAIRO STATIC RELEASE GATE")
if errors:
    for e in errors: print("[FAIL]", e)
    sys.exit(1)
print("[PASS] Required release structure")
print("[PASS] Python AST parsing")
print("[PASS] Known frontend crash patterns absent")
print("[PASS] Authorization/version/document safeguards present")
print("[INFO] Frontend bundling and live Fabric require the target runtime")
print("RELEASE GATE: PASS")
