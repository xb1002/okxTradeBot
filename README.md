# okxTradeBot

这是一个使用 okx api 实现的交易策略

数据获取部分已经完成，但交易逻辑需要自己写。
主要通过协程，使用 websocket 对数据进行实时获取。
其中`webSocketOkx.py`实现了 websocket 的登录、保存连接，断线重连的功能，通过订阅数据，返回的数据会交由`_msgProcess`函数处理，通过继承并重写`_msgProcess`方法，可以自定义数据的处理。
