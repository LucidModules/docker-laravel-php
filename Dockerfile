ARG PHP_VERSION=8.4.13

FROM php:${PHP_VERSION}-fpm

RUN apt-get update && apt-get install -y locales && locale-gen en_US.UTF-8

RUN apt install -y \
        zlib1g-dev libzip-dev libicu-dev libcurl4-openssl-dev \
        libfreetype6-dev libxml2-dev libxslt1-dev \
        libpq-dev \
        unzip \
        imagemagick libmagickwand-dev \
    && apt clean -y \
    && php -m \
    && docker-php-ext-install \
     bcmath \
     pgsql \
     pdo_pgsql \
     zip \
     pcntl \
    && docker-php-ext-enable bcmath opcache pgsql pdo_pgsql zip \
    && pecl install redis && docker-php-ext-enable redis \
    && pecl install imagick && docker-php-ext-enable imagick \
    && rm -rf /var/lib/apt/lists/*

RUN curl https://frankenphp.dev/install.sh | sh \
    && mv frankenphp /usr/local/bin/ \
    && chmod +x /usr/local/bin/frankenphp