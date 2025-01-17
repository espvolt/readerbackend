import wave
import os
from pydub import AudioSegment

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

if (__name__ == "__main__"):
    merge_output()