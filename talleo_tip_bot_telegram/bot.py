import click
import mongoengine

from mongoengine.errors import ValidationError

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, JobQueue
from telegram.ext import PrefixHandler

from talleo_tip_bot_telegram import models, store
from talleo_tip_bot_telegram.config import config

TALLEO_DIGITS = 100
TALLEO_REPR = 'TLO'
COMMAND_PREFIX = '!'

bot_description = f"Tip {TALLEO_REPR} to other users on your server."
bot_help_register = "Register or change your withdrawal address."
bot_help_info = "Get your account's info."
bot_help_withdraw = f"Withdraw {TALLEO_REPR} from your balance."
bot_help_balance = f"Check your {TALLEO_REPR} balance."
bot_help_transfer = f"Send {TALLEO_REPR} to external wallet from your balance."
bot_help_tip = f"Give {TALLEO_REPR} to a user from your balance."
bot_help_optimize = "Optimize wallet."
bot_help_outputs = "Get number of optimizable and unspent outputs."

updater = Updater(token=config.telegram.token, use_context=True)
dispatcher = updater.dispatcher


def commands(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text='Talleo Telegram Tip Bot commands\n\n'
        '/help - Show available commands\n'
        f'/register <wallet_address> - {bot_help_register}\n'
        f'/info - {bot_help_info}\n'
        f'/withdraw <amount> - {bot_help_withdraw}\n'
        f'/balance - {bot_help_balance}\n'
        f'/transfer <wallet> <amount> - {bot_help_transfer}\n'
        f'/tip @user <amount> - {bot_help_tip}\n'
        f'/optimize - {bot_help_optimize}\n'
        f'/outputs - {bot_help_outputs}')


def info(update: Update, context: CallbackContext):
    username = update.message.from_user.username
    if update.effective_chat is None:
        _chat_type = "private"
    else:
        _chat_type = update.effective_chat.type
    if _chat_type != "private":
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Wallet information is only available in private chat')
    elif username is None:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Please set a Telegram username in your profile settings!')
    else:
        user = store.register_user(username)
        context.bot.send_message(
            chat_id=update.message.chat_id, text='Account Info\n\n'
            f'Deposit Address: {user.balance_wallet_address}\n\n'
            f'Registered Wallet: {user.user_wallet_address}')


def balance(update: Update, context: CallbackContext):
    username = update.message.from_user.username
    if update.effective_chat is None:
        _chat_type = "private"
    else:
        _chat_type = update.effective_chat.type
    if _chat_type != "private":
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Wallet balance is only available in private chat')
    elif username is None:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Please set a Telegram username in your profile settings!')
    else:
        user: models.User = models.User.objects(user_id=username).first()
        wallet = store.get_user_wallet(user.user_id)
        context.bot.send_message(
            chat_id=update.message.chat_id, text='Your balance\n\n'
            f'Available: {wallet.actual_balance / TALLEO_DIGITS:.2f} '
            f'{TALLEO_REPR}\n'
            f'Pending: {wallet.locked_balance / TALLEO_DIGITS:.2f} '
            f'{TALLEO_REPR}\n')


def register(update: Update, context: CallbackContext):
    username = update.message.from_user.username
    wallet_address = context.args[0]
    if update.effective_chat is None:
        _chat_type = "private"
    else:
        _chat_type = update.effective_chat.type
    if _chat_type != "private":
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Registering is only available in private chat')
    elif username is None:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Please set a Telegram username in your profile settings!')
    else:
        existing_user: models.User = models.User.objects(
            user_id=username).first()
        if existing_user:
            prev_address = existing_user.user_wallet_address
            try:
                existing_user = store.register_user(existing_user.user_id,
                                                    user_wallet=wallet_address)
            except ValidationError:
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text='Invalid wallet address!')
                return
            if prev_address:
                context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text='Your withdrawal address has been changed from:\n'
                    f'{prev_address}\n to\n '
                    f'{existing_user.user_wallet_address}')
                return

        try:
            user = (existing_user or
                    store.register_user(username, user_wallet=wallet_address))
        except ValidationError:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text='Invalid wallet address!')
            return

        context.bot.send_message(
            chat_id=update.message.chat_id, text='You have been registered.\n'
            'You can send your deposits to '
            f'{user.balance_wallet_address} and your '
            f'balance will be available once confirmed.')


def withdraw(update: Update, context: CallbackContext):
    username = update.message.from_user.username
    amount = float(context.args[0])
    if update.effective_chat is None:
        _chat_type = "private"
    else:
        _chat_type = update.effective_chat.type
    if _chat_type != "private":
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Withdrawing is only available in private chat')
    elif username is None:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Please set a Telegram username in your profile settings!')
    else:
        user: models.User = models.User.objects(user_id=username).first()
        real_amount = int(amount * TALLEO_DIGITS)

        if not user.user_wallet_address:
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text='You do not have a withdrawal address, please use '
                '"register <wallet_address>" to register.')
            return

        user_balance_wallet: models.Wallet = models.Wallet.objects(
            wallet_address=user.balance_wallet_address).first()

        if real_amount + config.tx_fee >= user_balance_wallet.actual_balance:
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text='Insufficient balance to withdraw '
                f'{real_amount / TALLEO_DIGITS:.2f} '
                f'{TALLEO_REPR}.')
            return

        if real_amount > config.max_tx_amount:
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text='Transactions cannot be bigger than '
                f'{config.max_tx_amount / TALLEO_DIGITS:.2f} '
                f'{TALLEO_REPR}')
            return
        elif real_amount < config.min_tx_amount:
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text='Transactions cannot be lower than '
                f'{config.min_tx_amount / TALLEO_DIGITS:.2f} '
                f'{TALLEO_REPR}')
            return

        withdrawal = store.withdraw(user, real_amount)
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f'You have withdrawn {real_amount / TALLEO_DIGITS:.2f} '
            f'{TALLEO_REPR}.\n'
            f'Transaction hash: {withdrawal.tx_hash}')


def transfer(update: Update, context: CallbackContext):
    username = update.message.from_user.username
    recipient = context.args[0]
    amount = float(context.args[1])
    if username is None:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Please set a Telegram username in your profile settings!')
    else:
        user_from: models.User = models.User.objects(user_id=username).first()
        user_to: models.Wallet = models.Wallet.objects(
            wallet_address=recipient).first()
        if user_to is None:
            try:
                user_to = models.Wallet(wallet_address=recipient)
                user_to.save()
            except ValidationError:
                context.bot.send_message(chat_id=update.message.chat_id,
                                         text='Invalid wallet address!')
                return

        real_amount = int(amount * TALLEO_DIGITS)
        user_from_wallet: models.Wallet = models.Wallet.objects(
            wallet_address=user_from.balance_wallet_address).first()

        if real_amount + config.tx_fee >= user_from_wallet.actual_balance:
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text=f'Insufficient balance to send transfer of '
                f'{real_amount / TALLEO_DIGITS:.2f} '
                f'{TALLEO_REPR} to @{recipient}.')
            return

        if real_amount > config.max_tx_amount:
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text=f'Transactions cannot be bigger than '
                f'{config.max_tx_amount / TALLEO_DIGITS:.2f} '
                f'{TALLEO_REPR}.')
            return
        elif real_amount < config.min_tx_amount:
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text=f'Transactions cannot be smaller than '
                f'{config.min_tx_amount / TALLEO_DIGITS:.2f} '
                f'{TALLEO_REPR}.')
            return

        transfer = store.send(user_from, user_to, real_amount)

        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f'Transfer of {real_amount / TALLEO_DIGITS:.2f} '
            f'{TALLEO_REPR} '
            f'was sent to {recipient}\n'
            f'Transaction hash: {transfer.tx_hash}')


def tip(update: Update, context: CallbackContext):
    username = update.message.from_user.username
    recipient = context.args[0]
    amount = float(context.args[1])
    if username is None:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Please set a Telegram username in your profile settings!')
    else:
        if recipient == f'@{config.telegram.username}':
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text='HODL!')
        elif recipient == f'@{username}':
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text='Tipping oneself will just waste your balance!')
        elif "@" in recipient:
            recipient = recipient[1:]
            user_from: models.User = models.User.objects(
                user_id=username).first()
            user_to: models.User = store.register_user(recipient)
            real_amount = int(amount * TALLEO_DIGITS)

            user_from_wallet: models.Wallet = models.Wallet.objects(
                wallet_address=user_from.balance_wallet_address).first()

            if real_amount + config.tx_fee >= user_from_wallet.actual_balance:
                context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=f'Insufficient balance to send tip of '
                    f'{real_amount / TALLEO_DIGITS:.2f} '
                    f'{TALLEO_REPR} to @{recipient}.')
                return

            if real_amount > config.max_tx_amount:
                context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=f'Transactions cannot be bigger than '
                    f'{config.max_tx_amount / TALLEO_DIGITS:.2f} '
                    f'{TALLEO_REPR}.')
                return
            elif real_amount < config.min_tx_amount:
                context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=f'Transactions cannot be smaller than '
                    f'{config.min_tx_amount / TALLEO_DIGITS:.2f} '
                    f'{TALLEO_REPR}.')
                return

            tip = store.send_tip(user_from, user_to, real_amount)

            context.bot.send_message(
                chat_id=update.message.chat_id,
                text=f'Tip of {real_amount / TALLEO_DIGITS:.2f} '
                f'{TALLEO_REPR} '
                f'was sent to @{recipient}\n'
                f'Transaction hash: {tip.tx_hash}')
        else:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text='Error: Invalid username!')


def outputs(update: Update, context: CallbackContext):
    username = update.message.from_user.username
    if update.effective_chat is None:
        _chat_type = "private"
    else:
        _chat_type = update.effective_chat.type
    if _chat_type != "private":
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Wallet output information is only available in private chat')
    elif username is None:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Please set a Telegram username in your profile settings!')
    else:
        user = models.User = models.User.objects(user_id=username).first()

        user_balance_wallet: models.Wallet = models.Wallet.objects(
            wallet_address=user.balance_wallet_address).first()

        threshold = user_balance_wallet.actual_balance

        estimate = store.estimate_fusion(user, threshold)

        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=f'Optimizable outputs: {estimate.fusion_ready_count}\n'
            f'Unspent outputs: {estimate.total_count}')


def optimize(update: Update, context: CallbackContext):
    username = update.message.from_user.username
    if update.effective_chat is None:
        _chat_type = "private"
    else:
        _chat_type = update.effective_chat.type
    if _chat_type != "private":
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Wallet optimizing is only available in private chat')
    elif username is None:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text='Please set a Telegram username in your profile settings!')
    else:
        user = models.User = models.User.objects(user_id=username).first()

        user_balance_wallet: models.Wallet = models.Wallet.objects(
            wallet_address=user.balance_wallet_address).first()

        threshold = user_balance_wallet.actual_balance

        estimate = store.estimate_fusion(user, threshold)

        if estimate['fusion_ready_count'] == 0:
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text='No optimizable outputs!')
            return

        optimize = store.send_fusion(user, threshold)

        context.bot.send_message(
            chat_id=update.message.chat_id, text='Fusion transaction sent.\n'
            f'Transaction hash: {optimize.tx_hash}')


def update_balance_wallets(context: CallbackContext):
    store.update_balances()


def handle_errors(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text=f'Error occured: {context.error}')


@click.command()
def main():
    mongoengine.connect(db=config.database.db, host=config.database.host,
                        port=config.database.port,
                        username=config.database.user,
                        password=config.database.password)

    start_handler = CommandHandler('start', commands)
    dispatcher.add_handler(start_handler)

    help_handler = CommandHandler('help', commands)
    dispatcher.add_handler(help_handler)

    register_handler = CommandHandler('register', register)
    dispatcher.add_handler(register_handler)

    info_handler = CommandHandler('info', info)
    dispatcher.add_handler(info_handler)

    balance_handler = CommandHandler('balance', balance)
    dispatcher.add_handler(balance_handler)

    balance_prefix_handler = PrefixHandler(COMMAND_PREFIX, 'balance', balance)
    dispatcher.add_handler(balance_prefix_handler)

    withdraw_handler = CommandHandler('withdraw', withdraw)
    dispatcher.add_handler(withdraw_handler)

    transfer_handler = CommandHandler('transfer', transfer)
    dispatcher.add_handler(transfer_handler)

    transfer_prefix_handler = PrefixHandler(COMMAND_PREFIX, 'transfer',
                                            transfer)
    dispatcher.add_handler(transfer_prefix_handler)

    tip_handler = CommandHandler('tip', tip)
    dispatcher.add_handler(tip_handler)

    tip_prefix_handler = PrefixHandler(COMMAND_PREFIX, 'tip', tip)
    dispatcher.add_handler(tip_prefix_handler)

    outputs_handler = CommandHandler('outputs', outputs)
    dispatcher.add_handler(outputs_handler)

    optimize_handler = CommandHandler('optimize', optimize)
    dispatcher.add_handler(optimize_handler)

    dispatcher.add_error_handler(handle_errors)

    jobqueue = JobQueue()
    jobqueue.set_dispatcher(dispatcher)
    jobqueue.run_repeating(update_balance_wallets,
                           config.wallet_balance_update_interval)
    jobqueue.start()

    updater.start_polling()


if __name__ == '__main__':
    main()
