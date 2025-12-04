"""
Fetcher untuk Tranco Top Sites List (domain whitelist)
"""

import requests
import logging
import zipfile
import io
from typing import Set

logger = logging.getLogger(__name__)


def fetch(source: dict) -> Set[str]:
    """
    Fetch top domains dari Tranco list

    Args:
        source: Dictionary berisi konfigurasi sumber
            - url: URL untuk Tranco CSV
            - limit: (optional) jumlah maksimal domain (default: 10000)

    Returns:
        Set of domain names
    """
    url = source['url']
    limit = source.get('limit', 10000)

    try:
        logger.info(f"Fetching dari Tranco (top {limit} domains)...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        domains = set()

        # Tranco list dalam format ZIP
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            # Ambil file CSV pertama di dalam ZIP
            csv_filename = z.namelist()[0]
            with z.open(csv_filename) as f:
                count = 0
                for line in f:
                    if count >= limit:
                        break

                    line = line.decode('utf-8').strip()
                    if ',' in line:
                        # Format: rank,domain
                        rank, domain = line.split(',', 1)
                        if domain:
                            domains.add(domain)
                            count += 1

        logger.info(f"Berhasil mengambil {len(domains)} domains dari Tranco")
        return domains

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error saat fetching dari Tranco: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error saat parsing data dari Tranco: {e}")
        return set()
