from utils.logger import getLogger
import time
import json

logger = getLogger(__name__)

# 定时更新数据
def updateBasicInstrumentInfo(publicDataAPI,
                              basicInstrumentType:list[str] = ["SPOT", "MARGIN", "SWAP", "FUTURES"],
                              outputPath:str = "./data/basicInstrumentInfo/"):
    for instrumentType in basicInstrumentType:
        # 获取基础信息
        basicInfo = publicDataAPI.get_instruments(instType=instrumentType)
        if basicInfo['code'] != '0':
            logger.error(f"基础信息{instrumentType}更新失败, 详情: {basicInfo}")
            continue
        # 将结果写入./data/basicInstrumentInfo/{basicInstrumentType}.json中
        with open(outputPath+f"{instrumentType}.json", "w") as f:
            f.write(json.dumps(basicInfo['data'], indent=4))
        logger.info(f"基础信息{instrumentType}更新成功")
        time.sleep(5)

if __name__ == "__main__":
    import okx.PublicData as PublicData
    flag = "0"  # 实盘:0 , 模拟盘:1
    publicAPI = PublicData.PublicAPI(flag=flag)
    updateBasicInstrumentInfo(publicAPI)