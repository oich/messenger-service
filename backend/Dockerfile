FROM python:3.12-slim

WORKDIR /code

ENV PYTHONPATH=/code

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /code/

# Remove Windows line endings from start script
RUN sed -i 's/\r$//' /code/start.sh && chmod +x /code/start.sh

CMD ["/bin/bash", "/code/start.sh"]
