import okx.Account as Account
import okx.PublicData as PublicData
import asyncio
import time
import json
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from config import wsUrls, wsUrls_sim
from webSocketOkx import WebSocketOkx
from utils.logger import getLogger
from funcOnlyForMain import updateBasicInstrumentInfo

logger = getLogger(__name__)

class OkxSocket(WebSocketOkx):
    def __init__(self, wsUrls, login, **kwargs):
        super().__init__(wsUrls, login, **kwargs)

    async def _msgProcess(self, msg):
        try:
            msg = json.loads(msg)
        except:
            pass
        # 处理订阅
        if isinstance(msg,dict):
            if "event" in msg.keys() and msg['event'] in ["subscribe","unsubscribe"]:
                logger.info(msg)
                return
        # 处理消息
        await msgProcess(msg)
    
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

# tradePairs
tradePairs = ["BTC-USDT"]
# 更新basicInstrumentInfo
updateBasicInstrumentInfo(publicDataAPI)
# basicInstrumentInfo path ->
basicInstInfoDirPath = "./data/basicInstrumentInfo/"

# 全局变量保存数据,用于存储数据
basicInfoDf = pd.DataFrame(columns=['instId', 'instType', 'ctVal', 'ctValCcy', 'lotSz', 'minSz', 
                                    'alias', 'lever', 'listTime', 'expTime'])
lastPriceDf = pd.DataFrame(columns=['instId', 'lastUpateTime', 'markPrice'])
lastPriceDf.set_index("instId",inplace=True)
# retDf是一个矩阵，index是合约名称，列是也是合约名称，值是做多近期，做空远期的收益率
# aliasList = ["now", "this_week", "next_week", "this_month", "next_month", 
#              "quarter", "next_quarter", "third_quarter"]
# btcRetDf = pd.DataFrame(columns=aliasList, index=aliasList)
# ethRetDf = pd.DataFrame(columns=aliasList, index=aliasList)

# 初始化basicInfoDf
swapInstInfo_cache = None #->用完后删除
with open(basicInstInfoDirPath + "SWAP.json", "r") as f:
    swapInstInfo_cache = json.load(f)
    for inst in swapInstInfo_cache:
        if inst['instId'].strip('-SWAP') in tradePairs:
            basicInfoDf = basicInfoDf._append({
                'instId': inst['instId'],
                'instType': inst['instType'],
                'ctVal':inst['ctVal'],
                'ctValCcy':inst['ctValCcy'],
                'lotSz': inst['lotSz'],
                'minSz': inst['minSz'],
                'alias': inst['alias'] if inst['alias'] else "now",
                'lever': inst['lever'],
                'listTime': inst['listTime'],
                'expTime': inst['expTime']
            }, ignore_index=True)
del swapInstInfo_cache #->用完后删除
def updatefutureInstInfo():
    global basicInfoDf
    with open(basicInstInfoDirPath + "FUTURES.json", "r") as f:
        futureInstInfo_cache = json.load(f)
    for inst in futureInstInfo_cache:
        if sum([inst['instId'].startswith(pair) for pair in tradePairs]):
            basicInfoDf = basicInfoDf._append({
                'instId': inst['instId'],
                'instType': inst['instType'],
                'ctVal':inst['ctVal'],
                'ctValCcy':inst['ctValCcy'],
                'lotSz': inst['lotSz'],
                'minSz': inst['minSz'],
                'alias': inst['alias'],
                'lever': inst['lever'],
                'listTime': inst['listTime'],
                'expTime': inst['expTime']
            }, ignore_index=True)
updatefutureInstInfo()
logger.debug(f"\n{basicInfoDf}")

# aliasList
aliasList = basicInfoDf['alias'].unique().tolist()
btcRetDf = pd.DataFrame(columns=aliasList, index=aliasList)
ethRetDf = pd.DataFrame(columns=aliasList, index=aliasList)

# 获取数据
wsPublic = OkxSocket(wsUrls['public'], False)

def subscribeMarkPrice(instIds):
    channel = "mark-price"
    args = []
    for instId in instIds:
        args.append({"channel": channel, "instId": instId})
    # 订阅数据
    wsPublic.subscribe(args)

# 获取数据
def subscribeData():
    # 订阅
    instIds = basicInfoDf['instId'].to_list()
    subscribeMarkPrice(instIds)

# 计算收益
def calRet(buyPrice:str|float,sellPrice:str|float,startTime:str|int,endTime:str|int, feeRate=0.0005):
    # 转换成数字
    buyPrice, sellPrice, startTime, endTime = float(buyPrice), float(sellPrice), int(startTime), int(endTime)
    # 对买价买价调整
    buyPrice = buyPrice*(1+feeRate)
    sellPrice = sellPrice*(1-feeRate)
    # 这里的时间是毫秒级别
    dayDiff = ((endTime)-startTime)/1000/60/60/24
    ret = (1+(sellPrice-buyPrice)/buyPrice)**(365/dayDiff)
    return ret

# 数据处理
async def msgProcess(msg):
    global lastPriceDf
    instId = msg['arg']['instId']
    lastPriceDf.loc[instId,:] = {
        "lastUpateTime":msg['data'][0]['ts'],
        "markPrice":msg['data'][0]['markPx'],
    }

# 更新RetDf
def updataRetDf():
    global lastPriceDf, btcRetDf, basicInfoDf
    # 每隔10s计算一次btcRet
    lastPrice = lastPriceDf.copy()
    for i,aliasIndex in enumerate(aliasList):
        for j,aliasColumn in enumerate(aliasList):
            if i <= j:
                break
            try:
                indexOfI = basicInfoDf[(basicInfoDf['alias']==aliasIndex) & 
                                        (basicInfoDf['instId'].apply(lambda x: x.startswith('BTC')))].index[0]
                indexOfJ = basicInfoDf[(basicInfoDf['alias']==aliasColumn) & 
                                        (basicInfoDf['instId'].apply(lambda x: x.startswith('BTC')))].index[0]
                buyInstId, startTime = basicInfoDf.loc[indexOfJ,['instId','expTime']]
                sellInstId, endTime = basicInfoDf.loc[indexOfI,['instId','expTime']]
                buyPrice = lastPrice.loc[buyInstId,'markPrice']
                sellPrice = lastPrice.loc[sellInstId,'markPrice']
                if not startTime:
                    startTime = int(time.time()*1000)
                btcRetDf.loc[aliasIndex,aliasColumn] = calRet(buyPrice,sellPrice,startTime,endTime)
                logger.debug(f"buy {buyInstId} sell {sellInstId} ret {btcRetDf.loc[aliasIndex,aliasColumn]}")
            except Exception as e:
                logger.error(f"更新({aliasIndex},{aliasColumn})时出错, 错误信息:{e}")

async def test():
    for i in range(10):
        await asyncio.sleep(10)
        updataRetDf()
        logger.info(f"\n{btcRetDf}")


async def main():
    subscribeData()

    task1 = asyncio.create_task(test())

    taskMain0 = asyncio.create_task(wsPublic.initWebsocket())
    await taskMain0

asyncio.run(main())