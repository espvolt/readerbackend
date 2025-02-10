from pydantic import BaseModel

class ErrorCodes:
    INVALID_SESSION = 1000501
    PLAYLIST_ALREADY_EXISTS = 1000502
    USER_NOT_FOUND = 1000503
    PLAYLIST_NOT_FOUND = 1000504
    TRACK_NOT_FOUND = 1000505
    BOOK_ALREADY_BOOKMARKED = 1000506
    BOOK_NOT_BOOKMARKED = 1000507
    BOOK_NOT_FOUND = 1000508
    WRONG_OWNER = 1000509
    
class ErrorMessages:
    INVALID_SESSION = {"message": "session not found", "success": False, "error_id": ErrorCodes.INVALID_SESSION}
    USER_NOT_FOUND = {"message": "user not found", "success": False, "error_id": ErrorCodes.USER_NOT_FOUND}
    
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

class BookmarkCreateData(BaseModel):
    session_id: int
    username: str
    book_id: int    

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

class UpdateTrackProgressData(BaseModel):
    session_id: int
    username: str
    track_id: int
    progress: float    