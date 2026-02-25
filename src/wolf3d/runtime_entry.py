from __future__ import annotations

import argparse

from src.wolf3d.runtime import run_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run extracted Wolf3D real runtime")
    parser.add_argument("--smoke-test", action="store_true", help="Run a short headless loop")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_runtime(smoke_test=args.smoke_test)


if __name__ == "__main__":
    main()
