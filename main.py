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

# Variables to track burned coins
total_burned = 0

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
    update_balance_file()

def record_transaction(sender, receiver, amount):
    c.execute('INSERT INTO transactions (sender, receiver, amount) VALUES (?, ?, ?)', (sender, receiver, amount))
    conn.commit()
    update_transactions_file()

def update_balance_file():
    balances = {}
    c.execute('SELECT username, balance FROM users')
    for row in c.fetchall():
        balances[row[0]] = row[1]
    
    with open('balances.txt', 'w') as f:
        for user, balance in balances.items():
            f.write(f'{user}: {balance} SevenX\n')
        f.write(f'\nTotal burned: {total_burned} SevenX\n')

def update_transactions_file():
    with open('transactions.txt', 'w') as f:
        c.execute('SELECT sender, receiver, amount, timestamp FROM transactions ORDER BY timestamp DESC')
        transactions = c.fetchall()
        for trans in transactions:
            f.write(f'{trans[3]}: {trans[0]} -> {trans[1]} | {trans[2]} SevenX\n')

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

def apply_transaction_fee(amount):
    global total_burned
    fee = amount * 0.02
    burned = fee / 2
    privileged_user_share = fee - burned
    total_burned += burned

    return amount - fee, privileged_user_share, burned

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

        # Apply transaction fee
        amount_after_fee, privileged_user_share, burned = apply_transaction_fee(amount)

        update_balance(sender, -amount)
        print(f"Balance updated for sender {sender}")  # Debugging line
        update_balance(receiver, amount_after_fee)
        print(f"Balance updated for receiver {receiver}")  # Debugging line
        update_balance(config["PRIVILEGED_USER"], privileged_user_share)
        print(f"Balance updated for privileged user {config['PRIVILEGED_USER']}")  # Debugging line
        record_transaction(sender, receiver, amount_after_fee)
        delete_pending_transaction(trans_id)

        await context.bot.send_message(chat_id=query.message.chat_id,
                                       text=f'Payment of {amount_after_fee} SevenX to {receiver} confirmed!\nTransaction details:\nSender: {sender}\nReceiver: {receiver}\nAmount: {amount_after_fee} SevenX',
                                       parse_mode=ParseMode.MARKDOWN)

        # Send a message to the receiver
        receiver_chat_id = get_user_chat_id(receiver)
        if receiver_chat_id:
            await context.bot.send_message(chat_id=receiver_chat_id,
                                           text=f'You have received a payment of {amount_after_fee} SevenX from {sender}.\nTransaction details:\nSender: {sender}\nAmount: {amount_after_fee} SevenX')

        # Delete the confirmation message
        await query.message.delete()

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
        update_balance(username, 5)
        await update.message.reply_text('Claimed 5 SevenX!')
    else:
        await update.message.reply_text('You have already claimed your 5 SevenX!')

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
    update_balance(username, -amount)
    await update.message.reply_text(f'Burned {amount} SevenX!')

async def lookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /lookup <username>")
        return

    username = context.args[0].lstrip('@')  # Eliminar el "@" si está presente
    c.execute('SELECT balance FROM users WHERE username = ?', (username,))
    result = c.fetchone()

    if result:
        balance = result[0]
        await update.message.reply_text(f"User: {username}\nBalance: {balance} SevenX")
    else:
        await update.message.reply_text(f"User {username} not found.")

async def supply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    c.execute('SELECT SUM(balance) FROM users')
    total_supply = c.fetchone()[0] or 0
    await update.message.reply_text(f"Total supply of SevenX: {total_supply} SevenX")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    c.execute('SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10')
    top_users = c.fetchall()
    response = "Top 10 Users by Balance:\n\n"
    for user, balance in top_users:
        response += f"{user}: {balance} SevenX\n"
    await update.message.reply_text(response)

# Main function
def main():
    # Use config file for the bot token
    TOKEN = config["TELEGRAM_BOT_TOKEN"]
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pay", pay))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("claim", claim))
    application.add_handler(CommandHandler("burn", burn))
    application.add_handler(CommandHandler("lookup", lookup))
    application.add_handler(CommandHandler("supply", supply))
    application.add_handler(CommandHandler("top", top))
    application.add_handler(CallbackQueryHandler(handle_callback))

    application.run_polling()

if __name__ == '__main__':
    main()
