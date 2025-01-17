from schemas import PlaylistCreationData, PlaylistDeletionData, PlaylistModifyData, ErrorStuff, GetTrackProgress
from user import UserMan
from tts_helper import TTSingle
from dataclasses import dataclass
from copy import deepcopy

@dataclass
class PlaylistLookupData:
    parent_container: dict
    target: dict
    playlist_key: str

class Trackman():
    INSTANCE = None
    PLAYLIST_COUNT = 0

    def __init__(self):
        self.userman: UserMan = UserMan.get_instance()
        self.tts: TTSingle = TTSingle.get_instance()
        self.playlist_map = {} # for faster lookups if ever needed, although could be bulky on memory?
        # possible store playlists in a separate file, but that would require some substantial refactor

    
    def get_instance():
        if (Trackman.INSTANCE is None):
            Trackman.INSTANCE = Trackman()
            Trackman.PLAYLIST_COUNT = Trackman.INSTANCE.userman.data["playlist_id"]
        return Trackman.INSTANCE
    

    def _create_playlist_object(self, playlist_name: str):
        playlist_id = Trackman.PLAYLIST_COUNT
        Trackman.PLAYLIST_COUNT += 1
        
        self.userman.data["playlist_id"] += 1
        self.userman._save_data()

        return {
            "display_name": playlist_name,
            "tracks": [],
            "playlist_id": playlist_id
        }

    def create_playlist(self, info: PlaylistCreationData):
        username = info.username.lower()
        if (not self.userman.does_session_exist(username, info.session_id)):
            return {"success": False, "playlistId": None, "message": "invalid session", "error_id": ErrorStuff.INVALID_SESSION}
        
        playlist_name = info.playlist_name.lower()

        user_playlists = self.userman.data["users"][username]["playlists"]

        if (playlist_name in user_playlists):
            return {"success": False, "playlistId": None,
                     "message": "playlist already exists", "error_id": ErrorStuff.PLAYLIST_ALREADY_EXISTS}
        playlist_obj = self._create_playlist_object(info.playlist_name)
        user_playlists[playlist_name] = playlist_obj
        self.userman._save_data()

        return {
            "success": True,
            "playlistId": playlist_obj["playlist_id"],
            "message": "playlist successfully created"
        }
    
    def get_playlists(self, username: str):
        all_users = self.userman.data["users"]

        _username = username.lower()

        if (_username not in all_users):
            return {"message": "user not found", "error_id": ErrorStuff.USER_NOT_FOUND}
        
        return {"message": "", "playlists": all_users[_username]["playlists"]}

    def get_tracks_progress(self, info: GetTrackProgress):
        if (self.userman.does_session_exist(info.username, info.session_id)):
            res = {}

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

        all_users = self.userman.data["users"]

        for user in all_users:
            current_user = all_users[user]
            playlists = current_user["playlists"]

            for playlist_name in playlists:
                obj = deepcopy(playlists[playlist_name])
                new_tracks = []

                for track in obj["tracks"]:
                    new_tracks.append(self._get_track_information_from_id(track))

                obj["tracks"] = new_tracks

                if (obj["playlist_id"] == id):
                    return {
                        "message": "playlist found",
                        "success": True,
                        "playlist": obj
                    }
        
        return {
            "message": "playlist not found",
            "success": False,
            "playlist": None,
            "error_id": ErrorStuff.PLAYLIST_NOT_FOUND
        }
    
    def get_playlist(self, id: int):
        return self._get_playlist_no_cache(id)

    def delete_playlist(self, info: PlaylistDeletionData):

        if (not self.userman.does_session_exist(info.username, info.session_id)):
            return {"message": "playlist not found", "success": False, "error_id": ErrorStuff.INVALID_SESSION}

        self.userman.refresh_session(info.username, info.session_id)

        if (info.username not in self.userman.data["users"]):
            return {"message": "user not found (how)", "success": False, "error_id": ErrorStuff.USER_NOT_FOUND}
        
        playlist_data = self._get_user_playlist_obj(info.username, info.playlist_id)
            
        if (playlist_data is not None):
            playlist_data.parent_container.pop(playlist_data.playlist_key)

        self.userman._save_data()

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
            return {"message": "session invalid", "success": False, "error_id": ErrorStuff.INVALID_SESSION}
        
        self.userman.refresh_session(info.username, info.session_id)

        playlist_data = self._get_user_playlist_obj(info.username, info.playlist_id)

        if (playlist_data is None):
            return {"message": "playlist not found", "success": False, "error_id": ErrorStuff.PLAYLIST_NOT_FOUND}

        playlist_data.target["tracks"].append(info.track_id)

        self.userman._save_data()

        return {"message": "track added successfully", "success": True}
    
    def remove_track_from_playlist(self, info: PlaylistModifyData):
        if (not self.userman.does_session_exist(info.username, info.session_id)):
            return {"message": "session invalid", "success": False, "error__id": ErrorStuff.INVALID_SESSION}
        
        self.userman.refresh_session(info.username, info.session_id)
        
        playlist_data = self._get_user_playlist_obj(info.username, info.playlist_id)

        if (playlist_data is None):
            return {"message": "playlist not found", "success": False, "error_Id": ErrorStuff.PLAYLIST_NOT_FOUND}
        
        playlist_tracks: list[int] = playlist_data.target["tracks"]

        if (info.track_id not in playlist_tracks):
            return {"message": "track not found", "success": False, "error_id": ErrorStuff.TRACK_NOT_FOUND}

        playlist_tracks.remove(info.track_id)

        self.userman._save_data()

        return {"message": "track removed successfully", "success": True}
     



