"""
Fetcher untuk AWS IP ranges (whitelist)
"""

import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)


def fetch(source: dict) -> Set[str]:
    """
    Fetch IP ranges dari AWS

    Args:
        source: Dictionary berisi konfigurasi sumber
            - url: URL untuk AWS IP ranges JSON

    Returns:
        Set of IP addresses/CIDR ranges
    """
    url = source['url']

    try:
        logger.info(f"Fetching dari AWS IP Ranges...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        ips = set()

        # AWS IPv4 prefixes
        ipv4_prefixes = data.get('prefixes', [])
        for prefix in ipv4_prefixes:
            ip_prefix = prefix.get('ip_prefix')
            if ip_prefix:
                ips.add(ip_prefix)

        # AWS IPv6 prefixes
        ipv6_prefixes = data.get('ipv6_prefixes', [])
        for prefix in ipv6_prefixes:
            ipv6_prefix = prefix.get('ipv6_prefix')
            if ipv6_prefix:
                ips.add(ipv6_prefix)

        logger.info(f"Berhasil mengambil {len(ips)} IP ranges dari AWS")
        return ips

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error saat fetching dari AWS: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error saat parsing data dari AWS: {e}")
        return set()
