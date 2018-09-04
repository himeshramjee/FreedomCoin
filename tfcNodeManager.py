from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import logging
from pprint import pprint
from decimal import *
import decimal
import json
from pathlib import Path, PureWindowsPath
import sys
import os

logging.basicConfig()
logging.getLogger("TFC-RPC").setLevel(logging.DEBUG)

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

assert ('win32' in sys.platform), "This code runs on Windows only.";
# print("Python {}".format(getcontext()));

# Read Coin Configuration
coinConfFileName="Freedomcoin.conf";
coinConfFileDefaultPath=Path("{}/Freedomcoin/{}".format(os.getenv("APPDATA"), coinConfFileName));
coinConfFilePath=input("Enter the full file path to your coin config file (e.g. {}): ".format(coinConfFileDefaultPath));
if len(coinConfFilePath.strip()) == 0:
	print("\tTrying default location {}...".format(coinConfFileDefaultPath));
	coinConfFilePath=coinConfFileDefaultPath;

try:
	print("Reading coin configuration file ({})...".format(coinConfFileName));
	configBag={};
	with open(coinConfFilePath, "r") as coinConfigFile:
		for line in coinConfigFile:
			line=line.strip();
			if "=" not in line: continue;
			if line.startswith("#") or line.startswith("//"): continue;
			
			k,v=line.split("=", 1);
			configBag[k]=v;
except:
	print("Failed to read configuration file.");
	print("Unexpected error:", sys.exc_info()[0]);
	raise
			
rpcUser='';
if "rpcuser" in configBag:
	rpcUser=configBag["rpcuser"];
else:
	# raise ValueError("RPC User ('rpcuser') configuration is missing");
	print("\tRPC User ('rpcuser') configuration is missing. Aborting.");
	exit();

rpcPassword='';
if "rpcpassword" in configBag:
	rpcPassword=configBag["rpcpassword"];
else:
	# raise ValueError("RPC Password ('rpcpassword') configuration is missing");
	print("\tRPC Password ('rpcpassword') configuration is missing. Aborting.");
	exit();

rpcPort='';
if "rpcport" in configBag:
	rpcPort=configBag["rpcport"];
else:
	# raise ValueError("RPC Port ('rpcport') configuration is missing");
	print("\tRPC Port ('rpcport') configuration is missing. Aborting.");
	exit();

rpcIP='';
if "rpcip" in configBag:
	rpcIP=configBag["rpcip"];
else:
	# raise ValueError("RPC IP ('rpcip') configuration is missing");
	print("\tRPC IP ('rpcip') configuration is missing. Aborting.");
	exit();

masternodeCollateral='';
if "masternodeCollateral" in configBag:
	masternodeCollateral=Decimal(configBag["masternodeCollateral"]);
else:
	#raise ValueError("Masternode collateral ('masternodeCollateral') configuration is missing");
	print("\tMasternode collateral ('masternodeCollateral') configuration is missing. Aborting.");
	exit();
	
# Setup rpc connection
try:
	print("Setting up node connection to {}...".format(rpcIP));
	rpcConnection = AuthServiceProxy("http://%s:%s@%s:%s"%(rpcUser, rpcPassword, rpcIP, rpcPort));
	print("Getting node information...");
	pprint(rpcConnection.getinfo());
except:
	print("Failed to get node information.");
	print("Unexpected error:", sys.exc_info()[0]);
	raise
	
# pprint(rpcConnection.gettransaction(""));
# pprint(rpcConnection.gettransaction(""));
# pprint(rpcConnection.listunspent(1, 9999999));
# pprint(rpcConnection.decodescript(""));

# Application setup
# Holding addresses
holdingAddressPrefix="holdingAddress";

print();
inputUser=input("Who's wallet do you want to process? (Himesh|Satish) ");
inputUser=inputUser.lower().capitalize();
if (len(inputUser.strip()) > 0):
	print("\tChecking {} configuration for holding account address...".format(coinConfFileName));
	holdingAddressConfigName=holdingAddressPrefix + inputUser;
	if holdingAddressConfigName in configBag:
		holdingWalletAddress=configBag[holdingAddressConfigName];
	else:
		print("\tHolding Address configuration '{}' is missing. Aborting.".format(holdingAddressConfigName));
		exit();

	print("\tFinding account for address {}...".format(holdingWalletAddress));
	holdingWalletName=rpcConnection.getaccount(holdingWalletAddress);
	if (holdingWalletName is not None):
		print("\tCool {}, let's get started. This script will use {} as the holding wallet ({}).".format(inputUser, holdingWalletName, holdingWalletAddress));
	else:
		print("\tFailed to lookup account for user '{}'".format(inputUser));
else:
	print("Unrecognized user '{}'. Aborting.".format(inputUser));
	exit();

print();
print("Processing all node accounts...");
walletAccounts=rpcConnection.listaccounts();
allUnspent=[];
totalUnspentAmount=0;
for account in walletAccounts:
	if len(account.strip()) == 0:
		print("Ignoring unrecognised/invalid address ('{}')!\n".format(account));
		continue;
	else:
		print("Account: {}".format(account));
		
	if account.endswith(inputUser) == False:
		print("\tSkipping account. Doesn't belong to current user.\n");
		# pprint("{} with balance {}".format(account, walletAccounts[account]));
		continue;
	elif account == holdingWalletName:
		print("\tSkipping account. This is the holding address.\n");
	else:
		nodeBalance=walletAccounts[account];
		if nodeBalance > masternodeCollateral:
			unspentList=rpcConnection.listunspent(20, 9999999, rpcConnection.getaddressesbyaccount(account));
			unspentBalance=Decimal(0);
			if len(unspentList) > 0:
				print("\tUnspent list contains {} outs (incl. collateral). Calculating balance without collateral...".format(len(unspentList)));
				# pprint(unspentList);
				for otx in unspentList:
					if otx['amount'] != masternodeCollateral:
						print("\t\tAdding unspent amount of {} TFC.".format(Decimal(otx['amount'])));
						unspentBalance+=Decimal(otx['amount']);
						allUnspent.append(otx);
						totalUnspentAmount+=Decimal(otx['amount']);
				print("\t{} TFC can be moved to holding address.\n".format(unspentBalance));
		elif nodeBalance < masternodeCollateral:
			print("\tWarning! This node address has insufficient collateral ({} vs expected {}).\n".format(nodeBalance, masternodeCollateral));
		else:
			print("\tNothing to see here, keep scrolling.\n");

# Estimate total tx fee using 0.0001 TFC per 1000 bytes which is rougly 6 txns
totalTxFee=(len(allUnspent)/6)*0.00010000;
totalTxFee=round(totalTxFee, 8);
txAmount=round(totalUnspentAmount-Decimal(totalTxFee), 8);
print();
print("Holding wallet name is {} and it has address {}.".format(holdingWalletName, holdingWalletAddress));
acceptTxFeeInput=input("Using {} unspent txns valued at {} TFC will incur a fee of {} TFC. Continue? (y/n) ".format(len(allUnspent), txAmount, totalTxFee))	;
if acceptTxFeeInput.strip().lower() != "y":
	print("Tx not accepted by user. Aborting.");
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
print("Creating tx hash going to address {}...".format(toAddresses));
createTxHex=rpcConnection.createrawtransaction(inputsList, toAddresses);
createTxJson=rpcConnection.decoderawtransaction(createTxHex);
if len(createTxHex.strip()) > 0:
	# pprint(rpcConnection.decodescript(createTxHex));
	# pprint(rpcConnection.decoderawtransaction(createTxHex));
	createTxID=createTxJson["txid"];
	print("\tTX was successfulling created. TxID is: {}".format(createTxID));
else:
	print("\tFailed to create tx. Aborting.");
	exit();

# signrawtransaction <hex string> [{"txid":txid,"vout":n,"scriptPubKey":hex,"redeemScript":hex},...] [<privatekey1>,...] [sighashtype="ALL"]
print();
print("Signing tx...");
signTxResult=rpcConnection.signrawtransaction(createTxHex, inputsWithScriptKeysList);
if signTxResult["complete"] == True:
	print("\tSigning was successful.");
	# pprint(rpcConnection.decodescript(signTxResult["hex"]));
	# pprint(rpcConnection.decoderawtransaction(signTxResult));
else:
	print("\tSigning failed. Aborting.");
	exit();

# sendrawtransaction <hex string>
print();
print("Sending tx...");
sendTxResult=rpcConnection.sendrawtransaction(signTxResult["hex"]);
if len(sendTxResult.strip()) > 0:
	print("\tSend tx result received...");
	print("\tResulting TxID: {}".format(sendTxResult));
else:
	print("\tSend tx result is missing. Aborting.");

print("Total unspent was: {}".format(totalUnspentAmount));
