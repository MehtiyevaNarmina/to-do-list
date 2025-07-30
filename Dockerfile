FROM python:3.13-slim

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml README.md ./

# Disable venv creation and install deps
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

COPY src/ /app/src/

WORKDIR /app

CMD ["python", "-m", "src.to_do_list.runsserver"] 