import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import json
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

if os.getenv("GITHUB_ACTIONS") != "true":
    load_dotenv()

IPPUDO_URL = os.getenv("IPPUDO_URL")
MATCHA_JP_URL = os.getenv("MATCHA_JP_URL")
SAZEN_URLS = os.getenv("SAZEN_URLS", "").split(",")

SMTP_SERVER = "smtp.gmail.com" 
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
RECIPIENT_SMS = os.getenv("RECIPIENT_SMS")

STATUS_FILE = "stock_status.json"

def process_stock(url, stock_dict):
    response = requests.get(f"{url}.json")
    data = response.json()
    for product in data["products"]:
        product_title = product["title"]
        product_url = f"{url}/{product['handle']}"
        variant = product["variants"][0]
        is_available = variant["available"]
        stock_dict[product_title] = {
            "available": is_available,
            "url": product_url
        }

def process_sazen(stock_dict):
    for url in SAZEN_URLS:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        unavailable_msg = soup.find("strong", class_="red")
        quantity_select = soup.find("select", id="quantity")
        product_title = soup.find("h1").text.strip() if soup.find("h1") else "Sazen Matcha Product"
        is_available = not unavailable_msg and quantity_select is not None
        stock_dict[product_title] = {
            "available": is_available,
            "url": url
        }

def get_stock_status():
    stock_dict = {}
    try:
        process_stock(IPPUDO_URL, stock_dict)
    except Exception as e:
        print("Error fetching Ippudo stock data:", e)
    try:
        process_stock(MATCHA_JP_URL, stock_dict)
    except Exception as e:
        print("Error fetching MatchaJP stock data:", e)
    try:
        process_sazen(stock_dict)
    except Exception as e:
        print("Error fetching Sazen stock data:", e)
    return stock_dict

def load_previous_status():
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_status(status):
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        print("Error saving status:", e)

def send_email_alert(product_title, product_url):
    msg = MIMEMultipart("alternative")
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = f"🍵 Restock Alert 🍵: {product_title} is Available!"

    text_part = f"{product_title} is BACK IN STOCK!\nBuy here: {product_url}"
    html_part = f"""
    <html>
      <head>
        <style>
          a.matcha-link {{
            color: #b1d8b7;
            text-decoration: none;
            font-size: 20px;
          }}
          a.matcha-link:hover {{
            color: #06402B;
          }}
        </style>
      </head>
      <body style="font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #f6f4f2; padding: 20px; margin: 0;">
        <div style="max-width: 600px; margin: auto; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px;">
          <p style="font-size: 16px; color: #333333; margin-bottom: 10px;">
            The following matcha product is now available:
          </p>
          <p style="font-weight: bold; font-size: 18px; color: #b1d8b7; margin-bottom: 10px;">
            {product_title}
          </p>
          <p style="font-size: 16px; color: #333333; margin-bottom: 10px;">
            Click the link below to view or purchase it:
          </p>
          <p style="margin-bottom: 20px;">
            <a href="{product_url}" class="matcha-link">{product_url}</a>
          </p>
          <p style="font-size: 12px; color: #777777; text-align: center;">
            This is an automated notification from your matcha restock tracker.
          </p>
        </div>
      </body>
    </html>
    """
    msg.attach(MIMEText(text_part, "plain"))
    msg.attach(MIMEText(html_part, "html"))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())
        print(f"📧 Email sent for: {product_title}")
    except Exception as e:
        print("Failed to send email:", e)

def send_sms_alert(product_title, product_url):
    msg = MIMEText(f"{product_title} is BACK IN STOCK!\n\nBuy here: {product_url}")
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT_SMS
    msg["Subject"] = "🍵 Restock Alert 🍵\n\n"
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, RECIPIENT_SMS, msg.as_string())
        print(f"📱 SMS sent for: {product_title}")
    except Exception as e:
        print("Failed to send SMS:", e)

if __name__ == "__main__":
    try:
        current_status = get_stock_status()
        prev_status = load_previous_status()
        print(current_status == prev_status)
        for title, info in current_status.items():
            current_avail = info["available"]
            prev_avail = prev_status.get(title, {}).get("available", False)
            if not prev_avail and current_avail:
                send_email_alert(title, info["url"])
                send_sms_alert(title, info["url"])
            else:
                print(f"{title} - In stock: {current_avail}")
        save_status(current_status)
    except Exception as e:
        print("Error in main loop:", e)
