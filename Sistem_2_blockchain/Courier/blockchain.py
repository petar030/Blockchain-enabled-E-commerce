import json
import secrets

import web3
from eth_account import Account
from solcx import install_solc, set_solc_version, compile_standard
import json
from web3 import Web3, HTTPProvider
from web3.exceptions import ContractLogicError


def compile_contract():
    install_solc('0.8.0')

    set_solc_version('0.8.0')

    with open("Contract.sol", "r") as f:
        source_code = f.read()

    compiled_sol = compile_standard({
        "language": "Solidity",
        "sources": {"Contract.sol": {"content": source_code}},
        "settings": {"outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}}}
    })

    contract_name = "OrderContract"
    abi = compiled_sol['contracts']['Contract.sol'][contract_name]['abi']
    bytecode = compiled_sol['contracts']['Contract.sol'][contract_name]['evm']['bytecode']['object']

    with open("Contract.json", "w") as f:
        json.dump({"abi": abi, "bytecode": bytecode}, f, indent=4)



class OrderContract:
    w3 = Web3(Web3.HTTPProvider("http://ganache:8545"))  # Promeni prema svom provider-u

    with open("Contract.json", "r") as f:
        data = json.load(f)
        abi = data["abi"]
        bytecode = data["bytecode"]

    @staticmethod
    def get_owner_account_and_key():
        accounts = OrderContract.w3.eth.accounts
        if not accounts:
            raise ValueError("Nema dostupnih računa u provider-u")
        # Ovde poslednji nalog + njegov privatni ključ
        return accounts[-1], "0xb64be88dd6b89facf295f4fd0dda082efcbe95a2bb4478f5ee582b7efe88cf60"


    @staticmethod
    def address_valid(address) -> bool:
        if not OrderContract.w3.is_address(address):
            return False

        try:
            balance = OrderContract.w3.eth.get_balance(address)
            if (balance > 0):
                return True
            else:
                return False
        except Exception:
            return False

    @staticmethod
    def deploy(customer_address, price):
        if not OrderContract.address_valid(customer_address):
            return {"success": False, "message": "Invalid address."}
        owner_address, owner_private_key = OrderContract.get_owner_account_and_key()
        print(owner_address)
        contract = OrderContract.w3.eth.contract(abi=OrderContract.abi, bytecode=OrderContract.bytecode)
        price_wei = price * 100
        tx = contract.constructor(customer_address, int(price_wei)).build_transaction({
            'from': owner_address,
            'nonce': OrderContract.w3.eth.get_transaction_count(owner_address),
            'gas': 1000000,
            'gasPrice': OrderContract.w3.to_wei('1', 'gwei')
        })

        signed_tx = OrderContract.w3.eth.account.sign_transaction(tx, owner_private_key)
        tx_hash = OrderContract.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = OrderContract.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {"success": True, "message": receipt.contractAddress}

    @staticmethod
    def assign_courier(contract_address, courier_address):
        if not OrderContract.address_valid(courier_address):
            return {"success": False, "message": "Invalid address."}
        owner_address, owner_private_key = OrderContract.get_owner_account_and_key()
        contract = OrderContract.w3.eth.contract(address=contract_address, abi=OrderContract.abi)
        paid = contract.functions.paid().call()
        if not paid:
            return {"success": False, "message": "Transfer not complete."}
        tx = contract.functions.assignCourier(courier_address).build_transaction({
            'from': owner_address,
            'nonce': OrderContract.w3.eth.get_transaction_count(owner_address),
            'gas': 1000000,
            'gasPrice': OrderContract.w3.to_wei('1', 'gwei')
        })
        signed_tx = OrderContract.w3.eth.account.sign_transaction(tx, owner_private_key)
        tx_hash = OrderContract.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        OrderContract.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {"success": True, "message": "Courier assigned successfully."}

    @staticmethod
    def confirm_delivery(contract_address):
        contract = OrderContract.w3.eth.contract(address=contract_address, abi=OrderContract.abi)
        owner_address, owner_private_key = OrderContract.get_owner_account_and_key()
        courier_address = contract.functions.courier().call()
        if courier_address == '0x0000000000000000000000000000000000000000':
            return {"success": False, "message": "Delivery not complete."}
        tx = contract.functions.confirmDelivery().build_transaction({
            'from': owner_address,
            'gas': 150000,
            'nonce': OrderContract.w3.eth.get_transaction_count(owner_address),
            'gasPrice': OrderContract.w3.to_wei(1, 'gwei')
        })
        signed_tx = OrderContract.w3.eth.account.sign_transaction(tx, owner_private_key)
        tx_hash = OrderContract.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        OrderContract.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {"success": True, "message": f"Delivery confirmed. Tx hash: {tx_hash.hex()}"}

    @staticmethod
    def generate_invoice(contract_address, customer_address):
        if not OrderContract.address_valid(customer_address):
            return {"success": False, "message": "Invalid address."}

        contract = OrderContract.w3.eth.contract(address=contract_address, abi=OrderContract.abi)

        # Provera da li je već plaćeno
        paid = contract.functions.paid().call()
        if paid:
            return {"success": False, "message": "Transfer already complete."}

        # Uzima cenu direktno iz contract-a
        price_wei = contract.functions.price().call()

        # Generisanje transakcije (invoice) bez izvršenja
        tx = contract.functions.pay().build_transaction({
            'from': customer_address,
            'value': price_wei,
            'gas': 200000,
            'nonce': OrderContract.w3.eth.get_transaction_count(customer_address),
            'gasPrice': OrderContract.w3.to_wei(1, 'gwei')
        })

        return {"success": True, "message": tx}


#
#
def create_and_initialize_account ( provider_url ):
    web3 = Web3 ( HTTPProvider ( provider_url ) )
    # create account
    private_key = "0x" + secrets.token_hex ( 32 )
    account     = Account.from_key ( private_key )
    address     = account.address

    # send funds from account 0
    result = web3.eth.send_transaction ( {
        "from": web3.eth.accounts[0],
        "to": address,
        "value": web3.to_wei ( 2, "ether" ),
        "gasPrice": 1
    } )
    receipt = web3.eth.wait_for_transaction_receipt(result)
    return ( private_key, address )


