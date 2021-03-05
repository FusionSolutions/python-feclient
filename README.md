# Fusion Explorer API python client

## Introduction

This utility makes easier to use Fusion Explorer API which uses JSON-RPC protocol.

## Installation

Requires python 3.8 or later version.

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

fec = Client()
request = fec.request("ping")
print(request.get())
```

**IMPORTANT**

Object sharing is **MAY NOT** safe for multi-threading/processing, do not share any initialized objects with another thread or process. If you want to use another thread or process you need [clone](#clone) it and give that as argument.

### Initialize Client
```python
feClient.Client(projectPublicKey:str=None, projectSecretKey:str=None, hexNumbers:bool=False, connectTimeout:int=15, timeout:int=320, compression:bool=True, timeWindow:int=60, retryCount=10, retryDelay=5, stopSignal:object=None, log:object=None)
```
| Parameter | Type | Default | Description |
| - | - | - | - |
| `projectPublicKey` | hex | `None` | Project public key - if available - 16 byte hex like: "9cd433f765a8818c1002241190deae51". |
| `projectSecretKey` | hex | `None` | Project secret key - if available - 16 byte hex like: "ace3ebb9a17b5b40b8b2bd87b92296b1". Required when `projectPublicKey` is used. |
| `hexNumbers` | bool | `False` | All integer in the result will be converted to hex (javascript compatible for big numbers). |
| `connectTimeout` | int | `15` | Connection timeout in second. |
| `timeout` | int | `320` | Send/Receive timeout in second. |
| `compression` | bool | `True` | Enable or disable compression for transmitting results. |
| `timeWindow` | int | `60` | Security time window for avoid old queries repeat attack. The amount is in seconds. |
| `retryCount` | int | `10` | How many retries should be have before Error raises during operation. |
| `retryDelay` | int | `5` | Delay in seconds between two retry. |
| `stopSignal` | object | `None` | Object ([example](#stopsignal)) with `get()` function which returns _true_ if we need to stop, and _False_ when not. |
| `log` | object | `None` | Logger object. If `None` given default will use built-in `logging.logger`. |

### `Client` API reference

#### Create request
```python
feClient.Client.request(method:str, args:list=[], kwargs:dict={}, id:any=None)
```
| Parameter | Type | Default | Description |
| - | - | - | - |
| `method` | str | | Method name |
| `args` | list | `[]` | Arguments of parameters |
| `kwargs` | dict | `{}` | Keyword arguments of parameters |
| `id` | any | `None` | ID of the request. If `None` given an automatic incremental number will be used. Do not reuse older values. |

Returns a [`feClient.Request`](#request-object) object.

#### Create iterator
```python
feClient.Client.createIterator(method:str, *args, sortBy:str=None, fromKey:hex=None, desc:bool=None, bitmask:int=None, chunks:int=12)
```
| Parameter | Type | Default | Description |
| - | - | - | - |
| `method` | | | Method name which need to begin with _iter_. |
| `*args` | argument list | | This parameter definition is given by the method. |
| `sortBy` | None | | Sorting definition. |
| `fromKey` | None | | Last referenced item ID. |
| `desc` | None | | Ordering option. If _True_ will be descending, when _False_ will be ascending. |
| `bitmask` | int | | Bitmask value. |
| `chunks` | 12 | | How many items should the iterator cache. |

Returns a [`feClient.FEIterator`](#feiterator-object) object.

Example usage:
```python
from feClient import Client

fec = Client()
it = fec.createIterator("iterTransactionInputs", "btc", "0x8c659902068f0af33849a6d49c4c92150bbb28a9d60c766e47379bbb04726ea0", chunks=5)
for key, data in it:
	print((key, data))
```
Example for continue iteration from the last element:
```python
from feClient import Client
from itertools import islice

fec = Client()

it = fec.createIterator("iterAddresses", "btc", sortBy="balance", desc=True, chunks=2)
for key, data in islice(it, 2):
	print((key, data))

it = fec.createIterator("iterAddresses", "btc", sortBy="balance", fromKey=key, desc=True, chunks=2)
for key, data in it:
	print((key, data))
```

#### `with` usage
The `Client` class has enter/exit functions, so you can use with `with` statement. You need to know, that on every enter, the client [clones](#clone) himself.

Example:
```python
from feClient import Client

fec = Client()

with fec as c:
	request = fec.request("ping")
	print(request.get())
```

#### Connect
```python
feClient.Client.connect()
```
Connect to server. It is automatic during request.

#### Close connection
```python
feClient.Client.close()
```
Closing connection and clear cache. It is automatic during deallocation.

#### Clear caches
```python
feClient.Client.clear()
```
Clearing request and response cache. It is automatic during deallocation.

#### Clone
```python
feClient.Client.clone(**kwargs)
```
This will return a brand new created [`Client`](#initialize-client) object which is completely reset/cleared. If you create a thread or process you need give the cloned object. You can give keyword arguments to replace some [initalization parameter](#initialize-client).

Example:
```python
import threading
from feClient import Client

fec = Client()

def threadFn(id, c):
	for i in range(2):
		request = c.request("ping")
		print(( id, request.get() ))

threads = []
for i in range(4):
	threads.append( threading.Thread(target=threadFn, args=(i, fec.clone())) )

for th in threads:
	th.start()

request = fec.request("ping")
print(( "Main", request.get() ))

for th in threads:
	th.join()
```

### Objects

#### Request object

You can create this object with [`feClient.Client.request`](#create-request) function.

Functions:
- `Request.get()`: Returns the request response. On any server error the `Client` will reconnect and send all un-responded requests again.
- `Request.getDelay()`: Returns the response delay in seconds as `float`.
- `Request.getID()`: Returns the request ID.
- `Request.isDone()`: Returns _True_ as a `bool` when response arrived, _False_ when not.
- `Request.getUID()`: Returns the unique response ID as `str`. On an issue report you can give this as reference.
- `Request.isSuccess()`: Returns _True_ when no error happened else return _False_ as a `bool`.

#### FEIterator object

You can create this object with [`feClient.Client.createIterator`](#create-iterator) function.

This is a simple iterator extended with the following functions:
- `it.__next__` and `it.next()`: Returns a tuple: ```( key, data )```. Technically pops the cache first item and returns it back. The key is the unique ID of the item, may you need reference this when you want continue the iteration later.
- `it.checkNext()`: This function returns the same as the `__next__`, but will not delete from the cache. Calling this function the iteration would not be moving forward. If there is nothing for next `StopIteration` will be raised.

### StopSignal
```python
feClient.StopSignal()
```
This is an example class which ready to use. If the process get _SIGINT_ signal, then during any request/get call will raise [StopSignalError](#Stop-signal-error)

### Exceptions

#### Stop signal error
```python
feClient.StopSignalError(Exception)
```
Will be raised when the process get _SIGINT_ signal.

#### Base error
```python
feClient.Error(Exception)
```
Example to catch errors:
```python
try:
  # some request..
except feClient.Error as err:
  print(err.message)
  # do something else..
```

#### Initialization error
```python
feClient.InitializationError(Error)
```
Will be raises when you give bad parameters during initializing the client.

#### Socket error
```python
feClient.SocketError(Error)
```
Will be raised when the client has lost the connection with the server or can not connect to it.

#### Request error
```python
feClient.RequestError(Error)
```
Will be raised when you give bad type for [`feClient.Client.request`](#create-request) `id` parameter or the `id` is already in use.

#### Response error
```python
feClient.ResponseError(Error)
```
Will be raised:
- when the server did not answered for the request or you did not have sent the request for that ID.
- when you give bad parameters to `createIterator` and server sends error back.

## Contribution

Bug reports, constructive criticism and suggestions are welcome. If you have some create an issue on [github](https://github.com/FusionSolutions/python-feclient/issues).

## API Limitations

Server limitations are very strict. As GUEST you will share resources with other GUEST sessions, currently one GUEST request can run at the same time.

Every project has his own resources and one request can run at the same time.

At the moment subscriptions are not free and can be requested in private.

## Copyright

All of the code in this distribution is Copyright (c) 2021 Fusion Solutions Kft.

The utility is made available under the GNU General Public license. The included LICENSE file describes this in detail.

## Warranty

THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE ENTIRE RISK AS TO THE USE OF THIS SOFTWARE IS WITH YOU.

IN NO EVENT WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MAY MODIFY AND/OR REDISTRIBUTE THE LIBRARY, BE LIABLE TO YOU FOR ANY DAMAGES, EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

Again, see the included LICENSE file for specific legal details.