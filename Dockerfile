ARG PHP_VERSION=8.4.18

FROM php:${PHP_VERSION}-fpm

RUN apt-get update && apt-get install -y locales && locale-gen en_US.UTF-8 && \
    apt-get install -y \
        zlib1g-dev libzip-dev libicu-dev libcurl4-openssl-dev \
        libfreetype6-dev libxml2-dev libxslt1-dev \
        libpq-dev \
        unzip \
        curl \
        imagemagick libmagickwand-dev \
    && docker-php-ext-install \
     bcmath \
     pgsql \
     pdo_pgsql \
     zip \
     pcntl \
    && docker-php-ext-enable bcmath opcache pgsql pdo_pgsql zip \
    && pecl install redis && docker-php-ext-enable redis \
    && pecl install imagick && docker-php-ext-enable imagick \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then FOR_ARCH="linux-x86_64"; \
    elif [ "$ARCH" = "aarch64" ]; then FOR_ARCH="linux-aarch64"; \
    else echo "Unsupported arch: $ARCH" && exit 1; fi && \
    curl -L -o /usr/local/bin/frankenphp "https://github.com/dunglas/frankenphp/releases/latest/download/frankenphp-${FOR_ARCH}" && \
    chmod +x /usr/local/bin/frankenphp