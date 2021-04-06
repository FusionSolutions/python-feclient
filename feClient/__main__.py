# Builtin modules
import logging, unittest
# Own modules
# Local modules
# Program
from .client import Client, Request, FEIterator

class ClientTest(unittest.TestCase):
	def test1(self):
		fec = Client(log=logging.getLogger("test1.Client"))
		self.assertIs(type(fec), Client)
		with fec as c:
			obj = c.request("ping")
			self.assertIs(type(obj), Request)
			self.assertEqual(obj.isSuccess(), True)
			self.assertIs(type(obj.get()), int)
	def test2(self):
		fec = Client(log=logging.getLogger("test2.Client"))
		self.assertIs(type(fec), Client)
		obj = fec.request("ping")
		self.assertIs(type(obj), Request)
		self.assertEqual(obj.isSuccess(), True)
		self.assertIs(type(obj.get()), int)
	def test3(self):
		fec = Client(log=logging.getLogger("test3.Client"))
		objs = fec.request("ping"), fec.request("ping")
		fec.socket.close()
		for obj in objs:
			self.assertIs(type(obj.get()), int)
	def test4(self):
		from itertools import islice
		fec = Client(log=logging.getLogger("test4.Client"))
		inputAddresses = [
			"0x04222cdcba67350ae6ccf038dfb335648bb439d64b212dd1cd3a5ee112ff76de25d026214c36877577fd9eb4fafa6d52100367256f54157be4b339a8f49837206e",
			"0x04da43d782c6506b926e9f5f7627ff62e8fc1e3c55ac5d22729a600743cfb98e0c2376ccd2d636ceb45a5a8630d31ff14253a60ffd2aabce6036b766ac73d4013b",
			"0x047e3d8d5a05808cb46089dc7cc78633b5b2f8760f9a8c9a54736980348c8a2b05f72840038f8475178e4265ae30c1b1f25a3d3c7806c18cea38111dc9ba596cd5",
			"0x04c3f849fb3dcc29a4c1b02a6003ae68f9536182ad3a027f18548754e1c4eac3a31d3fb4f7ce5eb129d78bbe04d05bfc52599ff756c858f50e3bfc0c11074842c2",
			"0x044889c277d5191153701e0e686d6388c7e427087f716b079d8697583cba7cd6c66ca44791286cc5a69eb6b61ef9fb88a4315ba6bac75d17ec114d2168bedebda7",
			"0x04b5cc3e2c3ab73de6445c9adbe67e189a3acaa95aa0a328705c42d4cff747b0b2e3f63ad0ff231d7598d98a0b6d5ed199ec2831928bff1e9ee59de7dea9b8f6a5",
			"0x04da40df988e0b0f0dff125cce7b7a120b870641fa95147d96513334111c852b5c1c36b5661c56034a00fba43c23112f309016fd08a572a9cd8e15d401f2732461",
			"0x045d4944869283654e775307eb4ddfdc0d261395a4bf9c76916bc09f2b2e534a7051331a433c0eb6db01448fb1c752b69a80c79e4ab4fc2976810b57e1e4660b7a",
			"0x045af7f44a5bb9938dbeb5130e8c6e42fbb3196f4fcec508bce8d5eae3404c1ae65a6d2522c53d9d67d4b6d315b15ae2a13c8be985afb3c3113c821723075c48d7",
			"0x0480dc2647ef1aed071be6092c16c7f936f04008c3d4ccedd6ef4b380058cec5e1e6890d7a6c542604ec72422612d82b055e149e3e28c10335576ca2e578a15268",
		]
		it = fec.createIterator("iterTransactionInputs", "btc", "0x8897ea9ceaf18a546cdc513b9179bae31a462ee5bf47818eb7ba909082d11777", chunks=2)
		self.assertIs(type(it), FEIterator)
		for i, (key, data) in islice(enumerate(it), 3):
			self.assertEqual(inputAddresses[i], data["address"])
		for i, (key, data) in islice(enumerate(it, 3), 1):
			self.assertEqual(inputAddresses[i], data["address"])
		it = fec.createIterator("iterTransactionInputs", "btc", "0x8897ea9ceaf18a546cdc513b9179bae31a462ee5bf47818eb7ba909082d11777", fromKey=key, chunks=2)
		for i, (key, data) in enumerate(it, 4):
			self.assertEqual(inputAddresses[i], data["address"])
	def test5(self):
		class Dummy:
			def do(self, c):
				for i in range(5):
					c.request("ping").get()
		from itertools import islice
		fec = Client(log=logging.getLogger("test5.Client"))
		objs = [ fec.request("ping") for i in range(5) ]
		for obj in objs:
			obj.get()
		self.assertEqual( 5, len(list(fec.requests.itervaluerefs())) )
		objs = None
		self.assertNotEqual( 5, len(list(fec.requests.itervaluerefs())) )
		fec.clear()
		d = Dummy()
		d.do(fec)
		del d
		self.assertEqual( 0, len(list(fec.requests.itervaluerefs())) )
	def test6(self):
		fec = Client(log=logging.getLogger("test6.Client"), compression=False)
		objs = [fec.request("ping"), fec.request("ping")]
		fec.connect()
		objs.append(fec.request("ping"))
		fec.socket.close()
		for obj in objs:
			self.assertIs(type(obj.get()), int)
	def test7(self):
		fec = Client(log=logging.getLogger("test7.Client"), compression=False)
		objs = [fec.request("ping"), fec.request("ping")]
		fec.connect()
		objs.append(fec.request("ping"))
		for obj in objs:
			self.assertIs(type(obj.get()), int)
	def test8(self):
		fec = Client("a344613fe3d9ea517ffa0e89e645cdbc", "417e9e027bcd7efb89d250a7cbf701b4", log=logging.getLogger("test8.Client"), compression=False)
		obj = fec.request("sleepWell", [1])
		if obj.isSuccess():
			self.assertEqual(obj.get(), True)

logging.basicConfig(format='[%(levelname).3s][%(asctime)s][%(name)s]: %(message)s', level=logging.INFO)
unittest.main(verbosity=0)
