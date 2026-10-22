#!/usr/bin/env python3
"""Discover the latest FrankenPHP image for each maintained PHP line (versions.json)
and emit a GitHub Actions build matrix.

FrankenPHP tags look like "1.12.6-php8.5.8". For each PHP line we take the highest
PHP patch available, and for that patch the highest FrankenPHP version. Set
FRANKENPHP_VERSION (the workflow_dispatch input) to require that exact FrankenPHP
release instead: the run fails rather than build an older one.

Besides the moving tags (8.5.12, 8.5, 8, latest), every image gets
"<php>-frankenphp<frankenphp>", e.g. "8.5.12-frankenphp1.13.2". Apps pin that one,
so the tag alone says which PHP and FrankenPHP they run."""
import functools
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

IMAGE = os.environ.get("IMAGE", "docker.io/lucidmodules/docker-laravel-php")
REQUIRED_FRANKENPHP = os.environ.get("FRANKENPHP_VERSION", "").strip()


RETRY_STATUSES = {403, 429, 500, 502, 503, 504}
REGISTRY = "https://registry-1.docker.io"
REGISTRY_AUTH = "https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull"


def fetch_json(url, headers=None, attempts=5):
    """GET a JSON document, retrying transient failures with exponential backoff.
    Returns (data, response headers)."""
    headers = {"User-Agent": "lucidmodules-ci", **(headers or {})}
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response), response.headers
        except urllib.error.URLError as exc:  # HTTPError is a subclass
            status = getattr(exc, "code", None)
            if attempt == attempts or (status is not None and status not in RETRY_STATUSES):
                raise
            delay = 2 ** attempt
            print(f"::warning::{url}: {exc}; retrying in {delay}s ({attempt}/{attempts - 1})", file=sys.stderr)
            time.sleep(delay)


def get_json(url):
    return fetch_json(url)[0]


def next_link(link_header, base_url):
    if link_header and (m := re.search(r'<([^>]+)>;\s*rel="next"', link_header)):
        return urllib.parse.urljoin(base_url, m.group(1))
    return None


@functools.lru_cache(maxsize=None)
def hub_tags(repo):
    """All tags of a Docker Hub repository, fetched through the registry API (the same
    endpoint `docker pull` uses). hub.docker.com's web API intermittently answers
    anonymous requests from GitHub-hosted runners with 403, the registry does not."""
    token = get_json(REGISTRY_AUTH.format(repo=repo))["token"]
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{REGISTRY}/v2/{repo}/tags/list"
    tags = []
    while url:
        data, response_headers = fetch_json(url, headers)
        tags += data.get("tags") or []
        url = next_link(response_headers.get("Link"), url)
    return tuple(tags)


def latest_frankenphp(line):
    pattern = re.compile(rf"(\d+)\.(\d+)\.(\d+)-php{re.escape(line)}\.(\d+)")
    candidates = []
    for tag in hub_tags("dunglas/frankenphp"):
        if m := pattern.fullmatch(tag):
            fp = tuple(map(int, m.group(1, 2, 3)))
            if REQUIRED_FRANKENPHP and ".".join(map(str, fp)) != REQUIRED_FRANKENPHP:
                continue
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
            if REQUIRED_FRANKENPHP:
                sys.exit(f"no dunglas/frankenphp:{REQUIRED_FRANKENPHP}-php{line}.* tag")
            print(f"::warning::no frankenphp tag found for php {line}, skipping {line}", file=sys.stderr)
            continue
        available.append((line, frankenphp_version, php_version))

    if not available:
        sys.exit("no buildable PHP lines discovered")

    newest = available[-1][0]
    entries = []
    for line, frankenphp_version, php_version in available:
        tags = [f"{php_version}-frankenphp{frankenphp_version}", php_version, line]
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
