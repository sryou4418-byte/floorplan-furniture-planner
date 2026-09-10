"""Reload already-imported dependencies once per build on a warm Cloud worker."""
import importlib
import sys
import threading

import planner


def ensure_build(version: str) -> None:
    lock = planner.__dict__.setdefault("_build_lock", threading.RLock())
    with lock:
        if getattr(planner, "_loaded_build", None) == version:
            return
        # Dependencies first. Unimported modules will load normally afterwards.
        for name in ("models", "geometry", "project_io", "presets", "workspace", "actions", "canvas"):
            module = sys.modules.get(f"planner.{name}")
            if module is not None:
                importlib.reload(module)
        planner._loaded_build = version
