from schemas import PlaylistCreationData, \
    PlaylistDeletionData, PlaylistModifyData, ErrorCodes, ErrorMessages, \
    GetTrackProgress, BookmarkCreateData, UpdateTrackProgressData
from user import UserMan
from book_tts import BookTTS
from dataclasses import dataclass
from copy import deepcopy
from fileman import get_json_file_data
import json


@dataclass
class PlaylistLookupData:
    parent_container: dict
    target: dict
    playlist_key: str

class Trackman():
    INSTANCE = None
    CURRENT_PLAYLIST_ID = 0
    PERSISTENT_PATH = "./data/playlist.json"
    
    def __init__(self):
        self.userman: UserMan = UserMan.get_instance()
        self.tts: BookTTS = BookTTS.get_instance()
        self.playlist_data = {} # playlist data
    
    def get_instance():
        if (Trackman.INSTANCE is None):
            Trackman.INSTANCE = Trackman()
            Trackman.INSTANCE._load_data()

        return Trackman.INSTANCE
    

    def _load_data(self):
        default_playlist_data = {
            "current_playlist_id": 0,
            "playlists": {}
        }
        self.playlist_data = get_json_file_data(Trackman.PERSISTENT_PATH, default_playlist_data)
        Trackman.CURRENT_PLAYLIST_ID = self.playlist_data["current_playlist_id"]
    
    def _save_data(self):
        with open(Trackman.PERSISTENT_PATH, "w") as f:
            json.dump(self.playlist_data, f, indent=4)
            

    def create_playlist(self, info: PlaylistCreationData):
        if (not self.userman.does_session_exist(info.username, info.session_id)):
            return ErrorMessages.INVALID_SESSION

        self.userman.refresh_session(info.username, info.session_id)

        new_playlist = {
            "playlist_name": info.playlist_name,
            "tracks": [],
            "owner": info.username 
        }

        self.playlist_data["playlists"][str(Trackman.CURRENT_PLAYLIST_ID)] = new_playlist
        self.userman.data["users"][info.username]["playlists"].append(Trackman.CURRENT_PLAYLIST_ID)

        Trackman.CURRENT_PLAYLIST_ID += 1
        self.playlist_data["current_playlist_id"] = Trackman.CURRENT_PLAYLIST_ID
        
        self._save_data()
        self.userman._save_data()

        return {"message": "playlist created successfully", "success": True, "playlist_id": Trackman.CURRENT_PLAYLIST_ID - 1}

    def _get_playlists_data(self, username: str) -> list | None:
        all_users = self.userman.data["users"]

        if (username not in all_users):
            return None

        res = []
        playlists = self.playlist_data["playlists"]

        for playlist_id in all_users[username]["playlists"]:
            if (str(playlist_id) in playlists):    
                res.append(self.playlist_data["playlists"][playlist_id])

        return res
    
    def get_playlists(self, username: str):
        """
        only IDS
        """

        all_users = self.userman.data["users"]

        _username = username.lower()

        if (_username not in all_users):
            return {"message": "user not found", "success": False, "error_id": ErrorCodes.USER_NOT_FOUND}
        
        res = {}

        for playlist_id in all_users[username]["playlists"]:
            res[str(playlist_id)] = self.playlist_data["playlists"][str(playlist_id)]

        return {"message": "got playlists", "success": True, "playlists": res}
    
    def get_tracks_progress(self, info: GetTrackProgress): # not implemented
        if (self.userman.does_session_exist(info.username, info.session_id)):
            res = {}

    def get_track_progress_array(self, tracks: list[int], username: str, session_id: int):
        # unfortunately json keys must be strs so its really annoying converted between int and strs
        if (not self.userman.does_session_exist(username, session_id)):
            return ErrorMessages.INVALID_SESSION
        
        users = self.userman.data["users"]

        if (username not in users):
            return ErrorMessages.USER_NOT_FOUND

        res = {}

        track_progress_dict = users[username]["track_progress"]
        
        for track_id in tracks:
            track_id_str = str(track_id)
            if (str(track_id) not in track_progress_dict):
                res[int(track_id)] = 0

            else:
                res[int(track_id)] = track_progress_dict[track_id_str]

        return {"message": "track progress retrieved successfully", "success": True, "track_progress_data": res}

    def set_track_progress(self, info: UpdateTrackProgressData):
        if (not self.userman.does_session_exist(info.username, info.session_id)):
            return {"message": "session does not exist", "success": False, "error_id": ErrorCodes.INVALID_SESSION}
        
        self.userman.refresh_session(info.username, info.session_id)

        tracks = self.tts.track_data["tracks"]
        id_str = str(info.track_id)
        
        if (id_str not in tracks):
            return {"message": "track not found", "success": False, "error_id": ErrorCodes.TRACK_NOT_FOUND}
        
        users = self.userman.data["users"]

        if (info.username not in users):
            return {"message": "user not found", "success": False, "error_id": ErrorCodes.USER_NOT_FOUND}

        users[info.username]["track_progress"][id_str] = info.progress
        self._save_data()
        self.userman._save_data()

        return {"message": "track progress updated successfully", "success": False}

    def _get_track_information_from_id(self, track_id: int, ref=False) -> dict | None:
        _id = str(track_id)

        if (_id not in self.tts.data["selections"]):
            return None
        
        res: dict = self.tts.data["selections"][_id]

        if (not ref):
            res = deepcopy(res)
            res.pop("filename")
            res["track_id"] = track_id

        return res
    
    def _get_playlist_no_cache(self, id: int):
        """
            for now it's very brute force because i dont expect very many users anyways.
            and honestly playlist for audio books is quite redundant, i feel queues are more important
            however i dont care
        """

        id_str = str(id)

        
        if (id_str not in self.playlist_data["playlists"]):
            return {
                "message": "playlist not found",
                "success": False,
                "playlist": None,
                "error_id": ErrorCodes.PLAYLIST_NOT_FOUND
            }
        
        res = deepcopy(self.playlist_data["playlists"][id_str])
        tracks = []
        for track_id in res["tracks"]:
            current_track = self.tts.track_data["tracks"][str(track_id)]

            tracks.append({"track_id": int(track_id), "track_name": current_track["title"], "length": current_track["length"]})

        res["tracks"] = tracks
        return {"message": "playlist found", "success": True, "playlist": res}
     
    def get_playlist(self, id: int):
        return self._get_playlist_no_cache(id)

    def delete_playlist(self, info: PlaylistDeletionData):

        if (not self.userman.does_session_exist(info.username, info.session_id)):
            return {"message": "playlist not found", "success": False, "error_id": ErrorCodes.INVALID_SESSION}

        self.userman.refresh_session(info.username, info.session_id)

        str_id = str(info.playlist_id) 
        playlists = self.playlist_data["playlists"]

        if (str_id not in playlists):
            return {"message": "playlist not found", "success": False, "error_id": ErrorCodes.PLAYLIST_NOT_FOUND}
        
        if (info.username != playlists[str_id]["owner"]):
            return {"message": "owner is not", "success": False, "error_id": ErrorCodes.WRONG_OWNER}
        
        playlists.pop(str_id)

        users = self.userman.data["users"]
        
        if (info.username in users and int(info.playlist_id) in users[info.username]["playlists"]):
            users[info.username]["playlists"].remove(int(info.playlist_id))

        self.userman._save_data()
        self._save_data()

        return {"message": "playlist deleted", "success": True}
    
    def _get_user_playlist_obj(self, username: str, playlist_id: int) -> PlaylistLookupData | None:
        """
            Returns the parent container as reference
            returns playlist data object as reference
            return playlist key
            EVERYTHING IS REFERENCED BE CAREFUL
        """
        if (username not in self.userman.data["users"]):
            return False
        
        playlist_found = False
        playlist_name = None

        playlists: dict[str, dict] = self.userman.data["users"][username]["playlists"]

        for playlist_name in playlists:
            if (playlists[playlist_name]["playlist_id"] == playlist_id):
                playlist_found = True
                break
        
        if (playlist_found):
            return PlaylistLookupData(playlists, playlists[playlist_name], playlist_name)
        
    def add_track_to_playlist(self, info: PlaylistModifyData):
        if (not self.userman.does_session_exist(info.username, info.session_id)):
            return {"message": "session invalid", "success": False, "error_id": ErrorCodes.INVALID_SESSION}
        
        self.userman.refresh_session(info.username, info.session_id)

        playlist_id_str = str(info.playlist_id)
        playlists = self.playlist_data["playlists"]

        if (playlist_id_str not in playlists):
            return {"message": "message not found", "success": False, "error_id": ErrorCodes.PLAYLIST_NOT_FOUND}

        playlists[playlist_id_str]["tracks"].append(info.track_id)
        self._save_data()

        return {"message": "track added successfully", "success": True}
    
    def remove_track_from_playlist(self, info: PlaylistModifyData):
        if (not self.userman.does_session_exist(info.username, info.session_id)):
            return {"message": "session invalid", "success": False, "error_id": ErrorCodes.INVALID_SESSION}
        
        self.userman.refresh_session(info.username, info.session_id)
        
        playlist_id_str = str(info.playlist_id)
        playlists = self.playlist_data["playlists"]

        if (playlist_id_str not in playlists):
            return {"message": "message not found", "success": False, "error_id": ErrorCodes.PLAYLIST_NOT_FOUND}
        
        if (int(info.track_id) not in playlists[playlist_id_str]["tracks"]):
            return {"message": "track not found", "success": False, "error_id": ErrorCodes.TRACK_NOT_FOUND}
        
        playlists[playlist_id_str]["tracks"].remove(int(info.track_id))
        self._save_data()
        
        return {"message": "track removed successfully", "success": True}

    def get_book_data(self, book_id: int):
        books = self.tts.book_data["books"]
        id_str = str(book_id)
        
        if (id_str not in books):
            return {"message": "book not found", "success": False, "error_id": ErrorCodes.BOOK_NOT_FOUND}

        else:
            return {"message": "book_found", "success": True, "data": books[id_str]}

    