from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from tts_helper import TTSingle
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
tt_instance = TTSingle.get_instance(True)
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
        for i in tt_instance.data["selections"]:
            res[int(i)] = tt_instance.data["selections"][i]

    else:
        tags = set(tag_filter)

        for i in tt_instance.data["selections"]:
            current = tt_instance.data["selections"][i]
            display_name: str = current["display_name"]
            current_tags: set[str] = set(current["tags"])

            if ((name_filter != "" and name_filter in display_name) or (len(tags.intersection(current_tags)) > 0)):
                res[int(i)] = current

    res = deepcopy(res)
    _filter_selection(res)
    return res

@app.get("/audio")
async def video_endpoint(id: int):
    selections = tt_instance.data["selections"]

    if (str(id) in selections):
        def iterfile():
            with open(f"public/selection/{selections[str(id)]['filename']}", mode="rb") as file_like:
                yield from file_like

        return StreamingResponse(iterfile(), media_type="audio/wav")
    
    return None

@app.get("/audioinformation")
async def get_audio_information(id: int, sessionId: int=-1, username: str=""):
    selections = tt_instance.data["selections"]
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
    return trackman_instance.create_playlist(info)

@app.post("/deleteplaylist")
async def delete_playlist(info: PlaylistDeletionData):
    return trackman_instance.delete_playlist(info)

@app.get("/getplaylists")
async def get_playlists(username: str):
    return trackman_instance.get_playlists(username)

@app.get("/playlist")
async def get_playlist(id: int):
    return trackman_instance.get_playlist(id)

@app.post("/addtracktoplaylist")
async def add_track_to_playlist(info: PlaylistModifyData):
    return trackman_instance.add_track_to_playlist(info)

@app.post("/removetrackfromplaylist")
async def remove_track_from_playlist(info: PlaylistModifyData):
    return trackman_instance.remove_track_from_playlist(info)

@app.get("/getvoiceoptions")
async def get_voice_options():
    return {"message": "voices", "voices": list(get_voices())}

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8080)
    
