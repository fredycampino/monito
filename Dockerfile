# Monito Box includes a fixed Skiller runtime and the Monito flow.
FROM python:3.12-slim

ARG SKILLER_VERSION=0.1.0-beta.42

ENV HOME=/home/monito \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 monito \
    && useradd --create-home --uid 10001 --gid monito --shell /usr/sbin/nologin monito \
    && pip install "skiller==${SKILLER_VERSION}"

# The application is part of the immutable image. Mutable state belongs in /data.
COPY monito/ /opt/monito/monito/

# Running from this directory makes the bundled flow resolve as `@monito` without
# changing the user's persistent Skiller configuration.
WORKDIR /opt/monito/monito
# Safe default for `docker run`. Compose may override this with
# `user: "${HOST_UID}:${HOST_GID}"` so bind-mounted files belong to the host user.
USER monito

ENTRYPOINT ["skiller"]
CMD ["--help"]
