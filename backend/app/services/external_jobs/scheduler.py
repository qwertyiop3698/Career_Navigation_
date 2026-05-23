import logging
import threading

from app.core.config import get_env
from app.db import SessionLocal
from app.services.external_jobs.persistence import collect_external_jobs_to_db

logger = logging.getLogger(__name__)

_stop_event = threading.Event()
_worker_thread: threading.Thread | None = None


def start_external_jobs_scheduler() -> None:
    global _worker_thread

    if not _is_enabled():
        logger.info("External jobs scheduler is disabled.")
        return
    if _worker_thread is not None and _worker_thread.is_alive():
        return

    _stop_event.clear()
    _worker_thread = threading.Thread(
        target=_run_scheduler,
        name="external-jobs-daily-scheduler",
        daemon=True,
    )
    _worker_thread.start()


def stop_external_jobs_scheduler() -> None:
    _stop_event.set()


def _run_scheduler() -> None:
    initial_delay_seconds = _get_int_env("EXTERNAL_JOBS_INITIAL_DELAY_SECONDS", 60)
    interval_seconds = _get_int_env("EXTERNAL_JOBS_INTERVAL_SECONDS", 24 * 60 * 60)

    logger.info(
        "External jobs scheduler started: initial_delay=%ss interval=%ss",
        initial_delay_seconds,
        interval_seconds,
    )

    if _stop_event.wait(initial_delay_seconds):
        return

    while not _stop_event.is_set():
        _collect_once()
        if _stop_event.wait(interval_seconds):
            break


def _collect_once() -> None:
    db = SessionLocal()
    try:
        result = collect_external_jobs_to_db(db)
        logger.info("Scheduled external jobs collection finished: %s", result)
    except Exception:
        logger.exception("Scheduled external jobs collection failed")
    finally:
        db.close()


def _is_enabled() -> bool:
    value = (get_env("EXTERNAL_JOBS_AUTO_COLLECT_ENABLED", "true") or "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    value = get_env(name)
    try:
        return int(value) if value is not None else default
    except ValueError:
        logger.warning("Invalid %s=%r; using default %s", name, value, default)
        return default
