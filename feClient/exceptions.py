# Builtin modules
# Local modules
# Program
class Error(Exception):
	def __init__(self, typ:str, message:str):
		self.message = "{}: {}".format(typ, message)
		super().__init__(self.message)

class InitializationError(Error):
	def __init__(self, message:str):
		super().__init__("Initialization error", message)

class SocketError(Error):
	def __init__(self, message:str):
		super().__init__("Socket error", message)

class RequestError(Error):
	def __init__(self, message:str):
		super().__init__("Request error", message)

class ResponseError(Error):
	def __init__(self, message:str):
		super().__init__("Response error", message)

class StopSignalError(Exception): pass
