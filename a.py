import torch
from TTS.api import TTS
from website_scraper import wikipedia, split_text_to_tokens
import soundfile as sf
from concurrent.futures import ThreadPoolExecutor
import threading
import fileman
from pprint import pprint

# OUTPUT_FILE = ""
# Get device
device = "cuda" if torch.cuda.is_available() else "cpu"
# print("Hello from cloud code")
# # List available 🐸TTS models
# print(TTS().list_models())

# # Init TTS
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
lock = threading.Lock()
# # Run TTS
# ❗ Since this model is multi-lingual voice cloning model, we must set the target speaker_wav and language
# Text to speech list of amplitude values as output
# wav = tts.tts(text="Hello world!", speaker_wav="my/cloning/audio.wav", language="en")
# Text to speech to a file

text = wikipedia("Lucid_Dream")
m = -1

done = {}

def threaded(i: int, t: str):
    wav = tts.tts(text=t, speaker_wav="./input/male_en.mp3", language="en")
    print(len(wav), i, t)
    with lock:
        done[i] = t
        sf.write(f"./output/{i}.wav", wav, 24000)

junk = split_text_to_tokens(text)[:10]

print(junk)

while (True):
    if (len(done) == len(junk)):
        break

    with ThreadPoolExecutor(max_workers=2) as executor:
        for i, t in enumerate(junk):
            if (i not in done):
                future = executor.submit(threaded, i, t)

fileman.merge_output()
fileman.cleanup()

print("DN")
