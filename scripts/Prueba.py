import requests

def get_bsc_contract(symbol):
    # Mapa símbolo -> ID de CoinGecko
    symbol_to_id = {
        "BTCB": "binance-bitcoin",
        "CAKE": "pancakeswap-token",
        "USDT": "tether",
        "DOGE": "dogecoin"
        # Puedes ampliar esta lista
    }

    token_id = symbol_to_id.get(symbol.upper())
    if not token_id:
        print("❌ Símbolo no encontrado en el mapeo.")
        return None

    url = f"https://api.coingecko.com/api/v3/coins/{token_id}"
    response = requests.get(url)

    if response.status_code != 200:
        print("❌ Error al consultar CoinGecko")
        return None

    data = response.json()
    return data["platforms"].get("binance-smart-chain")


def get_token_transactions(contract_address, limit=10, api_key="KVDQ4DN4B36ZSIVF8M4B8EF2J9J8ANZFF8"):
    url = (
        "https://api.bscscan.com/api"
        "?module=account"
        "&action=tokentx"
        f"&contractaddress={contract_address}"
        "&startblock=0&endblock=99999999"
        f"&page=1&offset={limit}&sort=desc"
        f"&apikey={api_key}"
    )
    response = requests.get(url)
    return response.json()["result"] if response.ok else []


# 🧪 Ejemplo
if __name__ == "__main__":
    symbol = "DOGE"
    contract = get_bsc_contract(symbol)

    if contract:
        print(f"✅ Contrato para {symbol}: {contract}")
        txs = get_token_transactions(contract)
        for tx in txs:
            print(f"{tx['hash']} - From: {tx['from']} To: {tx['to']} Value: {int(tx['value']) / 10**18} {symbol}")
    else:
        print("❌ No se pudo obtener el contrato.")
