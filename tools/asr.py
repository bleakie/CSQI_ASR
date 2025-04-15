import os
import sys
import uuid
import torch
import base64
import pandas as pd
import time, json
import torchaudio
import ffmpeg
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.dirname(__file__))
from config import base_config
from funasr import AutoModel
from tools.sts import STS
from tools.server_utils import logger
from tools.sensitive_words import WordsSearch
from pycorrector.proper_corrector import ProperCorrector
from funasr.utils.postprocess_utils import rich_transcription_postprocess


class ASR:
    def __init__(self, ):
        self.user_id = base_config.user_id
        self.sample_rate = 16000
        self.asr_model_path = os.path.join(os.path.dirname(__file__), '..', base_config.asr_model)
        self.vad_model_path = os.path.join(os.path.dirname(__file__), '..', base_config.vad_model)
        self.base_hotword = os.path.join(os.path.dirname(__file__), '..', base_config.base_hotword)
        self.base_sensitive = os.path.join(os.path.dirname(__file__), '..', base_config.base_sensitive)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.asr_model = AutoModel(
            model=self.asr_model_path,
            vad_model=self.vad_model_path,
            vad_kwargs={"max_single_segment_time": 30000},
            ncpu=base_config.ncpu,
            device=device,
            disable_update=True,
        )
        logger.info("init model...")
        self.param_dict = {"language": "zh",
                           "batch_size_s": 32,
                           "use_itn": True,
                           "cache": {}}
        self.HotWordCorrector = ProperCorrector(proper_name_path=self.base_hotword)
        proper_names = [len(proper_name) for proper_name in self.HotWordCorrector.proper_names]
        self.max_word_length, self.min_word_length = max(proper_names), min(proper_names)
        sheet = pd.read_excel(self.base_sensitive)
        self.sensitive_words, values = {}, []
        for col in sheet.columns:
            value = sheet[col].dropna().tolist()
            self.sensitive_words[col] = value
            values.extend(value)
        self.SensitiveDetector = WordsSearch()
        self.SensitiveDetector.SetKeywords(values)
        self.STS = STS()

    def update_hotword(self, businessID, data) -> dict:
        if len(data) > 0:
            self.HotWordCorrector.proper_names = set(data)
            msg = f"{businessID} update hotword success"
            return dict(code=200, msg=msg)
        else:
            msg = f"{businessID} update hotword failed"
            return dict(code=404, msg=msg)

    def update_sensitive_word(self, businessID, data) -> dict:
        if len(data) > 0:
            values = []
            for key in data.keys():
                for value in data[key]:
                    values.append(value)
            self.SensitiveDetector.SetKeywords(values)
            self.sensitive_words = data.copy()
            msg = f"{businessID} update sensitive word success"
            return dict(code=200, msg=msg)
        else:
            msg = f"{businessID} update sensitive word failed"
            return dict(code=404, msg=msg)

    def update_sts_word(self, businessID, data) -> dict:
        if len(data) > 0:
            self.STS.SetKeywords(data)
            msg = f"{businessID} update sts word success"
            return dict(code=200, msg=msg)
        else:
            msg = f"{businessID} update sts word failed"
            return dict(code=404, msg=msg)

    def merge_overlapping(self, text_left, text_right, duration=500):
        def __merge_interval(result, duration=300):
            merged = []
            if len(result) > 0:
                last = result[0].copy()
                for interval in result[1:]:
                    if interval['timestamp'][0] - last['timestamp'][1] < duration:
                        last['text'] += interval["text"]
                        last['emo'] = min(last["emo"], interval["emo"])
                        last['timestamp'][1] = interval["timestamp"][1]
                    else:
                        merged.append(last)
                        last = interval.copy()
                merged.append(last)
            return merged

        if self.user_id == "left":
            left_role, right_role = "user", "assistant"
        else:
            left_role, right_role = "assistant", "user"
        res_left, res_right = [], []
        for i in range(len(text_left)):
            distance = text_left[i]["timestamp"][1] - text_left[i]["timestamp"][0]
            res_left.append({"role": left_role, "timestamp": text_left[i]["timestamp"], "text": text_left[i]["text"],
                             "emo": text_left[i]["emo"] if distance > 4 * duration else 0})
        # res_left = __merge_interval(res_left)
        for i in range(len(text_right)):
            distance = text_right[i]["timestamp"][1] - text_right[i]["timestamp"][0]
            res_right.append({"role": right_role, "timestamp": text_right[i]["timestamp"], "text": text_right[i]["text"],
                             "emo": text_right[i]["emo"] if distance > 4 * duration else 0})
        # res_right = __merge_interval(res_right)
        res_merge = res_left + res_right
        output_merged = []
        if len(res_merge) > 0:
            res_merge.sort(key=lambda x: x['timestamp'][0])
            last = res_merge[0].copy()
            for interval in res_merge[1:]:
                cur_duration = interval['timestamp'][0] - last['timestamp'][1]
                if last['role'] == interval['role'] and cur_duration < 8 * duration:
                    last['text'] += interval["text"]
                    last['emo'] = min(last["emo"], interval["emo"])
                    last['timestamp'][1] = interval["timestamp"][1]
                else:
                    output_merged.append(last)
                    last = interval.copy()
            output_merged.append(last)
        return output_merged

    async def audio_process(self, audio_input):
        def process_audio_channel(audio_data, sample_rate):
            output, _ = (
                ffmpeg.input('pipe:', format='f32le', ac=1, ar=sample_rate)
                .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=self.sample_rate)
                .run(input=audio_data, capture_stdout=True, capture_stderr=True)
            )
            return output

        audio_bytes_left, audio_bytes_right = None, None
        audio_bytes = base64.b64decode(audio_input)

        audio_file = BytesIO(audio_bytes)
        waveform, sample_rate = torchaudio.load(audio_file)
        if waveform.size()[1] < sample_rate:
            return None, None
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_left = executor.submit(
                process_audio_channel,
                waveform[0].numpy().tobytes(),
                sample_rate
            )
            if waveform.size()[0] == 2:
                future_right = executor.submit(
                    process_audio_channel,
                    waveform[1].numpy().tobytes(),
                    sample_rate
                )
                audio_bytes_right = future_right.result()

            audio_bytes_left = future_left.result()
        return audio_bytes_left, audio_bytes_right

    async def inference(self, businessID, input) -> dict:
        # 1.load data
        audio_bytes_left, audio_bytes_right = await self.audio_process(input)
        if audio_bytes_left is None and audio_bytes_right is None:
            msg = f"businessID: {businessID} 音频读取异常"
            return dict(code=404, msg=msg)
        # 2.left channel asr
        rec_results_left = self.asr_model.generate(input=audio_bytes_left, **self.param_dict)[0]
        res_left = rich_transcription_postprocess(rec_results_left)
        res_right = []
        if audio_bytes_right is not None:  # multi channel
            rec_results_right = self.asr_model.generate(input=audio_bytes_right, **self.param_dict)[0]
            res_right = rich_transcription_postprocess(rec_results_right)
        res_merge = self.merge_overlapping(res_left, res_right)

        text_list = [res["text"] for res in res_merge]
        sts_words = [self.STS.get_top_context(text) for text in text_list]
        text_correct = self.HotWordCorrector.correct_batch(text_list, sim_threshold=0.8,
                                                           max_word_length=self.max_word_length,
                                                           min_word_length=self.min_word_length, cut_type="word")
        for idx, res in enumerate(res_merge):
            res_merge[idx]["text"] = text_correct[idx]['target']
            _sensitive_list = self.SensitiveDetector.FindAll(res_merge[idx]["text"])
            sensitive_list = []
            for ss in _sensitive_list:
                for key, value_list in self.sensitive_words.items():
                    if ss["Keyword"] in value_list:
                        if key == "色情辱骂":
                            res_merge[idx]["emo"] = -1
                        sensitive_list.append(
                            {"keyword": ss["Keyword"], "keyword_type": key, "start": ss["Start"], "end": ss["End"]})
                        break
            res_merge[idx]["sensitive"] = sensitive_list
            res_merge[idx]["sts"] = sts_words[idx]
        msg = f"businessID: {businessID} 识别成功."
        return dict(code=200, data=res_merge, msg=msg)


asr_engine = ASR()

if __name__ == "__main__":
    import asyncio

    filepath = "../datasets/audio"
    idlist = os.listdir(filepath)

    start = time.time()
    for id in idlist:
        wavlist = os.listdir(os.path.join(filepath, id))
        for wav in wavlist:
            cur_start = time.time()
            wav_path = "/home/sai/YANG/ASR/datasets/1127_post_loan_mp3/2e10b854d3c45f45bc015bba9e22668d.mp3"#os.path.join(filepath, id, wav)
            with open(wav_path, "rb") as file:
                base64_audio = base64.b64encode(file.read()).decode('utf-8')
            businessID = uuid.uuid4()
            print(f'-------------------{wav}--------------------')
            output_res = asyncio.run(asr_engine.inference(businessID, input=base64_audio))
            print('total:', time.time() - cur_start)
            print(output_res)
    print(time.time() - start)
