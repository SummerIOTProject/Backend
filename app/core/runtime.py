from __future__ import annotations

import tempfile
from pathlib import Path

from app.core.config import settings


def ensure_upload_storage_ready() -> None:
    root = settings.upload_path
    probe = None
    try:
        root.mkdir(parents=True, exist_ok=True)
        for child in ("before", "after"):
            (root / child).mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=root, prefix=".write-test-", delete=False) as tmp:
            tmp.write(b"ok")
            probe = Path(tmp.name)
        if probe is not None and probe.exists():
            probe.unlink()
    except OSError as exc:
        if probe is not None and probe.exists():
            probe.unlink()
        raise RuntimeError("Upload storage is not writable.") from exc
