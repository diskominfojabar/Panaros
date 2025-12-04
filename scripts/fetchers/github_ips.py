"""
Fetcher untuk GitHub IP ranges (whitelist)
"""

import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)


def fetch(source: dict) -> Set[str]:
    """
    Fetch IP ranges dari GitHub Meta API

    Args:
        source: Dictionary berisi konfigurasi sumber
            - url: URL untuk GitHub Meta API

    Returns:
        Set of IP addresses/CIDR ranges
    """
    url = source['url']

    try:
        logger.info(f"Fetching dari GitHub Meta API...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        ips = set()

        # GitHub Meta API returns multiple IP ranges categories
        # hooks, web, api, git, pages, importer, actions, dependabot
        categories = ['hooks', 'web', 'api', 'git', 'pages', 'importer', 'actions', 'dependabot']

        for category in categories:
            ip_list = data.get(category, [])
            if isinstance(ip_list, list):
                for ip in ip_list:
                    if ip:
                        ips.add(ip)

        logger.info(f"Berhasil mengambil {len(ips)} IP ranges dari GitHub")
        return ips

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error saat fetching dari GitHub: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error saat parsing data dari GitHub: {e}")
        return set()
