# PyPi Notifier

A script to notify you about new releases of Python packages via Discord webhooks. The script checks for updates on the specified packages at regular intervals, stores the information in a SQLite database, and sends notifications when a new version is released.

### Supported Notification Clients:

- Discord

## Prerequisites

- Python 3.10 or higher
- Docker (if using Docker setup)
- `.env` file for environment variables (can pass variables as environment variables in Docker)

## Setup

### 1. **Setup Outside Docker** (Manual Environment)

#### Install Dependencies

1. Clone the repository:

   ```bash
   git clone https://github.com/jessielw/PyPI-Update-Notifier
   cd PyPI-Update-Notifier
   ```

2. Install required Python packages using `pip` or `poetry`:

   ```bash
   pip install -r requirements.txt
   ```

   Or if you're using poetry:

   ```bash
   poetry install
   ```

#### Create `.env` File

You'll need to create a `.env` file in the root directory of your project. Here's an example `.env` configuration:

```env
DISCORD_WEBHOOK="https://discord.com/api/webhooks/your_webhook_url"
TRACKED_PACKAGES='{"PySide6": "https://pypi.org/rss/project/PySide6/releases.xml", "TkFontSelector": "https://pypi.org/rss/project/tkfontselector/releases.xml"}'
INTERVAL="600"
```

- `DISCORD_WEBHOOK`: Your Discord webhook URL.
- `TRACKED_PACKAGES`: A JSON string containing the names and URLs of the packages to track.
- `INTERVAL`: The interval in seconds between each check for new releases.

#### Running the Script

Once everything is set up, you can run the script with:

```bash
python run_notifier.py
```

### 2. **Setup with Docker**

#### Pull the Docker Image

1. Make sure you have Docker installed and running. If not, follow the [Docker installation guide](https://docs.docker.com/get-docker/).

2. Pull the Docker image [Link](https://hub.docker.com/repository/docker/jlw4049/pypi-update-notifier/):

   ```bash
   docker pull jlw4049/pypi-update-notifier
   ```

#### Running the Docker Container

To run the Docker container with the appropriate environment variables, use the following command:

```bash
docker run -e "DISCORD_WEBHOOK=<your_webhook_url>" -e "TRACKED_PACKAGES=<your_tracked_packages_json>" -e "INTERVAL=<interval_in_seconds>" -v "app_data:/app_data"
```

- Replace `<your_webhook_url>` with your Discord webhook URL.
- Replace `<your_tracked_packages_json>` with the JSON string of tracked packages.
- Replace `<interval_in_seconds>` with the interval for checking updates.

This command will mount the `app_data` volume to persist the database and logs across container restarts.

#### Checking Logs

Outside of docker you can view the logs in `./app_data/logs/`.

To view the logs of the running container, use the following command:

```bash
docker logs -f <container_name>
```

This will stream the logs and show any output from the script.

---

### Notes:

- The `app_data` volume is used for persistent storage, including the SQLite database and logs.
- If you're running the script outside Docker, the `app_data` folder will be created in your local directory to store logs and the database.
