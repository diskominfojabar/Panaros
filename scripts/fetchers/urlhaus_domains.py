"""
Fetcher untuk URLhaus Malware Domains (domain blacklist)
"""

import requests
import logging
import csv
import io
from typing import Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def fetch(source: dict) -> Set[str]:
    """
    Fetch malware domains dari URLhaus

    Args:
        source: Dictionary berisi konfigurasi sumber
            - url: URL untuk URLhaus CSV

    Returns:
        Set of malicious domain names
    """
    url = source['url']

    try:
        logger.info(f"Fetching dari URLhaus...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        domains = set()

        # Parse CSV
        csv_content = response.text
        reader = csv.DictReader(io.StringIO(csv_content), delimiter=',')

        for row in reader:
            # URLhaus CSV berisi kolom 'url'
            malware_url = row.get('url', '')
            if malware_url:
                # Extract domain dari URL
                try:
                    parsed = urlparse(malware_url)
                    domain = parsed.netloc
                    if domain:
                        # Remove port jika ada
                        domain = domain.split(':')[0]
                        domains.add(domain)
                except Exception:
                    continue

        logger.info(f"Berhasil mengambil {len(domains)} malware domains dari URLhaus")
        return domains

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error saat fetching dari URLhaus: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error saat parsing data dari URLhaus: {e}")
        return set()
