import websockets
import asyncio
import json
import sys
from utils.login import getLoginParams
from utils.check import webSocketOkxCheck
from utils.logger import getLogger

logger = getLogger(__name__)

class LoginError(Exception):
    """自定义异常类，用于处理登录错误"""
    pass

class WebSocketOkx:
    def __init__(self, url, login, apiKey=None, secretkey=None, passphrase=None,**kwargs):
        # 保存登录参数
        self.url = url
        self.login = login
        self.apiKey = apiKey
        self.secretKey = secretkey
        self.passphrase = passphrase
        # 设置状态
        self.ws = None
        self.connected = False
        self.reconnectCount = 0
        self.pingIndex = 0
        self.pongIndex = 0
        self.subscribeList:list[dict] = []  # 订阅列表
        self.waitForSend:list[dict] = []  # 等待发送请求的列表，订阅和取消订阅的请求
        # 读取其他参数
        self.ping_interval = kwargs.get("ping_interval", 8)
        self.ping_timeout = kwargs.get("ping_timeout", 15)
        self.maxReconnect = kwargs.get("maxReconnect", 5)
        self.maxPingPongInterval = kwargs.get("maxPingPongInterval", 3)

        # 执行参数检查
        webSocketOkxCheck.checkLoginParams(self.login, self.apiKey, self.secretKey, self.passphrase)
        webSocketOkxCheck.checkPingTimeParams(self.ping_interval, self.ping_timeout)
        


    async def initWebsocket(self):
        """
        初始化WebSocket连接
        """
        await asyncio.gather(
            self.connectServer(),
            self.keepAlive(),
            self.msgProcess(),
            self.listenRequest()
        )

    async def keepAlive(self):
        """
        保持连接
        """
        while True:
            if self.connected:
                try:
                    await asyncio.sleep(self.ping_interval)
                    if self.connected:
                        self.pingIndex += 1
                        await self.ws.send("ping")
                        logger.debug("Ping sent")
                    if self.pingIndex > self.pongIndex + self.maxPingPongInterval:
                        logger.error(f"Websocket connect was disconnected")
                        await self.__reconnect()
                except Exception as e:
                    logger.error(f"Error in keepAlive: {e}")
                    await self.__reconnect()
            else:
                logger.debug("Not connected, waiting to connect...")
                await asyncio.sleep(0.5)

    async def connectServer(self):
        """
        连接到WebSocket服务器
        """
        try:
            logger.info("Connecting to WebSocket server...")
            if self.login:
                signParam = getLoginParams("login", self.apiKey, self.secretKey, self.passphrase)
                self.ws = await websockets.connect(self.url)
                await self.ws.send(signParam)
                msg = await self.ws.recv()
                msg = json.loads(msg)
            else:
                self.ws = await websockets.connect(self.url)
                await self.ws.send("ping")
                msg = await self.ws.recv()
            # 检查登录状态
            if (webSocketOkxCheck.checkLoginStatus(msg)):
                logger.info("WebSocketOkx login success!")
                self.connected = True
                self.reconnectCount = 0
                self.pingIndex = 0
                self.pongIndex = 0
                # 重新订阅之前的所有订阅
                if self.subscribeList:
                    for args in self.subscribeList:
                        await self.subscribe(args)
                if self.waitForSend:
                    for params in self.waitForSend:
                        await self.executeRequest(params)
            else:
                self.connected = False
                await self.ws.close()
                raise LoginError("WebSocketOkx login failed!\n msgInfo:{}".format(msg))
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.connected = False
            if self.ws:
                await self.ws.close()
            logger.info("Try to reconnect...")
            await self.__reconnect()

    async def __reconnect(self):
        """
        重连
        """
        self.reconnectCount += 1
        if self.reconnectCount > self.maxReconnect:
            logger.error("Max reconnect attempts reached, exiting...")
            return
        await asyncio.sleep(2 ** self.reconnectCount)
        logger.info(f"Reconnecting... Attempt {self.reconnectCount}")
        try:
            await self.connectServer()
        except Exception as e:
            logger.error(f"Reconnect failed: {e}")
            await self.reconnect()

    async def msgProcess(self):
        """
        处理消息
        """
        while True:
            if self.connected and self.ws:
                try:
                    msg = await asyncio.wait_for(self.ws.recv(), timeout=self.ping_timeout)
                    logger.debug(f"Received message: {msg}")
                    if msg == "pong":
                        self.pongIndex += 1
                    else:
                        await self._msgProcess(msg)
                except websockets.exceptions.ConnectionClosed:
                    logger.error("Connection closed")
                    self.ws = None
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
            else:
                logger.debug("Not connected, waiting to connect...")
                await asyncio.sleep(0.5)  # Avoid busy waiting
    
    async def _msgProcess(self, msg):
        """
        处理消息
        """
        pass

    async def listenRequest(self):
        """
        监听请求
        """
        while True:
            if self.waitForSend:
                if self.connected and self.ws:
                    params = self.waitForSend.pop(0)
                    await self.executeRequest(params)
                else:
                    logger.warning("exist request wait for sending but no connection")
                    await asyncio.sleep(0.5)
            await asyncio.sleep(0.5)

    async def executeRequest(self, params:dict):
        while True:
            if self.connected and self.ws:
                try:
                    await self.ws.send(json.dumps(params))
                    if params["op"] == "subscribe":
                        self.subscribeList.append(params["args"])
                        logger.debug(f"Subscribed to {params['args']}")
                    elif params["op"] == "unsubscribe":
                        self.subscribeList.remove(params["args"])
                        logger.debug(f"Unsubscribed from {params['args']}")
                    return True
                except Exception as e:
                    logger.error(f"Error executeRequest: {e}")
                    return False
            else:
                logger.debug("Not connected, waiting to connect...")
                await asyncio.sleep(0.5)

        
    def subscribe(self,args:list[dict]):
        op = "subscribe"
        params = {
            "op": op,
            "args": args
        }
        logger.debug(f"add subscribe request: {args}")
        self.waitForSend.append(params)
    
    def unsubscribe(self,args:list[dict]):
        op = "unsubscribe"
        params = {
            "op": op,
            "args": args
        }
        logger.debug(f"add unsubscribe request: {args}")
        self.waitForSend.append(params)

    
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(override=True)
    import os
    url = "wss://wspap.okx.com:8443/ws/v5/public"
    apikey = os.getenv("OKX_API_KEY")
    secretkey = os.getenv("OKX_API_SECRET")
    passphrase = os.getenv("OKX_API_PASSPHRASE")

    ws = WebSocketOkx(url, False, apikey, secretkey, passphrase)
    args = [{
        "channel": "price-limit",
        "instId": "LTC-USDT"
    }]
    
    async def main():
        task1 = asyncio.create_task(ws.initWebsocket())
        ws.subscribe(args)
        await task1

    
    asyncio.run(main())