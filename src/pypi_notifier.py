from datetime import datetime
from discord_webhook import DiscordWebhook
from feedparser import parse as feed_parse
from requests.exceptions import Timeout
from packaging.version import parse as parse_version
from time import sleep
from src.logger import init_logger
from src.config import Config
from src.database import init_database


class PyPiNotifier:
    def __init__(self) -> None:
        self.config = Config()
        self.logger = init_logger(self.config.log_path)
        self.logger.info("PyPiNotifier initialized.")
        self.db_conn = init_database(self.config.db_path)
        self.validate_config()
        self.run()

    def validate_config(self) -> None:
        if not self.config.DISCORD_WEBHOOK:
            self.logger.critical("You must provide a discord webhook.")
            raise AttributeError("You must provide a discord webhook.")
        if not self.config.TRACKED_PACKAGES:
            self.logger.critical("You must provide packages to track.")
            raise AttributeError("You must provide packages to track.")
        if not self.config.INTERVAL or self.config.INTERVAL == 0:
            self.logger.critical("You must provide a interval.")
            raise ValueError("You must provide a interval.")

    def run(self) -> None:
        while True:
            self.logger.info("Checking for updates.")
            self.parse_feed()
            sleep(self.config.INTERVAL)

    def parse_feed(self) -> None:
        for package_name, url in self.config.TRACKED_PACKAGES.items():
            feed = feed_parse(url)
            for entry in feed.get("entries", []):
                version = entry.get("title", "Unknown")
                last_updated = entry.get("published", None)
                parsed_link = entry.get("link", "")

                if url and last_updated:
                    # ensure proper timestamp format
                    last_updated = self.format_timestamp(last_updated)

                    # check if this package is already in the database
                    cursor = self.db_conn.execute(
                        "SELECT last_updated, version FROM releases WHERE url = ?",
                        (url,),
                    )
                    row = cursor.fetchone()

                    # this is a new package, log it but don't notify
                    if row is None:
                        self.logger.info(
                            f"New package added to database: {package_name}"
                        )
                        self.update_last_updated(
                            url, package_name, version, last_updated
                        )

                    # this is an existing package, check if a new version has been released
                    else:
                        stored_version = row[1]
                        if parse_version(version) > parse_version(stored_version):
                            self.logger.info(
                                f"New version detected for {package_name}: {version}"
                            )
                            self.notify(package_name, version, parsed_link)
                            self.update_last_updated(
                                url, package_name, version, last_updated
                            )

                    self.db_conn.commit()

    def format_timestamp(self, published_str: str) -> str:
        return datetime.strptime(published_str, "%a, %d %b %Y %H:%M:%S GMT").isoformat()

    def update_last_updated(
        self, release_url: str, package_name: str, version: str, last_updated: str
    ) -> None:
        with self.db_conn:
            self.db_conn.execute(
                """
                INSERT INTO releases (package_name, url, version, last_updated) 
                VALUES (?, ?, ?, ?) 
                ON CONFLICT(url) DO UPDATE SET
                    version = excluded.version,
                    last_updated = excluded.last_updated
            """,
                (package_name, release_url, version, last_updated),
            )

    def notify(self, package_name: str, version: str, release_url: str) -> None:
        MAX_RETRIES = 3
        RETRY_DELAY = 5
        notification = f"**{package_name} v{version}** [available]({release_url})"
        for attempt in range(MAX_RETRIES):
            try:
                webhook = DiscordWebhook(
                    url=self.config.DISCORD_WEBHOOK, content=notification
                )
                webhook.execute()
                self.logger.debug(f"Notification sent: {notification}")
                return
            except Timeout as e:
                self.logger.warning(f"Error sending webhook: {e}")
                if attempt < MAX_RETRIES - 1:
                    self.logger.warning(f"Retrying in {RETRY_DELAY} seconds...")
                    sleep(RETRY_DELAY)
                else:
                    self.logger.critical("Max retries reached. Exiting with failure.")
