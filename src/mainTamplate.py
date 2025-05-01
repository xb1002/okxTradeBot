import okx.Account as Account
import okx.PublicData as PublicData
import asyncio
from dotenv import load_dotenv
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from config import wsUrls, wsUrls_sim
from webSocketOkx import WebSocketOkx
from utils.logger import getLogger

logger = getLogger(__name__)

class OkxSocket(WebSocketOkx):
    def __init__(self, wsUrls, login, **kwargs):
        super().__init__(wsUrls, login, **kwargs)

    async def _msgProcess(self, msg):
        # 数据处理的逻辑
        pass
    
# 默认加载 .env 文件
load_dotenv(override=True)  

flag = "0"  # 实盘:0 , 模拟盘:1
if flag == "1":
    # 模拟盘初始化
    wsUrls = wsUrls_sim

# API登录信息初始化
apikey = os.getenv("OKX_API_KEY")
secretkey = os.getenv("OKX_API_SECRET")
passphrase = os.getenv("OKX_API_PASSPHRASE")
# okxAPI
publicDataAPI = PublicData.PublicAPI(flag=flag)