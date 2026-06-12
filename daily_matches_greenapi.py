"""
Daily FIFA World Cup fixture alert via WhatsApp (Green API).
Runs on GitHub Actions at 8:00 AM BDT (2:00 AM UTC).

Required environment variables (set as GitHub Secrets):
  FOOTBALL_DATA_TOKEN  - free key from https://www.football-data.org/client/register
  GREENAPI_INSTANCE    - instance id from console.green-api.com, e.g. 1101234567
  GREENAPI_TOKEN       - API token of that instance
  WHATSAPP_NUMBER      - your number, digits only with country code, e.g. 8801XXXXXXXXX
"""

import os
import sys
import urllib.request
import json
from datetime import datetime, timedelta, timezone

FOOTBALL_DATA_TOKEN = os.environ["FOOTBALL_DATA_TOKEN"]
GREENAPI_INSTANCE = os.environ["GREENAPI_INSTANCE"]
GREENAPI_TOKEN = os.environ["GREENAPI_TOKEN"]
WHATSAPP_NUMBER = os.environ["WHATSAPP_NUMBER"]

BDT = timezone(timedelta(hours=6))


def fetch_matches():
    now = datetime.now(timezone.utc)
    date_from = now.date().isoformat()
    date_to = (now + timedelta(days=2)).date().isoformat()
    url = (
        "https://api.football-data.org/v4/competitions/WC/matches"
        f"?dateFrom={date_from}&dateTo={date_to}"
    )
    req = urllib.request.Request(url, headers={"X-Auth-Token": FOOTBALL_DATA_TOKEN})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    cutoff = now + timedelta(hours=24)
    upcoming = []
    for m in data.get("matches", []):
        kickoff = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
        if now <= kickoff <= cutoff:
            upcoming.append(
                {
                    "home": m["homeTeam"]["name"],
                    "away": m["awayTeam"]["name"],
                    "stage": m.get("stage", "").replace("_", " ").title(),
                    "group": m.get("group"),
                    "kickoff_bdt": kickoff.astimezone(BDT),
                }
            )
    upcoming.sort(key=lambda x: x["kickoff_bdt"])
    return upcoming


def build_message(matches):
    today = datetime.now(BDT).strftime("%d %b %Y")
    if not matches:
        return f"World Cup, {today}: no matches in the next 24 hours."

    lines = [f"*World Cup matches, next 24h* ({today}):", ""]
    for m in matches:
        when = m["kickoff_bdt"].strftime("%I:%M %p")
        extra = m["group"] if m["group"] else m["stage"]
        lines.append(f"{when} BDT: {m['home']} vs {m['away']} ({extra})")
    return "\n".join(lines)


def send_whatsapp(text):
    url = (
        f"https://api.green-api.com/waInstance{GREENAPI_INSTANCE}"
        f"/sendMessage/{GREENAPI_TOKEN}"
    )
    payload = json.dumps(
        {"chatId": f"{WHATSAPP_NUMBER}@c.us", "message": text}
    ).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print("Green API response:", resp.read().decode())


if __name__ == "__main__":
    try:
        matches = fetch_matches()
        msg = build_message(matches)
        print(msg)
        send_whatsapp(msg)
    except Exception as e:
        print("Failed:", e)
        sys.exit(1)
