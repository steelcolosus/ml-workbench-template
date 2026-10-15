import os
import shutil
import uuid
from pathlib import Path


def tmp_sibling(path: Path) -> Path:
    """
    Temporary path next to `path`. The original name is kept as a suffix so tools
    that pick the format from the extension (savefig, ProfileReport...) still work.
    """
    return path.with_name(f".tmp-{uuid.uuid4().hex[:8]}-{path.name}")


def remove_path(path: Path):
    """Remove a file or folder if it exists."""
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def replace_path(src: Path, dst: Path):
    """
    Move `src` to `dst`, replacing whatever `dst` currently is (file or folder).
    The previous `dst` is only removed once `src` is in place.
    """
    if not (dst.exists() or dst.is_symlink()):
        os.replace(src, dst)
        return

    backup = tmp_sibling(dst)
    os.replace(dst, backup)
    try:
        os.replace(src, dst)
    except BaseException:
        os.replace(backup, dst)
        raise
    remove_path(backup)
