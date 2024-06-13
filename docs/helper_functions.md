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
