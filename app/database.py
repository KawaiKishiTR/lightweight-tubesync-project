import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

type video_entry = dict
type playlist_entry = dict

class sqlite3DataBaseManager:
    @classmethod
    def init_from_env(cls):
        env_keys = []
        none_keys = []

        for key in env_keys:
            if os.getenv(key) is None:
                none_keys.append(key)
        
        if none_keys:
            raise EnvironmentError(
                f"{cls} depends on {none_keys} enviroment keys. which is missing"
                )

        return cls(os.getenv("DB_NAME"))

    def __init__(self, file_name:str):
        self.file_name = file_name
        self.connection:sqlite3.Connection | None 

    def connect_database(self) -> sqlite3.Connection:
        if not os.path.exists(self.file_name):
            raise FileNotFoundError(self.file_name)

        self.connection = sqlite3.connect(self.file_name)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

        return self.connection
    
    def execute(self, sql:str, parameters = ()) -> None:
        cursor = self.connection.cursor()
        cursor.execute(sql=sql, parameters=parameters)
        self.connection.commit()
    
    def fetchone(self, sql:str, parameters = ()) -> Any:
        cursor = self.connection.cursor()
        cursor.execute(sql=sql, parameters=parameters)
        return cursor.fetchone()

    def fetchall(self, sql:str, parameters = ()) -> list[Any]:
        cursor = self.connection.cursor()
        cursor.execute(sql=sql, parameters=parameters)
        return cursor.fetchall()

    def create_tables(self):
        if self.connection is None:
            try:
                self.connect_database()
            except Exception as e:
                raise RuntimeError("connect database first")
            
        with self.connection:
            cursor = self.connection.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                yt_id TEXT UNIQUE NOT NULL,
                path TEXT NOT NULL
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id TEXT UNIQUE NOT NULL,
                url TEXT NOT NULL
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlist_videos (
                playlist_id INTEGER,
                video_id INTEGER,
                PRIMARY KEY (playlist_id, video_id),
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
            )
            """)



##########
## MODELS
##########

@dataclass
class Video:
    id:int
    yt_id:str
    path:Path

    @classmethod
    def init_with_data_dict(cls, data:dict):
        return cls(
            id=data["id"],
            yt_id=data["yt_id"],
            path=data["path"]
        )

    def exists(self) -> bool:
        return self.path.exists()

@dataclass
class Playlist:
    id:int
    yt_id:str
    url:str

    @classmethod
    def init_with_data_dict(cls, data:dict):
        return cls(
            id=data["id"],
            yt_id=data["yt_id"],
            url=data["url"]
        )



#########
## REPOS
#########

class VideoRepo:
    def __init__(self, database):
        self.db:sqlite3DataBaseManager = database

    def get_video(self, yt_id:str) -> Video | None:
        video_data = self.db.fetchone(
            "SELECT * FROM videos WHERE yt_id=?",
            (yt_id,)
        )
        if not video_data:
            return None
        return Video.init_with_data_dict(video_data)

    def exists(self, yt_id:str) -> bool:
        return bool(self.get_video(yt_id))

    def add_video(self, yt_id:str, path:str) -> Video:
        self.db.execute("""
            INSERT INTO videos (yt_id, path)
            VALUES (?, ?)
            ON CONFLICT(yt_id) DO NOTHING            
        """, (yt_id, path))
        return self.get_video(yt_id)

    def remove_video(self, video:Video) -> None:
        self.db.execute("""
            DELETE FROM videos
            WHERE yt_id = ?
        """, (video.yt_id,))

    def remove_video_safe(self, video:Video) -> None:
        """
        deleting connections before deleting data
        """
        self.db.execute("""
            DELETE FROM playlist_videos
            WHERE video_id = ?
        """, (video.id,))

        self.remove_video(video)

    def is_video_used(self, video: Video) -> bool:
        resp = self.db.fetchone("""
            SELECT 1
            FROM playlist_videos
            WHERE video_id = ?
            LIMIT 1
        """, (video.id,))

        return bool(resp)

    def update_path(self, video: Video, new_path: str) -> Video:
        self.db.execute("""
            UPDATE videos
            SET path = ?
            WHERE id = ?
        """, (new_path, video.id))

        return self.get_video(video.yt_id)

class PlaylistRepo:
    def __init__(self, database):
        self.db:sqlite3DataBaseManager = database

    def get_playlist(self, playlist_id:str) -> Playlist | None:
        playlist_data = self.db.fetchone(
            "SELECT * FROM playlists WHERE playlist_id=?",
            (playlist_id,)            
        )
        if not playlist_data:
            return None
        return Playlist.init_with_data_dict(playlist_data)

    def exists(self, playlist_id:str):
        return bool(self.get_playlist(playlist_id))

    def add_playlist(self, playlist_id:str, url:str) -> Playlist:
        self.db.execute("""
            INSERT INTO playlists (playlist_id, url)
            VALUES (?, ?)
            ON CONFLICT(playlist_id) DO NOTHING
        """, (playlist_id, url))
        return self.get_playlist(playlist_id)

    def get_playlist_videos(self, playlist:Playlist) -> list[Video]:
        resp = self.db.fetchall("""
            SELECT v.*
            FROM videos v
            JOIN playlist_videos pv ON v.id = pv.video_id
            JOIN playlists p ON p.id = pv.playlist_id
            WHERE p.playlist_id = ?
        """, (playlist.yt_id,))

        if not resp:
            return []
        
        result = []
        for entry in resp:
            video = Video.init_with_data_dict(entry)
            result.append(video)

        return result

    def is_have_video(self, playlist:Playlist, video: Video) -> bool:
        resp = self.db.fetchone("""
            SELECT 1
            FROM playlist_videos
            WHERE playlist_id = ? AND video_id = ?
            LIMIT 1
        """, (playlist.id, video.id))

        return bool(resp)

    def add_video(self, playlist:Playlist, video:Video) -> None:
        self.db.execute("""
            INSERT OR IGNORE INTO playlist_videos (playlist_id, video_id)
            VALUES (?, ?)
        """, (playlist.id, video.id))

    def remove_video(self, playlist:Playlist, video:Video) -> None:
        if not self.is_have_video(playlist, video):
            return None
        
        self.db.execute("""
            DELETE FROM playlist_videos
            WHERE playlist_id = ? AND video_id = ?
        """, (playlist.id, video.id))


def main():
    db = sqlite3DataBaseManager.init_from_env()
    db.connect_database()
    db.create_tables()
    v_repo = VideoRepo(db)
    p_repo = PlaylistRepo(db)

    return db, v_repo, p_repo

if __name__ == "__main__":
    main()