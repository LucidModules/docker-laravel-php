#!/usr/bin/env python3
"""Propose updates for the PECL extensions pinned in the Dockerfile.

For each extension (ARG <NAME>_VERSION / <NAME>_SHA256), look up the latest stable release on PECL.
If it is newer than the pinned version and at least MIN_RELEASE_AGE_DAYS old, download the tarball
twice, require identical sha256s, and rewrite both ARGs in the Dockerfile.

PECL publishes no checksums, so the recorded sha256 is trust-on-first-use: it pins exactly what we
reviewed; the cooldown and the human PR review cover the first download. Prints a Markdown summary of
the changes (empty when nothing changed) for the pull request body.
"""
import datetime as dt
import hashlib
import re
import sys
import time
import urllib.error
import urllib.request

MIN_RELEASE_AGE_DAYS = 7
EXTENSIONS = {"REDIS": "redis", "IMAGICK": "imagick"}  # ARG prefix -> PECL package
PECL = "https://pecl.php.net"
DOCKERFILE = "Dockerfile"


def fetch(url, attempts=4):
    req = urllib.request.Request(url, headers={"User-Agent": "lucidmodules-ci"})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except urllib.error.URLError:
            if attempt == attempts:
                raise
            time.sleep(2 ** attempt)


def version_key(version):
    return tuple(int(p) for p in re.findall(r"\d+", version))


def main():
    dockerfile = open(DOCKERFILE).read()
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=MIN_RELEASE_AGE_DAYS)
    changes = []

    for prefix, package in EXTENSIONS.items():
        pinned = re.search(rf"^ARG {prefix}_VERSION=(\S+)$", dockerfile, re.M).group(1)
        latest = fetch(f"{PECL}/rest/r/{package}/stable.txt").decode().strip()
        if not re.fullmatch(r"\d+\.\d+\.\d+", latest) or version_key(latest) <= version_key(pinned):
            print(f"{package}: pinned {pinned}, latest stable {latest}: nothing to do", file=sys.stderr)
            continue

        release_xml = fetch(f"{PECL}/rest/r/{package}/{latest}.xml").decode()
        released = dt.datetime.strptime(re.search(r"<da>([^<]+)</da>", release_xml).group(1),
                                        "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)
        if released > cutoff:
            print(f"{package}: {latest} released {released:%Y-%m-%d}, waiting for the "
                  f"{MIN_RELEASE_AGE_DAYS}-day cooldown", file=sys.stderr)
            continue

        url = f"{PECL}/get/{package}-{latest}.tgz"
        first, second = (hashlib.sha256(fetch(url)).hexdigest() for _ in range(2))
        if first != second:
            sys.exit(f"{url}: two downloads gave different sha256s ({first} vs {second}); refusing")

        dockerfile = re.sub(rf"^ARG {prefix}_VERSION=\S+$", f"ARG {prefix}_VERSION={latest}", dockerfile, flags=re.M)
        dockerfile = re.sub(rf"^ARG {prefix}_SHA256=\S+$", f"ARG {prefix}_SHA256={first}", dockerfile, flags=re.M)
        changes.append(
            f"| `{package}` | {pinned} | **{latest}** | {released:%Y-%m-%d} | `{first}` | "
            f"[changelog]({PECL}/package-changelog.php?package={package}&release={latest}) |")

    if changes:
        open(DOCKERFILE, "w").write(dockerfile)
        print("| Extension | From | To | Released | sha256 (first use) | Notes |\n|---|---|---|---|---|---|")
        print("\n".join(changes))


if __name__ == "__main__":
    main()
