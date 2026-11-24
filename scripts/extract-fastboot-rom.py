#!/usr/bin/env python3
"""Resolve, verify, and inventory the Redmi 12C Fastboot ROM from a MiFirm page.

This script never executes firmware flash scripts and never writes to a phone.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import PurePosixPath
from pathlib import Path

EXPECTED_FILENAME = "earth_global_images_OS1.0.16.0.UCVMIXM_20260227.0000.00_14.0_global_b2ab987cbf.tgz"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
MAX_DOWNLOAD_BYTES = 15 * 1024**3


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._attrs = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._attrs = dict(attrs)
            self._text = []

    def handle_data(self, data):
        if self._attrs is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._attrs is not None:
            self.links.append((self._attrs, " ".join(self._text).strip()))
            self._attrs = None
            self._text = []


def allowed_url(value: str, base: str) -> str | None:
    value = html.unescape(value).strip().strip("\"' ")
    if not value or value.startswith(("javascript:", "data:", "#")):
        return None
    absolute = urllib.parse.urljoin(base, value)
    parsed = urllib.parse.urlparse(absolute)
    host = (parsed.hostname or "").lower()
    allowed = (
        host == "mifirm.net" or host.endswith(".mifirm.net")
        or host == "miui.com" or host.endswith(".miui.com")
        or host == "xiaomi.com" or host.endswith(".xiaomi.com")
    )
    if parsed.scheme != "https" or not allowed:
        return None
    return absolute


def resolve_download(page_url: str) -> str:
    req = urllib.request.Request(page_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        page = response.read(12 * 1024 * 1024).decode("utf-8", "replace")
        page_base = response.geturl()

    parser = LinkParser()
    parser.feed(page)
    candidates: list[tuple[int, str, str]] = []

    for attrs, text in parser.links:
        attr_values = [attrs.get(k, "") for k in ("href", "data-href", "data-url", "onclick")]
        for raw in attr_values:
            # Extract a URL from ordinary attributes or JavaScript onclick handlers.
            found = re.findall(r"""https?://[^\s\"'<>]+|(?:/|\.\./)[^\s\"'<>]+""", raw)
            if not found and raw:
                found = [raw]
            for value in found:
                url = allowed_url(value, page_base)
                if not url:
                    continue
                low = (url + " " + text).lower()
                if EXPECTED_FILENAME.lower() in low or ".tgz" in low:
                    score = 100
                elif "download server xiaomi" in low:
                    score = 80
                elif "download" in low and ("earth" in low or "rom" in low):
                    score = 40
                else:
                    score = 1
                candidates.append((score, url, text))

    # Some pages keep server URLs in inline scripts instead of anchor hrefs.
    for raw in re.findall(r"""https?://[^\s\"'<>]+""", page):
        url = allowed_url(raw.rstrip("),;"), page_base)
        if url and (EXPECTED_FILENAME.lower() in url.lower() or ".tgz" in url.lower()):
            candidates.append((110, url, "inline page URL"))

    unique = {}
    for score, url, label in candidates:
        unique[url] = max(score, unique.get(url, (0, ""))[0]), label
    ordered = sorted(((s, u, label) for u, (s, label) in unique.items()), reverse=True)

    if not ordered:
        raise RuntimeError(
            "Tidak menemukan URL unduhan langsung di HTML MiFirm. "
            "Kemungkinan tautan dibuat oleh JavaScript atau proteksi situs. "
            "Tidak ada file yang diunduh."
        )

    # Prefer a URL that visibly names the expected ROM archive.
    for score, url, label in ordered:
        if EXPECTED_FILENAME.lower() in url.lower() or ".tgz" in url.lower():
            print(f"Download source ditemukan: {label or 'tautan firmware'}")
            return url

    preview = "\n".join(f"- {label}: {url}" for _, url, label in ordered[:8])
    raise RuntimeError(
        "MiFirm menampilkan tautan server, tetapi tidak ada URL .tgz langsung yang "
        "dapat diverifikasi otomatis. Kandidat yang ditemukan:\n" + preview
    )


def download_and_verify(url: str, destination: Path, expected_md5: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    md5 = hashlib.md5()
    total = 0
    with urllib.request.urlopen(req, timeout=120) as response:
        final_url = response.geturl()
        final_host = (urllib.parse.urlparse(final_url).hostname or "").lower()
        if not (
            final_host == "mifirm.net" or final_host.endswith(".mifirm.net")
            or final_host == "miui.com" or final_host.endswith(".miui.com")
            or final_host == "xiaomi.com" or final_host.endswith(".xiaomi.com")
        ):
            raise RuntimeError(f"Redirect ke host yang tidak diizinkan: {final_host}")
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
            raise RuntimeError(f"Ukuran unduhan melebihi batas {MAX_DOWNLOAD_BYTES} byte")
        print(f"Mengunduh arsip firmware dari host: {final_host}")
        with destination.open("wb") as out:
            while True:
                chunk = response.read(8 * 1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise RuntimeError("Unduhan melewati batas ukuran 15 GiB")
                md5.update(chunk)
                out.write(chunk)
                print(f"Unduhan: {total / (1024**3):.2f} GiB", end="\r", flush=True)
    print()
    actual = md5.hexdigest()
    print(f"Ukuran: {total} byte")
    print(f"MD5:    {actual}")
    if actual.lower() != expected_md5.lower():
        destination.unlink(missing_ok=True)
        raise RuntimeError("MD5 tidak cocok; arsip dihapus dan tidak akan diekstrak.")


def safe_member_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("..", "") for part in path.parts):
        raise RuntimeError(f"Path arsip tidak aman: {name}")
    return path


def inspect_and_extract(archive: Path, output: Path) -> None:
    image_dir = output / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    extracted = []

    with tarfile.open(archive, mode="r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            if not member.isfile():
                continue
            rel = safe_member_path(member.name)
            entries.append({"path": str(rel), "size": member.size})
            lower = str(rel).lower()
            if lower.endswith(".img"):
                # Keep image basenames in a flat directory; duplicate names are rejected.
                name = PurePosixPath(str(rel)).name
                target = image_dir / name
                if target.exists():
                    raise RuntimeError(f"Nama image duplikat di arsip: {name}")
                source = tar.extractfile(member)
                if source is None:
                    continue
                with source, target.open("wb") as out:
                    shutil.copyfileobj(source, out, length=8 * 1024 * 1024)
                digest = hashlib.sha256()
                with target.open("rb") as image_file:
                    for chunk in iter(lambda: image_file.read(8 * 1024 * 1024), b""):
                        digest.update(chunk)
                extracted.append({
                    "path": str(target.relative_to(output)),
                    "source_path": str(rel),
                    "size": target.stat().st_size,
                    "sha256": digest.hexdigest(),
                })

    entries.sort(key=lambda x: x["path"])
    extracted.sort(key=lambda x: x["path"])
    (output / "archive-inventory.json").write_text(
        json.dumps(entries, indent=2) + "\n", encoding="utf-8"
    )
    (output / "image-manifest.json").write_text(
        json.dumps(extracted, indent=2) + "\n", encoding="utf-8"
    )
    with (output / "image-manifest.tsv").open("w", encoding="utf-8") as f:
        f.write("image\tsize_bytes\tsha256\tsource_path\n")
        for item in extracted:
            f.write(
                f"{item['path']}\t{item['size']}\t{item['sha256']}\t{item['source_path']}\n"
            )
    print(f"File arsip terinventarisasi: {len(entries)}")
    print(f"Image diekstrak: {len(extracted)}")
    if not extracted:
        raise RuntimeError("Tidak ditemukan file .img dalam arsip Fastboot ROM.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page-url", required=True)
    ap.add_argument("--expected-md5", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / EXPECTED_FILENAME

    try:
        url = resolve_download(args.page_url)
        download_and_verify(url, archive, args.expected_md5)
        inspect_and_extract(archive, output)
        archive.unlink(missing_ok=True)
        summary = {
            "device": "Xiaomi Redmi 12C",
            "codename": "earth",
            "firmware": "V816.0.16.0.UCVMIXM",
            "android": "14",
            "archive": EXPECTED_FILENAME,
            "expected_md5": args.expected_md5,
            "status": "verified-and-extracted",
            "note": "Images are extracted for analysis only; no flashing is performed.",
        }
        (output / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
        print("Firmware berhasil diverifikasi dan image diekstrak.")
        return 0
    except (urllib.error.URLError, tarfile.TarError, OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
