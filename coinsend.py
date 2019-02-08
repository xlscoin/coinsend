#!/usr/bin/env python3

#'''
#Coin Send script, adapted from makechange.py by MadHatter with small additions by Morpheus, 2019
#Original script written and copyright; The TurtleCoin Developers 2018

#Usage: python3 coinsend.py 10000 XL3wePjyFUEUJHCYnnVWoghye8kR3xPEwQXBmkrGBxSfUjVQ31DhdjhDNAuDComxXybS4CugJWa9wUJ7EibnbWz91swXQA24J 
#Or make executable (chmod +x coinsend.py) and run from  your command interpreter

#Send large amounts of coins from local wallet to public address.

#Script communicates with WalletGreen.  Start the wallet service something like below:

#./xls-service -w testnetA.wallet -p yourpass --rpc-password test --bind-port 4456
#'''

import requests
import json
import secrets
import time
import sys
from threading import Thread

addressB = sys.argv[2]
#addressB = "XL3wePjyFUEUJHCYnnVWoghye8kR3xPEwQXBmkrGBxSfUjVQ31DhdjhDNAuDComxXybS4CugJWa9wUJ7EibnbWz91swXQA24J"

moveDecimal = 100000                # Coinunits TRTL has 2 decimals so 100 is the divide/multiply factor

TransferAmount = float(sys.argv[1]) * moveDecimal     # setup Amount to be transfered
#TransferAmount = 9.9 * moveDecimal
paymentID =""                                         # setup a PaymentID added to tx, can be empty

# Forks adjust as needed

Amount = int(TransferAmount)        # convert to int

maxAmount = 10000 * moveDecimal     # max Amount to be transfered every  xfer if Amount to big, < or = Amount !!
minAmount = 1000 * moveDecimal      # min Amount to sent if funds are locked

minanonymity = 1                    # define min mixin 
maxanonymity = 7                    # define max mixin
#anonymity = maxanonymity

fee = 10                            # atomic units, Fee , TRTL would be 0.10 as the tx network fee

def getAddress(host, port, rpcPassword):
    payload = {
        'jsonrpc': '2.0',
        'method': "getAddresses",
        'password': rpcPassword,
        'id': 'test',
        'params': {}
    }

    url = 'http://' + host + ':' + port + '/json_rpc'

    response = requests.post(
        url, data=json.dumps(payload),
        headers={'content-type': 'application/json'}
    ).json()

    if 'error' in response:
        print(response['error'])
        print('Failed to get address, exiting')
        sys.exit()
    else:
        return response['result']['addresses'][0]


def sendTransaction(host, port, rpcPassword, **kwargs):
    payload = {
        'jsonrpc': '2.0',
        'method': "sendTransaction",
        'password': rpcPassword,
        'id': 'test',
        'params': kwargs
    }

    url = 'http://' + host + ':' + port + '/json_rpc'

    response = requests.post(url, data=json.dumps(payload),headers={'content-type': 'application/json'}).json()

    #debug
    #pretty_data = json.dumps(response, indent=4)
    #print (pretty_data)

    #{
    # "error": {
    #           "code": -32700,
    #           "data": {
    #                       "application_code": 9
    #                   },
    #           "message": "Wrong amount"
    #           },
    # "id": "test",
    # "jsonrpc": "2.0"
    # }


    if 'error' in response:
        if (response['error']['data']['application_code'] == 9):
            print(response['error']['message'])         #Wrong Amount , not enough funds
            return -9

        elif (response['error']['data']['application_code'] == 32):
            print(response['error']['message'])         #Mixin above maximum allowed threshold
            return -32

        elif (response['error']['data']['application_code'] == 8):
            print(response['error']['message'])         #Transaction size is too big
            return -8

    # no error
    else:
        response['result']['amount'] = kwargs['transfers'][0]['amount']        #/moveDecimal
        print(response['result'])
        return response['result']['amount']        #return Amount transfered


def sendTXs(host, port, rpcPassword, sender, receiver):

    sleeptime = 1

    amountrest = Amount      #init Amount to be transfered
    amountcount = 0          #init CountTransfer
    amount = 0               #init next tx amount

    anonymity = maxanonymity # set mixing to max mixin
    
    while(amountcount != Amount and amountrest != 0):

        if( amount != 0 and amountrest > 0):

            print("Start to transfer Amount = " +str(amount / moveDecimal))
            print("Amount already transfered = " +str(amountcount /moveDecimal))
            print("Amount not transfered = " +str(amountrest /moveDecimal))

            params = {'transfers': [{'address': receiver, 'amount': amount}],
                      'fee': fee,
                      'anonymity': anonymity,
                      'changeAddress': sender,
                      'paymentId': paymentID
                      }

            value = sendTransaction(host, port, rpcPassword, **params)

            if (value > 0 ):                        # transaction ok
                # update amount sent
                print("Amount sent = " + str(value / moveDecimal))
                amountcount += value
                amountrest -= value
                amount = amountrest
                print("Amount sum sent = " + str(amountcount / moveDecimal))

            elif (value < 0 and value == -8):       # Transaction size is too big
                sleeptime = 1
                if (amountrest < maxAmount):
                    amount = amountrest             # set leftover amount to tx
                else:
                    amount = maxAmount              # set max tx amount manual by defenition above

                print("A error happened, waiting for " + str(sleeptime) + " sec and sending " + str(amount / moveDecimal))
                time.sleep(sleeptime)

            elif(value < 0 and value == -9):        #Wrong Amount , not enough funds
                sleeptime += 1
                if (amountrest < minAmount):        #check if amountrest < minAmount
                    amount = amountrest
                else:
                    amount = minAmount              #amountrest #minAmount
                print("Not enought funds or funds locked, waiting for " + str(sleeptime) + " sec and sending " + str(amount / moveDecimal))
                time.sleep(sleeptime)
            
            elif(value < 0 and value == -32):       # Mixin above maximum allowed threshold 
                print("Anonymity Error , mixin " + str(anonymity) + " reducing ..")
                if (anonymity > minanonymity):  
                    anonymity -= 1                  # decrement mixing
                else:
                    anonymity = minanonymity
                print("Anonymity set to mixin " + str(anonymity))
        
        else:
            amount = amountrest                     #set first fullamount to try tx

    print("END Transfered Amount = " + str(amountcount / moveDecimal))
    if (paymentID != ""): print("used Payment ID = " + paymentID)
    print("Anonymity used " + str(anonymity))


# Wallet service setting 
walletdHostA = "127.0.0.1"
walletdPortA = "4455"
rpcPasswordA = "verysecret"

addressA = getAddress(walletdHostA, walletdPortA, rpcPasswordA)

Thread(target=sendTXs, args=(walletdHostA, walletdPortA, rpcPasswordA,
       addressA, addressB)).start()
