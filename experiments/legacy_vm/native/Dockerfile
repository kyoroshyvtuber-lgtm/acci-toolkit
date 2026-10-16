FROM ubuntu:22.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential ca-certificates pkg-config python3 python3-pil meson ninja-build \
    autoconf automake libtool gettext bison flex \
    libglib2.0-dev libpixman-1-dev libfdt-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
# Builds run later with --network none, no credentials, dropped capabilities,
# read-only source/toolchain mounts and a separate writable output mount.
WORKDIR /work