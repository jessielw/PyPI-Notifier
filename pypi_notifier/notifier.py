import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from discord_webhook import DiscordWebhook
from feedparser import parse as feed_parse
from random import uniform as random_uniform
from requests.exceptions import Timeout
from time import sleep
from threading import Thread
from sqlite3 import Connection
from packaging.version import parse as parse_version
from queue import Queue, Empty

from .logger import init_logger
from .config import Config
from .database import init_database, db_worker_insert, db_worker_select


class PyPiNotifier:
    def __init__(
        self,
        discord_webhook: str | None = None,
        tracked_packages: dict[str, str] | None = None,
        cron_schedule: str | None = None,
    ) -> None:
        self.config = Config()

        # update config only if not running in Docker and arguments are provided
        if not self.config.in_docker:
            if not discord_webhook or not tracked_packages or not cron_schedule:
                raise ValueError(
                    "You must provide all arguments if not running in docker."
                )
            self.config.discord_webhook = discord_webhook
            self.config.tracked_packages = tracked_packages
            self.config.cron_schedule = cron_schedule

        self.logger = init_logger(self.config.log_path)
        self.validate_config()

        # database
        self.db_conn: Connection | None = None
        self.use_db_queue: bool = False

        # database queued vars
        self.db_queue = Queue()
        self.db_response_queue = Queue()
        self.db_thread: Thread | None = None

    def initialize_db_worker(self):
        """Initialize the database worker thread if needed."""
        if not self.use_db_queue:
            return

        self.db_thread = Thread(target=self.db_worker, daemon=True)
        self.db_thread.start()

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
        validate_field(self.config.cron_schedule, "Cron schedule", str)

    def db_worker(self) -> None:
        """Worker thread to handle database operations."""
        db_conn = init_database(self.config.db_path)
        pending_changes = False
        while True:
            try:
                operation, args = self.db_queue.get_nowait()
                if operation == "insert":
                    db_worker_insert(db_conn, *args)
                    pending_changes = True
                elif operation == "select":
                    result = db_worker_select(db_conn, *args)
                    self.db_response_queue.put(result)
                elif operation == "write":
                    if pending_changes:
                        db_conn.commit()
                        pending_changes = False
                elif operation == "exit":
                    if pending_changes:
                        db_conn.commit()
                    db_conn.close()
                    break
                self.db_queue.task_done()
            except Empty:
                sleep(0.25)

    def get_db_select(self, url: str) -> tuple | None:
        if self.use_db_queue:
            self.db_queue.put(("select", (url,)))
            try:
                result = self.db_response_queue.get(timeout=5)
                self.db_response_queue.task_done()
                return result
            except Empty:
                return None
        else:
            if not self.db_conn:
                raise AttributeError("Could not detect database connection.")
            return db_worker_select(self.db_conn, url)

    def insert_into_db(self, package_name, url, version, last_updated):
        if self.use_db_queue:
            self.db_queue.put(("insert", (package_name, url, version, last_updated)))
        else:
            if not self.db_conn:
                raise AttributeError("Could not detect database connection.")
            db_worker_insert(self.db_conn, package_name, url, version, last_updated)

    def check_updates(self) -> None:
        """Check for updates and notify if a new version is found."""
        self.logger.info("Checking for updates.")

        if not self.db_conn:
            self.db_conn = init_database(self.config.db_path)

        for package_name, url in self.config.tracked_packages.items():
            feed = feed_parse(url)
            for entry in feed.get("entries", []):
                version = entry.get("title", "Unknown")
                last_updated = entry.get("published", None)
                parsed_link = entry.get("link", "")

                if url and last_updated:
                    last_updated = self.format_timestamp(last_updated)

                    # check if package exists in the database
                    row = self.get_db_select(url)

                    # new package, add to database
                    if not row:
                        self.logger.info(
                            f"New package added to database: {package_name}"
                        )
                        self.insert_into_db(package_name, url, version, last_updated)

                    # existing package, check for updates
                    else:
                        stored_version = row[1]
                        if parse_version(version) > parse_version(stored_version):
                            self.logger.info(
                                f"New version detected for {package_name}: {version}"
                            )
                            self.notify(package_name, version, parsed_link)
                            self.insert_into_db(
                                package_name, url, version, last_updated
                            )

        if not self.use_db_queue:
            self.db_conn.commit()
        else:
            self.db_queue.put(("write", None))

    def format_timestamp(self, published_str: str) -> str:
        """Format timestamp to ISO format."""
        return datetime.strptime(published_str, "%a, %d %b %Y %H:%M:%S GMT").isoformat()

    def notify(self, package_name: str, version: str, release_url: str) -> None:
        """Send a Discord notification for a new version with exponential backoff retries."""
        MAX_RETRIES = 5
        BASE_DELAY = 2
        MAX_DELAY = 60

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
                    delay = min(BASE_DELAY * (2**attempt), MAX_DELAY)
                    delay += random_uniform(0, 1)
                    self.logger.warning(
                        f"Retrying in {delay:.2f} seconds (attempt {attempt + 1}/{MAX_RETRIES})..."
                    )
                    sleep(delay)
                else:
                    self.logger.critical(
                        "Max retries reached. Notification failed permanently."
                    )

    def run(self) -> None:
        """Run the script once (for user-based execution)."""
        self.use_db_queue = False
        self.check_updates()

    async def _keep_alive(self, scheduler: BackgroundScheduler):
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            if self.use_db_queue:
                self.db_queue.put(("exit", None))
            scheduler.shutdown()

    def run_forever(self) -> None:
        """Run the script using APScheduler (for scheduler-based execution)."""
        self.logger.info(
            f"PyPiNotifier initialized (CRON schedule: {self.config.cron_schedule})."
        )
        self.use_db_queue = True
        self.initialize_db_worker()
        self.check_updates()

        scheduler = BackgroundScheduler()
        cron_schedule = CronTrigger.from_crontab(self.config.cron_schedule)
        scheduler.add_job(self.check_updates, cron_schedule)
        scheduler.start()

        # keep main thread alive
        asyncio.run(self._keep_alive(scheduler))
