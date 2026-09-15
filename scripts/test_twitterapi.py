"""Smoke test for twitterapi.io: fetch a user's recent tweets, with retry on 429."""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

KEY = os.environ.get("TWITTERAPI_IO_KEY") or next(
    (l.split("=", 1)[1].strip() for l in open(".env") if l.startswith("TWITTERAPI_IO_KEY=")), ""
)
BASE = "https://api.twitterapi.io"


def get(path, **params):
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"X-API-Key": KEY})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            raise


handle = sys.argv[1] if len(sys.argv) > 1 else "SantManukyan"

info = get("/twitter/user/info", userName=handle)
d = info.get("data", {})
print("USER:", d.get("userName"), "| followers:", d.get("followers"), "| tweets:", d.get("statusesCount"))

time.sleep(1)
page = get("/twitter/user/last_tweets", userName=handle)
data = page.get("data", {})
tweets = data.get("tweets", [])
print("TWEETS returned:", len(tweets), "| has_next:", page.get("has_next_page"), "| cursor:", bool(page.get("next_cursor")))
if tweets:
    print("keys:", sorted(tweets[0].keys()))
    for t in tweets[:6]:
        print(f"- {t.get('id')} {t.get('createdAt','')[:25]} reply={t.get('isReply')} :: {t.get('text','')[:80]!r}")
    print("oldest in page:", tweets[-1].get("createdAt"))

time.sleep(1)
print("CREDITS:", get("/oapi/my/info"))
