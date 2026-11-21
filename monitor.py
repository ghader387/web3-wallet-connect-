import requests
import os

# خواندن مقادیر امن
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
WALLET_ADDRESS = "TXU41F4Y1TkUggM7SX589abP7HCfnyvTt1"
USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

def send_telegram_message(text):
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
payload = {"chat_id": CHAT_ID, "text": text}
requests.post(url, json=payload)

def check_transactions():
url = f"https://api.trongrid.io/v1/accounts/{WALLET_ADDRESS}/transactions/trc20?limit=1&contract_address={USDT_CONTRACT}"
try:
response = requests.get(url)
data = response.json()

if 'data' in data and len(data['data']) > 0:
latest_tx = data['data'][0]
tx_id = latest_tx['transaction_id']

last_tx = ""
if os.path.exists("last_tx.txt"):
with open("last_tx.txt", "r") as f:
last_tx = f.read().strip()

if tx_id != last_tx and last_tx != "":
amount = int(latest_tx['value']) / 1000000
sender = latest_tx['from']
message = f"💰 پرداخت جدید در KitchenGo!\n\n💵 مبلغ: {amount} USDT\n👤 فرستنده: {sender}"
send_telegram_message(message)
print(f"پیام ارسال شد: {amount} USDT")

with open("last_tx.txt", "w") as f:
f.write(tx_id)
except Exception as e:
print("خطا:", e)

if __name__ == "__main__":
check_transactions()
