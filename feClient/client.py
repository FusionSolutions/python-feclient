# Builtin modules
import json, re, hmac, logging, weakref
from hashlib import sha256
from time import time, sleep
from collections import OrderedDict
from itertools import starmap
# Local modules
from .exceptions import *
from .utils import hexToBytes, StopSignal, chunks
from .clientSocket import ClientSocket
# Program
class Client:
	__slots__ = ("log", "pubkey", "seckey", "hexNumbers", "connTimeout", "timeout", "compression", "timeWindow", "retryCount",
		"retryDelay", "stopSignal", "id", "requests", "socket" )
	endpoint = "api.fusionexplorer.io"
	port = 443
	ssl = True
	max_bulk_request = 0xFF
	max_payload = 0xFFFF
	def __init__(self, projectPublicKey:str=None, projectSecretKey:str=None, hexNumbers:bool=False, connectTimeout:int=15,
	timeout:int=320, compression:bool=True, timeWindow:int=60, retryCount=10, retryDelay=5, stopSignal:object=None,
	log:object=None):
		self.log = log or logging.getLogger("FusionExplorer")
		self.log.info("Initializing..")
		self.pubkey = projectPublicKey
		self.seckey = projectSecretKey
		if self.pubkey != None:
			if self.seckey == None:
				raise InitializationError("`projectSecretKey` is required when `projectPublicKey` is set")
			if type(self.pubkey) is not bytes:
				if not re.match(r'^(0x|)[0-9a-f]{32}$', self.pubkey, re.I):
					raise InitializationError("`projectPublicKey` must be 32 character hex string")
				self.pubkey = hexToBytes(self.pubkey)
			if len(self.pubkey) != 16:
				raise InitializationError("`projectPublicKey` must be 16 byte long")
			if type(self.seckey) is not bytes:
				if not re.match(r'^(0x|)[0-9a-f]{32}$', self.seckey, re.I):
					raise InitializationError("`projectSecretKey` must be 32 character hex string")
				self.seckey = hexToBytes(self.seckey)
			if len(self.seckey) != 16:
				raise InitializationError("`projectSecretKey` must be 16 byte long")
		self.hexNumbers = hexNumbers
		self.connTimeout = connectTimeout
		self.timeout = timeout
		self.compression = compression
		self.timeWindow = timeWindow
		self.retryCount = retryCount
		self.retryDelay = retryDelay
		self.stopSignal = stopSignal or StopSignal
		self.id = 0
		self.requests = weakref.WeakValueDictionary()
		self.socket = ClientSocket(self, self.endpoint, self.port, self.ssl, self.compression,
			self.connTimeout, self.timeout, self.stopSignal)
		self.log.debug("Public token: {}".format(self.pubkey.hex() if self.pubkey else "None"))
		self.log.debug("Secret token: {}".format( ("{}...{}".format(
			self.seckey[:1].hex(),
			self.seckey[-1:].hex())) if self.seckey else "None"
		))
		self.log.info("Initialized")
	def __del__(self):
		self.close()
	def __getstate__(self):
		return {
			"log":        self.log,
			"pubkey":     self.pubkey,
			"seckey":     self.seckey,
			"hexNumbers": self.hexNumbers,
			"connTimeout":self.connTimeout,
			"timeout":    self.timeout,
			"compression":self.compression,
			"timeWindow": self.timeWindow,
			"retryCount": self.retryCount,
			"retryDelay": self.retryDelay,
			"stopSignal": self.stopSignal,
		},
	def __setstate__(self, states):
		self.log         =states["log"]
		self.pubkey      =states["pubkey"]
		self.seckey      =states["seckey"]
		self.hexNumbers  =states["hexNumbers"]
		self.connTimeout =states["connTimeout"]
		self.timeout     =states["timeout"]
		self.compression =states["compression"]
		self.timeWindow  =states["timeWindow"]
		self.retryCount  =states["retryCount"]
		self.retryDelay  =states["retryDelay"]
		self.stopSignal  =states["stopSignal"]
		self.killFn      =states["killFn"]
		self.forceKillFd =states["forceKillFn"]
		self.id          =0
		self.requests    =weakref.WeakValueDictionary()
		self.socket      =None
	def __enter__(self):
		return self.clone()
	def __exit__(self, type, value, traceback):
		self.close()
	def _checkSocketError(self):
		if self.socket.error:
			err = self.socket.error
			self.socket.close()
			raise SocketError(err)
	def _connect(self, sendOlderRequests:bool=True):
		if not self.socket.isAlive():
			self.socket.connect()
			self._checkSocketError()
			self.log.info("Connected")
			if sendOlderRequests:
				objs = list(filter(lambda x: not x.isDone(), self.requests.values()))
				if objs:
					self.log.info("Sending {} previous requests".format(len(objs)))
					objs.sort(key=lambda x: x._requestTime)
					for chunk in chunks(list(map( lambda x: x._toJson(), objs)), self.max_bulk_request, self.max_payload):
						self.socket.send(chunk, self._createAuth(chunk))
	def _createAuth(self, data:bytes) -> str:
		if not self.seckey: return ""
		ts = int(time()+self.timeWindow).to_bytes(4, "big")
		return b"".join((
			ts,
			self.pubkey,
			hmac.digest(
				self.seckey,
				b"".join([
					ts,
					self.pubkey,
					sha256(data).digest(),
				]),
				sha256
			)
		)).hex()
	def _get(self, id:any) -> object:
		def wh():
			for obj in self.requests.values():
				if obj.getID() == id:
					if not obj.isDone():
						return True
					else:
						return False
			return False
		if id not in self.requests:
			raise ResponseError("Unknown request ID: {}".format(id))
		self.socket.loop(wh)
		self._checkSocketError()
		if id not in self.requests:
			raise ResponseError("Unknown request ID: {}".format(id))
		elif not self.requests[id].isDone():
			raise ResponseError("Did not get any response for ID: {}".format(id))
	def _gotResult(self, data:dict, connectionID:str, HTTPRequestID:str, JSONRequestID:str):
		if data['id'] not in self.requests:
			return
		obj = self.requests[data['id']]
		success = not ("error" in data and data["error"])
		self.log.info("Got result for ID: {}".format(data["id"]))
		uid = "-".join((connectionID, HTTPRequestID, JSONRequestID))
		self.log.info("Got result for UID: {}".format(uid))
		obj._parseResponse( uid, data )
	def _tryAgain(self, fn, *args, **kwargs) -> any:
		lastErr = None
		c = self.retryCount
		while True:
			try:
				return fn(*args, **kwargs)
			except Exception as err:
				lastErr = err
				if isinstance(err, (SocketError, ResponseError)):
					if c > 0:
						if c != self.retryCount:
							sleep(self.retryDelay)
						c -= 1
						self.connect()
						continue
				break
		raise lastErr from None
	def clear(self):
		self.requests.clear()
	def clone(self, **kwargs) -> object:
		opts = {
			"projectPublicKey":self.pubkey,
			"projectSecretKey":self.seckey,
			"hexNumbers":self.hexNumbers,
			"connectTimeout":self.connTimeout,
			"timeout":self.timeout,
			"compression":self.compression,
			"timeWindow":self.timeWindow,
			"retryCount":self.retryCount,
			"retryDelay":self.retryDelay,
			"log":self.log,
			"stopSignal":self.stopSignal,
		}
		opts.update(kwargs)
		return Client(**opts)
	def close(self):
		self.socket.close()
		self.clear()
	def connect(self):
		self.socket.close()
		self._tryAgain(self._connect)
	def createIterator(self, method:str, *args,
	sortBy:str=None, fromKey:hex=None, desc:bool=None, bitmask:int=None, chunks:int=12) -> object:
		if not method.startswith("iter"):
			raise InitializationError("For iterating you need choose method which name begins with `iter`.")
		kwargs = { "limit":chunks }
		if sortBy != None: kwargs["sortBy"] = sortBy
		if fromKey != None: kwargs["fromKey"] = fromKey
		if desc != None: kwargs["desc"] = desc
		if bitmask != None: kwargs["bitmask"] = bitmask
		return FEIterator(self, method, args, kwargs)
	def request(self, method:str, args:list=[], kwargs:dict={}, id:any=None):
		if id == None:
			id = self.id
			self.id += 1
		if type(id) not in [int, str]:
			raise RequestError("Request ID can be only str or int")
		if id in self.requests:
			raise RequestError("Request ID already in use: {}".format(id))
		obj = Request(
			[self._tryAgain, self._get],
			id,
			method,
			args,
			kwargs,
			self.hexNumbers
		)
		payload = json.dumps(obj._toJson()).encode("utf8")
		if len(payload) > self.max_payload:
			raise RequestError("Request payload too long")
		self.requests[id] = obj
		self.log.info("Request queued: {} [{}]".format(method, id))
		if not self.socket.isAlive():
			self.socket.close()
			self._tryAgain(self._connect, False)
		self.socket.send(payload, self._createAuth(payload))
		return obj

class Request:
	__slots__ = (
		"_getter", "_id", "_method", "_args", "_kwargs", "_hexNumbers", "_requestTime",
		"_responseTime", "_uid", "_done", "_success", "_response", "__weakref__"
	)
	def __init__(self, getter:callable, id:any, method:str, args:list, kwargs:dict, hexNumbers:bool):
		self._getter = getter
		self._id = id
		self._method = method
		self._args = args
		self._kwargs = kwargs
		self._hexNumbers = hexNumbers
		self._requestTime = time()
		self._responseTime = None
		self._uid = None
		self._done = False
		self._success = None
		self._response = None
	def _get(self):
		self._getter[0](self._getter[1], self._id)
	def _parseResponse(self, uid, data):
		self._done = True
		self._responseTime = time()
		self._uid = uid
		self._success = not ("error" in data and data["error"])
		self._response = data["result"] if self._success else data["error"]
	def _toJson(self) -> dict:
		return {
			"jsonrpc":"fsp1",
			"args":self._args,
			"kwargs":self._kwargs,
			"method":self._method,
			"id":self._id,
			"hexNumbers":self._hexNumbers
		}
	def get(self) -> any:
		if not self._done:
			self._get()
		return self._response
	def getDelay(self) -> float:
		if not self._done:
			self._get()
		return self._requestTime - self._responseTime
	def getID(self) -> any:
		return self._id
	def isDone(self) -> bool:
		return self._done
	def getUID(self) -> str:
		if not self._done:
			self._get()
		return self._uid
	def isSuccess(self) -> bool:
		if not self._done:
			self._get()
		return self._success

class FEIterator:
	def __init__(self, client:object, method:str, args:list, kwargs:dict):
		self.client = client
		self.method = method
		self.args = args
		self.kwargs = kwargs
		self.cache = []
	def __enter__(self):
		return self
	def __exit__(self, type, value, traceback):
		pass
	def __iter__(self):
		return self
	def __request__(self):
		if not self.cache:
			req = self.client.request(self.method, self.args, self.kwargs)
			data = req.get()
			if not req.isSuccess():
				raise ResponseError(data)
			if type(data) is list:
				self.cache = [ (x["key"], x["data"]) for x in data ]
	def __next__(self):
		self.__request__()
		if not self.cache:
			raise StopIteration
		key, data = self.cache.pop(0)
		self.kwargs["fromKey"] = key
		return key, data
	def checkNext(self):
		self.__request__()
		if not self.cache:
			raise StopIteration
		return self.cache[0]
	next = __next__
