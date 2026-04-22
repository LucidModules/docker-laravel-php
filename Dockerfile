FROM dunglas/frankenphp:1.12.2-php8.5.5

RUN apt-get update && apt-get install -y \
        libzip-dev libicu-dev libcurl4-openssl-dev \
        libfreetype6-dev libxml2-dev libxslt1-dev \
        libpq-dev unzip curl \
        imagemagick libmagickwand-dev \
    && install-php-extensions \
        bcmath pgsql pdo_pgsql zip pcntl \
        redis imagick opcache \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*
