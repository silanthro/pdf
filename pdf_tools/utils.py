import json
import os
from pathlib import Path


class NotAuthorizedError(Exception):
    pass


def _get_allowed_dir() -> list[Path]:
    allowed_dir_str = os.environ.get("ALLOWED_DIR")
    if not allowed_dir_str:
        return None
    if "[" in allowed_dir_str:
        return [Path(p).resolve() for p in json.loads(allowed_dir_str)]
    else:
        return [Path(allowed_dir_str).resolve()]


ALLOWED_DIR = _get_allowed_dir()


def path_is_allowed(path: str):
    if ALLOWED_DIR is None:
        return True
    if any(Path(path).resolve() == dir for dir in ALLOWED_DIR):
        return True
    if not any(dir in Path(path).resolve().parents for dir in ALLOWED_DIR):
        raise NotAuthorizedError()
