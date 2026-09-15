"""Print twitterapi.io credit balance and what it covers."""
import json
import os
import urllib.request

KEY = os.environ.get("TWITTERAPI_IO_KEY") or next(
    (ln.split("=", 1)[1].strip() for ln in open(".env") if ln.startswith("TWITTERAPI_IO_KEY=")), ""
)
req = urllib.request.Request("https://api.twitterapi.io/oapi/my/info", headers={"X-API-Key": KEY})
info = json.load(urllib.request.urlopen(req, timeout=20))
credits = info.get("recharge_credits", 0) + info.get("bonus_credits", 0)
print(json.dumps(info, indent=1))
# 1 USD = 100,000 credits; a tweet costs 15 credits, a page (20 tweets) = 300 credits, min request 15 credits
print(f"\n≈ ${credits / 100_000:.2f}  →  ~{credits // 15:,} tweets  /  ~{credits // 300:,} timeline pages")
