from urllib.parse import urlparse
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

def help_command(update: Update, context: CallbackContext) -> None:
    """Displays a help message with available commands."""
    user_id = str(update.message.chat_id)

    # Basic user commands
    help_text = (
        "🤖 **Mailtractor Bot Help**\n\n"
        "📌 **User Commands:**\n"
        "`/start` - Start the bot\n"
        "`/id` - Get your Telegram ID\n"
        "`/help` - Show this help message\n"
        "To extract emails, send a website URL.\n\n"
    )

    # Show admin commands only if the user is the admin
    if user_id == ADMIN_ID:
        help_text += (
            "🛠 **Admin Commands:**\n"
            "`/approve <user_id>` - Approve a user\n"
            "`/revoke <user_id>` - Revoke a user's access\n"
            "`/users` - View all approved users\n"
        )

    update.message.reply_text(help_text, parse_mode="Markdown")

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
        "👋 Welcome to Enthernet Crawler – Your Ethical Webmail Extractor!\n\n"
        "📌 **How to Use:**\n"
        "1️⃣ Send a website URL\n"
        "2️⃣ Choose: Let me *Atomate loggn  OR  provide session cookies\n"
        "3️⃣ Bot extracts emails ethically\n\n"
        "🔹 **Admin Approval Needed**\n"
        "Send your user ID to the admin for access.\n\n"
        f"🛠 **Admin EMAIL:** {ADMIN_EMAIL}"
    )

# Function to extract cookies via Selenium
import subprocess

def get_cookies_via_selenium(url, update):
    """ Opens a browser for manual login on a remote server and tunnels it using localhost.run """
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()

    # Enable remote debugging for tunneling
    options.add_argument("--remote-debugging-port=9222")  
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=service, options=options)

    stealth(driver, ["en-US", "en"], "Google Inc.", "Win32", "Intel Inc.", "Intel Iris OpenGL Engine", True)

    try:
        driver.get(url)
        update.message.reply_text("🔹 **Browser Opened on Server! Setting up a secure login link...**")

        # Start localhost.run tunnel
        tunnel_cmd = "ssh -R 80:localhost:9222 nokey@localhost.run"
        tunnel_process = subprocess.Popen(tunnel_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Wait for tunnel to initialize and extract the URL
        tunnel_url = None
        for _ in range(10):  # Wait for localhost.run to set up
            output = tunnel_process.stdout.readline().decode().strip()
            if "https://" in output:
                tunnel_url = output
                break
            time.sleep(1)

        if not tunnel_url:
            update.message.reply_text("❌ **Tunnel failed to initialize. Try again later.**")
            return {}

        # Send the tunnel URL to the Telegram user
        update.message.reply_text(
            f"🔹 **Manual Login Required**\n"
            f"🔗 Click here to log in: [Login Here]({tunnel_url})\n"
            f"⚠️ **DO NOT close the browser until you see a confirmation!**",
            parse_mode="Markdown"
        )

        time.sleep(30)  # Wait for user to log in

        cookies = {cookie["name"]: cookie["value"] for cookie in driver.get_cookies()}
        driver.quit()

        if cookies:
            update.message.reply_text("✅ **Session cookies captured successfully! Extracting emails now...**")
            return cookies
        else:
            update.message.reply_text("⚠️ **No cookies found. Make sure you logged in properly.**")
            return {}

    except Exception as e:
        driver.quit()
        update.message.reply_text(f"❌ **Error: {e}**")
        return {}

'''def get_cookies_via_selenium(url):
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
        return f"Error: {e}" '''

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
        "👉 Reply with:\n"
        "`auto` → Bot will log in & get cookies\n"
        "`manual` → You will provide session cookies"
    )

    context.user_data["url"] = url
'''
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
        "🔹 Do you want me to automate login and fetch cookies OR will you provide cookies?\n\n"
        "👉 Reply with:\n"
        "`auto` → Bot will log in & get cookies\n"
        "`manual` → You will provide session cookies"
    )

    context.user_data["url"] = url
'''

def is_valid_url(url):
    """Check if a URL is valid using urllib.parse"""
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme and parsed_url.netloc)
'''
def handle_url(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.chat_id)

    if user_id not in APPROVED_USERS:
        update.message.reply_text(
            "❌ You are not approved to use this bot.\n"
            "🔹 Contact the admin to request access."
        )
        return

    url = update.message.text.strip()

    # Validate URL using urllib.parse
    if not is_valid_url(url):
        update.message.reply_text("❌ Invalid URL! Please send a valid link (e.g., `https://example.com`).")
        return

    update.message.reply_text(
        "🔹 Do you want me to **automate login** and fetch cookies OR will you provide cookies?\n\n"
        "👉 **Reply with:**\n"
        "`auto` → Bot will log in & get cookies\n"
        "`manual` → You will provide session cookies"
    )

    context.user_data["url"] = url
'''
'''def handle_url(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.chat_id)

    if user_id not in APPROVED_USERS:
        update.message.reply_text("❌ You are not approved to use this bot.\n🔹 Contact the admin to request access.")
        return

    url = update.message.text.strip()
    logging.info(f"Received URL: {url}")  # Log received URL

    if not is_valid_url(url):
        update.message.reply_text(f"❌ Invalid URL! Received: `{url}`")  # Show what the bot received
        return

    update.message.reply_text(
        "🔹 Do you want me to **automate login** and fetch cookies OR will you provide cookies?\n\n"
        "👉 **Reply with:**\n"
        "`auto` → Bot will log in & get cookies\n"
        "`manual` → You will provide session cookies"
    )
    context.user_data["url"] = url'''

def handle_url(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.chat_id)

    if user_id not in APPROVED_USERS:
        update.message.reply_text("❌ You are not approved to use this bot.\n🔹 Contact the admin to request access.")
        return

    url = update.message.text.strip()
    logging.info(f"Received URL: {url}")  # Debugging: Log received URL

    if not is_valid_url(url):  
        update.message.reply_text(f"❌ Invalid URL! Received: `{url}`")
        return

    update.message.reply_text("🔍 Fetching session cookies... Please wait.")

    # Fetch cookies automatically
    cookies = get_cookies_via_selenium(url, update)  

    # Start email extraction with fetched cookies$
    threading.Thread(target=extract_emails_threaded, args=(update, context, url, cookies)).start()

def view_approved_users(update: Update, context: CallbackContext) -> None:
    """Admin command to view all approved users."""
    if str(update.message.chat_id) != ADMIN_ID:
        update.message.reply_text("❌ Only the admin can view approved users.")
        return

    if not APPROVED_USERS:
        update.message.reply_text("⚠️ No approved users yet.")
        return

    user_list = "\n".join(APPROVED_USERS.keys())
    update.message.reply_text(f"✅ Approved Users:\n\n{user_list}")

def get_user_id(update: Update, context: CallbackContext) -> None:
    """Sends the user's Telegram ID."""
    update.message.reply_text(f"Your Telegram ID: `{update.message.chat_id}`")

'''
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
'''
'''
def handle_cookies(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.chat_id)

    # Ensure a URL was provided first
    if user_id not in APPROVED_USERS or "url" not in context.user_data:
        update.message.reply_text("❌ Invalid request. Please send a valid URL first.")
        return

    choice = update.message.text.strip().lower()

    if choice not in ["auto", "manual"]:
        update.message.reply_text("❌ Invalid choice! Reply with either `auto` or `manual`.")
        return  # Stop execution if an invalid response is given

    if choice == "auto":
        update.message.reply_text("🔍 Fetching session cookies...")
        cookies = get_cookies_via_selenium(context.user_data["url"])  
    else:
        update.message.reply_text("📌 Send your session cookies as a text message.")
        return  # Wait for user input instead of proceeding

    # Store cookies and start email extraction
    context.user_data["cookies"] = cookies
    threading.Thread(target=extract_emails_threaded, args=(update, context, context.user_data["url"], cookies)).start()
'''

def handle_cookies(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.chat_id)

    if user_id not in APPROVED_USERS or "url" not in context.user_data:
        update.message.reply_text("❌ **Invalid request. Send a URL first.**")
        return

    choice = update.message.text.strip().lower()

    if choice == "auto":
        update.message.reply_text("🔍 **Setting up remote login... Please wait!**")

        cookies = get_cookies_via_selenium(context.user_data["url"], update)

        if cookies:
            context.user_data["cookies"] = cookies
            threading.Thread(target=extract_emails_threaded, args=(update, context, context.user_data["url"], cookies)).start()
        else:
            update.message.reply_text("⚠️ **Failed to capture session cookies. Try again.**")

    else:
        update.message.reply_text("📌 **Send your session cookies as a text message.**")

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
    dp.add_handler(CommandHandler("help", help_command))


    # Safe polling with automatic restart on failure
    while True:
        try:
            updater.start_polling()  
            updater.idle()  
        except Exception as e:
            print(f"⚠️ Bot crashed: {e}")
            print("🔄 Restarting bot...")
            time.sleep(5)  # Wait before restarting

if __name__ == "__main__":
    main()

'''    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
'''


