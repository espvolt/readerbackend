import torch
from TTS.api import TTS
from website_scraper import wikipedia, split_text_to_tokens
import soundfile as sf
from concurrent.futures import ThreadPoolExecutor
import threading
import fileman
import os
from dataclasses import dataclass
import json
import os
from pprint import pprint

OUT_FILE = "fin.wav"
INITIAL_FILE = "0"

@dataclass
class Selection:
    text: str
    filename: str
    display_name: str
    tags: list[str]

class TTSingle:
    INSTANCE = None
    NUM_THREADS = 2
    DEBUG_LIMIT = 5
    VOICE_FILE = "./input/espvolt.wav"

    def __init__(self, dummy=False):
        if (TTSingle.INSTANCE):
            raise Exception("You trash boy")
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.queue: list[Selection] = []
        
        if (not dummy):
            self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        else:
            self.tts = None

        self.lock = threading.Lock()
        self.current_thread: threading.Thread = None
        self.data = {}

        self.busy = False

    def _load_from_file(self, path: str):
        if (os.path.exists(path)):
            with open(path, "r") as f:
                self.data = json.load(f)


        else:
            self.data = {
                "current_selection_id": 0,
                "selections": {
                    
                }
            }

            with open(path, "w") as f:
                json.dump(self.data, f, indent=4)

    def get_instance(dummy=False):
        if (TTSingle.INSTANCE is None):
            TTSingle.INSTANCE = TTSingle(dummy=dummy)
            TTSingle.INSTANCE._load_from_file("./data/selections.json")
            print("Loaded data")
            pprint(TTSingle.INSTANCE.data)

        return TTSingle.INSTANCE

    def _update(self):
        if (self.is_busy() or len(self.queue) <= 0):
            return
        
        print("STARTED_THREAD")

        self.current_thread = threading.Thread(target=self._thread, args=[self.queue.pop(0)])
        self.current_thread.start()

    def _finished(self):
        with self.lock:
            self.busy = False

        self._update()
        pass

    def _worker_thread(self, index: str, text: str, finished_files: dict[int, str]):
        print("COULD MAYBE BE STUCK OR SOMETHING")

        wav = self.tts.tts(text=text, speaker_wav=TTSingle.VOICE_FILE, language="en")
        
        print("\t", len(wav), index, text)

        with self.lock:
            finished_files[index] = text
            sf.write(f"./output/{index}.wav", wav, 24000)

    def _thread(self, selection_data: Selection):
        with self.lock:
            self.busy = True

        finished_files = {}

        split_text = []

        if (TTSingle.DEBUG_LIMIT > 0):
            split_text = split_text_to_tokens(selection_data.text)[:TTSingle.DEBUG_LIMIT]
        else:
            split_text = split_text_to_tokens(selection_data.text)

        while (True):
            if (len(finished_files) == len(split_text)):
                break

            with ThreadPoolExecutor(max_workers=TTSingle.NUM_THREADS) as executor:
                for i, t in enumerate(split_text):
                    if (i not in finished_files):
                        _ = executor.submit(self._worker_thread, i, t, finished_files) # dont actually need the future

        length = fileman.merge_output()
        fileman.cleanup()

        self._move_fin(selection_data, length)
        self._finished()

    def _save_data(self):
        if (os.path.exists("./data/selections.json")):
            with open("./data/selections.json", "w") as f:
                json.dump(self.data, f, indent=4)

    def _move_fin(self, selection_data: Selection, length: float):
        with self.lock:
            os.rename("./output/fin.wav", f"./public/selection/{selection_data.filename}")

            current_selection_id = self.data["current_selection_id"]
            self.data["selections"][current_selection_id] = {
                "filename": selection_data.filename,
                "display_name": selection_data.display_name,
                "tags": selection_data.tags,
                "length": length
            }


            self.data["current_selection_id"] = current_selection_id + 1
            self._save_data()

    def is_busy(self):
        return self.busy
    
    # def _does_file_already_exist(self, file: str):

    def start_wikipedia(self, target_article: str, tags=[]):
        output_file_name = f"WIKIPEDIA_{target_article.upper()}.wav"

        if (os.path.exists(f"./public/selection/{output_file_name}")):
            return False
        
        self.start_text(Selection(wikipedia(target_article),
                                  output_file_name,
                                  f"{target_article.replace('_', ' ').title()}",
                                  ["wikipedia"] + tags))
        
        return True

    def start_text(self, selection_data: str):
        self.queue.append(selection_data)
        self._update()
