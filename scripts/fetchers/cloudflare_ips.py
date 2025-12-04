"""
Fetcher untuk Cloudflare IP ranges (whitelist)
"""

import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)


def fetch(source: dict) -> Set[str]:
    """
    Fetch IP ranges dari Cloudflare

    Args:
        source: Dictionary berisi konfigurasi sumber
            - url: URL untuk Cloudflare IPs

    Returns:
        Set of IP addresses/CIDR ranges
    """
    url = source['url']

    try:
        logger.info(f"Fetching dari Cloudflare...")

        # Fetch IPv4
        response_v4 = requests.get("https://www.cloudflare.com/ips-v4", timeout=30)
        response_v4.raise_for_status()

        # Fetch IPv6
        response_v6 = requests.get("https://www.cloudflare.com/ips-v6", timeout=30)
        response_v6.raise_for_status()

        ips = set()

        # Parse IPv4
        for line in response_v4.text.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                ips.add(line)

        # Parse IPv6
        for line in response_v6.text.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                ips.add(line)

        logger.info(f"Berhasil mengambil {len(ips)} IP ranges dari Cloudflare")
        return ips

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error saat fetching dari Cloudflare: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error saat parsing data dari Cloudflare: {e}")
        return set()
