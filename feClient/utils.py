# Builtin modules
import zlib, signal, json
# Local modules
# Program
class deflate:
	@staticmethod
	def compress(data:bytes) -> bytes:
		o = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
		r = o.compress(data)
		r += o.flush()
		return r
	def decompress(data:bytes) -> bytes:
		o = zlib.decompressobj(-zlib.MAX_WBITS)
		r = o.decompress(data)
		r += o.flush()
		return r

class StopSignal:
	_i = False
	killed = False
	@classmethod
	def activate(self):
		assert self._i == False, "Aleady initialized"
		self._i = True
		signal.signal(signal.SIGINT, self.kill)
		return self
	@classmethod
	def kill(self, signum=None, frame=None):
		self.killed = True
	@classmethod
	def get(self):
		return self.killed

def hexToBytes(data:str) -> bytes:
	if data[:2].lower() == "0x":
		data = data[2:]
	return bytes.fromhex(data)

def chunks(lst, n, pl):
	r = []
	rl = [ json.dumps(d).encode("utf8") for d in lst ]
	sr = []
	srl = 2
	for i in range(len(rl)):
		sr.append(rl[i])
		srl += len(rl[i])
		if len(sr) == n or (len(rl)-1 > i and srl+len(rl[i+1])+len(sr) > pl):
			# Uj chunk kell!
			r.append(b"["+(b",".join(sr))+b"]")
			srl = 2
			sr = []
	if sr:
		r.append(b"["+(b",".join(sr))+b"]")
	return r
