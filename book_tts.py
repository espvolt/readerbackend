from book_scraper import Wikipedia
import soundfile as sf
from concurrent.futures import ThreadPoolExecutor
import threading
import fileman
import os
import json
from pprint import pprint
from book import Book, Chapter
import pathlib
import re
import subprocess
from gradio_client import Client, handle_file
import atexit
import time
from dotenv import load_dotenv
 
OUT_FILE = "fin.wav"
INITIAL_FILE = "0"

def do_quote_text(text: str) -> str:
        quote_text_stuff = [
            "stating",
            "stating",
            "called the",
            "saying"
        ]

        already_defined_areas = []
        addition_match = ".{0,30}\".*\""
        lower_text = text.lower()
        for express in quote_text_stuff:
            for match in re.findall(express + addition_match, lower_text):
                match_index = lower_text.index(match)
                match_index_a = match_index + match.index("\"")
                match_index_b = match_index + len(match) - 1
                
                area_already_defined = False

                for defined_area in already_defined_areas:
                    if (match_index_a < defined_area[1] and match_index_a > defined_area[0] or
                        match_index_b < defined_area[1] and match_index_b > defined_area[0]):
                        area_already_defined = True

                if (area_already_defined):
                    continue

                text = text[:match_index] + text[match_index:match_index_a] + "Quote, " + text[match_index_a + 1:match_index_b] + ", End Quote" + text[match_index_b + 1:]

        return text

def remove_pattern(text: str, match: str):
    while (match in text and (index := text.index(match)) > 0):
        a = text[:index]
        b = text[index + len(match):]
        
        text = a + b

    return text

def split_text(chapter_text: str, split_character: str=".") -> list[str]:
    TOKEN_LIMIT = 150

    chapter_text = remove_pattern(chapter_text, "[...]")
    # chapter_text = do_quote_text(chapter_text)
    sentence_split = chapter_text.split(split_character)
    current_merged_sentence: str | None = None
    res = []

    i = 0
    
    while (i < len(sentence_split)):
        sentence = sentence_split[i].strip()

        if (current_merged_sentence is None):
            current_merged_sentence = sentence
            i += 1
            continue

        if (len(current_merged_sentence) + len(sentence) <= TOKEN_LIMIT):
            current_merged_sentence += split_character + " " + sentence

        else:
            if (len(current_merged_sentence) > TOKEN_LIMIT):
                res.extend(split_text(current_merged_sentence, ","))
                current_merged_sentence = sentence
            else:
                res.append(current_merged_sentence + split_character)
                current_merged_sentence = sentence
                # print(current_merged_sentence, sentence)
        
        i += 1

    if (current_merged_sentence is not None):
        res.append(current_merged_sentence + split_character)

    i = 0

    return res
        
class BookTTS:
    INSTANCE = None
    MODEL_TYPE = "xtts"
    NUM_THREADS = 2
    DEBUG_LIMIT = 5
    CURRENT_BOOK_ID = 0
    CURRENT_TRACK_ID = 0
    VOICE_FILE = "./input/espvolt.wav"

    def __init__(self, dummy=False):
        if (BookTTS.INSTANCE):
            raise Exception("You trash boy")
        
        self.queue: list[Book] = []

        self.clone_voices = {}
        self._build_clone_voices()
        
        if (not dummy):
            if (BookTTS.MODEL_TYPE == "xtts"):
                import torch
                from TTS.api import TTS

                device = "cuda" if torch.cuda.is_available() else "cpu"
                self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
            elif (BookTTS.MODEL_TYPE == "f5"):
                self.f5_proc = subprocess.Popen("f5-tts_infer-gradio")

                def cleanup():
                    self.f5_proc.terminate()
                    self.f5_proc.wait()

                atexit.register(cleanup)
                while (True):
                    try:
                        self.gradio_client = Client("http://127.0.0.1:7860/")
                        break

                    except Exception as e:
                        print(e)
                        print("Waiting on gradio webserver\n")
                        time.sleep(5)

            elif (BookTTS.MODEL_TYPE == "suno"):
                from bark import SAMPLE_RATE, generate_audio, preload_models
                from scipy.io.wavfile import write as write_wav

                self.generate_audio = generate_audio
                self.write_wav = write_wav
                self.SAMPLE_RATE = SAMPLE_RATE
                print("LOADING")
                preload_models()
                print("OOPS")

            elif (BookTTS.MODEL_TYPE == "elabs"):
                from elevenlabs.client import ElevenLabs
                load_dotenv()

                self.client = ElevenLabs(api_key=os.getenv("ELEVEN_LABS_API_KEY"))


        else:
            self.tts = None

        self.lock = threading.Lock()
        self.current_thread: threading.Thread = None
        
        self.track_data = {}
        self.book_data = {}

        self.current_book: Book = None
        self.current_book_chapter: Chapter = None
        self.current_book_chapter_progress: float = -1.0
        
        self.busy = False
    
    def _build_clone_voices(self):
        path = pathlib.Path("./input")

        self.clone_voices = {}

        if (path.exists()):
            for file in path.iterdir():
                if (file.is_file() and file.suffix in (".mp3", ".wav")):
                    # valid file
                    transcript_file = None

                    if (os.path.exists(file.parent.as_posix() + "/" + file.stem + ".txt")):
                        transcript_file = file.parent.as_posix() + "/" + file.stem + ".txt"
                    self.clone_voices[file.stem] = (file.as_posix(), transcript_file)

        print("REBUILD_CLONE_VOICES", self.clone_voices)

    def _load_from_file(self):
        book_default = {
            "current_book_id": 0,
            "books": {}
        }

        track_default = {
            "current_track_id": 0,
            "tracks": {}
        }

        self.book_data = fileman.get_json_file_data("./data/books.json", book_default)
        self.track_data = fileman.get_json_file_data("./data/tracks.json", track_default)

        BookTTS.CURRENT_BOOK_ID = self.book_data["current_book_id"]
        BookTTS.CURRENT_TRACK_ID = self.track_data["current_track_id"]

    def get_instance(dummy=False):
        if (BookTTS.INSTANCE is None):
            BookTTS.INSTANCE = BookTTS(dummy=dummy)
            BookTTS.INSTANCE._load_from_file()

        return BookTTS.INSTANCE

    def _update(self):
        if (self.is_busy() or len(self.queue) <= 0):
            return
        
        print("STARTED_THREAD")

        self.current_thread = threading.Thread(target=self.worker_thread, args=[self.queue.pop(0)])
        self.current_thread.start()

    def _finished(self):
        with self.lock:
            self.busy = False

        self._update()
        pass
    
    def f5(self, text: str, speaker: str): # probably have to use f5 overnight because its so DAMN SLOW
        return self.gradio_client.predict(
            ref_audio_input=handle_file(self.clone_voices[speaker][0]),
            gen_text_input=text,
            remove_silence=True,
            speed_slider=.3,
            api_name="/basic_tts"
        )
                
    def _worker_thread(self, index: str, text: str, clone_voice: str, finished_files: dict[int, str]):
        print("COULD MAYBE BE STUCK OR SOMETHING")
        wav = None

        if (BookTTS.MODEL_TYPE == "xtts"):
            wav = self.tts.tts(text=text, speaker_wav=self.clone_voices[clone_voice][0], language="en")
            
            print("\t", len(wav), index, text)
            
            with self.lock:
                sf.write(f"./output/{index}.wav", wav, 24000)
                finished_files[index] = text

        elif (BookTTS.MODEL_TYPE == "f5"):
            # self.gradio_client # TODO
            data = self.f5(text=text, speaker=clone_voice)

            file = data[0]
            with self.lock:
                os.rename(file, f"./output/{index}.wav")
                finished_files[index] = text

        elif (BookTTS.MODEL_TYPE == "suno"):
            audio_array = self.generate_audio(text)
            
            with self.lock:
                self.write_wav(f"./output/{index}.wav", self.SAMPLE_RATE, audio_array)
                finished_files[index] = text

        elif (BookTTS.MODEL_TYPE == "elabs"):
            stream = self.client.text_to_speech.convert_as_stream(
                text=text,
                voice_id="JBFqnCBsd6RMkjVDRZzb",
                model_id="eleven_multilingual_v2",
            )

            with open(f"./output/{index}.mp3", "wb") as f:
                for chunk in stream:
                    if (isinstance(chunk, bytes)):
                        f.write(chunk)

            with self.lock:
                finished_files[index] = text


    def worker_thread(self, book: Book):
        with self.lock:
            self.busy = True

        book_folder_name = "_".join(book.tags).upper() + "_" + "_".join(book.title.upper().split(" "))
        book_folder = "./public/" + book_folder_name

        path = pathlib.Path(book_folder)

        if (path.exists()):
            print("BOOK FOLDER ALREADY EXISTS")
            self._finished()
            return
        
        final_book_obj = {"title": book.title, "chapters": [], "tags": book.tags}

        self.current_book = book

        this_book_id = BookTTS.CURRENT_BOOK_ID

        with self.lock:
            BookTTS.CURRENT_BOOK_ID += 1

        for chapter in book.chapters:
            finished_files = {}
            split = []

            self.current_book_chapter = chapter

            if (BookTTS.MODEL_TYPE == "f5" or BookTTS.MODEL_TYPE == "elabs"):
                split = [chapter.text]
            else:
                if (BookTTS.DEBUG_LIMIT > 0):
                    split = split_text(chapter.text)[:BookTTS.DEBUG_LIMIT]
                else:
                    split = split_text(chapter.text)

            
            i = 0
            while (i < len(split)):
                found = False
                for j in split[i]:
                    if (j.isalnum()):
                        found = True
                        break

                if (found):
                    i += 1
                    continue

                if (split[i].strip("\"") == "."):
                    split.pop(i)
                    i -= 1
                i += 1

            while (True):
                if (len(finished_files) == len(split)):
                    break
            
                self.current_book_chapter_progress = len(finished_files) / len(split)
                with ThreadPoolExecutor(max_workers=BookTTS.NUM_THREADS) as executor:
                    for i, t in enumerate(split):
                        if (i not in finished_files):
                            _ = executor.submit(self._worker_thread, i, t, book.voice_clone, finished_files) # dont actually need the future

            fileman.safe_create_folder(book_folder)

            with self.lock:
                length = fileman.merge_output()
                fileman.cleanup()

            chapter_id = self._move_chapter(book_folder, book, this_book_id, chapter, length)

            final_book_obj["chapters"].append({
                "chapter_title": chapter.title,
                "chapter_track_id": chapter_id,
                "chapter_length": length,
                "tags": book.tags + [BookTTS.MODEL_TYPE]
            })

        with self.lock:
            self.book_data["books"][str(this_book_id)] = final_book_obj
            self.book_data["current_book_id"] = BookTTS.CURRENT_BOOK_ID

            self._save_data()

        self._finished()

    def _save_data(self):
        with open("./data/tracks.json", "w") as f:
            json.dump(self.track_data, f, indent=4)
        
        with open("./data/books.json", "w") as f:
            json.dump(self.book_data, f, indent=4)

    def _move_chapter(self, parent_folder: str, book: Book, book_id: int, chapter: Chapter, chapter_length: float):
        with self.lock:
            filename = parent_folder + "/" + chapter.title + ".wav"

            os.rename("./output/fin.wav", filename)

            self.track_data["tracks"][str(BookTTS.CURRENT_TRACK_ID)] = {
                "filename": filename,
                "length": chapter_length,
                "title": chapter.title,
                "source": book.title,
                "source_id": book_id
            }

            BookTTS.CURRENT_TRACK_ID += 1

            self.track_data["current_track_id"] = BookTTS.CURRENT_TRACK_ID

            self._save_data()

            return BookTTS.CURRENT_TRACK_ID - 1


    def get_progress(self):
        if (not self.is_busy()):
            return {"message": "currently not working", 
                    "current_book_name": None, 
                    "current_chapter_name": None, 
                    "current_chapter_progress": None}
        
        return {"message": "working", 
                "current_book_name": self.current_book.title, 
                "current_chapter_name": self.current_book_chapter.title, 
                "current_chapter_progress": self.current_book_chapter_progress}
    
    def is_busy(self):
        return self.busy
    
    def start_wikipedia(self, site_link: str):
        self.start_text(Wikipedia.scrape(site_link))
        print("STARTING WIKIPEDIA ARTICLE")

    def start_text(self, selection_data):
        self.queue.append(selection_data)
        self._update()


if (__name__ == "__main__"):
    instance = BookTTS.get_instance(dummy=False)
    instance.start_wikipedia("https://en.wikipedia.org/wiki/Lucid_dream")
    instance.start_wikipedia("https://en.wikipedia.org/wiki/Pip-Boy")
    instance.start_wikipedia("https://en.wikipedia.org/wiki/1989_Tiananmen_Square_protests_and_massacre")
    instance.start_wikipedia("https://en.wikipedia.org/wiki/Astral_projection")

    
    while (instance.current_thread.is_alive()):
        instance.current_thread.join()


    


