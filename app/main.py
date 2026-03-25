from pathlib import Path
import sys

from app import database, download_manager
from youtubedl import YoutubePlaylist

def main():
    db, v_repo, p_repo = database.main()
    DownladM = download_manager.main(v_repo, p_repo)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        raise FileNotFoundError(str(file_path))
    
    for playlist_url in file_path.open("r", encoding="utf-8"):
        DownladM.download(YoutubePlaylist(playlist_url))





if __name__ == "__main__":
    main()

