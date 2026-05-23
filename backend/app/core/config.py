import os
from pathlib import Path


def load_env() -> None:
    for env_path in _candidate_env_paths():
        if env_path.exists():
            _load_env_file(env_path)


def get_env(name: str, default: str | None = None) -> str | None:
    load_env()
    return os.getenv(name, default)


def _candidate_env_paths() -> list[Path]:
    cwd = Path.cwd()
    app_root = Path(__file__).resolve().parents[2]
    backend_root = app_root.parent
    project_root = backend_root.parent

    return [
        cwd / ".env",
        backend_root / ".env",
        project_root / ".env",
    ]


def _load_env_file(env_path: Path) -> None:
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
