## Helper Functions
### `get_balance(username)`
Retrieves the balance for a given user.
```python
def get_balance(username):
    c.execute('SELECT balance FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    return result[0] if result else 0
```

### `update_balance(username, amount)`
Updates the balance of a given user.
```python
def update_balance(username, amount):
    if get_balance(username) == 0:
        c.execute('INSERT INTO users (username, balance) VALUES (?, ?)', (username, amount))
    else:
        c.execute('UPDATE users SET balance = balance + ? WHERE username = ?', (amount, username))
    conn.commit()
```

### `record_transaction(sender, receiver, amount)`
Records a completed transaction.
```python
def record_transaction(sender, receiver, amount):
    c.execute('INSERT INTO transactions (sender, receiver, amount) VALUES (?, ?, ?)', (sender, receiver, amount))
    conn.commit()
```

### `store_pending_transaction(sender, receiver, amount)`
Stores a transaction that is pending confirmation.
```python
def store_pending_transaction(sender, receiver, amount):
    c.execute('INSERT INTO pending_transactions (sender, receiver, amount) VALUES (?, ?, ?)', (sender, receiver, amount))
    conn.commit()
    return c.lastrowid
```

### `get_pending_transaction(trans_id)`
Retrieves details of a pending transaction.
```python
def get_pending_transaction(trans_id):
    c.execute('SELECT sender, receiver, amount FROM pending_transactions WHERE id = ?', (trans_id,))
    return c.fetchone()
```

### `delete_pending_transaction(trans_id)`
Deletes a pending transaction.
```python
def delete_pending_transaction(trans_id):
    c.execute('DELETE FROM pending_transactions WHERE id = ?', (trans_id,))
    conn.commit()
```

### `store_user_chat_id(username, chat_id)`
Stores or updates the chat ID for a user.
```python
def store_user_chat_id(username, chat_id):
    c.execute('REPLACE INTO user_chat_ids (username, chat_id) VALUES (?, ?)', (username, chat_id))
    conn.commit()
```

### `get_user_chat_id(username)`
Retrieves the chat ID for a user.
```python
def get_user_chat_id(username):
    c.execute('SELECT chat_id FROM user_chat_ids WHERE username = ?', (username,))
    result = c.fetchone()
    return result[0] if result else None
```

## Command Handlers
### `start(update, context)`
Handles the `/start` command. Welcomes the user and stores their chat ID.
```python
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    store_user_chat_id(username, chat_id)
    await update.message.reply_text('Welcome to the 7x Currency Bot!')
```

### `pay(update, context)`
Handles the `/pay` command. Initiates a payment transaction.
```python
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

    await update.message.reply_text(f'Confirm payment of {amount} 7x to {receiver}?',
                                    reply_markup=reply_markup)
```

### `handle_callback(update, context)`
Handles callback queries for confirming or canceling transactions.
```python
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    callback_data = query.data.split('_')
    action = callback_data[0]
    trans_id = int(callback_data[1])

    if action == 'confirm':
        sender, receiver, amount = get_pending_transaction(trans_id)
        print(f"Transaction confirmed: {sender} pays {receiver} {amount} 7x")  # Debugging line
        update_balance(sender, -amount)
        print(f"Balance updated for sender {sender}")  # Debugging line
        update_balance(receiver, amount)
        print(f"Balance updated for receiver {receiver}")  # Debugging line
        record_transaction(sender, receiver, amount)
        delete_pending_transaction(trans_id)

        await context.bot.send_message(chat_id=query.message.chat_id,
                                       text=f'Payment of {amount} 7x to {receiver} confirmed!\nTransaction details:\nSender: {sender}\nReceiver: {receiver}\nAmount: {amount} 7x',
                                       parse_mode=ParseMode.MARKDOWN)

        # Send a message to the receiver
        receiver_chat_id = get_user_chat_id(receiver)
        if receiver_chat_id:
            await context.bot.send_message(chat_id=receiver_chat_id,
                                           text=f'You have received a payment of {amount} 7x from {sender}.\nTransaction details:\nSender: {sender}\nAmount: {amount} 7x')

    elif action == 'cancel':
        delete_pending_transaction(trans_id)
        await context.bot.send_message(chat_id=query.message.chat_id, text='Payment canceled!')
```

### `balance(update, context)`
Handles the `/balance` command. Displays the user's balance.
```python
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    store_user_chat_id(username, chat_id)

    balance = get_balance(username)
    await update.message.reply_text(f'Your balance is {balance} 7x.')
```

### `claim(update, context)`
Handles the `/claim` command. Allows users to claim free 7x currency if they haven't already.
```python
async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    store_user_chat_id(username, chat_id)

    if get_balance(username) == 0:
        update_balance(username, 50)
        await update.message.reply_text('Claimed 50 7x!')
    else:
        await update.message.reply_text('You have already claimed your 50 7x!')
```

### `request(update, context)`
Handles the `/request` command. Sends a request for 7x currency from another user.
```python
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

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f'{target}, {requester} is requesting {amount} 7x from you!')
```

### `refresh_balance(update, context)`
Handles the `/refresh` command. Refreshes the user's balance.
```python
async def refresh_balance(update: Update, context: ContextTypes.DEFAULT_TYPE

) -> None:
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    store_user_chat_id(username, chat_id)

    await update.message.reply_text('Balance refreshed!')
```

## Main Function
The main function sets up the bot and its command handlers, and starts the bot.
```python
def main():
    # Use environment variable for the bot token
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pay", pay))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("claim", claim))
    application.add_handler(CommandHandler("request", request))
    application.add_handler(CommandHandler("refresh", refresh_balance))
    application.add_handler(CallbackQueryHandler(handle_callback))

    application.run_polling()

if __name__ == '__main__':
    main()
```
