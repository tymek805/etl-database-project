import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def get_resource_dir():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)

    return Path(__file__).resolve().parent


def get_external_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


def find_free_port(start_port=8501, end_port=8510):
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port

    raise RuntimeError("No free port found for Streamlit in range 8501-8510")


def open_browser_later(url):
    def open_browser():
        time.sleep(2)
        webbrowser.open(url)

    thread = threading.Thread(target=open_browser, daemon=True)
    thread.start()


def main():
    resource_dir = get_resource_dir()
    external_dir = get_external_dir()
    dashboard_path = resource_dir / "dashboard.py"
    port = find_free_port()
    url = f"http://localhost:{port}"

    os.environ.setdefault("ETL_DATA_DIR", str(resource_dir / "data"))
    os.environ.setdefault("ETL_DOTENV_PATH", str(external_dir / ".env"))
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "false")

    os.chdir(external_dir)
    if os.getenv("ETL_NO_BROWSER") != "1":
        open_browser_later(url)

    from streamlit.web import cli as streamlit_cli

    sys.argv = [
        "streamlit",
        "run",
        str(dashboard_path),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--server.address",
        "localhost",
        "--global.developmentMode",
        "false",
        "--browser.gatherUsageStats",
        "false",
    ]

    return streamlit_cli.main()


if __name__ == "__main__":
    raise SystemExit(main())
