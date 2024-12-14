# PyPi Notifier

A script to notify you about new releases of Python packages via Discord webhooks. The script checks for updates on the specified packages at regular intervals, stores the information in a SQLite database, and sends notifications when a new version is released.

Upon initial launch, no notifications will be sent until a **new update** is detected.

### Supported Notification Clients:

- **Discord**

## Prerequisites

- Python 3.10 or higher
- Docker (if using Docker setup)

## Setup

#### Options for Use

- Docker
- Package

#### Running the Script as a Package

1. Install the package

   ```bash
   poetry add pypi-notifier
   # or
   pip install pypi-notifier
   ```

2. Use in your Python code

   ```python
   from pypi_notifier import PyPiNotifier
   notifier = PyPiNotifier(
        discord_webhook="https://discord.com/api/webhooks/...",
        tracked_packages={
            "PySide6": "https://pypi.org/rss/project/PySide6/releases.xml",
            "TkFontSelector": "https://pypi.org/rss/project/tkfontselector/releases.xml",
        },
        cron_schedule="0 * * * *",  # Cron schedule format for checking updates every hour
   )

   # Run the notifier once
   notifier.run()

   # Or run continuously as scheduled by cron
   notifier.run_forever()
   ```

#### Running the Docker Container

To run the Docker container with the appropriate environment variables, use the following command:

```bash
docker run -e "DISCORD_WEBHOOK=<your_webhook_url>" -e "TRACKED_PACKAGES=<your_tracked_packages_json>" -e "CRON_SCHEDULE=0 * * * *" -v "app_data:/app_data"
```

- Replace `<your_webhook_url>` with your Discord webhook URL.
- Replace `<your_tracked_packages_json>` with the JSON string of your tracked packages, for example:

```json
{
  "PySide6": "https://pypi.org/rss/project/PySide6/releases.xml",
  "TkFontSelector": "https://pypi.org/rss/project/tkfontselector/releases.xml"
}
```

This command will mount the `app_data` volume to persist the database and logs across container restarts.

#### Checking Logs

Outside of Docker, you can view the logs in `./app_data/logs/`.

### Notes

- The `app_data` volume is used for persistent storage, including the SQLite database and logs.
- If you're running the script outside Docker, the `app_data` folder will be created in your local directory to store logs and the database.
- The **cron_schedule** format follows standard cron syntax for scheduling tasks. For example, `0 * * * *` runs the script every hour.
- If no updates are detected for a package, no notifications will be sent until a newer version is found.

### Troubleshooting

- **Error Logs**: If something goes wrong, check the logs at `./app_data/logs/` for more details.
- **Database Issues**: Ensure that the SQLite database is properly initialized and accessible.
