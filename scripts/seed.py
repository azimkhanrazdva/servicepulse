"""Idempotent opt-in demo config; worker still performs every real check."""
import json
import urllib.request

base = "http://127.0.0.1:8080/api/monitors"
with urllib.request.urlopen(base) as response:
    existing = {m["url"] for m in json.load(response)}
for name, target in [("Demo · storefront", "storefront"), ("Demo · API", "api")]:
    url = f"http://simulator:8090/target/{target}"
    if url not in existing:
        request = urllib.request.Request(base, data=json.dumps({"name": name, "url": url}).encode(),
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request) as response:
            print(response.status, name)
