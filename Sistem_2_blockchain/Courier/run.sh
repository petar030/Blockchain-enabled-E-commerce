#!/bin/bash
# čekaj dok Ganache ne odgovori
while ! curl -s http://ganache:8545 > /dev/null; do
    echo "Waiting for Ganache..."
    sleep 2
done

# start blockchain inicijalizacije
#python init_blockchain.py
python courier.py

