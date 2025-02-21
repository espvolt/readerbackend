from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from book_tts import BookTTS
from user import UserMan
from trackman import Trackman
from schemas import *
from pydantic import validate_call
from copy import deepcopy
from fileman import get_voices
import uvicorn

CRED_STRING = "ILOVEYOUNIG"

app = FastAPI(swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Add your allowed origins here 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# tt_instance = TTSingle.get_instance()
tt_instance = BookTTS.get_instance(dummy=True)
user_instance = UserMan.get_instance()
trackman_instance = Trackman.get_instance()

@app.get("/")
async def root():
    return {"message": "Reader Server"}

@app.post("/start/")
async def start(data: StartRequest):
    if (data.cred == CRED_STRING):
        if (data.start_type == "wikipedia"):
            if (tt_instance.start_wikipedia(data.path)):
                return {"message": "Working"}
            
def _filter_selection(res: dict) -> None:
    for i in res:
        res[i].pop("filename")

@app.get("/get_selection/")
async def get_selection(name_filter="", tag_filter: list[str]=[]):
    res = {}

    if (name_filter == "" and len(tag_filter) == 0):
        for i in tt_instance.book_data["books"]:
            res[int(i)] = tt_instance.book_data["books"][i]

    else:
        tags = set(tag_filter)

        for i in tt_instance.book_data["books"]:
            current = tt_instance.book_data["books"][i]
            display_name: str = current["display_name"]
            current_tags: set[str] = set(current["tags"])

            if ((name_filter != "" and name_filter in display_name) or (len(tags.intersection(current_tags)) > 0)):
                res[int(i)] = current

    res = deepcopy(res)
    return res

def get_book_search(name_filter: str, tag_filter: list):
    if (name_filter == "" and len(tag_filter) == 0):
        return tt_instance.book_data["books"]
    
    else: # for now only tag filter
        res = {}
        for i in tt_instance.book_data["books"]:
            if name_filter.lower() in tt_instance.book_data["books"][i]["title"].lower():
                print(tt_instance.book_data["books"])
                res[i] = tt_instance.book_data["books"][i]

        return res

@app.get("/multisearch")
async def get_multiple_search(name_filter: str="", tag_filter: list[str]=[]):
    return {"message": "search results",
            "books": get_book_search(name_filter, tag_filter),
            "tracks": {}}



@app.get("/audio")
async def video_endpoint(id: int):
    tracks = tt_instance.track_data["tracks"]

    if (str(id) in tracks):
        def iterfile():
            with open(tracks[str(id)]["filename"], mode="rb") as file_like:
                yield from file_like

        return StreamingResponse(iterfile(), media_type="audio/wav")
    
    return None

@app.get("/audioinformation")
async def get_audio_information(id: int, sessionId: int=-1, username: str=""):
    selections = tt_instance.track_data["tracks"]
    id_str = str(id)
    res = None
    if (id_str in selections):
        res = deepcopy(selections[id_str])
        res.pop("filename")
    
    return res

@app.post("/signin")
async def signin(info: LoginInfo):
    return user_instance.attempt_user_signlog(info.username, info.password)

@app.post("/reuselogin")
async def reuselogin(info: ReuseLogin):
    return user_instance.attempt_reuse_login(info.username, info.last_login_key)

@app.get("/issessionactive")
async def is_session_active(session_id: int):
    return {"status": user_instance.check_session_id(session_id)}

@validate_call
@app.post("/createplaylist")
async def create_playlist(info: PlaylistCreationData):
    res = trackman_instance.create_playlist(info)
    print(res)
    return res

@app.post("/deleteplaylist")
async def delete_playlist(info: PlaylistDeletionData):
    return trackman_instance.delete_playlist(info)

@app.get("/getplaylists")
async def get_playlists(username: str):
    return trackman_instance.get_playlists(username)

@app.get("/playlist")
async def get_playlist(id: int, session_id: int=-1, username: str=""):
    res = trackman_instance.get_playlist(id)

    if (session_id != -1 and username != ""):
        track_ids = []

        for track in res["playlist"]["tracks"]:
            track_ids.append(track["track_id"])

        progress = trackman_instance.get_track_progress_array(track_ids, username, session_id)
        res["track_progress_data"] = progress["track_progress_data"]

    print(res)
    return res

@app.post("/addtracktoplaylist")
async def add_track_to_playlist(info: PlaylistModifyData):
    return trackman_instance.add_track_to_playlist(info)

@app.post("/removetrackfromplaylist")
async def remove_track_from_playlist(info: PlaylistModifyData):
    return trackman_instance.remove_track_from_playlist(info)

@app.get("/getvoiceoptions")
async def get_voice_options():
    return {"message": "voices", "voices": list(tt_instance.clone_voices.keys())}

@app.post("/createbookmark")
async def create_bookmark(info: BookmarkCreateData):
    return user_instance.create_bookmark(info)

@app.get("/getbookmarks")
async def get_bookmarks(username: str):
    return user_instance.get_bookmarks(username)

@app.post("/removebookmark")
async def remove_bookmark(info: BookmarkCreateData):
    return user_instance.remove_bookmark(info)

@app.get("/getbookdata")
async def get_book_data(book_id: int, username: str="", session_id: int=-1):
    res = trackman_instance.get_book_data(book_id)
    if (session_id != -1):
        track_ids = []

        for chapter in res["data"]["chapters"]:
            track_ids.append(chapter["chapter_track_id"])
        
        progress = trackman_instance.get_track_progress_array(track_ids, username, session_id)
        res["track_progress_data"] = progress["track_progress_data"]

    return res

@app.post("/posttrackprogress")
async def upload_track_progress(info: UpdateTrackProgressData):
    return trackman_instance.set_track_progress(info)

@app.get("/gettrackprogressarray")
async def get_track_progress_array(tracks: list[int], username: str, session_id: str):
    return trackman_instance.get_track_progress_from_array(tracks)

@app.post("/requestbook")
async def request_book(info: RequestBookData):
    if (not user_instance.does_session_exist(info.username, info.session_id)):
        return ErrorMessages.INVALID_SESSION
    
    if (info.book_type == "wikipedia"):
        started = tt_instance.start_wikipedia(info.book_link)
        
        return {"message": "check success", "success": started}
    
