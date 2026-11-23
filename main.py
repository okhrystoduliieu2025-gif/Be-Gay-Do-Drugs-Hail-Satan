from importlib.util import find_spec
from pathlib import Path
import subprocess
import sys


def ensure_dependencies():
    needed = []

    if find_spec("game2dboard") is None:
        needed.append("game2dboard")
    if find_spec("PIL") is None:
        needed.append("Pillow")

    if not needed:
        return

    requirements = Path(__file__).resolve().parent / "requirements.txt"
    print("Installing missing game libraries: " + ", ".join(needed), flush=True)

    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements)
        ])
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(
            "Could not install the required libraries automatically. "
            "Connect to the internet and run: "
            "python -m pip install -r requirements.txt"
        ) from exc

    if find_spec("game2dboard") is None or find_spec("PIL") is None:
        raise SystemExit(
            "The game libraries are still unavailable. "
            "Check your Python environment and run: "
            "python -m pip install -r requirements.txt"
        )


def main():
    ensure_dependencies()
    from battle_mode import BattleGameApp
    BattleGameApp().run()


if __name__ == "__main__":
    main()
