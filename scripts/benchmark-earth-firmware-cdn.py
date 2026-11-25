#!/usr/bin/env python3
"""Benchmark small HTTP Range samples from Xiaomi firmware CDN aliases.

Downloads at most --sample-bytes per host. It does not download or extract firmware.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_HOSTS = {
    "bigota.d.miui.com",
    "bn.d.miui.com",
    "cdnorg.d.miui.com",
    "cdn-ota.azureedge.net",
}
SAMPLE_BYTES = 8 * 1024 * 1024


def trusted_host(host: str) -> bool:
    host = (host or "").lower().rstrip(".")
    return (
        host in EXPECTED_HOSTS
        or host == "miui.com" or host.endswith(".miui.com")
        or host == "xiaomi.com" or host.endswith(".xiaomi.com")
    )


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != "https" or not trusted_host(parsed.hostname or ""):
            raise urllib.error.HTTPError(
                newurl, code, "Redirect host is outside the Xiaomi/CDN allowlist",
                headers, fp
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def candidate_urls(source_url: str) -> list[tuple[str, str]]:
    parsed = urllib.parse.urlparse(source_url)
    if parsed.scheme != "https" or not trusted_host(parsed.hostname or ""):
        raise ValueError("Source URL must use HTTPS on a Xiaomi/CDN host")
    result = []
    for host in sorted(EXPECTED_HOSTS):
        result.append((host, urllib.parse.urlunparse(
            (parsed.scheme, host, parsed.path, parsed.params, parsed.query, "")
        )))
    return result


def probe(label: str, url: str, sample_bytes: int, timeout: int) -> dict:
    request = urllib.request.Request(url, headers={
        "User-Agent": "Linsae-Firmware-CDN-Benchmark/1.0",
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Cache-Control": "no-cache",
        "Range": f"bytes=0-{sample_bytes - 1}",
    })
    started = time.perf_counter()
    result = {
        "candidate": label,
        "url": url,
        "status": "error",
        "http_status": None,
        "final_host": None,
        "range_supported": False,
        "sample_bytes": 0,
        "archive_size_bytes": None,
        "sample_mib_per_second": None,
        "elapsed_seconds": None,
        "gzip_signature": False,
        "error": None,
    }
    opener = urllib.request.build_opener(SafeRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            final = urllib.parse.urlparse(response.geturl())
            final_host = (final.hostname or "").lower()
            if final.scheme != "https" or not trusted_host(final_host):
                raise RuntimeError(f"Untrusted final URL host: {final_host}")
            result["http_status"] = response.status
            result["final_host"] = final_host
            content_range = response.headers.get("Content-Range", "")
            result["range_supported"] = response.status == 206 and content_range.startswith("bytes 0-")
            if "/" in content_range:
                total = content_range.rsplit("/", 1)[1]
                if total.isdigit():
                    result["archive_size_bytes"] = int(total)
            if result["archive_size_bytes"] is None:
                length = response.headers.get("Content-Length")
                if length and length.isdigit():
                    result["archive_size_bytes"] = int(length)

            first = b""
            received = 0
            deadline = started + timeout
            while received < sample_bytes and time.perf_counter() < deadline:
                chunk = response.read(min(256 * 1024, sample_bytes - received))
                if not chunk:
                    break
                if not first:
                    first = chunk[:2]
                received += len(chunk)
            elapsed = max(time.perf_counter() - started, 0.001)
            result["sample_bytes"] = received
            result["elapsed_seconds"] = round(elapsed, 3)
            result["sample_mib_per_second"] = round(received / (1024 * 1024) / elapsed, 3)
            result["gzip_signature"] = first == b"\x1f\x8b"
            if received and result["gzip_signature"]:
                result["status"] = "ok" if result["range_supported"] else "ok-range-ignored"
            elif received:
                result["status"] = "invalid-content"
                result["error"] = "First bytes are not a gzip signature"
            else:
                result["status"] = "empty-response"
    except Exception as exc:
        result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Canonical Xiaomi firmware archive URL")
    parser.add_argument("--output", required=True, help="JSON report path")
    parser.add_argument("--sample-bytes", type=int, default=SAMPLE_BYTES)
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()

    if args.sample_bytes < 1024 * 1024 or args.sample_bytes > 32 * 1024 * 1024:
        parser.error("--sample-bytes must be between 1 and 32 MiB")
    if args.timeout < 5 or args.timeout > 180:
        parser.error("--timeout must be between 5 and 180 seconds")

    results = []
    for host, url in candidate_urls(args.url):
        print(f"Testing {host} ...", flush=True)
        item = probe(host, url, args.sample_bytes, args.timeout)
        results.append(item)
        speed = item["sample_mib_per_second"]
        print(
            f"  {item['status']}: HTTP {item['http_status']}, "
            f"{item['sample_bytes']} bytes, "
            f"{speed if speed is not None else 'n/a'} MiB/s, "
            f"final={item['final_host'] or 'n/a'}",
            flush=True,
        )
        if item["error"]:
            print(f"  detail: {item['error']}", flush=True)

    valid = [r for r in results if r["gzip_signature"] and r["sample_bytes"] > 0]
    valid.sort(key=lambda r: r["sample_mib_per_second"] or 0, reverse=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_url": args.url,
        "sample_bytes_requested": args.sample_bytes,
        "timeout_seconds_per_host": args.timeout,
        "note": "Small Range probe only; no full firmware archive was downloaded.",
        "recommended_candidate": valid[0]["candidate"] if valid else None,
        "results": results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {output}")
    if not valid:
        print("No candidate returned a valid gzip sample.")
        return 1
    print(f"Fastest valid sample: {valid[0]['candidate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
