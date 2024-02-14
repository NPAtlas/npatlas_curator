FROM python:3.10-bullseye

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.4.0 \
    PATH="/root/.local/bin:${PATH}" \
    FLASK_APP="run.py" \
    FLASK_CONFIG=production \
    FLASK_ENV=production

RUN useradd --user-group --create-home --no-log-init --shell /bin/bash flask

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && curl -sSL 'https://install.python-poetry.org' | python - \
    && poetry --version


# Copy web dependecies and install
RUN mkdir /home/flask/app
WORKDIR /home/flask/app
COPY poetry.lock pyproject.toml ./
RUN  poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev --no-root

USER flask

# Copy backend code
COPY app/ ./app/
COPY run.py celery_worker.py ./

EXPOSE 5000
CMD /bin/bash -c "gunicorn -w 4 -b 0.0.0.0:5000 run:app --access-logfile /dev/stdout --preload"
