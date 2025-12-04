"""
Fetcher untuk AbuseIPDB IP Blacklist
API Documentation: https://docs.abuseipdb.com/#blacklist-endpoint
"""

import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)


def fetch(source: dict) -> Set[str]:
    """
    Fetch IP blacklist dari AbuseIPDB

    Args:
        source: Dictionary berisi konfigurasi sumber
            - url: API endpoint
            - api_key: API key untuk AbuseIPDB
            - confidence_minimum: (optional) minimum confidence score (default: 90)
            - limit: (optional) jumlah maksimal IP (default: 10000)

    Returns:
        Set of IP addresses
    """
    url = source['url']
    api_key = source.get('api_key')

    if not api_key:
        logger.error("API key tidak ditemukan untuk AbuseIPDB")
        return set()

    # Parameters
    params = {
        'confidenceMinimum': source.get('confidence_minimum', 90),
        'limit': source.get('limit', 10000)
    }

    headers = {
        'Accept': 'application/json',
        'Key': api_key
    }

    try:
        logger.info(f"Fetching dari AbuseIPDB dengan confidence minimum {params['confidenceMinimum']}...")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Extract IP addresses
        ips = set()
        if 'data' in data:
            for entry in data['data']:
                ip = entry.get('ipAddress')
                if ip:
                    ips.add(ip)

        logger.info(f"Berhasil mengambil {len(ips)} IP dari AbuseIPDB")
        return ips

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error saat fetching dari AbuseIPDB: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error saat parsing data dari AbuseIPDB: {e}")
        return set()
