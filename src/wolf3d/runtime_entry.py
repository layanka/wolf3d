from __future__ import annotations

import argparse
from pathlib import Path

from src.wolf3d.runtime import run_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run extracted Wolf3D real runtime")
    parser.add_argument("--smoke-test", action="store_true", help="Run a short headless loop")
    parser.add_argument("--quickload", action="store_true", help="Restore latest disk quick-save on startup")
    parser.add_argument("--data-root", type=Path, default=None, help="Override game data root directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_runtime(smoke_test=args.smoke_test, data_root=args.data_root, quickload=args.quickload)


if __name__ == "__main__":
    main()
