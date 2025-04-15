import os
from easydict import EasyDict as edict

base_config = edict()
base_config.LOG_PATH = os.path.join(os.path.dirname(__file__), "log")
if not os.path.exists(base_config.LOG_PATH):
    os.mkdir(base_config.LOG_PATH)

# ============= data_file_path ===========#
base_config.llm_url = "http://0.0.0.0:9997"
base_config.ncpu = 6
base_config.workers = 1
base_config.port = 10096
base_config.host = "0.0.0.0"
base_config.user_id = "left"
base_config.base_hotword = "models/hotwords.txt"
base_config.base_sensitive = "models/sensitive.xlsx"
base_config.base_autocomplete = "models/sts.xlsx"
base_config.asr_model = "models/SenseVoiceSmall"
base_config.vad_model = 'models/speech_fsmn_vad_zh-cn-16k-common-pytorch'