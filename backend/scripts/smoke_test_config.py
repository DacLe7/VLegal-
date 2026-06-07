"""
Smoke checks for local/demo configuration.
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


def _load_env_files() -> None:
    for env_file in (REPO_ROOT / ".env", BACKEND_ROOT / ".env"):
        if env_file.exists():
            if load_dotenv:
                load_dotenv(env_file, override=True)
            else:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")


def _resolve_data_dir(raw_value: str) -> Path:
    path = Path(raw_value)
    if path.is_absolute():
        return path

    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    repo_candidate = (REPO_ROOT / path).resolve()
    if repo_candidate.exists():
        return repo_candidate

    return cwd_candidate


def _gitignore_contains(pattern: str) -> bool:
    gitignore = REPO_ROOT / ".gitignore"
    if not gitignore.exists():
        return False
    return pattern in gitignore.read_text(encoding="utf-8").splitlines()


def main() -> int:
    _load_env_files()
    errors = []

    if not os.getenv("GEMINI_API_KEY"):
        errors.append("GEMINI_API_KEY is not set.")
    else:
        print("OK: GEMINI_API_KEY is set.")

    data_dir = _resolve_data_dir(os.getenv("DATA_DIR", "./Data"))
    if not data_dir.exists():
        errors.append(f"DATA_DIR does not exist: {data_dir}")
    else:
        print(f"OK: DATA_DIR exists: {data_dir}")

    try:
        chunk_size = int(os.getenv("CHUNK_SIZE", "0"))
        if chunk_size <= 0:
            errors.append("CHUNK_SIZE must be greater than 0.")
        else:
            print(f"OK: CHUNK_SIZE={chunk_size}")
    except ValueError:
        errors.append("CHUNK_SIZE must be an integer.")

    try:
        chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "-1"))
        if chunk_overlap < 0:
            errors.append("CHUNK_OVERLAP must be greater than or equal to 0.")
        else:
            print(f"OK: CHUNK_OVERLAP={chunk_overlap}")
    except ValueError:
        errors.append("CHUNK_OVERLAP must be an integer.")

    frontend_env_example = REPO_ROOT / "frontend" / ".env.local.example"
    frontend_text = frontend_env_example.read_text(encoding="utf-8") if frontend_env_example.exists() else ""
    frontend_lines = [line.strip() for line in frontend_text.splitlines() if line.strip()]
    if "GEMINI_API_KEY" in frontend_text:
        errors.append("frontend/.env.local.example must not contain GEMINI_API_KEY.")
    elif frontend_lines != ["NEXT_PUBLIC_API_URL=http://localhost:8000"]:
        errors.append("frontend/.env.local.example must only contain NEXT_PUBLIC_API_URL.")
    else:
        print("OK: frontend env example only contains NEXT_PUBLIC_API_URL.")

    for pattern in (".env", "backend/.env", "frontend/.env.local"):
        if not _gitignore_contains(pattern):
            errors.append(f".gitignore does not exclude {pattern}.")
    if not errors:
        print("OK: .env files are ignored and not expected for commit.")

    if errors:
        print("\nSmoke test failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("\nSmoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
