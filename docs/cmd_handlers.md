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
