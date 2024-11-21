FROM python:3.12-alpine

ENV PYTHONPATH /app/src/
ENV PATH /app/src/:$PATH
ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3
ENV TZ=Europe/Moscow

RUN addgroup -g 1000 report && adduser -u 1000 -G report -s /bin/sh -D report

WORKDIR /app/src

RUN pip install "poetry==$POETRY_VERSION"
RUN poetry config virtualenvs.create false
COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-root

ENTRYPOINT []

USER report
COPY --chown=report:report . /app

CMD ["python3", "main.py"]