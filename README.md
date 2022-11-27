# Talleo Tip Bot

This is a Telegram bot that can transfer TLO between users. It supports:

- Deposit TLO
- Tip TLO to Telegram users
- See your account info and TLO balance
- Withdraw TLO to your wallet

## Installation

**Requirements**

- MongoDB
- walletd (wallet daemon)
- Talleod (coin daemon)
- Python 3.8
- Telegram Authorization Token (Create a new bot by talking with [@BotFather](https://t.me/BotFather) to get one.)

I recommend using `supervisor` to keep `Talleod`, `walletd`
and `bot.py` running.

Here are some sample configs:

```ini
[program:bot]
command = /path/to/bin/python /path/to/talleo-tip-bot-telegram/talleo_tip_bot_telegram/bot.py --config /path/to/config.yml
user = user
autostart = yes
autorestart = yes
environment = LC_ALL="C.UTF-8",LANG="C.UTF-8"

[program:Talleod]
command = /path/to/Talleod
user = user
autostart = true
autorestart = true
directory = /path/to
environment=HOME="/home/user"

[program:walletd]
command = /path/to/walletd --container-file wallet/tip_wallets --container-password ****** --rpc-password ******
user = user
autostart = true
autorestart = true
directory = /path/to
environment=HOME="/home/user"
```

You will also need to make a copy of `config.yml.sample` to `config.yml` and
change the values so they work with your setup.

## CryptoNote compatibility

This project can most certainly be adapted to any
[CryptoNote](https://github.com/forknote/cryptonote-generator) coin.
You most likely won't have to change much.

- Change or remove the regex validation in `talleo_tip_bot_telegram.models:WalletAddressField`
to match the address prefix of your coin.
- Adapt the `TALLEO_DIGITS` and `TALLEO_REPR` to match your coin.

## Usage

**Telegram Commands**

- `register <wallet_address>`: Register a wallet to your account.
Will be used to withdraw later.
- `info`: See your deposit and withdrawal addresses.
- `balance`: See your current available and pending balance.
- `tip <user_mention> <amount>`: Tip `<amount>` TLO to `<user_mention>`.
- `withdraw <amount>`: Withdraws `<amount>` to your registered
withdrawal address.

## Local Env. Setup

This project uses `Pipfile`, `pipenv` and `tox`. To setup your environment
simply run `tox`. You can check the `tox.ini` file to see available environments
and commands that run within each of them.
