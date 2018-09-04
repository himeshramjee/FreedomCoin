# FreedomCoin
Learnings and notes on using and operating with TFC [website](https://www.freedom-coin.io/) and/or [portal](https://portal.freedom-coin.io/).

### Notes on setting up a Masternode (Cold Wallet Setup)
Original script used to be located at https://github.com/Realbityoda/FreedomCoin but that account/user has gone awon.

1. Wait till your wallet is up to date/sync'd with the network
1. Generate a new 'Receive' TFC wallet address on your local wallet app
1. send only 5000 TFC to your new address
1. Lookup the 5000TFC tx details that you will need later by going to http://explorer.freedom-coin.io/address/<wallet-id>
1. Lookup the "vout" output index number for your 5000TFC txn by viewing the raw output of your txn http://explorer.freedom-coin.io/api/getrawtransaction?txid=<5000TFC-transaction-id>&decrypt=1
1. Generate and store safely a new masternode key by running 'masternode genkey' on your local wallet app's debug console (Tools->Debug->Console)
1. Buy a server and log onto it via an ssh terminal (https://my.vultr.com/)
1. Download the node installer script (linux only) by executing this command 'curl -O https://raw.githubusercontent.com/himeshramjee/FreedomCoin/master/tfc_install.sh'
1. Execute the script by typing 'bash tfc_install.sh'
1. Paste the masternode key that you generated earlier when the script asks you to specify one (every masternode must have it's own key)
1. Once the script completes, note down any errors and only continue if you see none
1. Execute 'Freedomcoind masternode status' and wait till your node is up to date/sync'd with the network (check the count of blocks and compare to your local wallet)
1. Once your node is in sync go back to your local wallet
1. Click Masternodes tab on left side bar menu
1. Click Create new node button (it's actually just adding a node to your wallet for control, you've already actually created the node)
1. Complete the form (this is where you will need all the info you've looked up thus far)
1. Once added your node status should be "Updating network list"
1. Click Start All and it should change to "Masternode is Running"

### Notes on using tfcNodeManager script
1. Add following to you Freedomcoin.conf file
```
server=1
listen=1
daemon=1
rpcip=127.0.0.1
rpcport=7117
rpcuser=<type-in-random-username>
rpcpassword=<type-in-random-user-password>
rpcallowip=127.0.0.1
enableaccounts=1
staking=0
holdingAddressFooBar=<type-in-TFC-wallet-address>
```
2. You can test RPC calls to your local wallet using curl
```
curl -H "Content-Type: application/json" --data "{\"jsonrpc\":\"2.0\",\"method\":\"getinfo\",\"params\":[],\"id\":67}" http://<rpcuser>:<rpcpassword>@localhost:7117
```
3. Run the scrpt by executing the following in a python shell
```
# When asked "Who's wallet do you want to process?", the name you enter must be one that you've configured above. e.g. 'FooBar'
python tfcNodeManager.py
```
4. To the moon? :)
