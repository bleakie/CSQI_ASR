import json, base64
import os
import shutil
import uuid

import streamlit as st
import requests
from pathlib import Path
from config import base_config

headers = {
    'Content-Type': 'application/json'
}
chat_url = 'http://%s:%s/audio/asr' % (base_config.host, base_config.port)
# st.title("语音识别")
hot_words = st.text_input("请输入专有名词[选填]", "")
uploaded_file = st.file_uploader("选择一个文件上传", type=["mp3", "wav"])
if uploaded_file is not None:
    hot_words = hot_words.split("#")
    if hot_words[0]=="":hot_words=[]
    st.audio(uploaded_file)
    file_path = Path('./temp_dir') / uploaded_file.name
    with file_path.open(mode="wb") as f:
        f.write(uploaded_file.getvalue())
    with open(file_path.as_posix(), "rb") as file:
        base64_audio = base64.b64encode(file.read()).decode('utf-8')
    data = {"businessID":str(uuid.uuid4()), "input":base64_audio}#, "hotword":hot_words
    if st.button('提交'):
        response = requests.post(chat_url, headers=headers, data=json.dumps(data))
        response = response.json()
        if response["code"] == 200:
            for tmp in response["data"]:
                role = tmp["role"]
                text = tmp["text"]
                if tmp["emo"] == 0:
                    with st.chat_message(name=role, avatar=role):
                        st.markdown(text)
                elif tmp["emo"] > 0:
                    with st.chat_message(name=role, avatar=role):
                        st.markdown(f"<div style=color:blue;'>{text}</div>", unsafe_allow_html=True)
                else:
                    with st.chat_message(name=role, avatar=role):
                        st.markdown(f"<div style=color:red;'>{text}</div>", unsafe_allow_html=True)
        else:
            st.error(response["msg"])
        os.remove(file_path.as_posix())