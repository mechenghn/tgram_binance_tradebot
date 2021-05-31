#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.


import logging
import time

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from binance.client import Client
from binance.exceptions import BinanceAPIException
import configparser
import os

COIN_LIST = "supported_coin_list"
CFG_FL_NAME = "user.cfg"
USER_CFG_SECTION_BI = "binance_user_config"
USER_CFG_SECTION_TG = "tgram_user_config"


class configdata:
    def __init__(self):
        self.b_api_key=""
        self.b_api_secret_key=""
        self.t_api_token=""

class BinanceAPI:
    def __init__(self, cf:configdata):
        self.client = Client(cf.b_api_key,cf.b_api_secret_key)

def InitConfig():
    config = configparser.ConfigParser()
    ret = configdata()
    if not os.path.exists(CFG_FL_NAME):
        print("No configuration file (user.cfg) found! See README. Assuming default config...")
        config[USER_CFG_SECTION_BI] = {}    
        config[USER_CFG_SECTION_TG] = {}    
    else:
        config.read(CFG_FL_NAME)
        ret.b_api_key = config.get(USER_CFG_SECTION_BI, "api_key")
        ret.b_api_secret_key = config.get(USER_CFG_SECTION_BI, "api_secret_key")
        ret.t_api_token = config.get(USER_CFG_SECTION_TG, "api_token")
        return ret

config = InitConfig()
#Init Binance API
client = Client(config.b_api_key,config.b_api_secret_key)

supported_coin =[]

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.

def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('/coin: support crypto \n/balance: query asset\nget quotation in BUSD: quote <code> \nto buy: buy <code> <amount in BUSD>\nto sell: sell <code> <percentage>')

def balance(update,context):
    replytext="<code> - (free/lock)\n"
    try:
        acc = client.get_account()
        bal = acc['balances']
        for coin in supported_coin:
            subtext = str(coin) + ' - '
            free = float(get_balance_free(bal,str(coin)))
            subtext+=str(free)
            subtext+='/'
            lock = float(get_balance_lock(bal,str(coin)))
            subtext+=str(lock)
            subtext+='\n'
            if (free + lock) > 0:
                replytext+=subtext
        update.message.reply_text(replytext)
        #print(replytext)
    except BinanceAPIException as e:
            print(e)
            replytext = 'Failure\n' + str(e)[str(e).find(':')+2:len(str(e))]
            update.message.reply_text(replytext)
            #print(replytext)
            return

def get_balance_free(all_balance, coin):
    for asset in all_balance:
        if coin == asset['asset']:
            return asset['free']

def get_balance_lock(all_balance, coin):
    for asset in all_balance:
        if coin == asset['asset']:
            return asset['locked']

def query(update,context):
    update.message.reply_text('Updating balance...')
    replytext="<code> - (free/lock)\n"
    for coin in supported_coin:
        try:
            assetdata = str(client.get_asset_balance(asset=str(coin))).replace("\'",'')
        except BinanceAPIException as e:
            print(e)
            replytext = 'Failure\n' + str(e)[str(e).find(':')+2:len(str(e))]
            update.message.reply_text(replytext)
            return
        
        assetdata = assetdata.replace("}",'')
        assetdata = assetdata.replace("{",'')
        #print(assetdata)
        assetdata = assetdata.split(',')
        if len(assetdata) < 3:
            print('Invalid data')
            update.message.reply_text('Invalid data from Binance')
        else:
            #asset nanme
            subtext = ""
            asset_subdata = assetdata[0].split(':')
            subtext+=asset_subdata[1]
            subtext+=' -'

            #amount free
            asset_subdata = assetdata[1].split(':')
            subtext+=asset_subdata[1]
            free = float(asset_subdata[1])
            subtext+='/'

            #amount lock
            asset_subdata = assetdata[2].split(':')
            subtext+=asset_subdata[1]
            subtext+='\n'
            lock = float(asset_subdata[1])

            if (free + lock) > 0.0:
                replytext+=subtext
    update.message.reply_text(replytext)

def get_free_asset(coin):
    try:
        #print('get_free_asset ' + coin)
        assetdata = str(client.get_asset_balance(asset=str(coin))).replace("\'",'')
        assetdata = assetdata.replace("}",'')
        assetdata = assetdata.replace("{",'')
        assetdata = assetdata.split(',')
        #print('ENG: ' + assetdata[1])
        #amount free
        asset_subdata = assetdata[1].split(':')
        free = float(asset_subdata[1])
        #print('get_free_asset ' + coin +' ' + free)
        return free
    except BinanceAPIException as e:
        print(e)
        replytext = 'Failure\n' + str(e)[str(e).find(':')+2:len(str(e))]
        return 0

def test_buy_sell_all_coins(update,context):
    for item in supported_coin:
        try:
            if item == 'BUSD':
                continue
            buy_coin(update, str(item),'50')
            time.sleep(0.5)
            #query(update,context)
            sell_coin(update,str(item),'100')
            time.sleep(0.5)
        except BinanceAPIException as e:
            print(e)
        else:
            print("Success")


def supported_coin_list(update,context):
    replytext=""
    for item in supported_coin:
        replytext+=(item +",")
    update.message.reply_text(replytext)

def transaction_handle(update,context):
    CommandString = update.message.text
    print("Command: " + CommandString)
    #update.message.reply_text('Your command: ' + CommandString) 
    CommandString = CommandString.split(' ')
    #print(CommandString[0] + '\n' + CommandString[1] +'\n' + CommandString[2])

    if CommandString[0].lower() == 'buy':
        buy_coin(update, CommandString[1].upper(),CommandString[2])
    elif CommandString[0].lower() == 'sell':
        sell_coin(update, CommandString[1].upper(),CommandString[2])
    elif CommandString[0].lower() == 'quote':
        quote(update,CommandString[1].upper())
    else:
        update.message.reply_text('Unsupported command')

def quote(update, Ticket):
    if Ticket == 'USDT' or Ticket == 'BUSD':
        Status="Quotation for is prohibited: " + Ticket; 
        update.message.reply_text(Status) 
        return
    SYM = Ticket + 'BUSD'
    price = 0.0
    print(SYM)
    if check_supported_symbol(Ticket) == False: 
        Status='Failure: Unsupported crypto'
    else: 
        try:
            avg_data = str(client.get_avg_price(symbol=SYM)).replace("\'",'')
            print(avg_data)
            avg_price = avg_data.split(',')
            price = avg_price[1].split(':')
            price[1] = price[1].replace("}",'')
            price = float(price[1].replace("/'",''))
        except BinanceAPIException as e:
            print(e)
            Status = 'Failure\n' + str(e)[str(e).find(':')+2:len(str(e))]
        else:
            print("Success")
            Status = str(price)
    update.message.reply_text('Quotation: ' + Ticket + ' - ' + Status)

def get_round_precision(symbol):
    info = client.get_symbol_info(symbol)
    f = [i["stepSize"] for i in info["filters"] if i["filterType"] == "LOT_SIZE"][0]
    prec = 0
    for i in range(10):
        if f[i] == "1":
            break
        if f[i] == ".":
            continue
        else:
            prec += 1
    return prec

def buy_coin(update, Ticket, Amount):
    print('Buy_coin ' + Ticket + ' $' + Amount)
    Status = 'Failure'
    if Ticket == 'USDT' or Ticket == 'BUSD':
        Status+=" - Transaction is prohibited"
        update.message.reply_text('Buy: ' + Ticket + ': $'+ str(Amount) + ' - ' +Status) 
        return
    if float(Amount) > get_free_asset('BUSD'):
        Status = 'Failure: Insufficient BUSD balance'
        update.message.reply_text('Buy: ' + Ticket + str(Amount) + ' - ' +Status) 
        return       
               
    SYM = Ticket + 'BUSD'
    print(SYM)
    if check_supported_symbol(Ticket) == False: 
        Status='Failure: Unsupported crypto'
    else: 
        try:
            avg_data = str(client.get_avg_price(symbol=SYM)).replace("\'",'')
            print(avg_data)
            avg_price = avg_data.split(',')
            price = avg_price[1].split(':')
            price[1] = price[1].replace("}",'')
            price = float(price[1].replace("/'",''))
            Amount = float(Amount)/price
            PREC = get_round_precision(SYM)
            Amount = float(round(Amount, PREC))
            print('Amount: ' + str(Amount))
            order = client.order_market_buy(symbol=SYM,quantity=str(Amount))
        except BinanceAPIException as e:
            print(e)
            Status = 'Failure\n' + str(e)[str(e).find(':')+2:len(str(e))]
        else:
            print("Success")
            Status = "Success"
    update.message.reply_text('Buy: ' + Ticket + str(Amount) + ' - ' +Status) 

def sell_coin(update, Ticket, Amount):
    print('Sell_coin ' + Ticket + ' %' + Amount)
    Status = 'Failure'
    if Ticket == 'USDT' or Ticket == 'BUSD':
        Status+=" - Transaction is prohibited"
        update.message.reply_text('Sell: ' + Ticket + ': '+ str(Amount) + '% - ' +Status) 
        return
    if get_free_asset(Ticket) == 0:
        Status = 'Failure: Insufficient balance of ' + Ticket
        update.message.reply_text('Sell: ' + Ticket + ': ' + Ticket + str(Amount) + ' - ' +Status)
        return

    SYM = Ticket+'BUSD'
    if check_supported_symbol(Ticket) == False: 
        Status='Failure: Unsupported crypto'
    #elif check_symbol_validity(SYM) < 0 :
    #    print("symbol NOT found: " + SYM)
    #    update.message.reply_text('Invalid symbol: ' + SYM)
    else: 
        try:
            Amount = float(Amount) * get_free_asset(Ticket)/100
            PREC = get_round_precision(SYM)
            Amount = float(round(Amount, PREC))
            #print('Amount: ' + str(Amount))
            order =  client.order_market_sell(symbol=SYM,quantity=str(Amount))

        except BinanceAPIException as e:
            print(e)
            Status = 'Failure\n' + str(e)[str(e).find(':')+2:len(str(e))]
        else:
            print("Success")
            Status = "Success"
    update.message.reply_text('Sell: ' + Ticket + ': ' + Ticket + str(Amount) + ' - ' +Status) 

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    
def check_supported_symbol(symbol):
    for item in supported_coin:
        if item == symbol:
            return True
    return False

def update_crypto_list(path):
    text_file = open(path, "r")
    print('Init crypto list')
    bRead = True
    while bRead == True:
        line = text_file.readline()
        #print(line)
        symbol = line.replace('\n', '')
        #print(symbol)
        if len(symbol) > 1:
            ret = ""
            try:
                ret = client.get_asset_balance(asset=str(symbol))
            except BinanceAPIException as e:
                print(e)
            if len(ret) == 3: #valid binnce response
                supported_coin.append(symbol)
        else:
            bRead = False
    text_file.close()
    print(supported_coin)


def main():
    update_crypto_list(COIN_LIST)

    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(config.t_api_token, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("h", help))
    dp.add_handler(CommandHandler("balance", balance))
    dp.add_handler(CommandHandler("coin", supported_coin_list))
    
    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text,transaction_handle))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()



if __name__ == '__main__':
    main()
