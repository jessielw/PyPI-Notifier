import shutil
import json
import os
from dotenv import load_dotenv
from pathlib import Path


class Config:
    if str(Path.cwd()) == "/code":
        # TODO: test in docker container
        app_data: Path = Path(Path.cwd().parent / "app_data")
    else:
        load_dotenv()  # pyright: ignore [reportUnusedCallResult]
        app_data = Path(Path.cwd() / "app_data")

    log_path: Path = Path(app_data / "logs")
    db_path: Path = Path(app_data / "pypi_notifiar.db")
    # print(log_path)

    # exit()

    app_data.mkdir(exist_ok=True, parents=True)
    log_path.mkdir(exist_ok=True, parents=True)
    # shutil.copytree(
    #     Path(Path.cwd()) / "----" / "static", flask_static, dirs_exist_ok=True
    # )

    DISCORD_WEBHOOK: str = os.environ.get("DISCORD_WEBHOOK", "")
    TRACKED_PACKAGES: dict[str, str] = json.loads(
        os.environ.get("TRACKED_PACKAGES", "")
    )
    INTERVAL: int = int(os.environ.get("INTERVAL", 0))
