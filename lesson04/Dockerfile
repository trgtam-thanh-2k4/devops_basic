FROM python:3.14-slim

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
    -i http://mirrors.aliyun.com/pypi/simple \
    --trusted-host mirrors.aliyun.com \
    poetry

# . means /app
COPY main.py .

CMD ["python", "main.py"]
