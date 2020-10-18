from typing import List, Dict

from talleo_tip_bot_telegram import rpc_client
from talleo_tip_bot_telegram.config import config


def register() -> str:
    result = rpc_client.call_method('createAddress')
    return result['address']


def send_transaction(from_address: str, to_address: str, amount: int) -> str:
    payload = {
        'addresses': [from_address],
        'transfers': [{
            "amount": amount,
            "address": to_address
        }],
        'fee': config.tx_fee,
        'anonymity': 0
    }
    result = rpc_client.call_method('sendTransaction', payload=payload)
    return result['transactionHash']


def estimate_fusion(address: str, threshold: int) -> Dict[str, Dict]:
    outputs = {}
    payload = {'addresses': [address], 'threshold': threshold}
    result = rpc_client.call_method('estimateFusion', payload=payload)

    outputs['fusion_ready_count'] = result['fusionReadyCount']
    outputs['total_count'] = result['totalOutputCount']

    return outputs


def send_fusion(address: str, threshold: int) -> str:
    payload = {'addresses': [address], 'threshold': threshold}
    result = rpc_client.call_method('sendFusion', payload=payload)

    return result['transactionHash']


def get_wallet_balance(address: str) -> Dict[str, int]:
    result = rpc_client.call_method('getBalance', {'address': address})
    return result


def get_all_balances(wallet_addresses: List[str]) -> Dict[str, Dict]:
    wallets = {}
    for address in wallet_addresses:
        try:
            wallet = rpc_client.call_method('getBalance', {'address': address})
            wallets[address] = wallet
        except rpc_client.RPCException:
            print(
                f"Can't get balance of wallet {address}, it might be external."
            )
    return wallets
