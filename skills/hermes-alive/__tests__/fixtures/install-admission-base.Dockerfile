# Test-only bootstrap tooling. No Hermes profile, provider key or source is baked in.
# Hermes PM, not pip, owns application dependencies after this base is prepared.
FROM python:3.13-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends git gcc libc6-dev ca-certificates \
    && python -m pip install --disable-pip-version-check uv \
    && python -c "import shutil; assert shutil.which('git') and shutil.which('uv')"
