"""Quick integration check: static serving + API."""
import json
import urllib.request

BASE = "http://127.0.0.1:8000"

r = urllib.request.urlopen(f"{BASE}/api/v1/health")
print("health:", r.status, r.read().decode())

r = urllib.request.urlopen(f"{BASE}/")
body = r.read().decode()
print("GET / status:", r.status, "content-type:", r.headers.get("Content-Type"))
print("has root div:", 'id="root"' in body)
asset = body.split("assets/")[1].split('"')[0]
r2 = urllib.request.urlopen(f"{BASE}/assets/{asset}")
print("asset status:", r2.status, r2.headers.get("Content-Type"))

r = urllib.request.urlopen(f"{BASE}/api/v1/dataset/load")
print("dataset load:", r.status, json.loads(r.read())["message"])

r = urllib.request.urlopen(f"{BASE}/api/v1/settings")
print("settings:", r.status, sorted(r.json().keys()) if hasattr(r, "json") else "")
