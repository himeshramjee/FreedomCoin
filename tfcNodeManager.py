from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import logging
from pprint import pprint
from decimal import *
import decimal
import json
from pathlib import Path, PureWindowsPath
import sys, traceback
import os
import time

# create logger
datetimestamp = time.strftime("%Y%m%d-%H%M%S")
logger=logging.getLogger('tfc-node-manager-log');
logger.setLevel(logging.DEBUG);

# create a file handler and set level to debug
fh=logging.FileHandler("tfc-node-manager-log-{}.log".format(datetimestamp));
fh.setLevel(logging.DEBUG);

# create console handler and set level to debug
ch=logging.StreamHandler();
ch.setLevel(logging.DEBUG);

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s');

# add formatter to ch
ch.setFormatter(formatter);
fh.setFormatter(formatter);

# add ch to logger
logger.addHandler(ch);
logger.addHandler(fh);

'''
logger.debug('debug message');
logger.info('info message');
logger.warn('warn message');
logger.error('error message');
logger.critical('critical message');
'''

# Environment Setup
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

'''
TFC_COIN_PRECISION=15;
COIN_PRECISION=TFC_COIN_PRECISION;
getcontext().prec=COIN_PRECISION;
'''

UNSPENT_MIN_CONF=50;
UNSPENT_MAX_CONF=9999999;

assert ('win32' in sys.platform), "This code runs on Windows only.";
# print("Python {}".format(getcontext()));

# Read Coin Configuration
coinConfFileName="Freedomcoin.conf";
coinConfFileDefaultPath=Path("{}/Freedomcoin/{}".format(os.getenv("APPDATA"), coinConfFileName));
coinConfFilePath=input("Enter the full file path to your coin config file (e.g. {}): ".format(coinConfFileDefaultPath));
if len(coinConfFilePath.strip()) == 0:
	logger.info("Trying default location {}...".format(coinConfFileDefaultPath));
	coinConfFilePath=coinConfFileDefaultPath;

try:
	logger.info("Reading coin configuration file ({})...".format(coinConfFileName));
	configBag={};
	with open(coinConfFilePath, "r") as coinConfigFile:
		for line in coinConfigFile:
			line=line.strip();
			if "=" not in line: continue;
			if line.startswith("#") or line.startswith("//"): continue;
			
			k,v=line.split("=", 1);
			configBag[k]=v;
	logger.info("Done.");
except:
	logger.critical("Failed to read configuration file.");
	logger.critical("Unexpected error: {}".format(sys.exc_info()));
	raise
			
rpcUser='';
if "rpcuser" in configBag:
	rpcUser=configBag["rpcuser"];
else:
	# raise ValueError("RPC User ('rpcuser') configuration is missing");
	logger.critical("RPC User ('rpcuser') configuration is missing. Aborting.");
	exit();

rpcPassword='';
if "rpcpassword" in configBag:
	rpcPassword=configBag["rpcpassword"];
else:
	# raise ValueError("RPC Password ('rpcpassword') configuration is missing");
	logger.critical("RPC Password ('rpcpassword') configuration is missing. Aborting.");
	exit();

rpcPort='';
if "rpcport" in configBag:
	rpcPort=configBag["rpcport"];
else:
	# raise ValueError("RPC Port ('rpcport') configuration is missing");
	logger.critical("RPC Port ('rpcport') configuration is missing. Aborting.");
	exit();

rpcIP='';
if "rpcip" in configBag:
	rpcIP=configBag["rpcip"];
else:
	# raise ValueError("RPC IP ('rpcip') configuration is missing");
	logger.critical("RPC IP ('rpcip') configuration is missing. Aborting.");
	exit();

masternodeCollateral='';
if "masternodeCollateral" in configBag:
	masternodeCollateral=Decimal(configBag["masternodeCollateral"]);
else:
	#raise ValueError("Masternode collateral ('masternodeCollateral') configuration is missing");
	logger.critical("Masternode collateral ('masternodeCollateral') configuration is missing. Aborting.");
	exit();
	
# Setup rpc connection
try:
	logger.info("Setting up node connection to {}...".format(rpcIP));
	rpcConnection = AuthServiceProxy("http://%s:%s@%s:%s"%(rpcUser, rpcPassword, rpcIP, rpcPort));
	logger.info("Done.");
	logger.info("Testing connection...");
	rpcConnection.getinfo();
	logger.info("Done.");
except:
	logger.critical("Failed to get node information.");
	logger.critical("Unexpected error: {}".format(sys.exc_info()));
	raise

if 0:
	# pprint(rpcConnection.gettransaction("")); print();
	# pprint(rpcConnection.gettransaction("")); print();
	# pprint(rpcConnection.listunspent(UNSPENT_MIN_CONF, UNSPENT_MAX_CONF)); print();
	# pprint(rpcConnection.decodescript(""));
	exit();

# Application setup
# Holding addresses
holdingAddressPrefix="holdingAddress";

print();
inputUser=input("Who's wallet do you want to process? ");
inputUser=inputUser.lower().capitalize();
if (len(inputUser.strip()) > 0):
	logger.info("Checking {} configuration for holding account address...".format(coinConfFileName));
	holdingAddressConfigName=holdingAddressPrefix + inputUser;
	if holdingAddressConfigName in configBag:
		holdingWalletAddress=configBag[holdingAddressConfigName];
	else:
		logger.error("Holding Address configuration '{}' is missing. Aborting.".format(holdingAddressConfigName));
		exit();

	logger.info("Finding account for address {}...".format(holdingWalletAddress));
	holdingWalletName=rpcConnection.getaccount(holdingWalletAddress);
	if (holdingWalletName is not None):
		logger.info("Cool {}, let's get started. This script will use {} as the holding wallet ({}).".format(inputUser, holdingWalletName, holdingWalletAddress));
	else:
		logger.error("Failed to lookup account for user '{}'".format(inputUser));
else:
	logger.critical("Unrecognized user '{}'. Aborting.".format(inputUser));
	exit();

print();
logger.info("Processing all node accounts...");
walletAccounts=rpcConnection.listaccounts();
allUnspent=[];
totalUnspentAmount=0;
for account in walletAccounts:
	if len(account.strip()) == 0:
		logger.info("Ignoring unrecognised/invalid address ('{}')!\n".format(account));
		continue;
	else:
		logger.info("Account: {}".format(account));
		
	if account.endswith(inputUser) == False:
		logger.info("Skipping account. Doesn't belong to current user.\n");
		# pprint("{} with balance {}".format(account, walletAccounts[account]));
		continue;
	elif account == holdingWalletName:
		logger.info("Skipping account. This is the holding address.\n");
	else:
		nodeBalance=walletAccounts[account];
		if nodeBalance > masternodeCollateral:
			unspentList=rpcConnection.listunspent(UNSPENT_MIN_CONF, UNSPENT_MAX_CONF, rpcConnection.getaddressesbyaccount(account));
			unspentBalance=Decimal(0);
			if len(unspentList) > 0:
				logger.info("Unspent list contains {} outs (incl. collateral). Calculating balance without collateral...".format(len(unspentList)));
				# pprint(unspentList);
				for otx in unspentList:
					if otx['amount'] != masternodeCollateral:
						logger.info("Adding unspent amount of {} TFC (txid: {}).".format(Decimal(otx['amount']), otx['txid']));
						unspentBalance+=Decimal(otx['amount']);
						allUnspent.append(otx);
						totalUnspentAmount+=Decimal(otx['amount']);
				logger.info("{} TFC can be moved to holding address.\n".format(unspentBalance));
		elif nodeBalance < masternodeCollateral:
			logger.warn("Warning! This node address has insufficient collateral ({} vs expected {}).\n".format(nodeBalance, masternodeCollateral));
		else:
			logger.info("Nothing to see here, keep scrolling.\n");

# Estimate total tx fee using 0.0001 TFC per 1000 bytes which is rougly 6 txns
totalTxFee=(len(allUnspent)/6)*0.00010000;
totalTxFee=round(totalTxFee, 8);
txAmount=round(totalUnspentAmount-Decimal(totalTxFee), 8);
print();
logger.info("Holding wallet name is {} and it has address {}.".format(holdingWalletName, holdingWalletAddress));
acceptTxFeeInput=input("Using {} unspent txns valued at {} TFC will incur a fee of {} TFC. Continue? (y/n) ".format(len(allUnspent), txAmount, totalTxFee))	;
if acceptTxFeeInput.strip().lower() != "y":
	logger.info("Tx not accepted by user. Aborting.");
	exit();
	
# Gather tx inputs data
toAddresses={holdingWalletAddress:txAmount};
changeAddress=holdingWalletAddress;	
inputsWithScriptKeysList=[];
inputsList=[];
for u in allUnspent:
	inputsList.append({"txid":u["txid"],"vout":u["vout"], "address":changeAddress});
	inputsWithScriptKeysList.append({"txid":u["txid"],"vout":u["vout"],"scriptPubKey":u["scriptPubKey"]});

# createrawtransaction [{"txid":txid,"vout":n},...] {address:amount,...}
print();
logger.info("Creating tx hash going to address {}...".format(toAddresses));
createTxHex=rpcConnection.createrawtransaction(inputsList, toAddresses);
createTxJson=rpcConnection.decoderawtransaction(createTxHex);
if len(createTxHex.strip()) > 0:
	# pprint(rpcConnection.decodescript(createTxHex));
	# pprint(rpcConnection.decoderawtransaction(createTxHex));
	createTxID=createTxJson["txid"];
	logger.info("TX was successfulling created. TxID is: {}".format(createTxID));
else:
	logger.error("Failed to create tx. Aborting.");
	exit();

# signrawtransaction <hex string> [{"txid":txid,"vout":n,"scriptPubKey":hex,"redeemScript":hex},...] [<privatekey1>,...] [sighashtype="ALL"]
print();
logger.info("Signing tx...");
signTxResult=rpcConnection.signrawtransaction(createTxHex, inputsWithScriptKeysList);
if signTxResult["complete"] == True:
	logger.info("Signing was successful.");
	# pprint(rpcConnection.decodescript(signTxResult["hex"]));
	# pprint(rpcConnection.decoderawtransaction(signTxResult));
else:
	logger.error("Signing failed. Aborting.");
	exit();

# sendrawtransaction <hex string>
print();
logger.info("Sending tx...");
sendTxResult=rpcConnection.sendrawtransaction(signTxResult["hex"]);
if len(sendTxResult.strip()) > 0:
	logger.info("Send tx result received...");
	logger.info("Resulting TxID: {}".format(sendTxResult));
else:
	logger.error("Send tx result is missing. Aborting.");

logger.info("Total unspent was {} TFC and tx fee paid was {}".format(totalUnspentAmount, totalTxFee));
