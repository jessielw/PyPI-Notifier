FROM python:3.11-slim

RUN apt-get update && apt-get install -y cron

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# default cron schedule once per hour
ENV CRON_SCHEDULE="0 * * * *"
ENV IN_DOCKER="true"

# dynamically create the crontab
RUN echo '#!/bin/bash' > /app/start-cron.sh && \
    echo 'echo "$CRON_SCHEDULE python3 /app/run_notifier.py" > /etc/cron.d/pypi_notifier_cron' >> /app/start-cron.sh && \
    echo 'chmod 0644 /etc/cron.d/pypi_notifier_cron && crontab /etc/cron.d/pypi_notifier_cron' >> /app/start-cron.sh && \
    echo 'cron && tail -f /var/log/cron.log' >> /app/start-cron.sh && \
    chmod +x /app/start-cron.sh

CMD ["/app/start-cron.sh"]
