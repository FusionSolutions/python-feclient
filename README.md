[![Python tests](https://github.com/FusionSolutions/python-feclient/actions/workflows/python-package.yml/badge.svg?branch=master)](https://github.com/FusionSolutions/python-feclient/actions/workflows/python-package.yml)
# Python client for Fusion Explorer

## Introduction

This utility makes easier to use Fusion Explorer API which uses JSON-RPC protocol.

## Installation

Requires python version 3.7 or later.

To install the latest release on [PyPI](https://pypi.org/project/python-feclient/),
simply run:

```shell
pip3 install python-feclient
```

Or to install the latest version, run:

```shell
git clone https://github.com/FusionSolutions/python-feclient.git
cd python-feclient
python3 setup.py install
```

## Command Line Interface

**IMPORTANT**

The CLI utility downloads method and bitmask definitions from the server and stores it temporary for the terminal session. You can disable it when you set the following environment key: `FECLI_DISABLE_CACHE=1`

For get usage information please use:
```shell
$fexplorer-cli
```

## Python library

### Usage

Just import the `Client` class from the `feClient` library and it is ready to use.

Example for standard usage:
```python
from feClient import Client

with Client() as fec:
	request = fec.request("ping")
	print(request.get())
```

**IMPORTANT**

The initialized client is **NOT** safe for threads or multi-process at the same time, unless when you [`Client.clone`](#clone) it before you give it to the thread/process.

### Initialize Client
```python
feClient.Client(projectPublicKey:Optional[Union[str, bytes]]=None, projectSecretKey:Optional[Union[str, bytes]]=None, timeWindow:int=60, convertNumbers:Optional[str]=None, retryCount:int=10, retryDelay:Union[int, float]=5, connectTimeout:int=15, transferTimeout:int=320, disableCompression:bool=False, log:Optional[Logger]=None, signal:Optional[T_Signal]=None, target:Tuple[str, int]=("api.fusionexplorer.io", 443), httpHost:Optional[str]=None, ssl:bool=True)
```
| Parameter | Type | Default | Description |
| - | - | - | - |
| `projectPublicKey` | Optional[Union[str, bytes]] | `None` | Project public key - if available - 16 byte hex like: "0x9cd433f765a8818c1002241190deae51". |
| `projectSecretKey` | Optional[Union[str, bytes]] | `None` | Project secret key - if available - 16 byte hex like: "0xace3ebb9a17b5b40b8b2bd87b92296b1". **Required when `projectPublicKey` is used.** |
| `timeWindow` | int | `60` | Security time window for avoid old queries repeat attack. The amount is in seconds. |
| `convertNumbers` | Optional[str] | `None` | Please see [`numbers`](#numbers). |
| `retryCount` | int | `10` | How many retries should be have before Error raises during operation. |
| `retryDelay` | Union[int, float] | `5` | Delay in seconds between two retry. It can also be a fractal number like `0.25`. |
| `connectTimeout` | Union[int, float] | `15` | Socket connection timeout in second. It can also be a fractal number like `4.5`. |
| `transferTimeout` | Union[int, float] | `320` | Socket transfer/Receive timeout in second. It can also be a fractal number like `4.5`. |
| `disableCompression` | bool | `False` | Prohibit asking server for compressed response. |
| `log` | Optional[Logger] | `None` | Initialized `Logger` class from [python-fslogger](https://github.com/FusionSolutions/python-fslogger) package. |
| `signal` | Optional[T_Signal] | `None` | Signal, SoftSignal or HardSignal class from [python-fslsignal](https://github.com/FusionSolutions/python-fssignal) package. |
| `target` | Tuple[str, int] | `("api.fusionexplorer.io", 443)` | Explorer server address and port. May you  do not need set this. |
| `httpHost` | Optional[str] | `None` | HTTP `host` header during request. When is not set, then target data will be used. May you  do not need set this. |
| `ssl` | bool | `True` | Initialize SSL for the socket. May you do not need set this. |

### Numbers

If you need the integers in other format like hexadecimal, you can set `convertNumbers` during initialize. This option will be sent with every request, and the server will format the response before it sends back to the client.

Supported values:
- `None` or `"default"`: Protocol based predefined conversion. This client uses JSONRPC-P protocol which equals `"none"` for this value.
- `"none"`: Integers and floats will be not converted and stays in original type.
- `"str"`: Integers and floats will be converted into string. For example: `balance:int = 55` will be `balance:str = "55"``, and `percent:float = 3.14` will be `percent:str = "3.14"`
- `"hex"`: Integers and floats will be converted into string, but integers will be in hexadecimal format with `0x` prefix. For example: `balance:int = 55` will be `balance:str = "0x37"``, and `percent:float = 3.14` will be `percent:str = "3.14"`

### `Client` API reference

#### Create request
```python
Client.request(method:str, args:List[Any]=[], kwargs:Dict[str, Any]={}, id:Optional[Union[str, int]]=None, path:str="/") -> Request
```
| Parameter | Type | Default | Description |
| - | - | - | - |
| `method` | str | | Method name. |
| `args` | List[Any] | `[]` | Arguments of parameters. |
| `kwargs` | Dict[str, Any] | `{}` | Keyword arguments of parameters. |
| `id` | Optional[Union[str, int]] | `None` | Request identifier, for `None` a sequenced number will be used. **Do not** duplicate ID's in the same instance. |
| `path` | str | `/` | HTTP request path. May you  do not need set this. |
	
Returns a [`Request`](#request-object) object.

#### Create iterator
```python
feClient.Client.createIterator(method:str, *args:Any, sortBy:Optional[str]=None, fromKey:Optional[str]=None, desc:Optional[bool]=None, bitmask:Optional[int]=None, chunks:int=12)
```
| Parameter | Type | Default | Description |
| - | - | - | - |
| `method` | str | | Method name which need to begin with `iter`. |
| `*args` | List[Any] | | This parameter definition is given by the method. |
| `sortBy` | Optional[str] | `None` | Sorting definition key. |
| `fromKey` | Optional[str] | `None` | Last referenced item ID from where you want to continue the iteration. |
| `desc` | Optional[bool] | `None` | When `True` will be descending, when `False` will be ascending ordered. |
| `bitmask` | Optional[int] | `None` | Bitmask value. |
| `chunks` | int | 12 | Amount of the rows what the iterator should precache. |

Returns a [`feClient.FEIterator`](#feiterator-object) object with inside a **cloned** client.
You can read more [here](#feIterator-object).

Example usage:
```python
from feClient import Client

with Client() as fec:
	for key, data in fec.createIterator("iterTransactionInputs", "btc", "0x8c659902068f0af33849a6d49c4c92150bbb28a9d60c766e47379bbb04726ea0", chunks=5):
		print((key, data))
```
Example for continue iteration from the last element:
```python
from feClient import Client
from itertools import islice

with Client() as fec:
	for key, data in islice(fec.createIterator("iterAddresses", "btc", sortBy="balance", desc=True, chunks=2), 2):
		print(data)
	for key, data in fec.createIterator("iterAddresses", "btc", sortBy="balance", fromKey=key, desc=True, chunks=2):
		print(data)
		break
```

#### The `with` statement
The `Client` has enter/exit functions, so you can use with the `with` statement. **Attention** do not use the same instance when you are done with the statement, because on exit the socket will be closed and all states will be reset.

Example:
```python
from feClient import Client

fec = Client()

with fec as c:
	request = fec.request("ping")
	print(request.get())
```
#### Close connection
```python
feClient.Client.close()
```
Closing connection and reset all states.

#### Clear caches
```python
feClient.Client.clear()
```
Clearing request and response cache. It is automatic during de-allocation.

#### Clone
```python
feClient.Client.clone(**kwargs)
```
Creates a new [`Client`](#initialize-client) instance with the initialized parameters. When you use threading or multi-processing you should give an object like this forward. You can give keyword arguments to replace some [initialization parameter](#initialize-client).

Example:
```python
import threading
from feClient import Client

fec = Client()

def threadFn(id, c):
	for i in range(2):
		request = c.request("ping")
		print("Thread-{} : {}".format(id, request.get()))

threads = []
for i in range(4):
	threads.append( threading.Thread(target=threadFn, args=(i, fec.clone(convertNumbers="hex"))) )

for th in threads:
	th.start()

request = fec.request("ping")
print("Main : {}".format(request.get()))

for th in threads:
	th.join()
```

### Objects

#### Request object

You can create this object with [`feClient.Client.request`](#create-request) function.

Functions:
- `Request.get()`: Returns the request response. On any server error the `Client` will reconnect and send all non-responded requests again.
- `Request.getDelay()`: Returns the response delay in seconds as float.
- `Request.getID()`: Returns the request ID.
- `Request.isDone()`: Returns `True` when response arrived and `False` when not.
- `Request.getUID()`: Returns the unique response ID as `str`. On an issue report you can give this as reference.
- `Request.isSuccess()`: Returns `True` when no error happened else `False` when something went wrong.

#### FEIterator object

You can create this object with [`feClient.Client.createIterator`](#create-iterator) function.

This is a simple iterator extended with the following functions:
- `it.__next__()` and `it.next()`: Returns a tuple: ```( key, data )```. Technically pops the cache first item and returns it back. The key is the unique ID of the item, may you need reference this when you want continue the iteration later.
- `it.checkNext()`: This function returns the same as the `__next__`, but will not delete from the cache. Calling this function the iteration would not be moving forward. If there is nothing for next `StopIteration` will be raised.
- `it.hasNext()`: Will return `True` when next data exists, `False` when not.

### Exceptions

#### Base error
```python
feClient.BaseRPCError(Exception)
```
This is an `Exception` instance with a `message` attribute.
Example to catch errors:
```python
try:
  # some request..
except feClient.BaseRPCError as err:
  print(err.message)
  # or do something else..
```

#### Initialization error
```python
feClient.InitializationError(BaseRPCError)
```
Will be raises when you give bad parameters during initializing the client.

#### Socket error
```python
feClient.SocketError(BaseRPCError)
```
Will be raised when the client has lost the connection with the server or can not connect to it.

#### Message error
```python
feClient.MessageError(BaseRPCError)
```
Will be raised when the server gives an non-parseable response.

#### Request error
```python
feClient.RequestError(BaseRPCError)
```
Will be raised when you give bad type for [`feClient.Client.request`](#create-request) `id` parameter or the `id` is already in use.

#### Response error
```python
feClient.ResponseError(BaseRPCError)
```
Will be raised:
- when the server did not answered for the request or you did not have sent the request for that ID.
- When error happens during iteration of [`FEIterator`](#feiterator-object) object.

## Contribution

Bug reports, constructive criticism and suggestions are welcome. If you have some create an issue on [github](https://github.com/FusionSolutions/python-feclient/issues).

## API Limitations

Server limitations are very strict.
One way semaphores are used:
- Only one for the guests (GUEST session). For more details see above.
- One for each projects (PROJECT session).
- One for each user (USER session).

You will be sorted in GUEST session when:
- You don not not provide any auth.
- You provide invalid auth.
- Your subscription is expired.
- Your subscription has exceeded the daily quota.

For private subscribe request please send an [email](mailto:contact@fusionexplorer.io).

## Copyright

All of the code in this distribution is Copyright (c) 2021 Fusion Solutions Kft.

The utility is made available under the GNU General Public license. The included LICENSE file describes this in detail.

## Warranty

THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE ENTIRE RISK AS TO THE USE OF THIS SOFTWARE IS WITH YOU.

IN NO EVENT WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MAY MODIFY AND/OR REDISTRIBUTE THE LIBRARY, BE LIABLE TO YOU FOR ANY DAMAGES, EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

Again, see the included LICENSE file for specific legal details.