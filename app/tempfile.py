from pathlib import Path
from hashlib import md5
from random import randbytes

def rmtree(path:Path):
    for child in path.iterdir():
        if child.is_dir():
            rmtree(child)
            child.rmdir()
        else:
            child.unlink()
        


class tempFolder:
    temp_base = Path(__file__).parent.parent / "temp"
    def __init__(self, path:Path | None):
        if path is None:
            folder = md5(randbytes(16)).hexdigest()
            path = self.temp_base / folder
        self.path = path
    
    def __enter__(self):
        self.create(exist_ok=False)
        return self

    def create(self, exist_ok:bool = False):
        self.path.mkdir(exist_ok=exist_ok, parents=True)
    
    def __get__(self, instance, owner):
        return instance.path

    def __exit__(self, exc_type, exc, tb):
        rmtree(self.path)

    def __delete__(self, instance):
        rmtree(instance.path)
