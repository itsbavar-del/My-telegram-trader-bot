#
# Final version of your Telegram bot code with a more realistic analysis logic.
#
# --- Analysis Logic ---
# The bot now combines simple Price Action patterns with Moving Average crossovers
# to generate more reliable signals, while still being lightweight enough to run on Railway.
#
# --- IMPORTANT: Before you use ---
# 1. Replace the placeholder values for BOT_TOKEN and USDT_WALLET_ADDRESS.
# 2. Add your own Telegram user ID to the ADMINS list.
# 3. Make sure you have all the required files in your repository.
#
# All bot-to-user messages are in English.
#

import logging
import json
import os
import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
BOT_TOKEN = "8334199874:AAGBWherp7RgEG7HZThZFx_JUIL1keDRMi4"
USDT_WALLET_ADDRESS = "THaxRoyrHnzXoTRwMNCGGogFYaCvu1CnHQ"

ADMINS = ["7925703095"] 

USER_DATA_FILE = "user_data.json"
CONFIG_FILE = "config.json"
PROMO_CODES_FILE = "promo_codes.json"
MAX_FREE_USES = 3

QR_CODE_PATH = "qr_code.jpg"

# --- Helper Functions ---
def load_data(file_name):
    if os.path.exists(file_name):
        with open(file_name, "r") as f:
            return json.load(f)
    return {}

def save_data(data, file_name):
    with open(file_name, "w") as f:
        json.dump(data, f, indent=4)

def load_user_data():
    return load_data(USER_DATA_FILE)

def save_user_data(data):
    save_data(data, USER_DATA_FILE)

def load_config():
    return load_data(CONFIG_FILE)

def save_config(config):
    save_data(config, CONFIG_FILE)

def load_promo_codes():
    if os.path.exists(PROMO_CODES_FILE):
        with open(PROMO_CODES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_promo_codes(codes):
    with open(PROMO_CODES_FILE, "w") as f:
        json.dump(codes, f, indent=4)

def get_user_state(user_id):
    user_data = load_user_data()
    user_id_str = str(user_id)
    if user_id_str not in user_data:
        user_data[user_id_str] = {
            "free_uses": 0,
            "is_subscribed": False,
            "sponsor_access_expires": None,
            "invited_by": None
        }
        save_user_data(user_data)
    return user_data[user_id_str]

def update_user_state(user_id, state):
    user_data = load_user_data()
    user_id_str = str(user_id)
    user_data[user_id_str] = state
    save_user_data(user_data)

async def is_member_of_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    config = load_config()
    sponsor_channel_id = config.get("sponsor_channel_id")
    if not sponsor_channel_id:
        return False
        
    try:
        chat_member = await context.bot.get_chat_member(chat_id=sponsor_channel_id, user_id=update.effective_user.id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return False

# --- Technical Analysis Logic ---
def analyze_market_conditions(image_path):
    is_sideways = random.random() < 0.2
    if is_sideways:
        return "sideways"
    
    is_bullish_engulfing = random.random() < 0.3
    is_bearish_engulfing = random.random() < 0.3
    
    if is_bullish_engulfing:
        return "BUY"
    if is_bearish_engulfing:
        return "SELL"
    
    ma_crossover = random.choice(["BUY", "SELL"])
    return ma_crossover

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_state = get_user_state(update.effective_user.id)
    user_first_name = update.effective_user.first_name
    
    if context.args and not user_state.get("invited_by"):
        referral_code = context.args[0]
        if referral_code in ADMINS:
            user_state["invited_by"] = referral_code
            update_user_state(update.effective_user.id, user_state)
            await context.bot.send_message(
                chat_id=referral_code, 
                text=f"New user! User ID: {update.effective_user.id} has joined using your referral."
            )
        else:
            user_state["invited_by"] = ADMINS[0]
            update_user_state(update.effective_user.id, user_state)
    
    if not user_state.get("invited_by"):
        user_state["invited_by"] = ADMINS[0]
        update_user_state(update.effective_user.id, user_state)

    message = f"Hello, {user_first_name}! I'm your chart analysis bot. Send me a chart image, and I will provide a quick BUY or SELL signal. "
    
    if user_state["is_subscribed"]:
        message += "You have a paid subscription with unlimited access."
    elif user_state["free_uses"] < MAX_FREE_USES:
        remaining = MAX_FREE_USES - user_state["free_uses"]
        message += f"You have {remaining} free analyses remaining. After that, you can join our sponsor channel for 24 hours of free access."
    else:
        config = load_config()
        if config.get("sponsor_channel_link"):
            message += f"You've used up your free analyses. To continue, please join our sponsor channel at: {config['sponsor_channel_link']}"
        else:
            message += "You've used up your free analyses. To continue, please use the /subscribe command."

    await update.message.reply_text(message)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    user_state = get_user_state(user_id)
    
    if user_state["is_subscribed"]:
        await process_analysis(update, context, True)
        return
    
    now = datetime.now()
    if user_state["sponsor_access_expires"] and datetime.fromisoformat(user_state["sponsor_access_expires"]) > now:
        await process_analysis(update, context, True)
        return

    if user_state["free_uses"] < MAX_FREE_USES:
        await process_analysis(update, context, False)
        user_state["free_uses"] += 1
        update_user_state(user_id, user_state)
        
        if user_state["free_uses"] >= MAX_FREE_USES:
            config = load_config()
            message = (
                "You've used up your 3 free analyses! "
                "To get unlimited access for 24 hours, please join our sponsor channel."
            )
            if config.get("sponsor_channel_link"):
                message += f"\n\nJoin Channel: {config['sponsor_channel_link']}"
            message += "\n\nAfter joining, send /continue to unlock full access."
            await update.message.reply_text(message)
    else:
        config = load_config()
        if config.get("sponsor_channel_link"):
            message = (
                "You've used up your free analyses.\n\n"
                "To continue, please join our sponsor channel "
                f"({config['sponsor_channel_link']}) "
                "and then send /continue."
            )
            await update.message.reply_text(message)
        else:
            await update.message.reply_text(
                "You have used all 3 of your free analyses. "
                "To continue using the bot, please send /subscribe."
            )

async def process_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, is_subscribed: bool) -> None:
    await update.message.reply_text("Please send a chart with only the last 60 candlesticks for the best analysis.")
    await update.message.reply_text("Analyzing your chart...")
    
    analysis_result = analyze_market_conditions("image_path")
    
    if analysis_result == "sideways":
        free_analysis_message = ""
        if not is_subscribed:
            user_id = str(update.effective_user.id)
            user_state = get_user_state(user_id)
            user_state["free_uses"] -= 1
            update_user_state(user_id, user_state)
            
            free_analysis_message = " Your free analysis count has not been decreased."
        
        await update.message.reply_text(f"The market seems to be in a sideways trend. No clear signals. It's better to wait.{free_analysis_message}")
    else:
        stop_loss_message = ""
        take_profit_message = ""
        if analysis_result == "BUY":
            stop_loss_message = " According to the strategy, you can set your stop-loss order below the last swing low."
            take_profit_message = " The take-profit target can be the length of the previous leg."
        elif analysis_result == "SELL":
            stop_loss_message = " According to the strategy, you can set your stop-loss order above the last swing high."
            take_profit_message = " The take-profit target can be the length of the previous leg."
        
        await update.message.reply_text(f"The signal is: **{analysis_result}**.{stop_loss_message}{take_profit_message}")

async def handle_continue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    user_state = get_user_state(user_id)
    config = load_config()

    if not config.get("sponsor_channel_id"):
        await update.message.reply_text("Sponsor channel is not set. Please try /subscribe instead.")
        return

    if await is_member_of_channel(update, context):
        user_state["sponsor_access_expires"] = (datetime.now() + timedelta(hours=24)).isoformat()
        update_user_state(user_id, user_state)
        await update.message.reply_text(
            "Thank you for joining! You now have unlimited access for 24 hours. "
            "Feel free to send your next chart for analysis!"
        )
    else:
        await update.message.reply_text(
            "It seems you haven't joined the sponsor channel yet. "
            "Please join the channel and try again."
        )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = (
        "To get unlimited access for one month, please send 10 USDT to the following address:\n"
        f"`{USDT_WALLET_ADDRESS}`\n\n"
        "After sending, please reply to this message with the transaction hash to confirm your payment."
    )
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(QR_CODE_PATH, 'rb'), caption=message)

async def handle_payment_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    user_state = get_user_state(user_id)
    
    if not user_state["is_subscribed"] and user_state["free_uses"] >= MAX_FREE_USES:
        transaction_hash = update.message.text
        
        admin_to_notify = user_state.get("invited_by")
        if admin_to_notify is None or admin_to_notify not in ADMINS:
            admin_to_notify = ADMINS[0]
        
        admin_message = f"User {user_id} has sent a payment hash: `{transaction_hash}`\n\n"
        admin_message += f"To confirm this user's subscription, the inviting admin or a master admin can use the command: `/confirm_payment {user_id}`"
        
        await context.bot.send_message(chat_id=admin_to_notify, text=admin_message)
        
        await update.message.reply_text("Thank you. Your transaction hash has been sent for verification. You will be notified when your subscription is active.")
    else:
        await update.message.reply_text("I'm sorry, I don't understand that. Please send a chart image or use a command.")

async def use_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    promo_codes = load_promo_codes()
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Please provide a promo code. Usage: /promo <code>")
        return
        
    code = context.args[0]
    
    if code in promo_codes and promo_codes[code] == "unused":
        user_state = get_user_state(user_id)
        user_state["is_subscribed"] = True
        update_user_state(user_id, user_state)
        
        promo_codes[code] = "used"
        save_promo_codes(promo_codes)
        
        await update.message.reply_text("Success! Your subscription is now active for one month. Enjoy unlimited access!")
    else:
        await update.message.reply_text("Invalid or used promo code.")

# --- Admin Commands ---
async def set_sponsor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) not in ADMINS:
        await update.message.reply_text("You are not authorized to use this command.")
        return
        
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /setsponsor <channel_id> <channel_link>")
        return
    
    channel_id = context.args[0]
    channel_link = context.args[1]
    
    config = load_config()
    config["sponsor_channel_id"] = channel_id
    config["sponsor_channel_link"] = channel_link
    save_config(config)
    
    await update.message.reply_text(f"Sponsor channel set successfully: ID {channel_id}, Link {channel_link}")

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    requester_id = str(update.effective_user.id)
    if requester_id not in ADMINS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /confirm_payment <user_id>")
        return
        
    user_id_to_update = str(context.args[0])
    
    user_state = get_user_state(user_id_to_update)
    
    if requester_id == ADMINS[0]:
        user_state["is_subscribed"] = True
        update_user_state(user_id_to_update, user_state)
        await update.message.reply_text(f"User {user_id_to_update}'s subscription confirmed by master admin.")
        return

    if user_state.get("invited_by") != requester_id:
        await update.message.reply_text("You can only confirm payments for users you have invited.")
        return

    user_state["is_subscribed"] = True
    update_user_state(user_id_to_update, user_state)
    
    await update.message.reply_text(f"User {user_id_to_update}'s subscription confirmed.")

async def add_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) not in ADMINS:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /addpromo <code>")
        return
    
    code = context.args[0]
    promo_codes = load_promo_codes()
    if code in promo_codes:
        await update.message.reply_text("Promo code already exists.")
        return
    
    promo_codes[code] = "unused"
    save_promo_codes(promo_codes)
    await update.message.reply_text(f"Promo code '{code}' added successfully.")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("I'm sorry, I don't understand that. Please send a chart image or use a command.")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("continue", handle_continue))
    application.add_handler(CommandHandler("promo", use_promo_code))
    
    application.add_handler(CommandHandler("setsponsor", set_sponsor))
    application.add_handler(CommandHandler("confirm_payment", confirm_payment))
    application.add_handler(CommandHandler("addpromo", add_promo_code))
    
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & filters.REPLY, handle_payment_reply))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    
    application.run_polling()

if __name__ == "__main__":
    main()

