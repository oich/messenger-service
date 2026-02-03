FROM python:3.12-slim

WORKDIR /code

ENV PYTHONPATH=/code

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /code/

# Shared packages
COPY --from=shared hub_sync_client/ /opt/hub_sync_client/
COPY --from=shared hub_messenger_client/ /opt/hub_messenger_client/
COPY --from=shared satellite_api_client/ /opt/satellite_api_client/

# Remove Windows line endings from start script
RUN sed -i 's/\r$//' /code/start.sh && chmod +x /code/start.sh

CMD ["/bin/bash", "/code/start.sh"]
