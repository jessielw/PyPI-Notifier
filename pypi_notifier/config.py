import json
import os
from dotenv import load_dotenv
from pathlib import Path

# TODO: test all of these changes for both docker and python


class Config:
    in_docker = True if os.environ.get("IN_DOCKER") == "true" else False

    if in_docker:
        app_data = Path("/app_data")
    else:
        load_dotenv()  # pyright: ignore [reportUnusedCallResult]
        app_data = Path(Path.cwd() / "app_data")

    log_path: Path = Path(app_data / "logs")
    db_path: Path = Path(app_data / "pypi_notifier.db")

    app_data.mkdir(exist_ok=True, parents=True)
    log_path.mkdir(exist_ok=True, parents=True)

    discord_webhook: str = os.environ.get("DISCORD_WEBHOOK", "")
    tracked_packages: dict[str, str] = json.loads(
        os.environ.get("TRACKED_PACKAGES", "")
    )
    interval: int = int(os.environ.get("INTERVAL", 0))
