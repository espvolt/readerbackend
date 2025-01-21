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


OUT_FILE = "fin.wav"
INITIAL_FILE = "0"

def split_text(chapter_text: str, split_character: str=".") -> list[str]:
    TOKEN_LIMIT = 150

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
                res.append(current_merged_sentence)
                current_merged_sentence = sentence
                # print(current_merged_sentence, sentence)
        
        i += 1

    if (current_merged_sentence is not None):
        res.append(current_merged_sentence)

    i = 0

    return res
        
class BookTTS:
    INSTANCE = None
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
            import torch
            from TTS.api import TTS

            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
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
                    self.clone_voices[file.stem] = file.as_posix()

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

    def _worker_thread(self, index: str, text: str, clone_voice: str, finished_files: dict[int, str]):
        print("COULD MAYBE BE STUCK OR SOMETHING")

        wav = self.tts.tts(text=text, speaker_wav=self.clone_voices[clone_voice], language="en")
        
        print("\t", len(wav), index, text)

        with self.lock:
            finished_files[index] = text
            sf.write(f"./output/{index}.wav", wav, 24000)

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
        
        final_book_obj = {"title": book.title, "chapters": []}

        self.current_book = book

        for chapter in book.chapters:
            finished_files = {}
            split = []

            self.current_book_chapter = chapter

            if (BookTTS.DEBUG_LIMIT > 0):
                split = split_text(chapter.text)[:BookTTS.DEBUG_LIMIT]
            else:
                split = split_text(chapter.text)


            while (True):
                if (len(finished_files) == len(split)):
                    break
                
                self.current_book_chapter_progress = len(finished_files) / len(split)
                with ThreadPoolExecutor(max_workers=BookTTS.NUM_THREADS) as executor:
                    for i, t in enumerate(split):
                        if (i not in finished_files):
                            _ = executor.submit(self._worker_thread, i, t, finished_files) # dont actually need the future

            fileman.safe_create_folder(book_folder)
            length = fileman.merge_output()
            fileman.cleanup()

            chapter_id = self._move_chapter(book_folder, chapter, length)

            final_book_obj["chapters"].append({
                "chapter_title": chapter.title,
                "chapter_track_id": chapter_id,
                "chapter_length": length,
                "tags": book.tags
            })

        with self.lock:
            self.book_data["books"][str(BookTTS.CURRENT_BOOK_ID)] = final_book_obj
            BookTTS.CURRENT_BOOK_ID += 1
            self.book_data["current_book_id"] = BookTTS.CURRENT_BOOK_ID

            self._save_data()

        self._finished()

    def _save_data(self):
        with open("./data/tracks.json", "w") as f:
            json.dump(self.track_data, f, indent=4)
        
        with open("./data/books.json", "w") as f:
            json.dump(self.book_data, f, indent=4)

            

    def _move_chapter(self, parent_folder: str, chapter: Chapter, chapter_length: float):
        with self.lock:
            filename = parent_folder + "/" + chapter.title + ".wav"

            os.rename("./output/fin.wav", filename)

            self.track_data["tracks"][str(BookTTS.CURRENT_TRACK_ID)] = {
                "filename": filename,
                "length": chapter_length
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

    def start_text(self, selection_data):
        self.queue.append(selection_data)
        self._update()


if (__name__ == "__main__"):
    instance = BookTTS.get_instance(dummy=True)

