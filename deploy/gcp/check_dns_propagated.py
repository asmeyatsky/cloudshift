#!/usr/bin/env python3
"""
Check that DNS has propagated for a host and optionally that the URL responds.
Used after adding cloudshift.poc-searce.com to Cloud DNS; run until propagation succeeds.
"""
from __future__ import annotations

import argparse
import socket
import sys
import time

import httpx


def resolve_host(host: str) -> list[str]:
    """Resolve host to IPv4 addresses. Raises OSError on resolution failure."""
    results = socket.getaddrinfo(host, None, socket.AF_INET)
    return [r[4][0] for r in results]


def dns_resolved(host: str, expected_ip: str | None = None) -> tuple[bool, str]:
    """
    Return (True, message) if host resolves and optionally matches expected_ip.
    Return (False, message) otherwise.
    """
    try:
        ips = resolve_host(host)
    except OSError as e:
        return False, f"DNS resolution failed: {e}"
    if not ips:
        return False, "No IPv4 addresses found"
    if expected_ip is not None and expected_ip not in ips:
        return False, f"Resolved to {ips}, expected {expected_ip}"
    return True, f"Resolved to {ips[0]}" + (f" (matches {expected_ip})" if expected_ip else "")


def url_ok(url: str, timeout: float = 10.0, verify: bool = True) -> tuple[bool, str]:
    """Return (True, message) if GET url returns 2xx, else (False, message). verify=False skips SSL cert validation."""
    try:
        r = httpx.get(url, follow_redirects=True, timeout=timeout, verify=verify)
        if 200 <= r.status_code < 300:
            return True, f"HTTP {r.status_code}"
        return False, f"HTTP {r.status_code}"
    except httpx.HTTPError as e:
        return False, str(e)


def check_propagation(
    host: str,
    expected_ip: str | None,
    url: str | None,
    verify_ssl: bool = True,
) -> tuple[bool, list[str]]:
    """
    Run DNS and optional URL check. Return (all_ok, list of messages).
    verify_ssl=False skips SSL certificate validation for the URL check.
    """
    messages: list[str] = []
    ok = True

    resolved, msg = dns_resolved(host, expected_ip)
    messages.append(f"DNS {host}: {msg}")
    if not resolved:
        ok = False
        return ok, messages

    if url:
        url_ok_result, url_msg = url_ok(url, verify=verify_ssl)
        messages.append(f"URL {url}: {url_msg}")
        if not url_ok_result:
            ok = False

    return ok, messages


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check DNS propagation and optionally that the URL responds (e.g. after adding cloudshift.poc-searce.com)."
    )
    parser.add_argument("--host", default="cloudshift.poc-searce.com", help="Hostname to resolve")
    parser.add_argument("--expected-ip", help="Optional: require host to resolve to this IP (LB IP)")
    parser.add_argument("--url", help="Optional: also GET this URL and require 2xx (e.g. https://cloudshift.poc-searce.com/)")
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Loop until checks pass or --timeout",
    )
    parser.add_argument("--timeout", type=float, default=1200, help="Max seconds when using --wait (default 1200 = 20 min)")
    parser.add_argument("--interval", type=float, default=10, help="Seconds between attempts when using --wait (default 10)")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Skip SSL certificate verification for --url (use when LB cert does not yet include the hostname)",
    )
    args = parser.parse_args()

    deadline = time.monotonic() + args.timeout if args.wait else None

    while True:
        ok, messages = check_propagation(
            args.host, args.expected_ip or None, args.url, verify_ssl=not args.insecure
        )
        for m in messages:
            print(m)
        if ok:
            print("Propagation check passed.")
            return 0
        if deadline is None:
            return 1
        if time.monotonic() >= deadline:
            print("Timed out waiting for propagation.")
            return 1
        print(f"Retrying in {args.interval}s...")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
