import wave
import os
from pydub import AudioSegment
import pathlib
import json


OUT_FILE = "fin.wav"
INITIAL_FILE = "0"

def merge_output() -> float:
    """returns the length of the output file in seconds"""
    first: AudioSegment = AudioSegment.from_wav(f"./output/{INITIAL_FILE}.wav")
    files = os.listdir("./output")
    def f(x: str):
        if (x[:-4].isdigit()):
            return int(x[:-4])
        else:
            return -1
        
    files.sort(key=f)

    for file in files:
        if (file != INITIAL_FILE + ".wav" and file != OUT_FILE and file.endswith(".wav")):
            print(file)
            first = first.append(AudioSegment.from_wav(f"./output/{file}"))

    first.export(f"./output/{OUT_FILE}", format="wav")
    return len(first) / 1000

def cleanup():
    for file in os.listdir("./output"):
        if (file != OUT_FILE):
            os.remove(f"./output/{file}")

def get_voices():
    voices: list[str] = os.listdir("./input")

    res = set()

    for voice in voices:
        res.add(".".join(voice.split(".")[:-1]))

    return res

def get_json_file_data(path: str, default_data: dict=None): # maybe belongs in fileman
    path_obj = pathlib.Path(path)

    if (path_obj.exists()):
        with open(path_obj.as_posix(), "r") as f:
            try:
                data = json.load(f)

                return data
            
            except json.JSONDecodeError:
                return default_data
            
    else:
        if (default_data is None):
            default_data = {}
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        with open(path_obj.as_posix(), "w") as f:
            json.dump(default_data, f, indent=4)

        return default_data
    
def safe_create_folder(path: str):
    path_obj = pathlib.Path(path)

    path_obj.mkdir(parents=True, exist_ok=True)
    
if (__name__ == "__main__"):
    merge_output()