#!/usr/bin/env python3
# -*- coding: utf_8 -*-l

import crc16
import struct
import requests
import re
import time
from mypylib.mypylib import *

local = MyPyClass(__file__)

class LiteClient:
	def __init__(self):
		self.appPath = None
		self.configPath = None
		self.pubkeyPath = None
		self.addr = None
		self.ton = None # magic
	#end define

	def Run(self, cmd, **kwargs):
		timeout = kwargs.get("timeout", 3)
		ready = False
		if self.pubkeyPath:
			validatorStatus = self.ton.GetValidatorStatus()
			validatorOutOfSync = validatorStatus.get("outOfSync")
			if validatorOutOfSync < 20:
				args = [self.appPath, "--addr", self.addr, "--pub", self.pubkeyPath, "--verbosity", "0", "--cmd", cmd]
				ready = True
		if ready == False:
			args = [self.appPath, "--global-config", self.configPath, "--verbosity", "0", "--cmd", cmd]
		process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
		output = process.stdout.decode("utf-8")
		err = process.stderr.decode("utf-8")
		if len(err) > 0:
			local.AddLog("args: {args}".format(args=args), "error")
			raise Exception("LiteClient error: {err}".format(err=err))
		return output
	#end define
#end class

class ValidatorConsole:
	def __init__(self):
		self.appPath = None
		self.privKeyPath = None
		self.pubKeyPath = None
		self.addr = None
	#end define

	def Run(self, cmd, **kwargs):
		timeout = kwargs.get("timeout", 3)
		if self.appPath is None or self.privKeyPath is None or self.pubKeyPath is None:
			raise Exception("ValidatorConsole error: Validator console is not settings")
		args = [self.appPath, "-k", self.privKeyPath, "-p", self.pubKeyPath, "-a", self.addr, "-v", "0", "--cmd", cmd]
		process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
		output = process.stdout.decode("utf-8")
		err = process.stderr.decode("utf-8")
		if len(err) > 0:
			local.AddLog("args: {args}".format(args=args), "error")
			raise Exception("ValidatorConsole error: {err}".format(err=err))
		return output
	#end define
#end class

class Fift:
	def __init__(self):
		self.appPath = None
		self.libsPath = None
		self.smartcontsPath = None
	#end define

	def Run(self, args, **kwargs):
		timeout = kwargs.get("timeout", 3)
		for i in range(len(args)):
			args[i] = str(args[i])
		includePath = self.libsPath + ':' + self.smartcontsPath
		args = [self.appPath, "-I", includePath, "-s"] + args
		process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
		output = process.stdout.decode("utf-8")
		err = process.stderr.decode("utf-8")
		if len(err) > 0:
			local.AddLog("args: {args}".format(args=args), "error")
			raise Exception("Fift error: {err}".format(err=err))
		return output
	#end define
#end class

class Miner:
	def __init__(self):
		self.appPath = None
	#end define

	def Run(self, args):
		for i in range(len(args)):
			args[i] = str(args[i])
		args = [self.appPath] + args
		process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		output = process.stdout.decode("utf-8")
		err = process.stderr.decode("utf-8")
		# if len(err) > 0:
		# 	local.AddLog("args: {args}".format(args=args), "error")
		# 	raise Exception("Miner error: {err}".format(err=err))
		return err
	#end define
#end class

class Wallet:
	def __init__(self):
		self.name = None
		self.path = None
		self.addrFilePath = None
		self.privFilePath = None
		self.bocFilePath = None
		self.fullAddr = None
		self.workchain = None
		self.addr_hex = None
		self.addr = None
		self.addr_init = None
		self.oldseqno = None
		self.account = None
		self.subwallet = None
		self.v = None
	#end define

	def Refresh(self):
		buff = self.fullAddr.split(':')
		self.workchain = buff[0]
		self.addr_hex = buff[1]
		self.privFilePath = self.path + ".pk"
		if self.v == "v1":
			self.addrFilePath = self.path + ".addr"
			self.bocFilePath = self.path + "-query.boc"
		elif self.v == "hw":
			self.addrFilePath = self.path + str(self.subwallet) + ".addr"
			self.bocFilePath = self.path + str(self.subwallet) + "-query.boc"
	#end define

	def Delete(self):
		os.remove(self.addrFilePath)
		os.remove(self.privFilePath)
	#end define
#end class

class Account:
	def __init__(self):
		self.addr = None
		self.status = "empty"
		self.balance = 0
		self.lt = None
		self.hash = None
	#end define
#end class

class Domain(dict):
	def __init__(self):
		self["name"] = None
		self["adnlAddr"] = None
		self["walletName"] = None
	#end define
#end class

class MyTonCore():
	def __init__(self):
		self.walletsDir = None
		self.dbFile = None
		self.adnlAddr = None
		self.tempDir = None
		self.validatorWalletName = None
		self.nodeName = None

		self.liteClient = LiteClient()
		self.validatorConsole = ValidatorConsole()
		self.fift = Fift()
		self.miner = Miner()

		local.dbLoad()
		self.Refresh()
		self.Init()
	#end define

	def Init(self):
		# Check all directorys
		os.makedirs(self.walletsDir, exist_ok=True)
	#end define

	def Refresh(self):
		if self.dbFile:
			local.dbLoad(self.dbFile)
		else:
			local.dbLoad()

		if not self.walletsDir:
			self.walletsDir = dir(local.buffer.get("myWorkDir") + "wallets")
		self.tempDir = local.buffer.get("myTempDir")

		self.adnlAddr = local.db.get("adnlAddr")
		self.validatorWalletName = local.db.get("validatorWalletName")
		self.nodeName = local.db.get("nodeName")
		if self.nodeName is None:
			self.nodeName=""
		else:
			self.nodeName = self.nodeName + "_"

		liteClient = local.db.get("liteClient")
		if liteClient is not None:
			self.liteClient.ton = self # magic
			self.liteClient.appPath = liteClient["appPath"]
			self.liteClient.configPath = liteClient["configPath"]
			liteServer = liteClient.get("liteServer")
			if liteServer is not None:
				self.liteClient.pubkeyPath = liteServer["pubkeyPath"]
				self.liteClient.addr = "{0}:{1}".format(liteServer["ip"], liteServer["port"])

		validatorConsole = local.db.get("validatorConsole")
		if validatorConsole is not None:
			self.validatorConsole.appPath = validatorConsole["appPath"]
			self.validatorConsole.privKeyPath = validatorConsole["privKeyPath"]
			self.validatorConsole.pubKeyPath = validatorConsole["pubKeyPath"]
			self.validatorConsole.addr = validatorConsole["addr"]

		fift = local.db.get("fift")
		if fift is not None:
			self.fift.appPath = fift["appPath"]
			self.fift.libsPath = fift["libsPath"]
			self.fift.smartcontsPath = fift["smartcontsPath"]

		miner = local.db.get("miner")
		if miner is not None:
			self.miner.appPath = miner["appPath"]
			# set powAddr "kf8guqdIbY6kpMykR8WFeVGbZcP2iuBagXfnQuq0rGrxgE04"
			# set minerAddr "kQAXRfNYUkFtecUg91zvbUkpy897CDcE2okhFxAlOLcM3_XD"
	#end define

	def GetVarFromWorkerOutput(self, text, search):
		if ':' not in search:
			search += ':'
		if search is None or text is None:
			return None
		if search not in text:
			return None
		start = text.find(search) + len(search)
		count = 0
		bcount = 0
		textLen = len(text)
		end = textLen
		for i in range(start, textLen):
			letter = text[i]
			if letter == '(':
				count += 1
				bcount += 1
			elif letter == ')':
				count -= 1
			if letter == ')' and count < 1:
				end = i + 1
				break
			elif letter == '\n' and count < 1:
				end = i
				break
		result = text[start:end]
		if count != 0 and bcount == 0:
			result = result.replace(')', '')
		return result
	#end define

	def GetSeqno(self, wallet):
		local.AddLog("start GetSeqno function", "debug")
		cmd = "runmethod {addr} seqno".format(addr=wallet.addr)
		result = self.liteClient.Run(cmd)
		if "cannot run any methods" in result:
			return None
		if "result" not in result:
			return 0
		seqno = self.GetVarFromWorkerOutput(result, "result")
		seqno = seqno.replace(' ', '')
		seqno = Pars(seqno, '[', ']')
		seqno = int(seqno)
		return seqno
	#end define

	def GetAccount(self, addr):
		local.AddLog("start GetAccount function", "debug")
		account = Account()
		cmd = "getaccount {addr}".format(addr=addr)
		result = self.liteClient.Run(cmd)
		storage = self.GetVarFromWorkerOutput(result, "storage")
		if storage is None:
			return account
		balance = self.GetVarFromWorkerOutput(storage, "balance")
		grams = self.GetVarFromWorkerOutput(balance, "grams")
		value = self.GetVarFromWorkerOutput(grams, "value")
		state = self.GetVarFromWorkerOutput(storage, "state")
		status = Pars(state, "account_", '\n')
		account.addr = addr
		account.status = status
		account.balance = ng2g(value)
		account.lt = Pars(result, "lt = ", ' ')
		account.hash = Pars(result, "hash = ", '\n')
		return account
	#end define

	def GetAccountHistory(self, account, limit):
		local.AddLog("start GetAccountHistory function", "debug")
		lt=account.lt
		hash=account.hash
		history = list()
		ready = 0
		while True:
			cmd = "lasttrans {addr} {lt} {hash}".format(addr=account.addr, lt=lt, hash=hash)
			result = self.liteClient.Run(cmd)
			buff =  Pars(result, "previous transaction has", '\n')
			lt = Pars(buff, "lt ", ' ')
			hash = Pars(buff, "hash ", ' ')
			arr = result.split("transaction #0")
			for item in arr:
				ready += 1
				if "from block" not in item:
					continue
				if "VALUE:" not in item:
					continue
				block = Pars(item, "from block ", '\n')
				time = Pars(item, "time=", ' ')
				time = int(time)
				outmsg = Pars(item, "outmsg_cnt=", '\n')
				outmsg = int(outmsg)
				if outmsg == 1:
					item = Pars(item, "outbound message")
				buff = dict()
				buff["block"] = block
				buff["time"] = time
				buff["outmsg"] = outmsg
				buff["from"] = Pars(item, "FROM: ", ' ').lower()
				buff["to"] = Pars(item, "TO: ", ' ').lower()
				value = Pars(item, "VALUE:", '\n')
				if '+' in value: # wtf?
					value = value[:value.find('+')] # wtf? `-1:0000000000000000000000000000000000000000000000000000000000000000 1583059577 1200000000+extra`
				buff["value"] = ng2g(value)
				history.append(buff)
			if lt is None or ready >= limit:
				return history
	#end define

	def GetDomainAddr(self, domainName):
		cmd = "dnsresolve {domainName} -1".format(domainName=domainName)
		result = self.liteClient.Run(cmd)
		if "not found" in result:
			raise Exception("GetDomainAddr error: domain \"{domainName}\" not found".format(domainName=domainName))
		resolver = Pars(result, "next resolver", '\n')
		buff = resolver.replace(' ', '')
		buffList = buff.split('=')
		fullHexAddr = buffList[0]
		addr = buffList[1]
		return addr
	#end define

	def GetDomainEndTime(self, domainName):
		local.AddLog("start GetDomainEndTime function", "debug")
		buff = domainName.split('.')
		subdomain = buff.pop(0)
		dnsDomain = ".".join(buff)
		dnsAddr = self.GetDomainAddr(dnsDomain)
		
		cmd = "runmethod {addr} getexpiration \"{subdomain}\"".format(addr=dnsAddr, subdomain=subdomain)
		result = self.liteClient.Run(cmd)
		result = Pars(result, "result:", '\n')
		result = Pars(result, "[", "]")
		result = result.replace(' ', '')
		result = int(result)
		return result
	#end define

	def GetDomainAdnlAddr(self, domainName):
		local.AddLog("start GetDomainAdnlAddr function", "debug")
		cmd = "dnsresolve {domainName} 1".format(domainName=domainName)
		result = self.liteClient.Run(cmd)
		lines = result.split('\n')
		for line in lines:
			if "adnl address" in line:
				adnlAddr = Pars(line, "=", "\n")
				adnlAddr = adnlAddr.replace(' ', '')
				adnlAddr = adnlAddr
				return adnlAddr
	#end define

	def GetLocalWallet(self, walletName, v="v1", subwallet=1):
		local.AddLog("start GetLocalWallet function", "debug")
		if walletName is None:
			return None
		walletPath = self.walletsDir + walletName
		if v == "v1":
			wallet = self.GetWalletFromFile(walletPath)
		elif v == "hw":
			wallet = self.GetHighWalletFromFile(walletPath, subwallet)
		return wallet
	#end define

	def GetWalletFromFile(self, filePath):
		local.AddLog("start GetWalletFromFile function", "debug")
		# Check input args
		if (".addr" in filePath):
			filePath = filePath.replace(".addr", '')
		if (".pk" in filePath):
			filePath = filePath.replace(".pk", '')
		if os.path.isfile(filePath + ".pk") == False:
			raise Exception("GetWalletFromFile error: Private key not found: " + filePath)
		#end if

		# Create wallet object
		wallet = Wallet()
		wallet.v = "v1"
		wallet.path = filePath
		if '/' in filePath:
			wallet.name = filePath[filePath.rfind('/')+1:]
		else:
			wallet.name = filePath
		#end if

		addrFilePath = filePath + ".addr"
		self.AddrFile2Wallet(wallet, addrFilePath)
		return wallet
	#end define

	def GetHighWalletFromFile(self, filePath, subwallet=1):
		local.AddLog("start GetHighWalletFromFile function", "debug")
		# Check input args
		if (".addr" in filePath):
			filePath = filePath.replace(".addr", '')
		if (".pk" in filePath):
			filePath = filePath.replace(".pk", '')
		if os.path.isfile(filePath + ".pk") == False:
			raise Exception("GetHighWalletFromFile error: Private key not found: " + filePath)
		#end if

		# Create wallet
		wallet = Wallet()
		wallet.subwallet = subwallet
		wallet.v = "hw"
		wallet.path = filePath
		if '/' in filePath:
			wallet.name = filePath[filePath.rfind('/')+1:]
		else:
			wallet.name = filePath
		#end if

		addrFilePath = filePath + str(subwallet) + ".addr"
		self.AddrFile2Wallet(wallet, addrFilePath)
		return wallet
	#end define

	def AddrFile2Wallet(self, wallet, addrFilePath):
		#args = ["show-addr.fif", filePath]
		#result = self.fift.Run(args)
		#wallet.fullAddr = Pars(result, "Source wallet address = ", '\n').replace(' ', '')
		#buff = self.GetVarFromWorkerOutput(result, "Bounceable address (for later access)")
		#wallet.addr = buff.replace(' ', '')
		#buff = self.GetVarFromWorkerOutput(result, "Non-bounceable address (for init only)")
		#wallet.addr_init = buff.replace(' ', '')

		file = open(addrFilePath, "rb")
		data = file.read()
		addr_hex = data[:32].hex()
		workchain = struct.unpack("i", data[32:])[0]
		wallet.fullAddr = str(workchain) + ":" + addr_hex
		wallet.addr = self.HexAddr2Base64Addr(wallet.fullAddr)
		wallet.addr_init = self.HexAddr2Base64Addr(wallet.fullAddr, False)
		wallet.Refresh()
	#end define

	def GetFullConfigAddr(self):
		# get buffer
		timestamp = GetTimestamp()
		fullConfigAddr = local.buffer.get("fullConfigAddr")
		fullConfigAddr_time = local.buffer.get("fullConfigAddr_time")
		if fullConfigAddr:
			diffTime = timestamp - fullConfigAddr_time
			if diffTime < 10:
				return fullConfigAddr
		#end if

		local.AddLog("start GetFullConfigAddr function", "debug")
		result = self.liteClient.Run("getconfig 0")
		configAddr_hex = self.GetVarFromWorkerOutput(result, "config_addr:x")
		fullConfigAddr = "-1:{configAddr_hex}".format(configAddr_hex=configAddr_hex)
		local.buffer["fullConfigAddr"] = fullConfigAddr
		local.buffer["fullConfigAddr_time"] = timestamp
		return fullConfigAddr
	#end define

	def GetFullElectorAddr(self):
		# get buffer
		timestamp = GetTimestamp()
		fullElectorAddr = local.buffer.get("fullElectorAddr")
		fullElectorAddr_time = local.buffer.get("fullElectorAddr_time")
		if fullElectorAddr:
			diffTime = timestamp - fullElectorAddr_time
			if diffTime < 10:
				return fullElectorAddr
		#end if

		local.AddLog("start GetFullElectorAddr function", "debug")
		result = self.liteClient.Run("getconfig 1")
		electorAddr_hex = self.GetVarFromWorkerOutput(result, "elector_addr:x")
		fullElectorAddr = "-1:{electorAddr_hex}".format(electorAddr_hex=electorAddr_hex)
		local.buffer["fullElectorAddr"] = fullElectorAddr
		local.buffer["fullElectorAddr_time"] = timestamp
		return fullElectorAddr
	#end define

	def GetFullMinterAddr(self):
		# get buffer
		timestamp = GetTimestamp()
		fullMinterAddr = local.buffer.get("fullMinterAddr")
		fullMinterAddr_time = local.buffer.get("fullMinterAddr_time")
		if fullMinterAddr:
			diffTime = timestamp - fullMinterAddr_time
			if diffTime < 10:
				return fullMinterAddr
		#end if

		local.AddLog("start GetFullMinterAddr function", "debug")
		result = self.liteClient.Run("getconfig 2")
		minterAddr_hex = self.GetVarFromWorkerOutput(result, "minter_addr:x")
		fullMinterAddr = "-1:{minterAddr_hex}".format(minterAddr_hex=minterAddr_hex)
		local.buffer["fullMinterAddr"] = fullMinterAddr
		local.buffer["fullMinterAddr_time"] = timestamp
		return fullMinterAddr
	#end define

	def GetFullDnsRootAddr(self):
		# get buffer
		timestamp = GetTimestamp()
		fullDnsRootAddr = local.buffer.get("fullDnsRootAddr")
		fullDnsRootAddr_time = local.buffer.get("fullDnsRootAddr_time")
		if fullDnsRootAddr:
			diffTime = timestamp - fullDnsRootAddr_time
			if diffTime < 10:
				return fullDnsRootAddr
		#end if

		local.AddLog("start GetFullDnsRootAddr function", "debug")
		result = self.liteClient.Run("getconfig 4")
		dnsRootAddr_hex = self.GetVarFromWorkerOutput(result, "dns_root_addr:x")
		fullDnsRootAddr = "-1:{dnsRootAddr_hex}".format(dnsRootAddr_hex=dnsRootAddr_hex)
		local.buffer["fullDnsRootAddr"] = fullDnsRootAddr
		local.buffer["fullDnsRootAddr_time"] = timestamp
		return fullDnsRootAddr
	#end define

	def GetActiveElectionId(self, fullElectorAddr):
		local.AddLog("start GetActiveElectionId function", "debug")
		cmd = "runmethod {fullElectorAddr} active_election_id".format(fullElectorAddr=fullElectorAddr)
		result = self.liteClient.Run(cmd)
		active_election_id = self.GetVarFromWorkerOutput(result, "result")
		active_election_id = active_election_id.replace(' ', '')
		active_election_id = Pars(active_election_id, '[', ']')
		active_election_id = int(active_election_id)
		return active_election_id
	#end define

	def GetValidatorsElectedFor(self):
		local.AddLog("start GetValidatorsElectedFor function", "debug")
		config15 = self.GetConfig15()
		return config15["validatorsElectedFor"]
	#end define

	def GetMinStake(self):
		local.AddLog("start GetMinStake function", "debug")
		config17 = self.GetConfig17()
		return config17["minStake"]
	#end define

	def GetRootWorkchainEnabledTime(self):
		local.AddLog("start GetRootWorkchainEnabledTime function", "debug")
		config12 = self.GetConfig12()
		result = config12["workchains"]["root"]["enabledSince"]
		return result
	#end define

	def GetTotalValidators(self):
		local.AddLog("start GetTotalValidators function", "debug")
		config34 = self.GetConfig34()
		result = config34["totalValidators"]
		return result
	#end define

	def GetLastBlock(self):
		block = None
		cmd = "last"
		result = self.liteClient.Run(cmd)
		lines = result.split('\n')
		for line in lines:
			if "latest masterchain block" in line:
				buff = line.split(' ')
				block = buff[7]
				break
		return block
	#end define

	def GetTransactions(self, block):
		transactions = list()
		cmd = "listblocktrans {block} 999".format(block=block)
		result = self.liteClient.Run(cmd)
		lines = result.split('\n')
		for line in lines:
			if "transaction #" in line:
				buff = line.split(' ')
				trans_id = buff[1]
				trans_id = trans_id.replace('#', '')
				trans_id = trans_id.replace(':', '')
				trans_account = buff[3]
				trans_lt = buff[5]
				trans_hash = buff[7]
				trans = {"id": trans_id, "account": trans_account, "lt": trans_lt, "hash": trans_hash}
				transactions.append(trans)
		return transactions
	#end define

	def GetTrans(self, block, addr, lt):
		cmd = "dumptrans {block} {addr} {lt}".format(block=block, addr=addr, lt=lt)
		result = self.liteClient.Run(cmd)
		if "transaction is" not in result:
			return None
		#end if

		in_msg = self.GetVarFromWorkerOutput(result, "in_msg")
		ihr_disabled = Pars(in_msg, "ihr_disabled:", ' ')
		bounce = Pars(in_msg, "bounce:", ' ')
		bounced = Pars(in_msg, "bounced:", '\n')
		src_buff = self.GetVarFromWorkerOutput(in_msg, "src")
		src_buff2 = self.GetVarFromWorkerOutput(src_buff, "address")
		src = xhex2hex(src_buff2)
		dest_buff = self.GetVarFromWorkerOutput(in_msg, "dest")
		dest_buff2 = self.GetVarFromWorkerOutput(dest_buff, "address")
		dest = xhex2hex(dest_buff2)
		value_buff = self.GetVarFromWorkerOutput(in_msg, "value")
		grams_buff = self.GetVarFromWorkerOutput(value_buff, "grams")
		ngrams = self.GetVarFromWorkerOutput(grams_buff, "value")
		if ngrams is None:
			grams = None
		else:
			grams = ng2g(ngrams)
		ihr_fee_buff = self.GetVarFromWorkerOutput(in_msg, "ihr_fee")
		ihr_fee = self.GetVarFromWorkerOutput(ihr_fee_buff, "value")
		fwd_fee_buff = self.GetVarFromWorkerOutput(in_msg, "fwd_fee")
		fwd_fee = self.GetVarFromWorkerOutput(fwd_fee_buff, "value")
		body_buff = self.GetVarFromWorkerOutput(in_msg, "body")
		body_buff2 = self.GetVarFromWorkerOutput(body_buff, "value")
		body = Pars(body_buff2, '{', '}')
		comment = hex2str(body)

		total_fees_buff = self.GetVarFromWorkerOutput(result, "total_fees")
		total_fees = self.GetVarFromWorkerOutput(total_fees_buff, "value")
		storage_ph_buff = self.GetVarFromWorkerOutput(result, "storage_ph")
		storage_ph_buff2 = self.GetVarFromWorkerOutput(storage_ph_buff, "value")
		storage_ph = self.GetVarFromWorkerOutput(storage_ph_buff2, "value")
		credit_ph_buff = self.GetVarFromWorkerOutput(result, "credit_ph")
		credit_ph_buff2 = self.GetVarFromWorkerOutput(credit_ph_buff, "value")
		credit_ph = self.GetVarFromWorkerOutput(credit_ph_buff2, "value")
		compute_ph = self.GetVarFromWorkerOutput(result, "compute_ph")
		gas_fees_buff = self.GetVarFromWorkerOutput(compute_ph, "gas_fees")
		gas_fees = self.GetVarFromWorkerOutput(gas_fees_buff, "value")
		gas_used_buff = self.GetVarFromWorkerOutput(compute_ph, "gas_used")
		gas_used = self.GetVarFromWorkerOutput(gas_used_buff, "value")
		gas_limit_buff = self.GetVarFromWorkerOutput(compute_ph, "gas_limit")
		gas_limit = self.GetVarFromWorkerOutput(gas_limit_buff, "value")
		vm_init_state_hash_buff = Pars(result, "vm_init_state_hash:", ' ')
		vm_init_state_hash = xhex2hex(vm_init_state_hash_buff)
		vm_final_state_hash_buff = Pars(result, "vm_final_state_hash:", ')')
		vm_final_state_hash = xhex2hex(vm_final_state_hash_buff)
		action_list_hash_buff = Pars(result, "action_list_hash:", '\n')
		action_list_hash = xhex2hex(action_list_hash_buff)

		output = dict()
		output["ihr_disabled"] = ihr_disabled
		output["bounce"] = bounce
		output["bounced"] = bounced
		output["src"] = src
		output["dest"] = dest
		output["value"] = grams
		output["body"] = body
		output["comment"] = comment
		output["ihr_fee"] = ihr_fee
		output["fwd_fee"] = fwd_fee
		output["total_fees"] = total_fees
		output["storage_ph"] = storage_ph
		output["credit_ph"] = credit_ph
		output["gas_used"] = gas_used
		output["vm_init_state_hash"] = vm_init_state_hash
		output["vm_final_state_hash"] = vm_final_state_hash
		output["action_list_hash"] = action_list_hash

		return output
	#end define

	def GetTransactionsNumber(self, block):
		transactions = self.GetTransactions(block)
		transNum = len(transactions)
		return transNum
	#end define

	def GetShards(self, block=None):
		shards = list()
		if block:
			cmd = "allshards {block}".format(block=block)
		else:
			cmd = "allshards"
		result = self.liteClient.Run(cmd)
		lines = result.split('\n')
		for line in lines:
			if "shard #" in line:
				buff = line.split(' ')
				shard_id = buff[1]
				shard_id = shard_id.replace('#', '')
				shard_block = buff[3]
				shard = {"id": shard_id, "block": shard_block}
				shards.append(shard)
		return shards
	#end define

	def GetShardsNumber(self, block=None):
		shards = self.GetShards(block)
		shardsNum = len(shards)
		return shardsNum
	#end define

	def GetValidatorStatus(self):
		# get buffer
		timestamp = GetTimestamp()
		validatorStatus = local.buffer.get("validatorStatus")
		if validatorStatus:
			diffTime = timestamp - validatorStatus.get("unixtime")
			if diffTime < 10:
				return validatorStatus
		#end if

		# local.AddLog("start GetValidatorStatus function", "debug")
		validatorStatus = dict()
		try:
			validatorStatus["isWorking"] = True
			result = self.validatorConsole.Run("getstats")
			validatorStatus["unixtime"] = int(Pars(result, "unixtime", '\n'))
			validatorStatus["masterchainblocktime"] = int(Pars(result, "masterchainblocktime", '\n'))
			validatorStatus["stateserializermasterchainseqno"] = int(Pars(result, "stateserializermasterchainseqno", '\n'))
			validatorStatus["shardclientmasterchainseqno"] = int(Pars(result, "shardclientmasterchainseqno", '\n'))
			buff = Pars(result, "masterchainblock", '\n')
			validatorStatus["masterchainblock"] = self.GVS_GetItemFromBuff(buff)
			buff = Pars(result, "gcmasterchainblock", '\n')
			validatorStatus["gcmasterchainblock"] = self.GVS_GetItemFromBuff(buff)
			buff = Pars(result, "keymasterchainblock", '\n')
			validatorStatus["keymasterchainblock"] = self.GVS_GetItemFromBuff(buff)
			buff = Pars(result, "rotatemasterchainblock", '\n')
			validatorStatus["rotatemasterchainblock"] = self.GVS_GetItemFromBuff(buff)
			validatorStatus["transNum"] = local.buffer.get("transNum", -1)
			validatorStatus["blocksNum"] = local.buffer.get("blocksNum", -1)
			validatorStatus["masterBlocksNum"] = local.buffer.get("masterBlocksNum", -1)
		except:
			validatorStatus["isWorking"] = False
			validatorStatus["unixtime"] = timestamp
			validatorStatus["masterchainblocktime"] = 0
		validatorStatus["outOfSync"] = validatorStatus["unixtime"] - validatorStatus["masterchainblocktime"]
		local.buffer["validatorStatus"] = validatorStatus # set buffer
		return validatorStatus
	#end define
	
	def GVS_GetItemFromBuff(self, buff):
		buffList = buff.split(':')
		buff2 = buffList[0]
		buff2 = buff2.replace(' ', '')
		buff2 = buff2.replace('(', '')
		buff2 = buff2.replace(')', '')
		buffList2 = buff2.split(',')
		item = buffList2[2]
		item = int(item)
		return item
	#end define

	def GetConfig12(self):
		# get buffer
		timestamp = GetTimestamp()
		config12 = local.buffer.get("config12")
		if config12:
			diffTime = timestamp - config12.get("timestamp")
			if diffTime < 10:
				return config12
		#end if

		local.AddLog("start GetConfig12 function", "debug")
		config12 = dict()
		config12["timestamp"] = timestamp
		config12["workchains"] = dict()
		config12["workchains"]["root"] = dict()
		result = self.liteClient.Run("getconfig 12")
		workchains = self.GetVarFromWorkerOutput(result, "workchains")
		workchain_root = self.GetVarFromWorkerOutput(workchains, "root")
		config12["workchains"]["root"]["enabledSince"] = int(Pars(workchain_root, "enabled_since:", ' '))
		local.buffer["config12"] = config12 # set buffer
		return config12
	#end define

	def GetConfig15(self):
		# get buffer
		timestamp = GetTimestamp()
		config15 = local.buffer.get("config15")
		if config15:
			diffTime = timestamp - config15.get("timestamp")
			if diffTime < 10:
				return config15
		#end if

		local.AddLog("start GetConfig15 function", "debug")
		config15 = dict()
		config15["timestamp"] = timestamp
		result = self.liteClient.Run("getconfig 15")
		config15["validatorsElectedFor"] = int(Pars(result, "validators_elected_for:", ' '))
		config15["electionsStartBefore"] = int(Pars(result, "elections_start_before:", ' '))
		config15["electionsEndBefore"] = int(Pars(result, "elections_end_before:", ' '))
		config15["stakeHeldFor"] = int(Pars(result, "stake_held_for:", ')'))
		local.buffer["config15"] = config15 # set buffer
		return config15
	#end define

	def GetConfig17(self):
		# get buffer
		timestamp = GetTimestamp()
		config17 = local.buffer.get("config17")
		if config17:
			diffTime = timestamp - config17.get("timestamp")
			if diffTime < 10:
				return config17
		#end if

		local.AddLog("start GetConfig17 function", "debug")
		config17 = dict()
		config17["timestamp"] = timestamp
		result = self.liteClient.Run("getconfig 17")
		minStake = self.GetVarFromWorkerOutput(result, "min_stake")
		minStake = self.GetVarFromWorkerOutput(minStake, "value")
		config17["minStake"] = ng2g(minStake)
		maxStake = self.GetVarFromWorkerOutput(result, "max_stake")
		maxStake = self.GetVarFromWorkerOutput(maxStake, "value")
		config17["maxStake"] = ng2g(maxStake)
		maxStakeFactor = self.GetVarFromWorkerOutput(result, "max_stake_factor")
		config17["maxStakeFactor"] = maxStakeFactor
		local.buffer["config17"] = config17 # set buffer
		return config17
	#end define

	def GetConfig32(self):
		# get buffer
		timestamp = GetTimestamp()
		config32 = local.buffer.get("config32")
		if config32:
			diffTime = timestamp - config32.get("timestamp")
			if diffTime < 10:
				return config32
		#end if

		local.AddLog("start GetConfig32 function", "debug")
		config32 = dict()
		config32["timestamp"] = timestamp
		result = self.liteClient.Run("getconfig 32")
		config32["totalValidators"] = int(Pars(result, "total:", ' '))
		config32["startWorkTime"] = int(Pars(result, "utime_since:", ' '))
		config32["endWorkTime"] = int(Pars(result, "utime_until:", ' '))
		lines = result.split('\n')
		validators = list()
		for line in lines:
			if "public_key:" in line:
				validatorAdnlAddr = Pars(line, "adnl_addr:x", ')')
				validatorPubkey = Pars(line, "pubkey:x", ')')
				if config32["totalValidators"] > 1:
					validatorWeight = int(Pars(line, "weight:", ' '))
				else:
					validatorWeight = int(Pars(line, "weight:", ')'))
				buff = dict()
				buff["adnlAddr"] = validatorAdnlAddr
				buff["pubkey"] = validatorPubkey
				buff["weight"] = validatorWeight
				validators.append(buff)
		config32["validators"] = validators
		local.buffer["config32"] = config32 # set buffer
		return config32
	#end define

	def GetConfig34(self):
		# get buffer
		timestamp = GetTimestamp()
		config34 = local.buffer.get("config34")
		if config34:
			diffTime = timestamp - config34.get("timestamp")
			if diffTime < 10:
				return config34
		#end if

		local.AddLog("start GetConfig34 function", "debug")
		config34 = dict()
		config34["timestamp"] = timestamp
		result = self.liteClient.Run("getconfig 34")
		config34["totalValidators"] = int(Pars(result, "total:", ' '))
		config34["startWorkTime"] = int(Pars(result, "utime_since:", ' '))
		config34["endWorkTime"] = int(Pars(result, "utime_until:", ' '))
		lines = result.split('\n')
		validators = list()
		for line in lines:
			if "public_key:" in line:
				validatorAdnlAddr = Pars(line, "adnl_addr:x", ')')
				validatorPubkey = Pars(line, "pubkey:x", ')')
				if config34["totalValidators"] > 1:
					validatorWeight = int(Pars(line, "weight:", ' '))
				else:
					validatorWeight = int(Pars(line, "weight:", ')'))
				buff = dict()
				buff["adnlAddr"] = validatorAdnlAddr
				buff["pubkey"] = validatorPubkey
				buff["weight"] = validatorWeight
				validators.append(buff)
		config34["validators"] = validators
		local.buffer["config34"] = config34 # set buffer
		return config34
	#end define
	
	def GetConfig36(self):
		# get buffer
		timestamp = GetTimestamp()
		config36 = local.buffer.get("config36")
		if config36:
			diffTime = timestamp - config36.get("timestamp")
			if diffTime < 10:
				return config36
		#end if

		local.AddLog("start GetConfig36 function", "debug")
		config36 = dict()
		config36["timestamp"] = timestamp
		try:
			result = self.liteClient.Run("getconfig 36")
			config36["totalValidators"] = int(Pars(result, "total:", ' '))
			config36["startWorkTime"] = int(Pars(result, "utime_since:", ' '))
			config36["endWorkTime"] = int(Pars(result, "utime_until:", ' '))
			lines = result.split('\n')
			validators = list()
			for line in lines:
				if "public_key:" in line:
					validatorAdnlAddr = Pars(line, "adnl_addr:x", ')')
					validatorPubkey = Pars(line, "pubkey:x", ')')
					validatorWeight = Pars(line, "weight:", ' ')
					buff = dict()
					buff["adnlAddr"] = validatorAdnlAddr
					buff["pubkey"] = validatorPubkey
					buff["weight"] = validatorWeight
					validators.append(buff)
			config36["validators"] = validators
		except:
			config36["validators"] = list()
		local.buffer["config36"] = config36 # set buffer
		return config36
	#end define

	def GetPowParams(self, powAddr):
		local.AddLog("start GetPowParams function", "debug")
		params = dict()
		cmd = "runmethod  {addr} get_pow_params".format(addr=powAddr)
		result = self.liteClient.Run(cmd)
		data = self.Result2List(result)
		params["seed"] = data[0]
		params["complexity"] = data[1]
		params["iterations"] = data[2]
		return params
	#end define

	def CreatNewKey(self):
		local.AddLog("start CreatNewKey function", "debug")
		result = self.validatorConsole.Run("newkey")
		key = Pars(result, "created new key ", '\n')
		return key
	#end define

	def GetPubKeyBase64(self, key):
		local.AddLog("start GetPubKeyBase64 function", "debug")
		result = self.validatorConsole.Run("exportpub " + key)
		validatorPubkey_b64 = Pars(result, "got public key: ", '\n')
		return validatorPubkey_b64
	#end define

	def AddKeyToValidator(self, key, startWorkTime, endWorkTime):
		local.AddLog("start AddKeyToValidator function", "debug")
		output = False
		cmd = "addpermkey {key} {startWorkTime} {endWorkTime}".format(key=key, startWorkTime=startWorkTime, endWorkTime=endWorkTime)
		result = self.validatorConsole.Run(cmd)
		if ("success" in result):
			output = True
		return output
	#end define

	def AddKeyToTemp(self, key, endWorkTime):
		local.AddLog("start AddKeyToTemp function", "debug")
		output = False
		result = self.validatorConsole.Run("addtempkey {key} {key} {endWorkTime}".format(key=key, endWorkTime=endWorkTime))
		if ("success" in result):
			output = True
		return output
	#end define

	def AddAdnlAddrToValidator(self, adnlAddr):
		local.AddLog("start AddAdnlAddrToValidator function", "debug")
		output = False
		result = self.validatorConsole.Run("addadnl {adnlAddr} 0".format(adnlAddr=adnlAddr))
		if ("success" in result):
			output = True
		return output
	#end define

	def GetAdnlAddr(self):
		local.AddLog("start GetAdnlAddr function", "debug")
		adnlAddr = self.adnlAddr
		return adnlAddr
	#end define

	def AttachAdnlAddrToValidator(self, adnlAddr, key, endWorkTime):
		local.AddLog("start AttachAdnlAddrToValidator function", "debug")
		output = False
		result = self.validatorConsole.Run("addvalidatoraddr {key} {adnlAddr} {endWorkTime}".format(adnlAddr=adnlAddr, key=key, endWorkTime=endWorkTime))
		if ("success" in result):
			output = True
		return output
	#end define
	
	def CreateConfigProposalRequest(self, offerHash, validatorIndex):
		local.AddLog("start CreateConfigProposalRequest function", "debug")
		fileName = self.tempDir + self.nodeName + "proposal_validator-to-sign.req"
		args = ["config-proposal-vote-req.fif", "-i", validatorIndex, offerHash]
		result = self.fift.Run(args)
		fileName = Pars(result, "Saved to file ", '\n')
		resultList = result.split('\n')
		i = 0
		start_index = 0
		for item in resultList:
			if "Creating a request to vote for configuration proposal" in item:
				start_index = i
			i += 1
		var1 = resultList[start_index + 1]
		var2 = resultList[start_index + 2] # var2 not using
		return var1
	#end define

	def CreateComplaintRequest(self, electionId , complaintHash, validatorIndex):
		local.AddLog("start CreateComplaintRequest function", "debug")
		fileName = self.tempDir + "complaint_validator-to-sign.req"
		args = ["complaint-vote-req.fif", validatorIndex, electionId, complaintHash, fileName]
		result = self.fift.Run(args)
		fileName = Pars(result, "Saved to file ", '\n')
		resultList = result.split('\n')
		i = 0
		start_index = 0
		for item in resultList:
			if "Creating a request to vote for complaint" in item:
				start_index = i
			i += 1
		var1 = resultList[start_index + 1]
		var2 = resultList[start_index + 2] # var2 not using
		return var1
	#end define

	def PrepareComplaint(self, electionId, inputFileName):
		local.AddLog("start PrepareComplaint function", "debug")
		fileName = self.tempDir + "complaint-msg-body.boc"
		args = ["envelope-complaint.fif", electionId, inputFileName, fileName]
		result = self.fift.Run(args)
		fileName = Pars(result, "Saved to file ", ')')
		return fileName
	#end define

	def CreateElectionRequest(self, wallet, startWorkTime, adnlAddr, maxFactor):
		local.AddLog("start CreateElectionRequest function", "debug")
		fileName = self.tempDir + self.nodeName + str(startWorkTime) + "_validator-to-sign.bin"
		args = ["validator-elect-req.fif", wallet.addr, startWorkTime, maxFactor, adnlAddr, fileName]
		result = self.fift.Run(args)
		fileName = Pars(result, "Saved to file ", '\n')
		resultList = result.split('\n')
		i = 0
		start_index = 0
		for item in resultList:
			if "Creating a request to participate in validator elections" in item:
				start_index = i
			i += 1
		var1 = resultList[start_index + 1]
		var2 = resultList[start_index + 2] # var2 not using
		return var1
	#end define

	def GetValidatorSignature(self, validatorKey, var1):
		local.AddLog("start GetValidatorSignature function", "debug")
		cmd = "sign {validatorKey} {var1}".format(validatorKey=validatorKey, var1=var1)
		result = self.validatorConsole.Run(cmd)
		validatorSignature = Pars(result, "got signature ", '\n')
		return validatorSignature
	#end define

	def SignElectionRequestWithValidator(self, wallet, startWorkTime, adnlAddr, validatorPubkey_b64, validatorSignature, maxFactor):
		local.AddLog("start SignElectionRequestWithValidator function", "debug")
		fileName = self.tempDir + self.nodeName + str(startWorkTime) + "_validator-query.boc"
		args = ["validator-elect-signed.fif", wallet.addr, startWorkTime, maxFactor, adnlAddr, validatorPubkey_b64, validatorSignature, fileName]
		result = self.fift.Run(args)
		validatorPubkey = Pars(result, "validator public key ", '\n')
		fileName = Pars(result, "Saved to file ", '\n')
		return validatorPubkey, fileName
	#end define

	def SignFileWithWallet(self, wallet, filePath, addr, gram):
		local.AddLog("start SignFileWithWallet function", "debug")
		seqno = self.GetSeqno(wallet)
		resultFilePath = self.tempDir + self.nodeName + wallet.name + "_wallet-query"
		args = ["wallet.fif", wallet.path, addr, seqno, gram, "-B", filePath, resultFilePath]
		result = self.fift.Run(args)
		resultFilePath = Pars(result, "Saved to file ", ")")
		return resultFilePath
	#end define

	def SendFile(self, filePath, wallet=None, **kwargs):
		local.AddLog("start SendFile function: " + filePath, "debug")
		wait = kwargs.get("wait", True)
		if not os.path.isfile(filePath):
			raise Exception("SendFile error: no such file '{filePath}'".format(filePath=filePath))
		if wait and wallet:
			wallet.oldseqno = self.GetSeqno(wallet)
		result = self.liteClient.Run("sendfile " + filePath)
		if wait and wallet:
			self.WaitTransaction(wallet)
		os.remove(filePath)
	#end define
	
	def WaitTransaction(self, wallet, ex=True):
		local.AddLog("start WaitTransaction function", "debug")
		for i in range(10): # wait 30 sec
			time.sleep(3)
			seqno = self.GetSeqno(wallet)
			if seqno != wallet.oldseqno:
				return
		if ex:
			raise Exception("WaitTransaction error: time out")
	#end define

	def GetReturnedStake(self, fullElectorAddr, wallet):
		local.AddLog("start GetReturnedStake function", "debug")
		cmd = "runmethod {fullElectorAddr} compute_returned_stake 0x{addr_hex}".format(fullElectorAddr=fullElectorAddr, addr_hex=wallet.addr_hex)
		result = self.liteClient.Run(cmd)
		returnedStake = self.GetVarFromWorkerOutput(result, "result")
		returnedStake = returnedStake.replace(' ', '')
		returnedStake = Pars(returnedStake, '[', ']')
		returnedStake = ng2g(returnedStake)
		return returnedStake
	#end define

	def RecoverStake(self):
		local.AddLog("start RecoverStake function", "debug")
		resultFilePath = self.tempDir + self.nodeName + "recover-query"
		args = ["recover-stake.fif", resultFilePath]
		result = self.fift.Run(args)
		resultFilePath = Pars(result, "Saved to file ", '\n')
		return resultFilePath
	#end define
	
	def GetStake(self, account, validators, args=None):
		stake = local.db.get("stake")
		stakePercent = local.db.get("stakePercent", 99)

		# Check if optional arguments have been passed to us
		if args:
			desiredStake = args[0]
			m = re.match(r"(\d+\.?\d?)\%", desiredStake)
			if m:
				# Stake was in percent
				stake = round((account.balance / 100) * float(m.group(1)))
			elif desiredStake.isnumeric():
				# Stake was a number
				stake = int(desiredStake)
			else:
				local.AddLog("Specified stake must be a percentage or whole number", "error")
				return

			# Limit stake to maximum available amount minus 10 (for transaction fees)
			if stake > account.balance - 10:
				stake = account.balance - 10

			if minStake > stake:
				local.AddLog('Stake is smaller then Minimum stake: ' + str(minStake), "error")
				return
		#end if

		if stake is None:
			sp = stakePercent / 100
			if sp > 1 or sp < 0:
				local.AddLog("Wrong stakePercent value. Using default stake.", "warning")
			elif len(validators) == 0:
				stake = int(account.balance*sp/2)
			elif len(validators) > 0:
				stake = int(account.balance*sp)
		return stake
	#end define

	def ElectionEntry(self, args=None):
		local.AddLog("start ElectionEntry function", "debug")
		walletName = self.validatorWalletName
		wallet = self.GetLocalWallet(walletName)

		# Check if validator is not synchronized
		validatorStatus = self.GetValidatorStatus()
		validatorOutOfSync = validatorStatus.get("outOfSync")
		if validatorOutOfSync > 60:
			local.AddLog("Validator is not synchronized", "error")
			return
		#end if

		# Get startWorkTime and endWorkTime
		fullElectorAddr = self.GetFullElectorAddr()
		startWorkTime = self.GetActiveElectionId(fullElectorAddr)

		# Check if elections started
		if (startWorkTime == 0):
			local.AddLog("Elections have not yet begun", "info")
			return
		#end if

		# Check wether it is too early to participate
		if "participateBeforeEnd" in local.db:
			now = time.time()
			if (startWorkTime - now) > local.db["participateBeforeEnd"] and \
			   (now + local.db["periods"]["elections"]) < startWorkTime:
				return
		#end if

		# Check if election entry is completed
		vconfig = self.GetConfigFromValidator()
		validators = vconfig.get("validators")
		for item in validators:
			if item.get("election_date") == startWorkTime:
				local.AddLog("Elections entry already completed", "info")
				return
		#end for

		# Get account balance and minimum stake
		account = self.GetAccount(wallet.addr)
		minStake = self.GetMinStake()
		
		# Calculate stake
		stake = self.GetStake(account, validators, args)

		# Get rateMultiplier
		rateMultiplier = 1
		if args and len(args) > 1:
			rateMultiplier = float(args[1])
		#end if
		
		# Check if we have enough grams
		balance = account.balance
		if minStake > stake:
			text = "You don't have enough grams. Minimum stake: {minStake}".format(minStake=minStake)
			local.AddLog(text, "error")
			return
		if stake > balance:
			text = "You don't have enough grams. stake: {stake}, wallet balance: {balance}".format(stake=stake, balance=balance)
			local.AddLog(text, "error")
			return
		#end if

		# Calculate endWorkTime
		validatorsElectedFor = self.GetValidatorsElectedFor()
		endWorkTime = startWorkTime + validatorsElectedFor + 300 # 300 sec - margin of seconds

		# Create keys
		validatorKey = self.CreatNewKey()
		validatorPubkey_b64  = self.GetPubKeyBase64(validatorKey)

		# Add key to validator
		self.AddKeyToValidator(validatorKey, startWorkTime, endWorkTime)
		self.AddKeyToTemp(validatorKey, endWorkTime)

		# Get ADNL address
		adnlAddr = self.GetAdnlAddr()
		self.AttachAdnlAddrToValidator(adnlAddr, validatorKey, endWorkTime)

		# Create fift's
		config15 = self.GetConfig15()
		config17 = self.GetConfig17()
		# maxFactor = round((stake / minStake) * rateMultiplier, 1)
		maxFactor = round((config17["maxStakeFactor"] / config15["validatorsElectedFor"]) * rateMultiplier, 1)
		var1 = self.CreateElectionRequest(wallet, startWorkTime, adnlAddr, maxFactor)
		validatorSignature = self.GetValidatorSignature(validatorKey, var1)
		validatorPubkey, resultFilePath = self.SignElectionRequestWithValidator(wallet, startWorkTime, adnlAddr, validatorPubkey_b64, validatorSignature, maxFactor)

		# Send boc file to TON
		resultFilePath = self.SignFileWithWallet(wallet, resultFilePath, fullElectorAddr, stake)
		self.SendFile(resultFilePath, wallet)

		# Save vars to json file
		self.SaveElectionVarsToJsonFile(wallet=wallet, account=account, stake=stake, maxFactor=maxFactor, fullElectorAddr=fullElectorAddr, startWorkTime=startWorkTime, validatorsElectedFor=validatorsElectedFor, endWorkTime=endWorkTime, validatorKey=validatorKey, validatorPubkey_b64=validatorPubkey_b64, adnlAddr=adnlAddr, var1=var1, validatorSignature=validatorSignature, validatorPubkey=validatorPubkey)

		# Check is election entries successful and clear key if not ok
		# self.validatorConsole.Run("delpermkey {validatorKey}".format(validatorKey=validatorKey))
		
		local.AddLog("ElectionEntry completed. Start work time: " + str(startWorkTime))
	#end define

	def ReturnStake(self):
		local.AddLog("start ReturnStake function", "debug")
		#self.TestReturnStake()
		fullElectorAddr = self.GetFullElectorAddr()
		walletName = self.validatorWalletName
		wallet = self.GetLocalWallet(walletName)
		returnedStake = self.GetReturnedStake(fullElectorAddr, wallet)
		if returnedStake == 0:
			local.AddLog("You have nothing on the return stake", "debug")
			return
		resultFilePath = self.RecoverStake()
		resultFilePath = self.SignFileWithWallet(wallet, resultFilePath, fullElectorAddr, 1)
		self.SendFile(resultFilePath, wallet)
		local.AddLog("ReturnStake completed")
	#end define

	def SaveElectionVarsToJsonFile(self, **kwargs):
		local.AddLog("start SaveElectionVarsToJsonFile function", "debug")
		fileName = self.tempDir + self.nodeName + str(kwargs.get("startWorkTime")) + "_ElectionEntry.json"
		wallet = kwargs.get("wallet")
		account = kwargs.get("account")
		arr = {"wallet":wallet.__dict__, "account":account.__dict__}
		del kwargs["wallet"]
		del kwargs["account"]
		arr.update(kwargs)
		string = json.dumps(arr, indent=4)
		file = open(fileName, 'w')
		file.write(string)
		file.close()
	#ned define

	def CreateWallet(self, name, workchain=0):
		local.AddLog("start CreateWallet function", "debug")
		walletPath = self.walletsDir + name
		if os.path.isfile(walletPath + ".pk"):
			local.AddLog("CreateWallet error: Wallet already exists: " + name, "warning")
		else:
			args = ["new-wallet.fif", workchain, walletPath]
			result = self.fift.Run(args)
			if "Creating new wallet" not in result:
				raise Exception("CreateWallet error")
			#end if
		wallet = self.GetLocalWallet(name)
		return wallet
	#end define

	def CreateHighWallet(self, name, subwallet=1, workchain=0):
		local.AddLog("start CreateWallet function", "debug")
		walletPath = self.walletsDir + name
		if os.path.isfile(walletPath + ".pk") and os.path.isfile(walletPath + str(subwallet) + ".addr"):
			local.AddLog("CreateHighWallet error: Wallet already exists: " + name + str(subwallet), "warning")
		else:
			args = ["new-highload-wallet.fif", workchain, subwallet, walletPath]
			result = self.fift.Run(args)
			if "Creating new high-load wallet" not in result:
				raise Exception("CreateHighWallet error")
			#end if
		hwallet = self.GetLocalWallet(name, "hw", subwallet)
		return hwallet
	#end define

	def GetWalletsNameList(self):
		local.AddLog("start GetWalletsNameList function", "debug")
		walletsNameList = list()
		for fileName in os.listdir(self.walletsDir):
			if fileName.endswith(".addr"):
				fileName = fileName[:fileName.rfind('.')]
				pkFileName = self.walletsDir + fileName + ".pk"
				if os.path.isfile(pkFileName):
					walletsNameList.append(fileName)
		walletsNameList.sort()
		return walletsNameList
	#end define

	def GetWallets(self):
		local.AddLog("start GetWallets function", "debug")
		wallets = list()
		walletsNameList = self.GetWalletsNameList()
		for walletName in walletsNameList:
			wallet = self.GetLocalWallet(walletName)
			wallets.append(wallet)
		return wallets
	#end define

	def GenerateWalletName(self):
		local.AddLog("start GenerateWalletName function", "debug")
		index = 1
		index_str = str(index).rjust(3, '0')
		walletPrefix = "wallet_"
		indexList = list()
		walletName = walletPrefix + index_str
		walletsNameList = self.GetWalletsNameList()
		if walletName in walletsNameList:
			for item in walletsNameList:
				if item.startswith(walletPrefix):
					try:
						index = item[item.rfind('_')+1:]
						index = int(index)
						indexList.append(index)
					except: pass
			index = max(indexList) + 1
			index_str = str(index).rjust(3, '0')
			walletName = walletPrefix + index_str
		return walletName
	#end define

	def WalletsCheck(self):
		local.AddLog("start WalletsCheck function", "debug")
		wallets = self.GetWallets()
		for wallet in wallets:
			if os.path.isfile(wallet.bocFilePath):
				account = self.GetAccount(wallet.addr)
				if account.balance > 0:
					self.SendFile(wallet.bocFilePath, wallet)
	#end define

	def GetConfigFromValidator(self):
		local.AddLog("start GetConfigFromValidator function", "debug")
		result = self.validatorConsole.Run("getconfig")
		string = Pars(result, "---------", "--------")
		vconfig = json.loads(string)
		return vconfig
	#end define

	def MoveGrams(self, wallet, dest, grams, **kwargs):
		local.AddLog("start MoveGrams function", "debug")
		flags = kwargs.get("flags")
		wait = kwargs.get("wait", True)
		if grams == "all":
			mode = 130
			grams = 0
		elif grams == "alld":
			mode = 160
			grams = 0
		else:
			mode = 3
		seqno = self.GetSeqno(wallet)
		resultFilePath = local.buffer.get("myTempDir") + wallet.name + "_wallet-query"
		args = ["wallet.fif", wallet.path, dest, seqno, grams, "-m", mode, resultFilePath]
		if flags:
			args += flags
		result = self.fift.Run(args)
		savedFilePath = Pars(result, "Saved to file ", ")")
		self.SendFile(savedFilePath, wallet, wait=wait)
	#end define

	def MoveGramsFromHW(self, wallet, destList, **kwargs):
		local.AddLog("start MoveGramsFromHW function", "debug")
		flags = kwargs.get("flags")
		wait = kwargs.get("wait", True)

		if len(destList) == 0:
			local.AddLog("MoveGramsFromHW warning: destList is empty, break function", "warning")
			return
		#end if

		orderFilePath = local.buffer.get("myTempDir") + wallet.name + "_order.txt"
		lines = list()
		for dest, grams in destList:
			lines.append("SEND {dest} {grams}".format(dest=dest, grams=grams))
		text = "\n".join(lines)
		file = open(orderFilePath, 'wt')
		file.write(text)
		file.close()

		seqno = self.GetSeqno(wallet)
		resultFilePath = local.buffer.get("myTempDir") + wallet.name + "_wallet-query"
		args = ["highload-wallet.fif", wallet.path, wallet.subwallet, seqno, orderFilePath, resultFilePath]
		if flags:
			args += flags
		result = self.fift.Run(args)
		savedFilePath = Pars(result, "Saved to file ", ")")
		self.SendFile(savedFilePath, wallet, wait=wait)
	#end define
	
	def GetValidatorKey(self):
		data = self.GetConfigFromValidator()
		validators = data["validators"]
		for validator in validators:
			validatorId = validator["id"]
			key_bytes = base64.b64decode(validatorId)
			validatorKey = key_bytes.hex().upper()
			timestamp = GetTimestamp()
			if timestamp > validator["election_date"]:
				return validatorKey
		raise Exception("GetValidatorKey error: validator key not found. Are you sure you are a validator?")
	#end define
	
	def GetElectionEntries(self):
		local.AddLog("start GetElectionEntries function", "debug")
		fullConfigAddr = self.GetFullElectorAddr()
		# Get raw data
		cmd = "runmethod {fullConfigAddr} participant_list_extended".format(fullConfigAddr=fullConfigAddr)
		result = self.liteClient.Run(cmd)
		rawElectionEntries = self.Result2List(result)
		
		# Get json
		# Parser by @skydev (https://github.com/skydev0h)
		entries = list()
		startWorkTime = rawElectionEntries[0]
		endElectionsTime = rawElectionEntries[1]
		minStake = rawElectionEntries[2]
		allStakes = rawElectionEntries[3]
		electionEntries = rawElectionEntries[4]
		wtf1 = rawElectionEntries[5]
		wtf2 = rawElectionEntries[6]
		for entry in electionEntries:
			if len(entry) == 0:
				continue
				
			# Create dict
			item = dict()
			item["validatorPubkey"] = dec2hex(entry[0]).upper()
			item["stake"] = ng2g(entry[1][0])
			item["maxFactor"] = round(entry[1][1] / 655.36) / 100.0
			item["walletAddr_hex"] = dec2hex(entry[1][2]).upper()
			item["walletAddr"] = self.HexAddr2Base64Addr("-1:"+item["walletAddr_hex"])
			item["adnlAddr"] = dec2hex(entry[1][3]).upper()
			entries.append(item)
		return entries
	#end define
	
	def GetOffers(self):
		local.AddLog("start GetOffers function", "debug")
		fullConfigAddr = self.GetFullConfigAddr()
		# Get raw data
		cmd = "runmethod {fullConfigAddr} list_proposals".format(fullConfigAddr=fullConfigAddr)
		result = self.liteClient.Run(cmd)
		rawOffers = self.Result2List(result)
		rawOffers = rawOffers[0]

		# Get json
		offers = list()
		for offer in rawOffers:
			if len(offer) == 0:
				continue
			hash = offer[0]
			subdata = offer[1]
			
			# Create dict
			# parser from: https://github.com/ton-blockchain/ton/blob/dab7ee3f9794db5a6d32c895dbc2564f681d9126/crypto/smartcont/config-code.fc#L607
			item = dict()
			item["config"] = dict()
			item["hash"] = hash
			item["endTime"] = subdata[0] # *expires*
			item["critFlag"] = subdata[1] # *critical*
			item["config"]["id"] = subdata[2][0] # *param_id*
			item["config"]["value"] = subdata[2][1] # *param_val*
			item["config"]["oldValueHash"] = subdata[2][2] # *param_hash*
			# item["vsetId"] = subdata[3] # *vset_id*
			item["votedValidators"] = subdata[4] # *voters_list*
			item["weightRemaining"] = subdata[5] # *weight_remaining*
			item["roundsRemaining"] = subdata[6] # *rounds_remaining*
			item["losses"] = subdata[7] # *losses*
			item["wins"] = subdata[8] # *wins*
			offers.append(item)
		#end for
		return offers
	#end define

	def GetComplaints(self, electionId=None):
		local.AddLog("start GetComplaints function", "debug")
		fullElectorAddr = self.GetFullElectorAddr()
		if electionId is None:
			config34 = self.GetConfig34()
			electionId = config34.get("startWorkTime")
		cmd = "runmethod {fullElectorAddr} list_complaints {electionId}".format(fullElectorAddr=fullElectorAddr, electionId=electionId)
		result = self.liteClient.Run(cmd)
		rawComplaints = self.Result2List(result)
		rawComplaints = rawComplaints[0]

		# Get json
		complaints = list()
		for complaint in rawComplaints:
			if len(complaint) == 0:
				continue
			chash = complaint[0]
			subdata = complaint[1]

			# Create dict
			# parser from: https://github.com/ton-blockchain/ton/blob/dab7ee3f9794db5a6d32c895dbc2564f681d9126/crypto/smartcont/elector-code.fc#L1149
			item = dict()
			buff = subdata[0] # *complaint*
			item["hash"] = chash
			item["validatorPubkey"] = dec2hex(buff[0]).upper() # *validator_pubkey*
			# item["description"] = buff[1] # *description*
			item["createdTime"] = buff[2] # *created_at*
			item["severity"] = buff[3] # *severity*
			rewardAddr = buff[4]
			rewardAddr = "-1:" + dec2hex(rewardAddr)
			rewardAddr = self.HexAddr2Base64Addr(rewardAddr)
			item["rewardAddr"] = rewardAddr # *reward_addr*
			# item["paid"] = buff[5] # *paid*
			# item["suggestedFine"] = buff[6] # *suggested_fine*
			# item["suggestedFinePart"] = buff[7] # *suggested_fine_part*
			item["votedValidators"] = subdata[1] # *voters_list*
			# item["vsetId"] = subdata[2] # *vset_id*
			item["weightRemaining"] = subdata[3] # *weight_remaining*
			complaints.append(item)
		#end for
		return complaints
	#end define

	def GetComplaintsNumber(self):
		local.AddLog("start GetComplaintsNumber function", "debug")
		result = dict()
		complaints = self.GetComplaints()
		saveComplaints = self.GetSaveComplaints()
		buff = 0
		for complaint in complaints:
			complaintHash = complaint.get("hash")
			if complaintHash in saveComplaints:
				continue
			buff += 1
		result["all"] = len(complaints)
		result["new"] = buff
		return result
	#end define

	def GetComplaint(self, complaintHash):
		local.AddLog("start GetComplaint function", "debug")
		complaints = self.GetComplaints()
		for complaint in complaints:
			if complaintHash == complaint.get("hash"):
				return complaint
		raise Exception("GetComplaint error: complaint not found.")
	#end define

	def SignProposalVoteRequestWithValidator(self, offerHash, validatorIndex, validatorPubkey_b64, validatorSignature):
		local.AddLog("start SignProposalVoteRequestWithValidator function", "debug")
		fileName = self.tempDir + self.nodeName + "proposal_vote-msg-body.boc"
		args = ["config-proposal-vote-signed.fif", "-i", validatorIndex, offerHash, validatorPubkey_b64, validatorSignature, fileName]
		result = self.fift.Run(args)
		fileName = Pars(result, "Saved to file ", '\n')
		return fileName
	#end define

	def SignComplaintVoteRequestWithValidator(self, complaintHash, electionId, validatorIndex, validatorPubkey_b64, validatorSignature):
		local.AddLog("start SignComplaintRequestWithValidator function", "debug")
		fileName = self.tempDir + "complaint_vote-msg-body.boc"
		args = ["complaint-vote-signed.fif", validatorIndex, electionId, complaintHash, validatorPubkey_b64, validatorSignature, fileName]
		result = self.fift.Run(args)
		fileName = Pars(result, "Saved to file ", '\n')
		return fileName
	#end define

	def VoteOffer(self, offerHash):
		local.AddLog("start VoteOffer function", "debug")
		offerHash = int(offerHash)
		fullConfigAddr = self.GetFullConfigAddr()
		walletName = self.validatorWalletName
		wallet = self.GetLocalWallet(walletName)
		validatorKey = self.GetValidatorKey()
		validatorPubkey_b64 = self.GetPubKeyBase64(validatorKey)
		validatorIndex = self.GetValidatorIndex()
		offer = self.GetOffer(offerHash)
		if validatorIndex in offer.get("votedValidators"):
			local.AddLog("Proposal already has been voted", "debug")
			return
		var1 = self.CreateConfigProposalRequest(offerHash, validatorIndex)
		validatorSignature = self.GetValidatorSignature(validatorKey, var1)
		resultFilePath = self.SignProposalVoteRequestWithValidator(offerHash, validatorIndex, validatorPubkey_b64, validatorSignature)
		resultFilePath = self.SignFileWithWallet(wallet, resultFilePath, fullConfigAddr, 1.5)
		self.SendFile(resultFilePath, wallet)
		self.AddSaveOffer(offerHash)
	#end define

	def VoteComplaint(self, complaintHash):
		local.AddLog("start VoteComplaint function", "debug")
		complaintHash = int(complaintHash)
		fullElectorAddr = self.GetFullElectorAddr()
		walletName = self.validatorWalletName
		wallet = self.GetLocalWallet(walletName)
		validatorKey = self.GetValidatorKey()
		validatorPubkey_b64 = self.GetPubKeyBase64(validatorKey)
		validatorIndex = self.GetValidatorIndex()
		complaint = self.GetComplaint(complaintHash)
		if validatorIndex in complaint.get("votedValidators"):
			local.AddLog("Complaint already has been voted", "debug")
			return
		config34 = self.GetConfig34()
		electionId = config34.get("startWorkTime")
		createdTime = complaint.get("createdTime")
		if electionId > createdTime:
			config32 = self.GetConfig32()
			electionId = config32.get("startWorkTime")
		var1 = self.CreateComplaintRequest(electionId, complaintHash, validatorIndex)
		validatorSignature = self.GetValidatorSignature(validatorKey, var1)
		resultFilePath = self.SignComplaintVoteRequestWithValidator(complaintHash, electionId, validatorIndex, validatorPubkey_b64, validatorSignature)
		resultFilePath = self.SignFileWithWallet(wallet, resultFilePath, fullElectorAddr, 1.5)
		self.SendFile(resultFilePath, wallet)
		self.AddSaveComplaint(complaintHash)
	#end define

	def CheckComplaints(self):
		local.AddLog("start CheckComplaints function", "debug")
		config34 = self.GetConfig34()
		electionId = config34.get("startWorkTime")
		filePrefix = self.tempDir + "scheck_"
		cmd = "savecomplaints {electionId} {filePrefix}".format(electionId=electionId, filePrefix=filePrefix)
		result = self.liteClient.Run(cmd)
		lines = result.split('\n')
		checkComplaints = list()
		for line in lines:
			if "SAVE_COMPLAINT" in line:
				buff = line.split('\t')
				chash = buff[2]
				validatorPubkey = buff[3]
				createdTime = buff[4]
				filePath = buff[5]
				ok = self.CheckComplaint(filePath)
				if ok is True:
					checkComplaints.append(chash)
		return checkComplaints
	#end define

	def CheckComplaint(self, filePath):
		local.AddLog("start CheckComplaint function", "debug")
		cmd = "loadproofcheck {filePath}".format(filePath=filePath)
		result = self.liteClient.Run(cmd)
		lines = result.split('\n')
		ok = False
		for line in lines:
			if "COMPLAINT_VOTE_FOR" in line:
				buff = line.split('\t')
				chash = buff[1]
				ok_buff = buff[2]
				if ok_buff == "YES":
					ok = True
		return ok
	#end define

	def GetOnlineValidators(self):
		onlineValidators = list()
		vdata, compFiles = self.GetValidatorsLoad()
		for key, item in vdata.items():
			online = item.get("online")
			if online is True:
				onlineValidators.append(item)
		return onlineValidators
	#end define

	def GetValidatorsLoad(self):
		local.AddLog("start GetValidatorsLoad function", "debug")
		timeNow = GetTimestamp() - 10
		time2 = timeNow - 2000
		filePrefix = self.tempDir + "check_{timeNow}".format(timeNow=timeNow)
		cmd = "checkloadall {time2} {timeNow} {filePrefix}".format(timeNow=timeNow, time2=time2, filePrefix=filePrefix)
		result = self.liteClient.Run(cmd, timeout=10)
		lines = result.split('\n')
		vdata = dict()
		compFiles = list()
		for line in lines:
			if "COMPLAINT_SAVED" in line:
				buff = line.split('\t')
				var1 = buff[1]
				var2 = buff[2]
				fileName = buff[3]
				compFiles.append(fileName)
			elif "val" in line and "pubkey" in line:
				buff = line.split(' ')
				vid = buff[1]
				vid = vid.replace('#', '')
				vid = vid.replace(':', '')
				vid = int(vid)
				pubkey = buff[3]
				blocksCreated_buff = buff[6]
				blocksCreated_buff = blocksCreated_buff.replace('(', '')
				blocksCreated_buff = blocksCreated_buff.replace(')', '')
				blocksCreated_buff = blocksCreated_buff.split(',')
				masterBlocksCreated = float(blocksCreated_buff[0])
				workBlocksCreated = float(blocksCreated_buff[1])
				blocksExpected_buff = buff[8]
				blocksExpected_buff = blocksExpected_buff.replace('(', '')
				blocksExpected_buff = blocksExpected_buff.replace(')', '')
				blocksExpected_buff = blocksExpected_buff.split(',')
				masterBlocksExpected = float(blocksExpected_buff[0])
				workBlocksExpected = float(blocksExpected_buff[1])
				mr = masterBlocksCreated / masterBlocksExpected
				wr = workBlocksCreated / workBlocksExpected
				r = (mr + wr) / 2
				if r > 0.7:
					online = True
				else:
					online = False
				item = dict()
				item["id"] = vid
				item["pubkey"] = pubkey
				item["masterBlocksCreated"] = masterBlocksCreated
				item["workBlocksCreated"] = workBlocksCreated
				item["masterBlocksExpected"] = masterBlocksExpected
				item["workBlocksExpected"] = workBlocksExpected
				item["mr"] = mr
				item["wr"] = wr
				item["online"] = online
				vdata[vid] = item
		return vdata, compFiles
	#end define

	def CheckValidators(self):
		local.AddLog("start CheckValidators function", "debug")
		vdata, compFiles = self.GetValidatorsLoad()
		fullElectorAddr = self.GetFullElectorAddr()
		config34 = self.GetConfig34()
		electionId = config34.get("startWorkTime")
		walletName = self.validatorWalletName
		wallet = self.GetLocalWallet(walletName)
		account = self.GetAccount(wallet.addr)
		if wallet is None:
			raise Exception("Validator wallet not fond")
		if account.balance < 100:
			raise Exception("Validator wallet balance must be greater than 100")
		for fileName in compFiles:
			fileName = self.PrepareComplaint(electionId, fileName)
			fileName = self.SignFileWithWallet(wallet, fileName, fullElectorAddr, 100)
			self.SendFile(fileName, wallet)
	#end define

	def GetOffer(self, offerHash):
		local.AddLog("start GetOffer function", "debug")
		offers = self.GetOffers()
		for offer in offers:
			if offerHash == offer.get("hash"):
				return offer
		raise Exception("GetOffer error: offer not found.")
	#end define
	
	def GetOffersNumber(self):
		local.AddLog("start GetOffersNumber function", "debug")
		result = dict()
		offers = self.GetOffers()
		saveOffers = self.GetSaveOffers()
		buff = 0
		for offer in offers:
			offerHash = offer.get("hash")
			if offerHash in saveOffers:
				continue
			buff += 1
		result["all"] = len(offers)
		result["new"] = buff
		return result
	#end define
	
	def GetValidatorIndex(self, adnlAddr=None):
		config34 = self.GetConfig34()
		validators = config34.get("validators")
		if adnlAddr is None:
			adnlAddr = self.GetAdnlAddr()
		index = 0
		for validator in validators:
			searchAdnlAddr = validator.get("adnlAddr")
			if adnlAddr == searchAdnlAddr:
				return index
			index += 1
		local.AddLog("GetValidatorIndex warning: index not found.", "warning")
		return -1
	#end define
	
	def GetDbSize(self, exceptions="log"):
		local.AddLog("start GetDbSize function", "debug")
		exceptions = exceptions.split()
		totalSize = 0
		path = "/var/ton-work/"
		for directory, subdirectory, files in os.walk(path):
			for file in files:
				buff = file.split('.')
				ext = buff[-1]
				if ext in exceptions:
					continue
				filePath = os.path.join(directory, file)
				totalSize += os.path.getsize(filePath)
		result = round(totalSize / 10**9, 2)
		return result
	#end define
	
	def Result2List(self, text):
		buff = Pars(text, "result:", "\n")
		buff = buff.replace(')', ']')
		buff = buff.replace('(', '[')
		buff = buff.replace(']', ' ] ')
		buff = buff.replace('[', ' [ ')
		arr = buff.split()
		
		# Get good raw data
		output = ""
		arrLen = len(arr)
		for i in range(arrLen):
			item = arr[i]
			# get next item
			if i+1 < arrLen:
				nextItem = arr[i+1]
			else:
				nextItem = None
			# add item to output
			if item == '[':
				output += item
			elif nextItem == ']':
				output += item
			elif '{' in item or '}' in item:
				output += "\"{item}\", ".format(item=item)
			elif i+1 == arrLen:
				output += item
			else:
				output += item + ', '
		#end for
		data = json.loads(output)
		return data
	#end define
	
	def NewDomain(self, domain):
		local.AddLog("start NewDomain function", "debug")
		domainName = domain["name"]
		buff = domainName.split('.')
		subdomain = buff.pop(0)
		dnsDomain = ".".join(buff)
		dnsAddr = self.GetDomainAddr(dnsDomain)
		wallet = self.GetLocalWallet(domain["walletName"])
		expireInSec = 700000 # fix me
		catId = 1 # fix me
		
		# Check if domain is busy
		domainEndTime = self.GetDomainEndTime(domainName)
		if domainEndTime > 0:
			raise Exception("NewDomain error: domain is busy")
		#end if
		
		fileName = self.tempDir + self.nodeName + "dns-msg-body.boc"
		args = ["auto-dns.fif", dnsAddr, "add", subdomain, expireInSec, "owner", wallet.addr, "cat", catId, "adnl", domain["adnlAddr"], "-o", fileName]
		result = self.fift.Run(args)
		resultFilePath = Pars(result, "Saved to file ", ')')
		resultFilePath = self.SignFileWithWallet(wallet, resultFilePath, dnsAddr, 1.7)
		self.SendFile(resultFilePath, wallet)
		self.AddDomain(domain)
	#end define
	
	def AddDomain(self, domain):
		if "domains" not in local.db:
			local.db["domains"] = list()
		#end if
		local.db["domains"].append(domain)
		local.dbSave()
	#end define
	
	def GetDomains(self):
		domains = local.db.get("domains", list()) 
		for domain in domains:
			domainName = domain.get("name")
			domain["endTime"] = self.GetDomainEndTime(domainName)
		return domains
	#end define
	
	def GetDomain(self, domainName):
		domain = dict()
		domain["name"] = domainName
		domain["adnlAddr"] = self.GetDomainAdnlAddr(domainName)
		domain["endTime"] = self.GetDomainEndTime(domainName)
		return domain
	#end define
	
	def DeleteDomain(self, domainName):
		domains = local.db.get("domains")
		for domain in domains:
			if (domainName == domain.get("name")):
				domains.remove(domain)
				local.dbSave()
				return
		raise Exception("DeleteDomain error: Domain not found")
	#end define
	
	def AddRule(self, rule):
		if "rules" not in local.db:
			local.db["rules"] = list()
		#end if
		local.db["rules"].append(rule)
		local.dbSave()
	#end define
	
	def GetRules(self):
		rules = local.db.get("rules")
		return rules
	#end define
	
	def AddBookmark(self, bookmark):
		if "bookmarks" not in local.db:
			local.db["bookmarks"] = list()
		#end if
		local.db["bookmarks"].append(bookmark)
		local.dbSave()
	#end define
	
	def GetBookmarks(self):
		bookmarks = local.db.get("bookmarks")
		if bookmarks is not None:
			for bookmark in bookmarks:
				self.WriteBookmarkData(bookmark)
		return bookmarks
	#end define
	
	def GetBookmarkAddr(self, type, name):
		bookmarks = local.db.get("bookmarks", list())
		for bookmark in bookmarks:
			bookmarkType = bookmark.get("type")
			bookmarkName = bookmark.get("name")
			bookmarkAddr = bookmark.get("addr")
			if (bookmarkType == type and bookmarkName == name):
				return bookmarkAddr
		raise Exception("GetBookmarkAddr error: Bookmark not found")
	#end define
	
	def DeleteBookmark(self, name, type):
		bookmarks = local.db.get("bookmarks")
		for bookmark in bookmarks:
			bookmarkType = bookmark.get("type")
			bookmarkName = bookmark.get("name")
			if (type == bookmarkType and name == bookmarkName):
				bookmarks.remove(bookmark)
				local.dbSave()
				return
		raise Exception("DeleteBookmark error: Bookmark not found")
	#end define
	
	def WriteBookmarkData(self, bookmark):
		type = bookmark.get("type")
		if type == "account":
			addr = bookmark.get("addr")
			account = self.GetAccount(addr)
			if account.status == "empty":
				data = "empty"
			else:
				data = account.balance
		elif type == "domain":
			domainName = bookmark.get("addr")
			endTime = self.GetDomainEndTime(domainName)
			if endTime == 0:
				data = "free"
			else:
				data = Timestamp2Datetime(endTime, "%d.%m.%Y")
		else:
			data = "null"
		bookmark["data"] = data
	#end define
	
	def AddSaveOffer(self, offerHash):
		saveOffers = self.GetSaveOffers()
		if offerHash not in saveOffers:
			saveOffers.append(offerHash)
			local.dbSave()
	#end define

	def GetSaveOffers(self):
		saveOffers = local.db.get("saveOffers")
		if saveOffers is None:
			saveOffers = list()
			local.db["saveOffers"] = saveOffers
		return saveOffers
	#end define
	
	def GetSaveComplaints(self):
		saveComplaints = local.db.get("saveComplaints")
		if saveComplaints is None:
			saveComplaints = list()
			local.db["saveComplaints"] = saveComplaints
		return saveComplaints
	#end define

	def AddSaveComplaint(self, complaintHash):
		saveComplaints = self.GetSaveComplaints()
		if complaintHash not in saveComplaints:
			saveComplaints.append(complaintHash)
			local.dbSave()
	#end define

	def GetStrType(self, inputStr):
		if type(inputStr) is not str:
			result = None
		elif len(inputStr) == 48 and '.' not in inputStr:
			result = "account"
		elif ':' in inputStr:
			result = "account_hex"
		elif '.' in inputStr:
			result = "domain"
		else:
			result = "undefined"
		return result
	#end define
	
	def GetDestinationAddr(self, destination):
		destinationType = self.GetStrType(destination)
		if destinationType == "undefined":
			walletsNameList = self.GetWalletsNameList()
			if destination in walletsNameList:
				wallet = self.GetLocalWallet(destination)
				destination = wallet.addr
			else:
				destination = self.GetBookmarkAddr("account", destination)
		elif destinationType == "account_hex":
			destination = self.HexAddr2Base64Addr(destination)
		return destination
	#end define
	
	def HexAddr2Base64Addr(self, fullAddr, bounceable=True, testnet=True):
		buff = fullAddr.split(':')
		workchain = int(buff[0])
		addr_hex = buff[1]
		b = bytearray(36)
		b[0] = 0x51 - bounceable * 0x40 + testnet * 0x80
		b[1] = workchain % 256
		b[2:34] = bytearray.fromhex(addr_hex)
		buff = bytes(b[:34])
		crc = crc16.crc16xmodem(buff)
		b[34] = crc >> 8
		b[35] = crc & 0xff
		result = base64.b64encode(b)
		result = result.decode()
		result = result.replace('+', '-')
		result = result.replace('/', '_')
		return result
	#end define
	
	def GetNetLoadAvg(self):
		statistics = self.GetSettings("statistics")
		if statistics:
			netLoadAvg = statistics.get("netLoadAvg")
		else:
			netLoadAvg = [-1, -1, -1]
		return netLoadAvg
	#end define

	def GetTpsAvg(self):
		statistics = self.GetSettings("statistics")
		if statistics:
			tpsAvg = statistics.get("tpsAvg")
		else:
			tpsAvg = [-1, -1, -1]
		return tpsAvg
	#end define

	def GetSettings(self, name):
		local.dbLoad()
		result = local.db.get(name)
		return result
	#end define

	def SetSettings(self, name, data):
		if type(data) == str:
			data = json.loads(data)
		local.db[name] = data
		local.dbSave()
	#end define
#end class

def ng2g(ng):
	return int(ng)/10**9
#end define

def Init():
	# Event reaction
	if ("-e" in sys.argv):
		x = sys.argv.index("-e")
		eventName = sys.argv[x+1]
		Event(eventName)
	#end if

	local.Run()
	local.buffer["network"] = dict()
	local.buffer["network"]["type"] = "bytes"
	local.buffer["network"]["in"] = [0]*15*6
	local.buffer["network"]["out"] = [0]*15*6
	local.buffer["network"]["all"] = [0]*15*6

	local.buffer["oldBlock"] = None
	local.buffer["blocks"] = list()
	local.buffer["transNum"] = 0
	local.buffer["blocksNum"] = 0
	local.buffer["masterBlocksNum"] = 0
	local.buffer["transNumList"] = [0]*15*6
#end define

def Event(eventName):
	if eventName == "enableVC":
		EnableVcEvent()
	elif eventName == "validator down":
		ValidatorDownEvent()
	local.Exit()
#end define

def EnableVcEvent():
	local.AddLog("start EnableVcEvent function", "debug")
	# Создать новый кошелек для валидатора
	ton = MyTonCore()
	wallet = ton.CreateWallet("validator_wallet_001", -1)
	local.db["validatorWalletName"] = wallet.name

	# Создать новый ADNL адрес для валидатора
	adnlAddr = ton.CreatNewKey()
	ton.AddAdnlAddrToValidator(adnlAddr)
	local.db["adnlAddr"] = adnlAddr

	# Сохранить
	local.dbSave()
#end define

def ValidatorDownEvent():
	local.AddLog("start ValidatorDownEvent function", "debug")
	local.AddLog("Validator is down", "error")
#end define

def Elections(ton):
	if ton.validatorWalletName is None:
		return
	ton.ReturnStake()
	ton.ElectionEntry()
#end define

def Statistics(ton):
	ReadNetworkData()
	SaveNetworStatistics(ton)
	ReadTransNumData()
	SaveTransNumStatistics(ton)
#end define

def ReadNetworkData():
	interfaceName = GetInternetInterfaceName()
	buff = psutil.net_io_counters(pernic=True)
	data = buff[interfaceName]
	network_in = data.bytes_recv
	network_out = data.bytes_sent
	network_all = network_in + network_out

	local.buffer["network"]["in"].pop(0)
	local.buffer["network"]["in"].append(network_in)
	local.buffer["network"]["out"].pop(0)
	local.buffer["network"]["out"].append(network_out)
	local.buffer["network"]["all"].pop(0)
	local.buffer["network"]["all"].append(network_all)
#end define

def SaveNetworStatistics(ton):
	data = local.buffer["network"]["all"]
	data = data[::-1]
	zerodata = data[0]
	buff1 = data[1*6-1]
	buff5 = data[5*6-1]
	buff15 = data[15*6-1]

	# get avg
	if buff1 != 0:
		buff1 = zerodata - buff1
	if buff5 != 0:
		buff5 = zerodata - buff5
	if buff15 != 0:
		buff15 = zerodata - buff15

	# bytes -> bytes/s
	buff1 = buff1 / (1*60)
	buff5 = buff5 / (5*60)
	buff15 = buff15 / (15*60)

	# bytes/s -> bits/s
	buff1 = buff1 * 8
	buff5 = buff5 * 8
	buff15 = buff15 * 8

	# bits/s -> Mbits/s
	netLoad1 = b2mb(buff1)
	netLoad5 = b2mb(buff5)
	netLoad15 = b2mb(buff15)

	# save statistics
	statistics = local.db.get("statistics", dict())
	statistics["netLoadAvg"] = [netLoad1, netLoad5, netLoad15]
	local.db["statistics"] = statistics
#end define

def ReadTransNumData():
	transNum = local.buffer["transNum"]
	local.buffer["transNumList"].pop(0)
	local.buffer["transNumList"].append(transNum)
#end define

def SaveTransNumStatistics(ton):
	data = local.buffer["transNumList"]
	data = data[::-1]
	zerodata = data[0]
	buff1 = data[1*6-1]
	buff5 = data[5*6-1]
	buff15 = data[15*6-1]

	# get avg
	if buff1 != 0:
		buff1 = zerodata - buff1
	if buff5 != 0:
		buff5 = zerodata - buff5
	if buff15 != 0:
		buff15 = zerodata - buff15

	# trans -> trans per sec (TPS)
	buff1 = buff1 / (1*60)
	buff5 = buff5 / (5*60)
	buff15 = buff15 / (15*60)

	# round
	tps1 = round(buff1, 2)
	tps5 = round(buff5, 2)
	tps15 = round(buff15, 2)

	# if ScanBlocks thread not working
	diffTime = GetTimestamp() - local.buffer.get("scanBlocks_time", -1)
	if diffTime > 60:
		tps1 = -1
		tps5 = -1
		tps15 = -1
	#end if

	# save statistics
	statistics = local.db.get("statistics", dict())
	statistics["tpsAvg"] = [tps1, tps5, tps15]
	local.db["statistics"] = statistics
#end define

def Offers(ton):
	saveOffers = ton.GetSaveOffers()
	offers = ton.GetOffers()
	for offer in offers:
		offerHash = offer.get("hash")
		if offerHash in saveOffers:
			ton.VoteOffer(offerHash)
#end define

def Domains(ton):
	pass
#end define

def Telemetry(ton):
	if (local.db.get("sendTelemetry") != True):
		return
	#end if
	
	data = dict()
	data["adnlAddr"] = ton.adnlAddr
	data["validatorStatus"] = ton.GetValidatorStatus()
	data["cpuLoad"] = GetLoadAvg()
	data["netLoad"] = ton.GetNetLoadAvg()
	data["tps"] = ton.GetTpsAvg()
	url = "https://toncenter.com/api/newton_test/status/report_status"
	output = json.dumps(data)
	resp = requests.post(url, data=output, timeout=3)
	
	# fix me
	if ton.adnlAddr != "8F6B69A49F6AED54A5B92623699AA44E6F801CDD5BA8B89519AA0DDEA7E9A618":
		return
	data = dict()
	config34 = ton.GetConfig34()
	config36 = ton.GetConfig36()
	data["currentValidators"] = config34.get("validators")
	data["nextValidators"] = config36.get("validators")
	url = "https://toncenter.com/api/newton_test/status/report_validators"
	output = json.dumps(data)
	resp = requests.post(url, data=output, timeout=3)
#end define

def Mining(ton):
	powAddr = local.db.get("powAddr")
	minerAddr = local.db.get("minerAddr")
	if powAddr is None or minerAddr is None:
		return
	#end if

	local.AddLog("start Mining function", "debug")
	filePath = ton.tempDir + "mined.boc"
	cpus = psutil.cpu_count() - 1
	numThreads = "-w{cpus}".format(cpus=cpus)
	params = ton.GetPowParams(powAddr)
	args = ["-vv", numThreads, "-t100", minerAddr, params["seed"], params["complexity"], params["iterations"], powAddr, filePath]
	result = ton.miner.Run(args)

	if "Saving" in result:
		newParams = ton.GetPowParams(powAddr)
		if params["seed"] == newParams["seed"] and params["complexity"] == newParams["complexity"]:
			ton.liteClient.Run("sendfile " + filePath)
			local.AddLog("Yep!")
	#end if
#end define

def ScanBlocks(ton):
	if ton.liteClient.pubkeyPath is None:
		local.AddLog("ScanBlocks warning: local liteserver is not configured, stop thread", "warning")
		exit()
	validatorStatus = ton.GetValidatorStatus()
	validatorOutOfSync = validatorStatus.get("outOfSync")
	if validatorOutOfSync > 20:
		local.AddLog("ScanBlocks warning: local validator out of sync, sleep 60 sec", "warning")
		time.sleep(60)
		return
	block = ton.GetLastBlock()
	local.buffer["scanBlocks_time"] = GetTimestamp()
	if block != local.buffer["oldBlock"]:
		local.buffer["oldBlock"] = block
		local.buffer["blocks"].append(block)
		local.buffer["blocksNum"] += 1
		local.buffer["masterBlocksNum"] += 1
#end define

def ReadBlocks(ton):
	blocks = local.buffer["blocks"]
	if len(blocks) == 0:
		return
	block = blocks.pop(0)

	# Разделить
	buff1 = {"transNum": 0}
	t1 = threading.Thread(target=SaveTransNumFromBlock, args=(ton, block, buff1), daemon=True)
	t2 = threading.Thread(target=SaveShardsFromBlock, args=(ton, block, buff1), daemon=True)
	t1.start()
	t2.start()
	t1.join()
	t2.join()

	# Собрать
	transNum = buff1["transNum"]
	shards = buff1["shards"]

	# Разделить
	buff2 = dict()
	for shard in shards:
		local.buffer["blocksNum"] += 1
		threading.Thread(target=SaveTransNumFromShard, args=(ton, shard, buff2), daemon=True).start()
	while len(buff2) < len(shards):
		time.sleep(0.3)

	# Собрать
	for shard in shards:
		shard_id = shard["id"]
		transNum += buff2[shard_id]
	local.buffer["transNum"] += transNum
#end define

def SaveTransNumFromBlock(ton, block, buff):
	buff["transNum"] = ton.GetTransactionsNumber(block)
#end define

def SaveShardsFromBlock(ton, block, buff):
	buff["shards"] = ton.GetShards(block)
#end define

def SaveTransNumFromShard(ton, shard, buff):
	shard_id = shard["id"]
	shard_block = shard["block"]
	buff[shard_id] = ton.GetTransactionsNumber(shard_block)
#end define

def Complaints(ton):
	saveComplaints = ton.GetSaveComplaints()
	checkComplaints = ton.CheckComplaints()
	complaints = ton.GetComplaints()
	for complaint in complaints:
		complaintHash = complaint.get("hash")
		complaintHash_hex = dec2hex(complaintHash).upper()
		if complaintHash_hex in checkComplaints and complaintHash not in saveComplaints:
			ton.VoteComplaint(complaintHash)
#end define

def EnsurePeriodParams():
	default_periods = {
			"elections": 600,
			"statistics": 10,
			"offers": 600,
			"complaints": 600,
			"domains": 600,
			"telemetry": 60,
			"mining": 1,
			"scanBlocks": 1,
			"readBlocks": 0.3
		};
	if "periods" not in local.db:
		local.db["periods"] = default_periods
	else:
		for periodType in default_periods:
			if not periodType in local.db["periods"]:
				local.db["periods"][periodType] = default_periods[periodType]
	local.dbSave()

def General():
	local.AddLog("start General function", "debug")
	ton = MyTonCore()
	EnsurePeriodParams()
	# Запустить потоки
	for subprocess in [Elections, Statistics, Offers, Complaints,
			   Domains, Telemetry, Mining, ScanBlocks,
			   ReadBlocks]:
		# period names in camelCase
		periodName = subprocess.__name__[:1].lower() + subprocess.__name__[1:]
		period = local.db["periods"][periodName]
		local.StartCycle(subprocess, sec=period, args=(ton, ))
	Sleep()
#end define

def hex2str(h):
	try:
		h = h.replace("00", '')
		b = bytes.fromhex(h)
		t = b.decode("utf-8")
		return t
	except:
		return None
#end define

def xhex2hex(x):
	try:
		b = x[1:]
		h = b.lower()
		return h
	except:
		return None
#end define




###
### Start of the program
###

if __name__ == "__main__":
	Init()
	General()
#end if

