#!/usr/bin/env python3
"""Discover the latest FrankenPHP image for each maintained PHP line (versions.json)
and emit a GitHub Actions build matrix.

FrankenPHP tags look like "1.12.6-php8.5.8". For each PHP line we take the highest
PHP patch available, and for that patch the highest FrankenPHP version."""
import json
import os
import re
import sys
import urllib.request

IMAGE = os.environ.get("IMAGE", "docker.io/lucidmodules/docker-laravel-php")


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "lucidmodules-ci"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def hub_tags(repo, name_filter):
    url = f"https://hub.docker.com/v2/repositories/{repo}/tags/?page_size=100&name={name_filter}"
    while url:
        data = get_json(url)
        yield from (t["name"] for t in data["results"])
        url = data.get("next")


def latest_frankenphp(line):
    pattern = re.compile(rf"(\d+)\.(\d+)\.(\d+)-php{re.escape(line)}\.(\d+)")
    candidates = []
    for tag in hub_tags("dunglas/frankenphp", f"php{line}."):
        if m := pattern.fullmatch(tag):
            fp = tuple(map(int, m.group(1, 2, 3)))
            php_patch = int(m.group(4))
            candidates.append((php_patch, fp))
    if not candidates:
        return None, None
    php_patch, fp = max(candidates)
    return ".".join(map(str, fp)), f"{line}.{php_patch}"


def main():
    lines = json.load(open("versions.json"))["php_lines"]
    lines.sort(key=lambda l: tuple(map(int, l.split("."))))

    available = []
    for line in lines:
        frankenphp_version, php_version = latest_frankenphp(line)
        if not php_version:
            print(f"::warning::no frankenphp tag found for php {line}, skipping {line}", file=sys.stderr)
            continue
        available.append((line, frankenphp_version, php_version))

    if not available:
        sys.exit("no buildable PHP lines discovered")

    newest = available[-1][0]
    entries = []
    for line, frankenphp_version, php_version in available:
        tags = [php_version, line]
        if line == newest:
            tags += [line.split(".")[0], "latest"]
        entries.append({
            "frankenphp_version": frankenphp_version,
            "php_version": php_version,
            "tags": ",".join(f"{IMAGE}:{t}" for t in tags),
        })

    matrix = json.dumps({"include": entries})
    print(matrix)
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a") as fh:
            fh.write(f"matrix={matrix}\n")


if __name__ == "__main__":
    main()
