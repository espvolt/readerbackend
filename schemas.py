from pydantic import BaseModel

class ErrorStuff:
    INVALID_SESSION = 1000501
    PLAYLIST_ALREADY_EXISTS = 1000502
    USER_NOT_FOUND = 1000503
    PLAYLIST_NOT_FOUND = 1000504
    TRACK_NOT_FOUND = 1000505

class StartRequest(BaseModel):
    path: str
    start_type: str
    cred: str

class SearchRequest(BaseModel):
    name: str = ""
    tags: list[str] = []

class LoginInfo(BaseModel):
    username: str
    password: str

class ReuseLogin(BaseModel):
    username: str
    last_login_key: str

class PlaylistCreationData(BaseModel):
    session_id: int
    username: str
    playlist_name: str

class PlaylistDeletionData(BaseModel):
    session_id: int
    playlist_id: int
    username: str

class PlaylistModifyData(BaseModel):
    session_id: int
    username: str
    playlist_id: int
    track_id: int

class AddRemovePlaylistElementData(BaseModel):
    session_id: int
    username: str
    playlist_id: int
    track_id: int

class GetTrackProgress(BaseModel):
    session_id: int
    username: str
    tracks: list[int]

class UpdateTrackProgressData(BaseModel):
    session_id: int
    username: str
    track_id: int
    progress: float

class GetTrackUserData(BaseModel):
    session_id: int
    username: str
    tracks: list[int]


    