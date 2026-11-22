"""
نمایشگر واریزی‌های کیف‌پول TRON (USDT TRC-20) و اعلان در تلگرام.
فقط به کیف‌پول شما وصل است؛ هیچ سایت دیگری درگیر نیست و هیچ کلید خصوصی‌ای لازم نیست.

Secrets لازم در GitHub (Settings > Secrets and variables > Actions):
  TELEGRAM_TOKEN   توکن ربات تلگرام
  CHAT_ID          شناسه چت (نام قدیمی CHT_ID هم پذیرفته می‌شود)
اختیاری:
  WALLET_ADDRESS   آدرس کیف‌پول (پیش‌فرض: آدرس زیر)
  TRONGRID_API_KEY برای محدودیت درخواست بالاتر
"""
import json
import os
import sys

import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT_ID = (os.environ.get("CHAT_ID") or os.environ.get("CHT_ID") or "").strip()
WALLET_ADDRESS = (os.environ.get("WALLET_ADDRESS") or "TXU41F4Y1TkUggM7SX589abP7HCfnyvTt1").strip()
USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
API_KEY = os.environ.get("TRONGRID_API_KEY", "").strip()
STATE_FILE = "state.json"
TRONSCAN_TX = "https://tronscan.org/#/transaction/"


def headers():
    return {"TRON-PRO-API-KEY": API_KEY} if API_KEY else {}


def send_telegram(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("هشدار: TELEGRAM_TOKEN یا CHAT_ID تنظیم نشده؛ پیام ارسال نشد.")
        return False
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    if not r.ok:
        print("خطای تلگرام:", r.status_code, r.text[:300])
    return r.ok


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    # سازگاری با نسخه قبلی
    if os.path.exists("last_tx.txt"):
        with open("last_tx.txt", encoding="utf-8") as f:
            last = f.read().strip()
        return {"wallet": WALLET_ADDRESS, "seen": [last] if last else [], "last_ts": 0}
    return None


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fetch_incoming(min_ts):
    url = f"https://api.trongrid.io/v1/accounts/{WALLET_ADDRESS}/transactions/trc20"
    params = {
        "limit": 50,
        "contract_address": USDT_CONTRACT,
        "only_to": "true",
        "only_confirmed": "true",
        "order_by": "block_timestamp,desc",
    }
    if min_ts:
        params["min_timestamp"] = min_ts
    r = requests.get(url, params=params, headers=headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("success", True):
        raise RuntimeError(f"TronGrid: {data}")
    return [t for t in data.get("data", []) if t.get("to") == WALLET_ADDRESS]


def usdt_balance():
    try:
        r = requests.get(f"https://api.trongrid.io/v1/accounts/{WALLET_ADDRESS}", headers=headers(), timeout=30)
        acc = (r.json().get("data") or [{}])[0]
        for item in acc.get("trc20", []):
            if USDT_CONTRACT in item:
                return int(item[USDT_CONTRACT]) / 1_000_000
        return 0.0
    except Exception as e:  # موجودی فقط برای نمایش است
        print("خطا در خواندن موجودی:", e)
        return None


def fmt(x):
    return f"{x:,.2f}"


def main():
    state = load_state()
    first_run = state is None or state.get("wallet") != WALLET_ADDRESS
    if first_run:
        state = {"wallet": WALLET_ADDRESS, "seen": [], "last_ts": 0}

    txs = fetch_incoming(state["last_ts"])
    seen = set(state["seen"])
    new = [t for t in txs if t["transaction_id"] not in seen]
    new.sort(key=lambda t: t["block_timestamp"])

    if first_run:
        bal = usdt_balance()
        ok = send_telegram(
            "✅ نمایشگر کیف‌پول فعال شد\n\n"
            f"👛 {WALLET_ADDRESS}\n"
            + (f"💵 موجودی USDT: {fmt(bal)}\n" if bal is not None else "")
            + "از این به بعد هر واریز USDT به همین کیف‌پول اینجا اعلام می‌شود."
        )
        print("اجرای اول؛ پیام فعال‌سازی:", "ارسال شد" if ok else "ارسال نشد")
    elif new:
        bal = usdt_balance()
        for t in new:
            amount = int(t["value"]) / 10 ** int(t.get("token_info", {}).get("decimals", 6))
            send_telegram(
                "💰 واریز جدید به کیف‌پول شما\n\n"
                f"💵 مبلغ: {fmt(amount)} USDT\n"
                f"👤 از: {t['from']}\n"
                + (f"🏦 موجودی فعلی: {fmt(bal)} USDT\n" if bal is not None else "")
                + f"🔗 {TRONSCAN_TX}{t['transaction_id']}"
            )
            print(f"واریز {amount} USDT اعلام شد")
    else:
        print("واریز جدیدی نیست.")

    for t in txs:
        seen.add(t["transaction_id"])
        state["last_ts"] = max(state["last_ts"], t["block_timestamp"])
    state["seen"] = sorted(seen, key=lambda x: x)[-200:]
    save_state(state)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("خطا:", e)
        sys.exit(1)
