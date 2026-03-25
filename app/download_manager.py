from app.youtubedl import YoutubePlaylist, YoutubeVideo
from app.database import VideoRepo, PlaylistRepo, Video
from pathlib import Path
import hashlib
import os

def playlist_video_download_error_massage(playlist_url, video_url, err):
    print(f"""[ERROR] Video download FAILED for some reason. details:
[ERROR] playlist:   {playlist_url}
[ERROR] video:      {video_url}
actual_error_massage:
    {err}""")

def calc_download_folder(videoObj:YoutubeVideo | Video, base_path:Path = None) -> Path:
    if isinstance(videoObj, YoutubeVideo):
        yt_id = videoObj.get_video_id()
    elif isinstance(videoObj, Video):
        yt_id = videoObj.yt_id
    else:
        raise ValueError(f"Unknown videoObj type: {type(videoObj)} video object must be: {YoutubeVideo} or {Video}")
    
    h = hashlib.md5(yt_id.encode()).hexdigest()
    return base_path / h[0:2] / h[2:4] / h[4:6]


class DownloadManager:
    def __init__(self, v_repo:VideoRepo, p_repo:PlaylistRepo):
        self.VideoRepo = v_repo
        self.PlaylistRepo = p_repo

    def download(self, YoutubeItem:YoutubePlaylist | YoutubeVideo):
        if isinstance(YoutubeItem, YoutubePlaylist):
            return self.download_playlist(YoutubeItem)
        if isinstance(YoutubeItem, YoutubeVideo):
            return self.download_video(YoutubeItem)

    def download_playlist(self, playlist:YoutubePlaylist):
        playlist_data = self.PlaylistRepo.get_playlist(playlist.get_playlist_id())
        if playlist_data is None:
            playlist_data = self.PlaylistRepo.add_playlist(
                playlist.get_playlist_id(),
                playlist.get_url())

        for video in playlist.iter_videos():
            try:
                print(f"[INFO] [DOWNLOAD] downloading {video.get_video_id()} from playlist {playlist_data.yt_id}")
                video_data = self.download_video(video)
            except Exception as e:
                playlist_video_download_error_massage(playlist.get_url(), video.get_url(), e)
            else:
                self.PlaylistRepo.add_video(playlist_data, video_data)
        print(f"[INFO] [DOWNLOAD] playlist download complete: {playlist_data.yt_id}")

    def download_video(self, video:YoutubeVideo):
        video_data = self.VideoRepo.get_video(video.get_video_id())
        save_path = calc_download_folder(video, os.getenv("DOWNLOAD_FOLDER"))

        if video_data is not None:
            if video_data.exists():
                return video_data
            saved_file = video.download(save_path)
            return self.VideoRepo.update_path(video, saved_file)
            

        saved_file = video.download(save_path)
        return self.VideoRepo.add_video(video.get_video_id(), saved_file)

def main(v_repo:VideoRepo, p_repo:PlaylistRepo):
    DownladM = DownloadManager(
        v_repo=v_repo,
        p_repo=p_repo
        )
    return DownladM

if __name__ == "__main__":
    main()
