from urllib.parse import urlparse, parse_qs
from app.tempfile import tempFolder
from app.database import Video
from yt_dlp import YoutubeDL
from pathlib import Path
from typing import Any
import hashlib
import shutil
import copy

class VideoNotDownloadedError(Exception):pass


def get_from_url(url:str, key:str) -> str | None:
    return parse_qs(urlparse(url).query).get(key, [None])[0]

def calc_download_folder(videoObj:Video, base_path:Path = None) -> Path:
    if isinstance(videoObj, YoutubeVideo):
        yt_id = videoObj.get_video_id()
    elif isinstance(videoObj, Video):
        yt_id = videoObj.yt_id
    else:
        raise ValueError(f"Unknown videoObj type: {type(videoObj)} video object must be: {YoutubeVideo} or {Video}")
    
    h = hashlib.md5(yt_id.encode()).hexdigest()
    return base_path / h[0:2] / h[2:4] / h[4:6]

class YoutubePlaylist:
    PLAYLIST_PARSER: dict[str, bool] = {
        "quiet":True,
        "extract_flat":True,
    }

    @classmethod
    def init_with_id(cls, playlist_id:str):
        return cls(f"https://www.youtube.com/playlist?list={playlist_id}")

    def __init__(self, url:str):
        self.url = url
        self._info:dict = None

    def get_url(self) -> str:
        return self.url

    def request_info(self):
        with YoutubeDL(self.PLAYLIST_PARSER) as ydl:
            self._info = ydl.extract_info(self.url, download=False)
        return self._info
    
    def get_info(self):
        if self._info is not None:
            return self._info
        return self.request_info()

    def get_playlist_id(self) -> str:
        return get_from_url(self.get_url(), "list")
    
    def get_entries(self) -> list[dict]:
        return self.get_info().get("entries", [])
    
    def get_video_ids(self) -> list[str]:
        return [entry["id"] for entry in self.get_entries() if entry]

    def iter_videos(self):
        return (YoutubeVideo.init_with_id(id) for id in self.get_video_ids())

class YoutubeVideo:
    VIDEO_PARSER: dict[str, Any] = {
        "quiet": True,
        "format": "bestaudio[abr<=128]",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "opus",
                "preferredquality": "128",
            },
            {"key": "FFmpegMetadata"},
            {
                "key": "EmbedThumbnail",
                "already_have_thumbnail": False
            },
        ],
        "writethumbnail": True,
        "embedthumbnail":True,
        "addmetadata":True,
        "outtmpl": "%(id)s.%(ext)s"
    }

    @classmethod
    def init_with_id(cls, yt_id:str):
        return cls(f"https://www.youtube.com/watch?v={yt_id}")

    def __init__(self, url:str):
        self.url = url
        self._info:dict = None

    def request_info(self):
        video_parser = copy.deepcopy(self.VIDEO_PARSER)
        with YoutubeDL(video_parser) as ydl:
            self._info = ydl.extract_info(self.url, download=False)
        return self._info
    
    def get_info(self):
        if self._info is not None:
            return self._info
        return self.request_info()
    
    def _download(self, parser):
        with YoutubeDL(parser) as ydl:
            print(f"[INFO] downloading video: {self.get_url()}")
            return ydl.extract_info(self.get_url(), download=True)

    def download(self, save_path:Path) -> Path:
        video_parser = copy.deepcopy(self.VIDEO_PARSER)

        with tempFolder() as tmp:
            video_parser["outtmpl"] = str(tmp.path / video_parser["outtmpl"])
            self._download(video_parser)

            shutil.move(self.get_path(), save_path)
            print(f"[INFO] Video: {self.get_url()} saved to {str(save_path)}")
        return save_path / self.get_path().name

    def get_url(self) -> str:
        return self.url

    def get_path(self) -> Path:
        filepath = self.get_info().get("filepath") or self.get_info().get("_filename")
        if filepath is not None:
            return Path(filepath)
        filepath = calc_download_folder(self)
        if filepath.exists():
            return filepath
        raise VideoNotDownloadedError(f"{self.url} not downloaded")
    
    def get_duration(self) -> int:
        return self.get_info().get("duration", 0)

    def get_video_id(self) -> str:
        return get_from_url(self.get_url(), "v")

