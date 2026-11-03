"""Explicit build guards, including checks that remain enabled under python -O."""
from pathlib import Path
import hashlib, shutil

def require(condition, message):
    if not condition:
        raise ValueError(message)

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024**2), b''):h.update(block)
    return h.hexdigest()

def refuse_existing(output):
    output=Path(output)
    for path in (output, Path(str(output)+'.wal'), output.with_suffix('.manifest.json')):
        if path.exists() or path.is_symlink():raise FileExistsError(path)

def check_budget(work, output_parent, budget, reserve):
    used=0
    for path in Path(work).rglob('*'):
        try:
            if path.is_file():used+=path.stat().st_size
        except FileNotFoundError:
            # DuckDB may remove a WAL between enumeration and stat.
            continue
    free=shutil.disk_usage(output_parent).free
    if used>budget or free<reserve:
        raise RuntimeError(f'Physical budget exceeded: work_bytes={used}, free_bytes={free}, budget={budget}, reserve={reserve}')
    return {'work_bytes':used,'free_bytes':free}
