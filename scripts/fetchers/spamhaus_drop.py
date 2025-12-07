"""
Fetcher untuk Spamhaus DROP (Don't Route Or Peer) List
Returns IP subnets/CIDR ranges untuk blacklist
"""

import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)


def fetch(source: dict) -> Set[str]:
    """
    Fetch Spamhaus DROP list - IP subnets yang seharusnya di-drop

    Spamhaus DROP Format:
    - Lines starting with ; are comments
    - Format: CIDR ; SBL number
    - Example: 1.10.16.0/20 ; SBL12345

    Args:
        source: Dictionary berisi konfigurasi sumber
            - url: URL untuk Spamhaus DROP list

    Returns:
        Set of IP subnets/CIDR ranges
    """
    url = source['url']

    try:
        logger.info(f"Fetching dari Spamhaus DROP...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        subnets = set()

        for line in response.text.split('\n'):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip comments (lines starting with ;)
            if line.startswith(';'):
                continue

            # Parse CIDR format: "CIDR ; SBL_number"
            if ';' in line:
                parts = line.split(';')
                cidr = parts[0].strip()

                # Validate CIDR format (should contain /)
                if '/' in cidr:
                    subnets.add(cidr)
            else:
                # Some lines might not have ; separator
                if '/' in line:
                    subnets.add(line)

        logger.info(f"Berhasil mengambil {len(subnets)} IP subnets dari Spamhaus DROP")
        return subnets

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error saat fetching dari Spamhaus DROP: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error saat parsing data dari Spamhaus DROP: {e}")
        import traceback
        traceback.print_exc()
        return set()
