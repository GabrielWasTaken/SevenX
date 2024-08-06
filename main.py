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

# Global variables
burned_amount = 0

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

def get_total_supply():
    c.execute('SELECT SUM(balance) FROM users')
    result = c.fetchone()
    return result[0] if result else 0

def get_top_users():
    c.execute('SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10')
    return c.fetchall()

def get_transactions(limit=10, offset=0):
    c.execute('SELECT sender, receiver, amount, timestamp FROM transactions ORDER BY timestamp DESC LIMIT ? OFFSET ?', (limit, offset))
    return c.fetchall()

def save_balances_to_file():
    with open('balances.txt', 'w') as f:
        total_supply = get_total_supply()
        f.write(f'Total supply: {total_supply}\n')
        f.write(f'Total burned: {burned_amount}\n\n')
        c.execute('SELECT username, balance FROM users')
        for username, balance in c.fetchall():
            f.write(f'{username}: {balance} SevenX\n')

def save_transactions_to_file():
    with open('transactions.txt', 'w') as f:
        c.execute('SELECT sender, receiver, amount, timestamp FROM transactions ORDER BY timestamp DESC')
        for sender, receiver, amount, timestamp in c.fetchall():
            f.write(f'{timestamp}: {sender} -> {receiver} | {amount} SevenX\n')

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
    amount = int(amount)

    if get_balance(sender) < amount:
        await update.message.reply_text('Insufficient balance!')
        return

    # Apply 2% fee: 1% burned, 1% to privileged user
    burn_fee = amount // 100
    privileged_fee = amount // 100
    net_amount = amount - burn_fee - privileged_fee

    # Update balances
    update_balance(sender, -amount)
    update_balance(receiver, net_amount)
    update_balance(config["AUTHORIZED_USER"], privileged_fee)

    # Record burned amount
    global burned_amount
    burned_amount += burn_fee

    # Save balances and transactions
    save_balances_to_file()
    save_transactions_to_file()

    record_transaction(sender, receiver, net_amount)
    await update.message.reply_text(f'Payment of {net_amount} SevenX to {receiver} successful! Fee: {burn_fee} burned, {privileged_fee} to {config["AUTHORIZED_USER"]}.')

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
        update_balance(username, 5)
        save_balances_to_file()
        await update.message.reply_text('Claimed 5 SevenX!')
    else:
        await update.message.reply_text('You have already claimed your 5 SevenX!')

async def request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("This command is not available.")

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
    trans_id = store_pending_transaction(username, username, amount)

    keyboard = [
        [
            InlineKeyboardButton("Confirm", callback_data=f'confirm_mint_{trans_id}'),
            InlineKeyboardButton("Cancel", callback_data=f'cancel_{trans_id}')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f'Confirm minting of {amount} SevenX?', reply_markup=reply_markup)

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
    trans_id = store_pending_transaction(username, 'burn', amount)

    keyboard = [
        [
            InlineKeyboardButton("Confirm", callback_data=f'confirm_burn_{trans_id}'),
            InlineKeyboardButton("Cancel", callback_data=f'cancel_{trans_id}')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f'Confirm burning of {amount} SevenX?', reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    callback_data = query.data.split('_')
    action = callback_data[0]
    trans_id = int(callback_data[-1])

    if action == 'confirm_mint':
        sender, _, amount = get_pending_transaction(trans_id)
        update_balance(sender, int(amount))
        record_transaction(sender, 'mint', int(amount))
        delete_pending_transaction(trans_id)

        # Save balances and transactions
        save_balances_to_file()
        save_transactions_to_file()

        await context.bot.send_message(chat_id=query.message.chat_id, text=f'Minted {amount} SevenX.')
        await query.message.delete()

    elif action == 'confirm_burn':
        sender, _, amount = get_pending_transaction(trans_id)
        update_balance(sender, -int(amount))

        global burned_amount
        burned_amount += int(amount)

        delete_pending_transaction(trans_id)

        # Save balances and transactions
        save_balances_to_file()
        save_transactions_to_file()

        await context.bot.send_message(chat_id=query.message.chat_id, text=f'Burned {amount} SevenX.')
        await query.message.delete()

    elif action == 'cancel':
        delete_pending_transaction(trans_id)
        await context.bot.send_message(chat_id=query.message.chat_id, text='Operation canceled.')
        await query.message.delete()

async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text('Usage: /lookup <username>')
        return

    username = context.args[0]
    balance = get_balance(username)

    if balance is not None:
        await update.message.reply_text(f'{username} has a balance of {balance} SevenX.')
    else:
        await update.message.reply_text(f'User {username} not found.')

async def supply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    total_supply = get_total_supply()
    await update.message.reply_text(f'Total supply is {total_supply} SevenX.')

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    top_users = get_top_users()
    message = "Top users:\n\n"
    for user, balance in top_users:
        message += f'{user}: {balance} SevenX\n'
    await update.message.reply_text(message)

async def transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    limit = int(context.args[0]) if context.args else 10
    offset = int(context.args[1]) if len(context.args) > 1 else 0
    tx_list = get_transactions(limit, offset)

    message = "Recent Transactions:\n\n"
    for sender, receiver, amount, timestamp in tx_list:
        message += f'{timestamp}: {sender} -> {receiver} | {amount} SevenX\n'
    
    await update.message.reply_text(message)

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
    application.add_handler(CommandHandler("mint", mint))
    application.add_handler(CommandHandler("burn", burn))
    application.add_handler(CommandHandler("lookup", lookup))
    application.add_handler(CommandHandler("supply", supply))
    application.add_handler(CommandHandler("top", top))
    application.add_handler(CommandHandler("transactions", transactions))
    application.add_handler(CallbackQueryHandler(handle_callback))

    application.run_polling()

if __name__ == '__main__':
    main()
