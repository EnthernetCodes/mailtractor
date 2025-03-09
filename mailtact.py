import os
import json
import csv
import asyncio
import datetime
import pandas as pd
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.constants import ParseMode
from alibaba_scraper import scrape_alibaba  # Import your Alibaba scraper
from europages_scraper import scrape_europages  # Import your Europages scraper

TOKEN = "7976232009:AAH0rtAnqvveLPbu06UdXz65pvivh3L4o4U"
ADMIN_ID = 5166125467
USERS_FILE = "approved_users.json"
QUEUE_FILE = "scraping_queue.json"

# Load or initialize approved users
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

# Save users to JSON
def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# Check and remove expired users
def remove_expired_users():
    users = load_users()
    today = datetime.datetime.now().date()
    for user_id, data in list(users.items()):
        expiry_date = datetime.datetime.strptime(data["expiry"], "%Y-%m-%d").date()
        if expiry_date < today:
            del users[user_id]  # Remove expired user
    save_users(users)

# Approve users with a subscription period
async def approve(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /approve <user_id> <days>")
        return

    user_id, days = args[0], int(args[1])
    expiry_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    users = load_users()
    users[user_id] = {"expiry": expiry_date}
    save_users(users)

    await context.bot.send_message(chat_id=user_id, text=f"You have been approved for {days} days! 🎉")
    await update.message.reply_text(f"User {user_id} approved until {expiry_date}.")

# Request access command
async def request_access(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "Unknown"
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📢 *Access Request!*\nUser: @{username}\nUser ID: {user_id}\nApprove with: `/approve {user_id} 30`",
        parse_mode=ParseMode.MARKDOWN,
    )
    await update.message.reply_text("Your request has been sent to the admin. Please wait for approval.")

# Notify all users
async def notify_all(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    message = " ".join(context.args)
    users = load_users()
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except:
            pass  # Ignore errors if user can't be reached
    await update.message.reply_text("Message sent to all users.")

# Notify a specific user
async def notify(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /notify <user_id> <message>")
        return

    user_id, message = args[0], " ".join(args[1:])
    await context.bot.send_message(chat_id=user_id, text=message)
    await update.message.reply_text(f"Message sent to user {user_id}.")

# Queue system for scraping
def load_queue():
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r") as f:
            return json.load(f)
    return []

def save_queue(queue):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f)

async def process_queue(context: CallbackContext):
    queue = load_queue()
    if not queue:
        return  # No jobs in queue

    user_id, platform, niche = queue.pop(0)
    save_queue(queue)

    await context.bot.send_message(chat_id=user_id, text=f"🚀 Your scraping job for *{platform} - {niche}* is now running!", parse_mode=ParseMode.MARKDOWN)

    file_path = await scrape_alibaba(niche) if platform == "alibaba" else await scrape_europages(niche)

    if file_path:
        await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"))
        os.remove(file_path)  # Delete file after sending
    else:
        await context.bot.send_message(chat_id=user_id, text="❌ No results found.")

async def scrape(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    users = load_users()
    
    if user_id not in users:
        await update.message.reply_text("You are not authorized. Please request access using /request_access.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /scrape <alibaba/europages> <niche>")
        return

    platform, niche = args[0].lower(), args[1]
    if platform not in ["alibaba", "europages"]:
        await update.message.reply_text("Invalid platform. Use /scrape alibaba <niche> or /scrape europages <niche>.")
        return

    queue = load_queue()
    queue.append((user_id, platform, niche))
    save_queue(queue)

    position = len(queue)
    if position == 1:
        await process_queue(context)
    else:
        await update.message.reply_text(f"🚦 You are # {position} in the queue. Please wait...")

# Bot setup
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("request_access", request_access))
    app.add_handler(CommandHandler("notify_all", notify_all))
    app.add_handler(CommandHandler("notify", notify))
    app.add_handler(CommandHandler("scrape", scrape))

    app.run_polling()

if __name__ == "__main__":
    main()
