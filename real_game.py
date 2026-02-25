from __future__ import annotations

from pathlib import Path

from src.wolf3d.entrypoint import bootstrap


def main() -> None:
    data_root = Path(__file__).resolve().parent / "game_data"
    message = bootstrap(data_root)
    print(message)
    print("Real game runtime shell is initialized. Next step: engine module extraction from poc_game.py")


if __name__ == "__main__":
    main()
