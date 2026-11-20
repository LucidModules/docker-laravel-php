ARG FRANKENPHP_VERSION=1.13.6
ARG PHP_VERSION=8.5.13

FROM dunglas/frankenphp:${FRANKENPHP_VERSION}-php${PHP_VERSION}

# PECL extensions are pinned by version and sha256 (PECL publishes no checksums; the hash is
# recorded when the version is bumped, after a 7-day cooldown, see .github/scripts/pecl_bump.py).
ARG REDIS_VERSION=6.3.0
ARG REDIS_SHA256=0d5141f634bd1db6c1ddcda053d25ecf2c4fc1c395430d534fd3f8d51dd7f0b5
ARG IMAGICK_VERSION=3.8.1
ARG IMAGICK_SHA256=3a3587c0a524c17d0dad9673a160b90cd776e836838474e173b549ed864352ee

RUN apt-get update && apt-get install -y \
        libzip-dev libicu-dev libcurl4-openssl-dev \
        libfreetype6-dev libxml2-dev libxslt1-dev \
        libpq-dev unzip curl \
        imagemagick libmagickwand-dev \
    && curl -fsSL -o /tmp/redis.tgz "https://pecl.php.net/get/redis-${REDIS_VERSION}.tgz" \
    && curl -fsSL -o /tmp/imagick.tgz "https://pecl.php.net/get/imagick-${IMAGICK_VERSION}.tgz" \
    && printf '%s  %s\n' "${REDIS_SHA256}" /tmp/redis.tgz "${IMAGICK_SHA256}" /tmp/imagick.tgz | sha256sum -c - \
    && mkdir /tmp/redis /tmp/imagick \
    && tar xzf /tmp/redis.tgz -C /tmp/redis \
    && tar xzf /tmp/imagick.tgz -C /tmp/imagick \
    # PECL tarballs keep package.xml next to the source directory; install-php-extensions wants it inside
    && mv /tmp/redis/package.xml "/tmp/redis/redis-${REDIS_VERSION}/" \
    && mv /tmp/imagick/package.xml "/tmp/imagick/imagick-${IMAGICK_VERSION}/" \
    && install-php-extensions \
        bcmath intl pgsql pdo_pgsql zip pcntl opcache \
        "/tmp/redis/redis-${REDIS_VERSION}" "/tmp/imagick/imagick-${IMAGICK_VERSION}" \
    && rm -rf /tmp/redis* /tmp/imagick* \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*
