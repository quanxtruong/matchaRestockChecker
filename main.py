import requests
from email.mime.text import MIMEText
import smtplib
import time
import json
from dotenv import load_dotenv
import os

load_dotenv()

PRODUCTS_URL = os.getenv("PRODUCTS_URL")
CHECK_INTERVAL = 900  # Check every 15 mins (in seconds)

# Email (Gmail SMTP example)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("MY_EMAIL")
EMAIL_PASSWORD = os.getenv("APP_PASSWORD")

# Recipient (SMS via Email Gateway - T-Mobile example)
RECIPIENT_SMS = os.getenv("RECIPIENT_EMAIL")  # e.g., 1234567890@tmomail.net

# File to store previous stock status
STATUS_FILE = "stock_status.json"

# --- FUNCTIONS ---
def get_stock_status():
    try:
        response = requests.get(f"{PRODUCTS_URL}.json")
        data = response.json()
        stock_dict = {}
        for product in data["products"]:
            product_title = product["title"]
            product_url = f"{PRODUCTS_URL}/{product['handle']}"
            # Check availability of first variant (can modify to check all variants)
            variant = product["variants"][0]
            is_available = variant["available"]
            stock_dict[product_title] = {
                "available": is_available,
                "url": product_url
            }
        return stock_dict
    except Exception as e:
        print("Error fetching stock data:", e)
        return {}

def load_previous_status():
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_status(status):
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f)

def send_sms_alert(product_title, product_url):
    msg = MIMEText(f"{product_title} is BACK IN STOCK! Buy here: {product_url}\n\n")
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT_SMS
    msg["Subject"] = "Restock Alert !!!!\n\n"

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, RECIPIENT_SMS, msg.as_string())
        print(f"SMS sent for: {product_title}")
    except Exception as e:
        print("Failed to send SMS:", e)

# --- MAIN LOOP ---
if __name__ == "__main__":
    while True:
        current_status = get_stock_status()
        prev_status = load_previous_status()

        for title, info in current_status.items():
            current_avail = info["available"]
            prev_avail = prev_status.get(title, {}).get("available", False)

            if not prev_avail and current_avail:
                send_sms_alert(title, info["url"])
            else:
                print(f"{title} - In stock: {current_avail}")

        save_status(current_status)
        time.sleep(CHECK_INTERVAL)
