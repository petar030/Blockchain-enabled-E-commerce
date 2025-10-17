from web3 import Web3, HTTPProvider

def init_account():
    web3 = Web3(HTTPProvider("http://ganache:8545"))
    accounts = web3.eth.accounts

    if web3.eth.get_balance(accounts[-1]) == 0:
        tx_hash = web3.eth.send_transaction({
            "from": accounts[0],
            "to": accounts[-1],
            "value": web3.to_wei(5, "ether"),
            "gas": 21000,
            "gasPrice": 20000000000
        })
        print("tx hash:", tx_hash.hex())

    i = 0
    for account in accounts:
        print(f"Account({i}) balance: " + str(web3.eth.get_balance(account) / 1e18))
        i += 1

init_account()
