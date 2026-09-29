import json
from pathlib import Path
from typing import Optional, Set

from . import config


def _file(path: Optional[str]) -> Path:
    return Path(path or config.SUBSCRIBERS_FILE)


def load(path: Optional[str] = None) -> Set[int]:
    file = _file(path)
    if not file.exists():
        return set()
    try:
        return set(json.loads(file.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return set()


def _save(ids: Set[int], path: Optional[str]) -> None:
    _file(path).write_text(json.dumps(sorted(ids)), encoding="utf-8")


def add(chat_id: int, path: Optional[str] = None) -> bool:
    ids = load(path)
    if chat_id in ids:
        return False
    ids.add(chat_id)
    _save(ids, path)
    return True


def remove(chat_id: int, path: Optional[str] = None) -> bool:
    ids = load(path)
    if chat_id not in ids:
        return False
    ids.discard(chat_id)
    _save(ids, path)
    return True
