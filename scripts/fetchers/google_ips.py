"""
Fetcher untuk Google Bot IP ranges (whitelist)
Mengambil dari multiple endpoints Google
"""

import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)


def fetch(source: dict) -> Set[str]:
    """
    Fetch IP ranges dari Google (Googlebot, crawlers, fetchers)

    Args:
        source: Dictionary berisi konfigurasi sumber
            - urls: List of URLs untuk Google IP ranges

    Returns:
        Set of IP addresses/CIDR ranges
    """
    urls = source.get('urls', [])

    if not urls:
        logger.error("Tidak ada URLs untuk Google IPs")
        return set()

    ips = set()

    for url in urls:
        try:
            logger.info(f"Fetching dari {url}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Google JSON format: {"prefixes": [{"ipv4Prefix": "..."}, {"ipv6Prefix": "..."}]}
            prefixes = data.get('prefixes', [])

            for prefix in prefixes:
                # IPv4
                ipv4 = prefix.get('ipv4Prefix')
                if ipv4:
                    ips.add(ipv4)

                # IPv6
                ipv6 = prefix.get('ipv6Prefix')
                if ipv6:
                    ips.add(ipv6)

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP Error saat fetching dari {url}: {e}")
            continue
        except Exception as e:
            logger.error(f"Error saat parsing data dari {url}: {e}")
            continue

    logger.info(f"Berhasil mengambil {len(ips)} IP ranges dari Google")
    return ips
