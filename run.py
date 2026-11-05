"""One command prepares the local environment and starts a loopback-only demo."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--setup-only", action="store_true")
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        raise SystemExit("Use Python 3.12 or newer; 3.12–3.14 are recommended for the pinned Django release.")
    if sys.version_info >= (3, 15):
        print("Python 3.15+ is experimental for this pinned Django release; Python 3.12–3.14 are recommended.", flush=True)
    if not 1024 <= args.port <= 65535:
        raise SystemExit("Choose a port from 1024 to 65535.")
    environment = ROOT / ".venv"
    interpreter = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if Path(sys.prefix).resolve() != environment.resolve():
        pip_ready = interpreter.exists() and subprocess.run(
            [str(interpreter), "-m", "pip", "--version"], capture_output=True).returncode == 0
        if not pip_ready:
            subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
        subprocess.run([str(interpreter), str(__file__), *sys.argv[1:]], check=True, cwd=ROOT)
        return
    marker = environment / ".requirements-installed"
    requirement_text = (ROOT / "requirements.txt").read_text()
    if not marker.exists() or marker.read_text() != requirement_text:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True)
        marker.write_text(requirement_text)
    from lens import store, config
    store.seed()
    print("TranscriptLens: six synthetic sessions ready. Existing uploads are preserved.", flush=True)
    print("AI configured." if config.api_key() else "Search-only mode. Add a key to .env and restart for real AI.", flush=True)
    if not args.setup_only:
        print(f"Open http://127.0.0.1:{args.port} — Ctrl+C to stop.", flush=True)
        subprocess.run([sys.executable, str(ROOT / "manage.py"), "runserver", f"127.0.0.1:{args.port}",
                        "--insecure", "--noreload"], cwd=ROOT, check=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
