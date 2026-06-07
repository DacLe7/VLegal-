"""
Smoke test for lightweight FastAPI startup.

This script imports app.main and verifies that RAG dependencies are not loaded
during application import.
"""

import asyncio
import importlib
import sys
import time
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

MAX_IMPORT_SECONDS = 10.0
HEAVY_MODULES = (
    "sentence_transformers",
    "torch",
    "transformers",
    "chromadb",
    "google.generativeai",
    "google.genai",
)


def _is_imported(module_name: str) -> bool:
    return module_name in sys.modules or any(
        loaded.startswith(f"{module_name}.") for loaded in sys.modules
    )


def main() -> int:
    start = time.perf_counter()
    app_main = importlib.import_module("app.main")
    duration = time.perf_counter() - start

    print(f"app.main import duration: {duration:.3f}s")

    errors = []
    if duration > MAX_IMPORT_SECONDS:
        errors.append(
            f"app.main import took {duration:.3f}s, expected <= {MAX_IMPORT_SECONDS:.1f}s."
        )

    imported_heavy_modules = [module for module in HEAVY_MODULES if _is_imported(module)]
    if imported_heavy_modules:
        errors.append(
            "Heavy modules imported during startup: "
            + ", ".join(imported_heavy_modules)
        )

    if not errors:
        asyncio.run(app_main.root())
        asyncio.run(app_main.health_check())
        imported_after_health = [module for module in HEAVY_MODULES if _is_imported(module)]
        if imported_after_health:
            errors.append(
                "Heavy modules imported by lightweight root/health handlers: "
                + ", ".join(imported_after_health)
            )

    if errors:
        print("Startup smoke test failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Startup smoke test passed: app imports quickly and RAG is lazy-loaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
