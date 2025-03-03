import validators  # <-- Add this at the top of your file
import logging
import re
import time
import requests
import threading
import json
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Bot Settings
TELEGRAM_BOT_TOKEN = "7976232009:AAH0rtAnqvveLPbu06UdXz65pvivh3L4o4U"
ADMIN_ID = "5166125467"  # Replace with your Telegram ID
ADMIN_EMAIL = "info@enthernetservices.com"
APPROVED_USERS_FILE = "approved_users.json"

# Load approved users
try:
    with open(APPROVED_USERS_FILE, "r") as f:
        APPROVED_USERS = json.load(f)
except FileNotFoundError:
    APPROVED_USERS = {}

# Email Regex Pattern
email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

# Function to save approved users
def save_users():
    with open(APPROVED_USERS_FILE, "w") as f:
        json.dump(APPROVED_USERS, f)

# Function to approve users
def approve_user(update: Update, context: CallbackContext) -> None:
    if str(update.message.chat_id) != ADMIN_ID:
        update.message.reply_text("❌ Only the admin can approve users.")
        return
    
    args = context.args
    if len(args) != 1:
        update.message.reply_text("Usage: /approve <user_id>")
        return

    user_id = args[0]
    APPROVED_USERS[user_id] = True
    save_users()
    update.message.reply_text(f"✅ User {user_id} approved.")

# Function to revoke users
def revoke_user(update: Update, context: CallbackContext) -> None:
    if str(update.message.chat_id) != ADMIN_ID:
        update.message.reply_text("❌ Only the admin can revoke users.")
        return
    
    args = context.args
    if len(args) != 1:
        update.message.reply_text("Usage: /revoke <user_id>")
        return

    user_id = args[0]
    if user_id in APPROVED_USERS:
        del APPROVED_USERS[user_id]
        save_users()
        update.message.reply_text(f"❌ User {user_id} access revoked.")
    else:
        update.message.reply_text("⚠️ User not found.")

# Start Command
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "👋 Welcome to **Ethernet Crawler** – Your Ethical Webmail Extractor!\n\n"
        "📌 **How to Use:**\n"
        "1️⃣ Send a website URL\n"
        "2️⃣ Choose: Let me **automate login** OR **provide session cookies**\n"
        "3️⃣ Bot extracts emails ethically\n\n"
        "🔹 **Admin Approval Needed**\n"
        "Send your user ID to the admin for access.\n\n"
        f"🛠 **Admin EMAIL:** {ADMIN_EMAIL}"
    )

# Function to extract cookies via Selenium
def get_cookies_via_selenium(url):
    """ Automates login and retrieves session cookies. """
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=service, options=options)

    stealth(driver, ["en-US", "en"], "Google Inc.", "Win32", "Intel Inc.", "Intel Iris OpenGL Engine", True)

    try:
        driver.get(url)
        time.sleep(10)  # Allow user to log in manually
        cookies = {cookie["name"]: cookie["value"] for cookie in driver.get_cookies()}
        driver.quit()
        return cookies
    except Exception as e:
        driver.quit()
        return f"Error: {e}"

# Function to extract emails using Selenium with cookies
def extract_emails_selenium(url, cookies):
    """ Extracts emails from sites that require login using session cookies. """
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=service, options=options)

    stealth(driver, ["en-US", "en"], "Google Inc.", "Win32", "Intel Inc.", "Intel Iris OpenGL Engine", True)

    try:
        driver.get(url)
        for key, value in cookies.items():
            driver.add_cookie({"name": key, "value": value})
        driver.refresh()
        time.sleep(5)
        emails = re.findall(email_pattern, driver.page_source)
        driver.quit()
        return list(set(emails))
    except Exception as e:
        driver.quit()
        return [f"Error: {e}"]

# Multi-threaded email extraction
def extract_emails_threaded(update: Update, context: CallbackContext, url, cookies):
    update.message.reply_text("🔍 Crawling... Please wait.")

    emails = extract_emails_selenium(url, cookies)

    if emails:
        update.message.reply_text(f"📩 Extracted Emails:\n\n" + "\n".join(emails))
    else:
        update.message.reply_text("⚠️ No emails found or extraction failed.")

# Handle URL input
'''def handle_url(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.chat_id)
    
    if user_id not in APPROVED_USERS:
        update.message.reply_text(
            "❌ You are not approved to use this bot.\n"
            "🔹 Contact the admin to request access."
        )
        return

    url = update.message.text.strip()

    if not url.startswith(("http://", "https://")):
        update.message.reply_text("❌ Invalid URL! Please send a valid link.")
        return

    update.message.reply_text(
        "🔹 Do you want me to **automate login** and fetch cookies OR will you provide cookies?\n\n"
        "👉 **Reply with:**\n"
        "`auto` → Bot will log in & get cookies\n"
        "`manual` → You will provide session cookies"
    )

    context.user_data["url"] = url
'''

def handle_url(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.chat_id)

    if user_id not in APPROVED_USERS:
        update.message.reply_text(
            "❌ You are not approved to use this bot.\n"
            "🔹 Contact the admin to request access." f"ADMIN EMAIL: {ADMIN_EMAIL}"
        )
        return

    url = update.message.text.strip()

    # Improved URL validation
    if not validators.url(url):
        update.message.reply_text("❌ Invalid URL! Please send a valid link (e.g., `https://example.com`).")
        return

    update.message.reply_text(
        "🔹 Do you want me to **automate login** and fetch cookies OR will you provide cookies?\n\n"
        "👉 **Reply with:**\n"
        "`auto` → Bot will log in & get cookies\n"
        "`manual` → You will provide session cookies"
    )

    context.user_data["url"] = url

def view_approved_users(update: Update, context: CallbackContext) -> None:
    """Admin command to view all approved users."""
    if str(update.message.chat_id) != ADMIN_ID:
        update.message.reply_text("❌ Only the admin can view approved users.")
        return

    if not APPROVED_USERS:
        update.message.reply_text("⚠️ No approved users yet.")
        return

    user_list = "\n".join(APPROVED_USERS.keys())
    update.message.reply_text(f"✅ **Approved Users:**\n\n{user_list}")

def get_user_id(update: Update, context: CallbackContext) -> None:
    """Sends the user's Telegram ID."""
    update.message.reply_text(f"Your Telegram ID: `{update.message.chat_id}`")


def handle_cookies(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.chat_id)

    if user_id not in APPROVED_USERS or "url" not in context.user_data:
        update.message.reply_text("❌ Invalid request. Send a URL first.")
        return

    choice = update.message.text.strip().lower()

    if choice == "auto":
        update.message.reply_text("🔍 Fetching session cookies...")
        cookies = get_cookies_via_selenium(context.user_data["url"])
    else:
        update.message.reply_text("📌 Send your session cookies as a text message.")

    context.user_data["cookies"] = cookies
    threading.Thread(target=extract_emails_threaded, args=(update, context, context.user_data["url"], cookies)).start()

# Main Function
def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("approve", approve_user, pass_args=True))
    dp.add_handler(CommandHandler("revoke", revoke_user, pass_args=True))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_url))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_cookies))
    dp.add_handler(CommandHandler("users", view_approved_users))
    dp.add_handler(CommandHandler("id", get_user_id))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
