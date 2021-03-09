# Builtin modules
import re, socket, select, ssl, json, traceback
from time import monotonic
# Local modules
from . import __version__
from .utils import deflate
from .exceptions import StopSignalError
# Program
MASKS = {
	"R":select.POLLIN | select.POLLPRI | select.POLLERR | select.POLLHUP | select.POLLNVAL,
	"W":select.POLLOUT | select.POLLERR | select.POLLHUP | select.POLLNVAL,
	"RW":select.POLLOUT | select.POLLIN | select.POLLPRI | select.POLLERR | select.POLLHUP | select.POLLNVAL
}
NOT_CONNECTED = 0
CONNECTING = 1
CONNECTED = 2

class ClientSocket:
	__slots__ = ("log", "client", "endpoint", "port", "ssl", "compression", "connTimeout", "dataTimeout", "signal", "headers",
		"poll", "readBuffer", "writeBuffer", "connectionStatus", "timeoutTimer", "sock", "sockFD", "mask", "error", "sslTimer")
	def __init__(self, client:object, endpoint:str, port:int, ssl:bool, compression:bool,
		connTimeout:int, dataTimeout:int, stopSignal:object):
		self.log = client.log.getChild("socket")
		self.log.info("Initializing..")
		self.client = client
		self.endpoint = endpoint
		self.port = port
		self.ssl = ssl
		self.compression = compression
		self.connTimeout = connTimeout
		self.dataTimeout = dataTimeout
		self.signal = stopSignal
		self.headers = [
			"POST / HTTP/1.1",
			"Host: {}:{}".format(self.endpoint, self.port),
			"User-Agent: Fusion Explorer client {}".format(__version__),
			"Accept: */*",
			"Connection: Keep-Alive",
			"Content-Type: application/json;charset=utf-8",
		]
		if self.compression:
			self.headers.append("Accept-Encoding: deflate")
		self.headers = "\r\n".join(self.headers)
		self.poll = select.poll()
		self._reset()
		self.log.info("Initialized")
	def _connect(self, initial:bool=False):
		if initial:
			self.log.info("Connecting to {}:{} ..".format(self.endpoint, self.port))
		cerr = self.sock.connect_ex((self.endpoint, self.port))
		if cerr in [socket.errno.EAGAIN, socket.errno.EINPROGRESS]:
			return
		elif cerr in [0, socket.errno.EISCONN]:
			self._connected()
		elif not initial:
			return self._onError("Connection failed {}[{}]".format(socket.errno.errorcode[cerr], cerr))
	def _connected(self):
		if self.ssl:
			self.sslTimer = monotonic()
			sslCtx = ssl.create_default_context()
			sslCtx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
			sslCtx.set_ciphers(
				":".join([
					"ECDHE-ECDSA-AES256-GCM-SHA384",
					"ECDHE-RSA-AES256-GCM-SHA384",
					"DHE-RSA-AES256-GCM-SHA384",
					"ECDHE-ECDSA-CHACHA20-POLY1305",
					"ECDHE-RSA-CHACHA20-POLY1305",
					"DHE-RSA-CHACHA20-POLY1305",
					"ECDHE-ECDSA-AES256-SHA384",
					"ECDHE-RSA-AES256-SHA384",
					"DHE-RSA-AES256-SHA256",
					"ECDHE-ECDSA-AES256-SHA",
					"ECDHE-RSA-AES256-SHA",
					"DHE-RSA-AES256-SHA",
					"RSA-PSK-AES256-GCM-SHA384",
					"DHE-PSK-AES256-GCM-SHA384",
					"RSA-PSK-CHACHA20-POLY1305",
					"DHE-PSK-CHACHA20-POLY1305",
					"ECDHE-PSK-CHACHA20-POLY1305",
					"AES256-GCM-SHA384",
					"PSK-AES256-GCM-SHA384",
					"PSK-CHACHA20-POLY1305",
					"ECDHE-PSK-AES256-CBC-SHA384",
					"ECDHE-PSK-AES256-CBC-SHA",
					"SRP-RSA-AES-256-CBC-SHA",
					"SRP-AES-256-CBC-SHA",
					"RSA-PSK-AES256-CBC-SHA384",
					"DHE-PSK-AES256-CBC-SHA384",
					"RSA-PSK-AES256-CBC-SHA",
					"DHE-PSK-AES256-CBC-SHA",
					"AES256-SHA",
					"PSK-AES256-CBC-SHA384",
					"PSK-AES256-CBC-SHA"
				])
			)
			self.sock = sslCtx.wrap_socket(self.sock, do_handshake_on_connect=False, server_hostname=self.endpoint)
			self.log.debug("SSL handshake")
		self.connectionStatus = CONNECTING
		self._setMask("RW")
		if not self.ssl:
			self.connectionStatus = CONNECTED
			connectionDelay =  monotonic()-self.timeoutTimer
			self.timeoutTimer = monotonic()
			self.log.info("Connected in {:.3F} sec".format(connectionDelay))
			return True
	def _createSocket(self):
		if self.sock:
			return
		self._reset()
		self.sock = socket.socket()
		self.sock.setblocking(0)
		self.sockFD = self.sock.fileno()
		self.mask = "R"
		self.poll.register(self.sockFD, MASKS[self.mask])
		self.log.info("Socket created: {}".format(self.sockFD))
	def _doSSLHandshake(self):
		try:
			self.sock.do_handshake()
		except ssl.SSLWantReadError:
			self._setMask("R")
			return
		except ssl.SSLWantWriteError:
			self._setMask("W")
			return
		except Exception as err:
			return self._onError("SSL Handsake error")
		self._setMask("RW")
		connectionDelay =  monotonic()-self.timeoutTimer
		self.log.info("Connected in {:.3F} sec [SSL: {:.3F} sec]".format(connectionDelay, monotonic()-self.sslTimer))
		self.connectionStatus = CONNECTED
		return True
	def _haveRead(self) -> bool:
		data = None
		if self.ssl and self.connectionStatus == CONNECTING:
			return self._doSSLHandshake()
		try:
			data = self.sock.recv(16<<20)
		except ssl.SSLWantReadError:
			self._setMask("R")
			return
		except ssl.SSLWantWriteError:
			self._setMask("W")
			return
		except BlockingIOError:
			pass
		except ConnectionRefusedError:
			return self._onError("Connection {}".format("broken" if self.connectionStatus == CONNECTED else "refused"))
		except:
			return self._onError("Unkown error: {}".format(traceback.format_exc()))
		if data:
			self.readBuffer += data
			self.log.debug(data)
			self.log.info("Read {} bytes [{} bytes in buffer]".format(len(data), len(self.readBuffer)))
			if self._parseReadBuffer():
				return True
			self.timeoutTimer = monotonic()
		else:
			return self._onError("Connection broken")
	def _haveWrite(self) -> bool:
		sentLength = 0
		if self.connectionStatus == NOT_CONNECTED:
			return self._connect()
		if self.connectionStatus == CONNECTING and self.ssl:
			return self._doSSLHandshake()
		if not self.writeBuffer:
			self._setMask("R")
			return
		try:
			sentLength = self.sock.send(self.writeBuffer)
		except ssl.SSLWantReadError:
			self._setMask("R")
		except ssl.SSLWantWriteError:
			self._setMask("W")
		except BrokenPipeError:
			return self._onError("Connection broken")
		if sentLength:
			self.timeoutTimer = monotonic()
			self.log.debug(self.writeBuffer[:sentLength])
			self.writeBuffer = self.writeBuffer[sentLength:]
			self.log.info("Sent {} bytes [{} still in buffer]".format(sentLength, len(self.writeBuffer)))
		if not self.writeBuffer:
			self._setMask("R")
		return False
	def _onError(self, err:str):
		self.log.error(err)
		self.error = err
		return True
	def _parseReadBuffer(self):
		endLine = b"\r\n"
		pos = self.readBuffer.find(endLine*2)
		if pos == -1:
			endLine = b"\n"
			pos = self.readBuffer.find(endLine*2)
		elif pos > 4096:
			return self._onError("HTTP headers are too long")
		while pos != -1:
			rawData = self.readBuffer[pos+len(endLine)*2:]
			rawHeaders = self.readBuffer[:pos].decode("ISO-8859-1").split(endLine.decode("ISO-8859-1"))
			if not rawHeaders:
				return self._onError("Invalid HTTP headers")
			httpResponse = rawHeaders.pop(0).split(" ")
			if len(httpResponse) < 2:
				return self._onError("Invalid HTTP response")
			if httpResponse[1] == "503":
				return self._onError("Server offline")
			elif httpResponse[1] != "200":
				return self._onError("Request failure")
			#
			headers = {}
			for rawHeader in rawHeaders:
				s = rawHeader.find(":")
				if s <= 0 or s > 64:
					return "Header key too long"
				headers[ rawHeader[:s].strip().lower() ] = rawHeader[s+1:].strip()
			cLength = headers.get("content-length", "")
			if not cLength.isdigit():
				return self._onError("Invalid HTTP header value for content-length")
			cLength = int(cLength)
			if cLength < 0:
				return self._onError("Invalid HTTP header value for content-length")
			cEncoding = headers.get("content-encoding", "")
			if cEncoding == "":
				compression = False
			elif cEncoding == "deflate":
				compression = True
			else:
				return self._onError("Request HTTP encoding not supported")
			cType = headers.get("content-type", "")
			if cType == "":
				return self._onError("Invalid HTTP header value for content-type")
			cTypeS = re.findall("charset=([^ ]*)", cType, re.I)
			charset = cTypeS[0] if len(cTypeS) == 1 else "iso-8859-1"
			try:
				"".encode(charset)
			except:
				return self._onError("Not supported charset")
			#
			if cLength != len(rawData):
				return False
			#
			self.readBuffer = self.readBuffer[pos+len(endLine)*2+cLength:]
			try:
				if compression:
					data = json.loads( deflate.decompress(rawData[:cLength]).decode(charset) )
				else:
					data = json.loads( rawData[:cLength].decode(charset) )
			except:
				return self._onError("Invalid response content")
			if type(data) is list:
				for d, uid in zip(data, headers.get("x-jsonrequestid", ","*len(data)).split(",")):
					self.client._gotResult(
						d,
						headers.get("x-connectionid", ""),
						headers.get("x-httprequestid", ""),
						uid
					)
			else:
				self.client._gotResult(
					data,
					headers.get("x-connectionid", ""),
					headers.get("x-httprequestid", ""),
					headers.get("x-jsonrequestid", ""),
				)
			pos = self.readBuffer.find(endLine*2)
	def _removeMask(self):
		self.mask = None
		try: self.poll.unregister(self.sockFD)
		except: pass
	def _reset(self):
		self.readBuffer = b""
		self.writeBuffer = b""
		self.connectionStatus = NOT_CONNECTED
		self.timeoutTimer = 0
		self.sock = None
		self.sockFD = None
		self.mask = None
		self.error = None
		self.sslTimer = None
	def _setMask(self, newMask:str):
		if self.mask != newMask:
			self.poll.modify(self.sockFD, MASKS[newMask])
			self.mask = newMask
	def _write(self, data:bytes):
		self.writeBuffer += data
		self._setMask("RW")
	def close(self):
		if self.sock:
			self._removeMask()
			try: self.sock.close()
			except: pass
			self._reset()
			self.log.info("Closed")
	def connect(self):
		if self.connectionStatus != NOT_CONNECTED:
			return
		self._createSocket()
		self.timeoutTimer = monotonic()
		self._setMask("W")
		self._connect(initial=True)
		self.loop(lambda:not self.isConnected())
	def isAlive(self) -> bool:
		return not (
			(self.connectionStatus == NOT_CONNECTED) or
			(self.connectionStatus == CONNECTING and monotonic()-self.timeoutTimer > self.connTimeout) or
			(self.connectionStatus == CONNECTED and monotonic()-self.timeoutTimer > self.dataTimeout)
		)
	def isConnected(self):
		return self.connectionStatus == CONNECTED
	def loop(self, whileFn:callable=None):
		checkTimer = monotonic()
		while True and (whileFn == None or whileFn()):
			if self.signal.get():
				raise StopSignalError()
			if monotonic()-checkTimer >= 1:
				checkTimer = monotonic()
				if not self.isAlive():
					return self._onError("Timeout")
			for fd, bitmask in self.poll.poll(100):
				if fd != self.sockFD: continue
				readable = bool(bitmask & (select.POLLIN | select.POLLPRI))
				writeable = bool(bitmask & select.POLLOUT)
				error = bool(bitmask & (select.POLLERR | select.POLLHUP | select.POLLNVAL))
				# self.log.debug("Poll result: {}{}{}".format(
				# 	"read " if readable else "",
				# 	"write " if writeable else "",
				# 	"error " if error else "",
				# ))
				isConnected = self.connectionStatus == CONNECTED
				if readable and self._haveRead():
					if isConnected:
						self.close()
					return
				if writeable and self._haveWrite():
					if isConnected:
						self.close()
					return
				if error:
					self.log.error("Client socket broken")
					return self.close()
	def send(self, data:bytes, auth:str=None):
		if self.connectionStatus == CONNECTED:
			headers = self.headers
			if auth:
				headers += "\r\nX-Auth: {}".format(auth)
			headers += "\r\nContent-Length: {}\r\n\r\n".format(len(data))
			self._write( headers.encode("iso-8859-1") + data )