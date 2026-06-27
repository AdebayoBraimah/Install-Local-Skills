from __future__ import annotations

import logging
import time
from pathlib import Path

from .config import RAGConfig
from .discover import should_index_relative_path
from .index import update_index

LOGGER = logging.getLogger(__name__)


def watch_vault(config: RAGConfig, *, debounce: float = 2.0) -> None:
    from watchfiles import Change, watch

    LOGGER.info("Watching %s for Markdown changes", config.vault_path)
    pending = False
    last_event = 0.0
    for changes in watch(str(config.vault_path), stop_event=None):
        relevant = False
        for change, changed_path in changes:
            path = Path(changed_path)
            try:
                relative_path = path.relative_to(config.vault_path).as_posix()
            except ValueError:
                continue
            if change in {Change.added, Change.modified, Change.deleted} and should_index_relative_path(
                relative_path,
                config,
            ):
                relevant = True
                break
        if not relevant:
            continue
        pending = True
        last_event = time.monotonic()
        while pending and time.monotonic() - last_event < debounce:
            time.sleep(0.2)
        LOGGER.info("Applying debounced update")
        summary = update_index(config)
        LOGGER.info(
            "Update complete: indexed=%s deleted=%s unchanged=%s chunks=%s",
            summary.indexed,
            summary.deleted,
            summary.unchanged,
            summary.chunks_added,
        )
        pending = False

