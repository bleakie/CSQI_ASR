import os, sys
from loguru import logger
from fastapi import FastAPI, Request

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from tools.asr import asr_engine
from tools.server_utils import logger, BaseResponse

app = FastAPI(title="CSQI-ASR API Server")


@app.post("/audio/asr")
async def asr_inference(request: Request) -> BaseResponse:
    json_post = await request.json()
    businessID = json_post.get('businessID')
    input = json_post.get('input')
    if None in [businessID, input]:
        msg = f"输入参数有误"
        logger.error(msg)
        return BaseResponse(code=404, msg=msg)
    try:
        result = await asr_engine.inference(businessID, input)
        if result["code"] == 200:
            logger.info(result["msg"])
            return BaseResponse(code=result["code"], data=result["data"], msg=result["msg"])
        else:
            logger.error(result["msg"])
            return BaseResponse(code=result["code"], msg=result["msg"])
    except Exception as e:
        msg = f"businessID: {businessID} 错误信息：{e}"
        logger.error(msg)
        return BaseResponse(code=404, msg=msg)


@app.post("/audio/hotword_update")
async def hotword_update_api(request: Request) -> BaseResponse:
    json_post = await request.json()
    businessID = json_post.get('businessID')
    input = json_post.get('input')
    if None in [businessID, input]:
        msg = f"输入参数有误"
        logger.error(msg)
        return BaseResponse(code=404, msg=msg)
    try:
        result = asr_engine.update_hotword(businessID, input)
        if result["code"] == 200:
            logger.info(result["msg"])
            return BaseResponse(code=result["code"], msg=result["msg"])
        else:
            logger.error(result["msg"])
            return BaseResponse(code=result["code"], msg=result["msg"])
    except Exception as e:
        msg = f"businessID: {businessID} 错误信息：{e}"
        logger.error(msg)
        return BaseResponse(code=404, msg=msg)



@app.post("/audio/sensitive_update")
async def sensitive_update_api(request: Request) -> BaseResponse:
    json_post = await request.json()
    businessID = json_post.get('businessID')
    input = json_post.get('input')
    if None in [businessID, input]:
        msg = f"输入参数有误"
        logger.error(msg)
        return BaseResponse(code=404, msg=msg)
    try:
        result = asr_engine.update_sensitive_word(businessID, input)
        if result["code"] == 200:
            logger.info(result["msg"])
            return BaseResponse(code=result["code"], msg=result["msg"])
        else:
            logger.error(result["msg"])
            return BaseResponse(code=result["code"], msg=result["msg"])
    except Exception as e:
        msg = f"businessID: {businessID} 错误信息：{e}"
        logger.error(msg)
        return BaseResponse(code=404, msg=msg)



@app.post("/audio/sts_update")
async def sts_update_api(request: Request) -> BaseResponse:
    json_post = await request.json()
    businessID = json_post.get('businessID')
    input = json_post.get('input')
    if None in [businessID, input]:
        msg = f"输入参数有误"
        logger.error(msg)
        return BaseResponse(code=404, msg=msg)
    try:
        result = asr_engine.update_sts_word(businessID, input)
        if result["code"] == 200:
            logger.info(result["msg"])
            return BaseResponse(code=result["code"], msg=result["msg"])
        else:
            logger.error(result["msg"])
            return BaseResponse(code=result["code"], msg=result["msg"])
    except Exception as e:
        msg = f"businessID: {businessID} 错误信息：{e}"
        logger.error(msg)
        return BaseResponse(code=404, msg=msg)