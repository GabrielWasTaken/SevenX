import sqlite3
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Load config
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Database setup
conn = sqlite3.connect('7x_currency.db')
c = conn.cursor()

# Create tables
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        balance INTEGER DEFAULT 0
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        amount INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS pending_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        amount INTEGER
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS user_chat_ids (
        username TEXT PRIMARY KEY,
        chat_id INTEGER
    )
''')
conn.commit()

# Helper functions
def get_balance(username):
    c.execute('SELECT balance FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    return result[0] if result else 0

def update_balance(username, amount):
    if get_balance(username) == 0:
        c.execute('INSERT INTO users (username, balance) VALUES (?, ?)', (username, amount))
    else:
        c.execute('UPDATE users SET balance = balance + ? WHERE username = ?', (amount, username))
    conn.commit()

def record_transaction(sender, receiver, amount):
    c.execute('INSERT INTO transactions (sender, receiver, amount) VALUES (?, ?, ?)', (sender, receiver, amount))
    conn.commit()

def store_pending_transaction(sender, receiver, amount):
    c.execute('INSERT INTO pending_transactions (sender, receiver, amount) VALUES (?, ?, ?)', (sender, receiver, amount))
    conn.commit()
    return c.lastrowid

def get_pending_transaction(trans_id):
    c.execute('SELECT sender, receiver, amount FROM pending_transactions WHERE id = ?', (trans_id,))
    return c.fetchone()

def delete_pending_transaction(trans_id):
    c.execute('DELETE FROM pending_transactions WHERE id = ?', (trans_id,))
    conn.commit()

def store_user_chat_id(username, chat_id):
    c.execute('REPLACE INTO user_chat_ids (username, chat_id) VALUES (?, ?)', (username, chat_id))
    conn.commit()

def get_user_chat_id(username):
    c.execute('SELECT chat_id FROM user_chat_ids WHERE username = ?', (username,))
    result = c.fetchone()
    return result[0] if result else None

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    store_user_chat_id(username, chat_id)
    await update.message.reply_text('Welcome to the SevenX Currency Bot!')

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    store_user_chat_id(username, chat_id)

    if len(context.args) != 2:
        await update.message.reply_text('Usage: /pay <username> <amount>')
        return

    sender = update.message.from_user.username
    receiver, amount = context.args
    receiver = receiver.lstrip('@')  # Eliminar el "@" si está presente
    amount = int(amount)

    if get_balance(sender) < amount:
        await update.message.reply_text('Insufficient balance!')
        return

    trans_id = store_pending_transaction(sender, receiver, amount)
    keyboard = [
        [
            InlineKeyboardButton("Confirm", callback_data=f'confirm_{trans_id}'),
            InlineKeyboardButton("Cancel", callback_data=f'cancel_{trans_id}')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f'Confirm payment of {amount} SevenX to {receiver}?',
                                    reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    callback_data = query.data.split('_')
    action = callback_data[0]
    trans_id = int(callback_data[1])

    if action == 'confirm':
        sender, receiver, amount = get_pending_transaction(trans_id)
        print(f"Transaction confirmed: {sender} pays {receiver} {amount} SevenX")  # Debugging line
        update_balance(sender, -amount)
        print(f"Balance updated for sender {sender}")  # Debugging line
        update_balance(receiver, amount)
        print(f"Balance updated for receiver {receiver}")  # Debugging line
        record_transaction(sender, receiver, amount)
        delete_pending_transaction(trans_id)

        await context.bot.send_message(chat_id=query.message.chat_id,
                                       text=f'Payment of {amount} SevenX to {receiver} confirmed!\nTransaction details:\nSender: {sender}\nReceiver: {receiver}\nAmount: {amount} SevenX',
                                       parse_mode=ParseMode.MARKDOWN)

        # Send a message to the receiver
        receiver_chat_id = get_user_chat_id(receiver)
        if receiver_chat_id:
            await context.bot.send_message(chat_id=receiver_chat_id,
                                           text=f'You have received a payment of {amount} SevenX from {sender}.\nTransaction details:\nSender: {sender}\nAmount: {amount} SevenX')

    elif action == 'cancel':
        delete_pending_transaction(trans_id)
        await context.bot.send_message(chat_id=query.message.chat_id, text='Payment canceled!')

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    store_user_chat_id(username, chat_id)

    balance = get_balance(username)
    await update.message.reply_text(f'Your balance is {balance} SevenX.')

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    store_user_chat_id(username, chat_id)

    if get_balance(username) == 0:
        update_balance(username, 50)
        await update.message.reply_text('Claimed 50 SevenX!')
    else:
        await update.message.reply_text('You have already claimed your 50 SevenX!')

async def request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    store_user_chat_id(username, chat_id)

    if len(context.args) != 2:
        await update.message.reply_text('Usage: /request <username> <amount>')
        return

    requester = update.message.from_user.username
    target, amount = context.args
    amount = int(amount)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f'This command is not longer working and will be removed in future versions of the bot')

async def refresh_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    store_user_chat_id(username, chat_id)

    await update.message.reply_text('Balance refreshed!')

async def mint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username

    # Check if the user is authorized
    if username != config["AUTHORIZED_USER"]:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /mint <amount>")
        return

    amount = int(context.args[0])
    update_balance(username, amount)
    await update.message.reply_text(f'Minted {amount} SevenX!')

async def burn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username

    # Check if the user is authorized
    if username != config["AUTHORIZED_USER"]:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /burn <amount>")
        return

    amount = int(context.args[0])

    if get_balance(username) < amount:
        await update.message.reply_text("Insufficient balance to burn!")
        return

    update_balance(username, -amount)
    await update.message.reply_text(f'Burned {amount} SevenX!')

# Main function
def main():
    # Use config file for the bot token
    TOKEN = config["TELEGRAM_BOT_TOKEN"]
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pay", pay))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("claim", claim))
    application.add_handler(CommandHandler("request", request))
    application.add_handler(CommandHandler("refresh", refresh_balance))
    application.add_handler(CommandHandler("mint", mint))
    application.add_handler(CommandHandler("burn", burn))
    application.add_handler(CallbackQueryHandler(handle_callback))

    application.run_polling()

if __name__ == '__main__':
    main()
