from hashlib import sha3_256
import os, json
import dataclasses
import math
import time
from schemas import BookmarkCreateData, ErrorCodes
import fileman
from book_tts import BookTTS

@dataclasses.dataclass
class SessionData:
    user: str
    id: int
    last_time: float


class UserMan:
    INSTANCE = None
    USER_JSON_PATH = "./data/users.json"
    LAST_LOGIN_TIME = 3 * 24 * 60 * 60
    LAST_SESSION_TIME = 1 * 60 * 60
    current_sessions = 0
    CURRENT_USER_ID = 0

    def __init__(self):
        if (UserMan.INSTANCE is not None):
            return
        
        self.data = {}
        self.tt_instance = BookTTS.get_instance() 
        self.active_sessions: dict[int, SessionData] = {}


    def _load_data(self):
        default = {
            "current_user_id": 0,
            "users": {}
        }

        self.data = fileman.get_json_file_data("./data/users.json", default)
        UserMan.CURRENT_USER_ID = self.data["current_user_id"]



    def _save_data(self):
        if (os.path.exists(UserMan.USER_JSON_PATH)):
            with open(UserMan.USER_JSON_PATH, "w") as f:
                json.dump(self.data, f, indent=4)

    def get_instance():
        if (UserMan.INSTANCE == None):
            UserMan.INSTANCE = UserMan()
            UserMan.INSTANCE._load_data()

        return UserMan.INSTANCE
    
    def _generate_last_login_key(self, user: str):
        return self._get_encrypted(user, str(math.trunc(time.time())))
    
    def _create_session(self, user: str, display_name: str, create_last_login_key=True):
        res = SessionData(user.lower(), UserMan.current_sessions, time.time())
        self.active_sessions[res.id] = res
        UserMan.current_sessions += 1

        last_login_key = ""
        
        if (create_last_login_key):
            last_login_key = self._generate_last_login_key(user)
            self.data["users"][user]["last_login_key"] = last_login_key
            self.data["users"][user]["last_login_time"] = time.time()
            self._save_data()

        return {"session_id": res.id, "last_login": last_login_key, "user": user, "display_name": display_name}
    
    def _create_user(self, password: str):
        res = {
            "password": password,
            "bookmarks": [],
            "playlists": [],
            "track_progress": {},
            "current_queue": [],
            "user_id": UserMan.CURRENT_USER_ID,
            "last_login_key": "",
            "last_login_time": -1,
            "display_name": ""
        }

        UserMan.CURRENT_USER_ID += 1
        self.data["current_user_id"] = UserMan.CURRENT_USER_ID
        return res
    
    def _get_encrypted(self, user: str, password: str):
        p = sha3_256(password.encode()).hexdigest()
        u = sha3_256(user.encode()).hexdigest()

        return u + p
    
    def attempt_user_signlog(self, user: str, password: str): # this app hopefully WILL NOT contain sensitive info, so i am not too worried about this kind of thing
        _user = user
        user = user.lower()
        enc_pass = self._get_encrypted(user, password)

        if (user not in self.data["users"]):
            self.data["users"][user] = self._create_user(enc_pass)
            self.data["users"][user]["display_name"] = _user

            return self._create_session(user, _user)
        
        elif (self.data["users"][user]["password"] == enc_pass):
            return self._create_session(user, self.data["users"][user]["display_name"])
        
    def attempt_reuse_login(self, user: str, key: str):
        user = user.lower()
        if (user not in self.data["users"]):
            return None
        
        current_user = self.data["users"][user]
        match_key = current_user["last_login_key"]

        print(time.time() - current_user["last_login_time"], UserMan.LAST_LOGIN_TIME)
        print(match_key)
        print(key)
        print()
        
        if (match_key == key and time.time() - current_user["last_login_time"] < UserMan.LAST_LOGIN_TIME):
            return self._create_session(user, current_user["display_name"])
            
    def check_session_id(self, id: int):
        return id in self.active_sessions

    def _cleanup_dead_sessions(self):
        current_time = time.time()

        for sessionId, session in list(self.active_sessions.items()):
            if (current_time - session.last_time > UserMan.LAST_SESSION_TIME):
                self.active_sessions.pop(sessionId)

    def _does_session_exists(self, username: str, sessionId: int):
        return int(sessionId) in self.active_sessions and self.active_sessions[sessionId].user == username.lower()
    
    def does_session_exist(self, username: str, sessionId: int):
        self._cleanup_dead_sessions()
        return (self._does_session_exists(username, sessionId)
                 and time.time() - self.active_sessions[sessionId].last_time < UserMan.LAST_SESSION_TIME)
    
    def refresh_session(self, username: str, sessionId: int) -> bool:
        if (self._does_session_exists(username, sessionId)):
            self.active_sessions[sessionId].last_time = time.time()
            return True

        return False

    def create_bookmark(self, info: BookmarkCreateData):
        if (not self._does_session_exists(info.username, info.session_id)):
            return {"message": "session invalid", "success": False, "error_id": ErrorCodes.INVALID_SESSION}
        
        self.refresh_session(info.username, info.session_id)

        users = self.data["users"]
        user_obj = users.get(info.username)
        
        if (user_obj is None):
            return {"message": "user not found", "success": False, "error_id": ErrorCodes.USER_NOT_FOUND}
        
        if (info.book_id in user_obj["bookmarks"]):
            return {"message": "already bookmarked", "success": False, "error_id": ErrorCodes.BOOK_ALREADY_BOOKMARKED}
        
        user_obj["bookmarks"].append(info.book_id)
        self._save_data()
        
        return {"message": "bookmarked successfully", "success": True}

    def get_bookmarks(self, username: str): # who tf cares what you got bookmarked, so it doesnt need a session ID
        """
        this is part of the public dataset
        returns data like so
        [{
            "book_id": <>,
            "book_name: <>,
            "book_progress: <> <- later
        }]
        """
        
        users = self.data["users"]
        user_obj = users.get(username)
        
        if (user_obj is None):
            return {"message": "user not found", "success": False, "error_id": ErrorCodes.USER_NOT_FOUND}

        res = []

        for bookmark_id in user_obj["bookmarks"]:
            if (str(bookmark_id) in self.tt_instance.book_data["books"]): # book does still exist
                current_book = self.tt_instance.book_data["books"][str(bookmark_id)]
                res.append({
                    "book_id": bookmark_id,
                    "book_name": current_book["title"],
                    "progress": "TODO"
                })
        
        return {"message": "bookmarks found", "success": True, "bookmarks": res}
    
    def remove_bookmark(self, info: BookmarkCreateData):
        if (not self._does_session_exists(info.username, info.session_id)):
            return {"message": "session invalid", "success": False, "error_id": ErrorCodes.INVALID_SESSION}
        
        self.refresh_session(info.username, info.session_id)

        users = self.data["users"]
        user_obj = users.get(info.username)
        
        if (user_obj is None):
            return {"message": "user not found", "success": False, "error_id": ErrorCodes.USER_NOT_FOUND}
        
        if (info.book_id not in user_obj["bookmarks"]):
            return {"message": "bookmark not found", "success": False, "error_id": ErrorCodes.BOOK_NOT_BOOKMARKED}
        
        user_obj["bookmarks"].remove(info.book_id)

        self._save_data()

        return {"message": "bookmark removed", "success": True}
                
