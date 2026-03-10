"""Tests for deploy/gcp/check_dns_propagated.py (DNS propagation checker)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add deploy/gcp so we can import check_dns_propagated
_deploy_gcp = Path(__file__).resolve().parent.parent.parent / "deploy" / "gcp"
sys.path.insert(0, str(_deploy_gcp))
import check_dns_propagated as dns_check


class TestResolveHost:
    def test_resolve_returns_ipv4_list(self):
        with patch.object(dns_check.socket, "getaddrinfo") as m:
            m.return_value = [(None, None, None, None, ("34.120.1.2", 0))]
            ips = dns_check.resolve_host("cloudshift.poc-searce.com")
        assert ips == ["34.120.1.2"]
        m.assert_called_once_with("cloudshift.poc-searce.com", None, dns_check.socket.AF_INET)

    def test_resolve_returns_multiple_ips(self):
        with patch.object(dns_check.socket, "getaddrinfo") as m:
            m.return_value = [
                (None, None, None, None, ("34.120.1.2", 0)),
                (None, None, None, None, ("34.120.1.3", 0)),
            ]
            ips = dns_check.resolve_host("example.com")
        assert ips == ["34.120.1.2", "34.120.1.3"]

    def test_resolve_raises_on_failure(self):
        with patch.object(dns_check.socket, "getaddrinfo") as m:
            m.side_effect = OSError("Name or service not known")
            with pytest.raises(OSError):
                dns_check.resolve_host("nonexistent.example.com")


class TestDnsResolved:
    def test_resolved_no_expected_ip(self):
        with patch.object(dns_check, "resolve_host", return_value=["34.120.1.2"]):
            ok, msg = dns_check.dns_resolved("cloudshift.poc-searce.com", expected_ip=None)
        assert ok is True
        assert "34.120.1.2" in msg

    def test_resolved_matches_expected_ip(self):
        with patch.object(dns_check, "resolve_host", return_value=["34.120.1.2"]):
            ok, msg = dns_check.dns_resolved("cloudshift.poc-searce.com", expected_ip="34.120.1.2")
        assert ok is True
        assert "matches" in msg or "34.120.1.2" in msg

    def test_resolved_does_not_match_expected_ip(self):
        with patch.object(dns_check, "resolve_host", return_value=["34.120.1.2"]):
            ok, msg = dns_check.dns_resolved("cloudshift.poc-searce.com", expected_ip="10.0.0.1")
        assert ok is False
        assert "expected" in msg or "10.0.0.1" in msg

    def test_resolution_fails(self):
        with patch.object(dns_check, "resolve_host", side_effect=OSError("nodata")):
            ok, msg = dns_check.dns_resolved("bad.host", expected_ip=None)
        assert ok is False
        assert "failed" in msg.lower() or "nodata" in msg


class TestUrlOk:
    def test_returns_true_on_200(self):
        with patch.object(dns_check.httpx, "get") as m:
            m.return_value = MagicMock(status_code=200)
            ok, msg = dns_check.url_ok("https://cloudshift.poc-searce.com/")
        assert ok is True
        assert "200" in msg

    def test_returns_true_on_2xx(self):
        with patch.object(dns_check.httpx, "get") as m:
            m.return_value = MagicMock(status_code=204)
            ok, msg = dns_check.url_ok("https://example.com/")
        assert ok is True

    def test_returns_false_on_404(self):
        with patch.object(dns_check.httpx, "get") as m:
            m.return_value = MagicMock(status_code=404)
            ok, msg = dns_check.url_ok("https://example.com/")
        assert ok is False
        assert "404" in msg

    def test_returns_false_on_connection_error(self):
        with patch.object(dns_check.httpx, "get") as m:
            m.side_effect = dns_check.httpx.ConnectError("connection refused")
            ok, msg = dns_check.url_ok("https://example.com/")
        assert ok is False
        assert "refused" in msg or "Error" in msg

    def test_passes_verify_false_to_httpx(self):
        with patch.object(dns_check.httpx, "get") as m:
            m.return_value = MagicMock(status_code=200)
            dns_check.url_ok("https://example.com/", verify=False)
        m.assert_called_once()
        assert m.call_args.kwargs.get("verify") is False


class TestCheckPropagation:
    def test_all_pass_dns_only(self):
        with patch.object(dns_check, "dns_resolved", return_value=(True, "Resolved to 34.120.1.2")):
            ok, messages = dns_check.check_propagation("cloudshift.poc-searce.com", None, url=None)
        assert ok is True
        assert len(messages) == 1
        assert "DNS" in messages[0]

    def test_all_pass_dns_and_url(self):
        with patch.object(dns_check, "dns_resolved", return_value=(True, "OK")):
            with patch.object(dns_check, "url_ok", return_value=(True, "HTTP 200")):
                ok, messages = dns_check.check_propagation(
                    "cloudshift.poc-searce.com",
                    "34.120.1.2",
                    url="https://cloudshift.poc-searce.com/",
                )
        assert ok is True
        assert len(messages) == 2

    def test_fail_when_dns_does_not_resolve(self):
        with patch.object(dns_check, "dns_resolved", return_value=(False, "DNS resolution failed")):
            ok, messages = dns_check.check_propagation("bad.host", None, url=None)
        assert ok is False
        assert len(messages) >= 1

    def test_fail_when_url_not_ok(self):
        with patch.object(dns_check, "dns_resolved", return_value=(True, "OK")):
            with patch.object(dns_check, "url_ok", return_value=(False, "HTTP 502")):
                ok, messages = dns_check.check_propagation(
                    "cloudshift.poc-searce.com",
                    None,
                    url="https://cloudshift.poc-searce.com/",
                )
        assert ok is False
        assert any("502" in m for m in messages)

    def test_verify_ssl_false_passed_to_url_ok(self):
        with patch.object(dns_check, "dns_resolved", return_value=(True, "OK")):
            with patch.object(dns_check, "url_ok", return_value=(True, "HTTP 200")) as url_ok_mock:
                dns_check.check_propagation(
                    "cloudshift.poc-searce.com",
                    None,
                    url="https://cloudshift.poc-searce.com/",
                    verify_ssl=False,
                )
                url_ok_mock.assert_called_once()
                assert url_ok_mock.call_args.kwargs.get("verify") is False
