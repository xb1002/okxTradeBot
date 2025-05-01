import sys
class webSocketOkxCheck:
    def __init__(self):
        pass

    # 静态方法
    @staticmethod
    def checkLoginStatus(msg:dict|str) -> bool:
        """
        检查登录状态，如果登录成功，返回True，否则返回False
        :param msg: 消息
        :return: 登录状态
        """
        status = False
        try:
            if isinstance(msg, dict):
                if msg["event"] == "login":
                    if msg["code"] == "0":
                        status = True
            if isinstance(msg, str):
                if msg == "pong":
                    status = True
            return status
        except Exception as e:
            raise Exception(f"Error in checkLoginStatus: {e}")
        
    @staticmethod
    def checkPingTimeParams(pingInterval:int, pingTimeout:int) -> bool:
        if pingInterval > pingTimeout:
            sys.exit("Error: Ping interval must be less than ping timeout")

    @staticmethod
    def checkLoginParams(login:bool, apikey:str|None, secretkey:str|None, passphrase:str|None) -> bool:
        """
        检查登录参数，如果参数检查不通过，结束程序
        :param login: 是否登录
        :param apikey: apiKey
        :param secretkey: secretKey
        :param passphrase: passphrase
        """
        if login:
            # 登录信息
            if not apikey or not secretkey or not passphrase:
                sys.exit("登录需要apikey, secretkey, passphrase，如不需要登录请设置login=False")