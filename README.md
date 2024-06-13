# SevenX Telegram Bot

SevenX is a virtual currency for Telegram that allows users to send and receive tokens seamlessly within the Telegram ecosystem. This bot facilitates the usage of SevenX, making transactions and account management simple and efficient.

## Features

- **Send and Receive SevenX**: Easily send SevenX tokens to other users on Telegram.
- **Check Balance**: Quickly check your SevenX balance with a simple command.
- **Transaction History**: View your recent transactions.
- **Top Up**: Add SevenX to your account using supported methods.
- **Withdraw**: Withdraw your SevenX to an external wallet.

## Getting Started

### Prerequisites

- [Python 3.8+](https://www.python.org/downloads/)
- [Telegram Bot API Key](https://core.telegram.org/bots#3-how-do-i-create-a-bot)

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/SevenX-Telegram-Bot.git
    cd SevenX-Telegram-Bot
    ```

2. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

3. Configure the bot:
    - Rename `config.example.json` to `config.json`.
    - Fill in your Telegram Bot API key and other necessary configurations in `config.json`.

### Usage

1. Start the bot:
    ```sh
    python bot.py
    ```

2. Interact with the bot on Telegram using the commands:

    - `/start` - Start the bot and initialize your wallet.
    - `/balance` - Check your SevenX balance.
    - `/send <amount> <username>` - Send SevenX to another user.
    - `/history` - View your transaction history.
    - `/topup` - Get instructions on how to add more SevenX to your account.
    - `/withdraw <amount> <wallet_address>` - Withdraw SevenX to an external wallet.

## Contributing

We welcome contributions from the community! If you'd like to contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Open a pull request.

## License

This project is licensed under the GNU General Public License. See the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have any questions, feel free to open an issue on GitHub or contact us at support@archmc.es.

## Donations

If you would like to support the development of the SevenX Telegram bot, you can send Nano (XNO) donations to the following address:

**Nano (XNO) Donation Address**: `nano_18k48z84medbxyd4hzbibu86ibfhc3mi5cpshoxedbtkmryokwa1ags3pyhy`

Thank you for your support!
