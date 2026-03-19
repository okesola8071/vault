import requests
import os
from dotenv import load_dotenv

load_dotenv()

TATUM_API_KEY = os.getenv('TATUM_API_KEY')

HEADERS = {
    "x-api-key": TATUM_API_KEY,
    "Content-Type": "application/json"
}

BASE_URL = "https://api.tatum.io/v3"

def generate_wallet(crypto):
    """Generate a wallet for BTC, ETH or USDT"""
    crypto_map = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "USDT": "ethereum"  # USDT runs on Ethereum
    }

    chain = crypto_map.get(crypto.upper())
    if not chain:
        return None

    url = f"{BASE_URL}/{chain}/wallet"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error generating wallet: {response.text}")
        return None

def generate_address(crypto, xpub, index):
    """Generate a deposit address from wallet xpub"""
    crypto_map = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "USDT": "ethereum"
    }

    chain = crypto_map.get(crypto.upper())
    if not chain:
        return None

    url = f"{BASE_URL}/{chain}/address/{xpub}/{index}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json().get('address')
    else:
        print(f"Error generating address: {response.text}")
        return None

def get_balance(crypto, address):
    """Get balance of a wallet address"""
    crypto_map = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "USDT": "ethereum"
    }

    chain = crypto_map.get(crypto.upper())
    if not chain:
        return None

    url = f"{BASE_URL}/{chain}/account/balance/{address}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting balance: {response.text}")
        return None