from datetime import datetime
from discord_webhook import DiscordWebhook
from feedparser import parse as feed_parse
from requests.exceptions import Timeout
from packaging.version import parse as parse_version
from time import sleep
from .logger import init_logger
from .config import Config
from .database import init_database


class PyPiNotifier:
    def __init__(
        self,
        discord_webhook: str | None = None,
        tracked_packages: dict[str, str] | None = None,
        interval: int | None = None,
    ) -> None:
        self.config = Config()

        # update config only if not running in Docker and arguments are provided
        if (
            not self.config.in_docker
            and discord_webhook
            and tracked_packages
            and interval
        ):
            self.config.discord_webhook = discord_webhook
            self.config.tracked_packages = tracked_packages
            self.config.interval = interval

        self.logger = init_logger(self.config.log_path)
        self.validate_config()
        self.db_conn = init_database(self.config.db_path)

        if self.config.in_docker:
            self.run()

    def validate_config(self) -> None:
        def validate_field(value, field_name, expected_type):
            if value is None:
                raise AttributeError(f"{field_name} is required.")
            if not isinstance(value, expected_type):
                raise TypeError(
                    f"{field_name} should be of type {expected_type.__name__}."
                )

        validate_field(self.config.discord_webhook, "Discord webhook", str)
        validate_field(self.config.tracked_packages, "Tracked packages", dict)
        validate_field(self.config.interval, "Interval", int)

        if self.config.interval <= 0:
            raise ValueError("Interval should be greater than 0.")

    def check_updates(self) -> None:
        """Check for updates and notify if a new version is found."""
        self.logger.info("Checking for updates.")
        for package_name, url in self.config.tracked_packages.items():
            feed = feed_parse(url)
            for entry in feed.get("entries", []):
                version = entry.get("title", "Unknown")
                last_updated = entry.get("published", None)
                parsed_link = entry.get("link", "")

                if url and last_updated:
                    last_updated = self.format_timestamp(last_updated)

                    # check if package exists in the database
                    cursor = self.db_conn.execute(
                        "SELECT last_updated, version FROM releases WHERE url = ?",
                        (url,),
                    )
                    row = cursor.fetchone()

                    if row is None:
                        # new package, add to database
                        self.logger.info(
                            f"New package added to database: {package_name}"
                        )
                        self.update_last_updated(
                            url, package_name, version, last_updated
                        )
                    else:
                        # existing package, check for updates
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
        """Format timestamp to ISO format."""
        return datetime.strptime(published_str, "%a, %d %b %Y %H:%M:%S GMT").isoformat()

    def update_last_updated(
        self, release_url: str, package_name: str, version: str, last_updated: str
    ) -> None:
        """Update the database with the latest version and timestamp."""
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
        """Send a Discord notification for a new version."""
        MAX_RETRIES = 3
        RETRY_DELAY = 5
        notification = f"**{package_name} v{version}** [available]({release_url})"
        for attempt in range(MAX_RETRIES):
            try:
                webhook = DiscordWebhook(
                    url=self.config.discord_webhook, content=notification
                )
                webhook.execute()
                self.logger.info(f"Notification sent: {notification}")
                return
            except Timeout as e:
                self.logger.warning(f"Error sending webhook: {e}")
                if attempt < MAX_RETRIES - 1:
                    self.logger.warning(f"Retrying in {RETRY_DELAY} seconds...")
                    sleep(RETRY_DELAY)
                else:
                    self.logger.critical("Max retries reached. Exiting with failure.")

    def run(self) -> None:
        """Run the script once (for cron-based execution)."""
        self.check_updates()

    def run_forever(self) -> None:
        """Run the script in a loop (for scheduler-based execution)."""
        self.logger.info("PyPiNotifier initialized.")
        while True:
            self.check_updates()
            self.logger.debug(f"Sleeping for {self.config.interval} seconds...")
            sleep(self.config.interval)
