"""
#!/usr/bin/python3


"""
import requests
import time
import json
import os, base64
import uuid
from config import base_config

if __name__ == '__main__':
    headers = {
        'Content-Type': 'application/json'
    }
    hotword_kb = {
        "input": ["阿里巴巴", "百度"],
        "businessID": "1024",
    }
    sensitive_kb = {
        "input": {"key1":["逾期", "发短信"], "key2": ["罚息", "喘气"]},
        "businessID": "1024",
    }

    sts_kb = {
        "input": {"服务态度":["跟我急也没用", "需要多久来周转？"], "态度":["跟我急也没用", "需要多久来周转？"]},
        "businessID": "1024",
    }
    hotword_url = 'http://%s:%s/audio/hotword_update' % (base_config.host, base_config.port)
    hotword_response = requests.post(hotword_url, headers=headers, data=json.dumps(hotword_kb))
    hotword_response = hotword_response.json()
    if hotword_response["code"] == 200:
        print(hotword_response["msg"])

    sensitive_url = 'http://%s:%s/audio/sensitive_update' % (base_config.host, base_config.port)
    sensitive_response = requests.post(sensitive_url, headers=headers, data=json.dumps(sensitive_kb))
    sensitive_response = sensitive_response.json()
    if sensitive_response["code"] == 200:
        print(sensitive_response["msg"])


    sts_url = 'http://%s:%s/audio/sts_update' % (base_config.host, base_config.port)
    sts_response = requests.post(sts_url, headers=headers, data=json.dumps(sts_kb))
    sts_response = sts_response.json()
    if sts_response["code"] == 200:
        print(sts_response["msg"])


    chat_url = 'http://%s:%s/audio/asr' % (base_config.host, base_config.port)
    filepath = os.path.join(os.path.dirname(__file__), "datasets/audio")
    idlist = os.listdir(filepath)
    start = time.time()
    index = 0
    for id in idlist:
        wavlist = os.listdir(os.path.join(filepath, id))
        for wav in wavlist:
            wav_path = os.path.join(filepath, id, wav)
            with open(wav_path, "rb") as file:
                base64_audio = base64.b64encode(file.read()).decode('utf-8')
            data = {
                "businessID":str(uuid.uuid4()),
                "input": base64_audio,
            }
            question_info_response = requests.post(chat_url, headers=headers, data=json.dumps(data))
            index += 1
            response = question_info_response.json()
            if response["code"]==200:
                result = response["data"]
            else:
                result = response["msg"]
            print('-------', wav_path, '-------\n', result)
    print('times:', time.time() - start, (time.time() - start) / index)
