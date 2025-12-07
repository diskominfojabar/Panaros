"""
Fetcher untuk AdGuard DNS Filter - IP Blacklist
Extract IP addresses dari AdGuard DNS Filter format
"""

import requests
import logging
import re
from typing import Set

logger = logging.getLogger(__name__)


def fetch(source: dict) -> Set[str]:
    """
    Fetch IP addresses dari AdGuard DNS Filter

    AdGuard DNS Filter Format:
    - ||1.2.3.4^ = Block specific IP address
    - /regex/ = IP range patterns (skip untuk sekarang)

    Args:
        source: Dictionary berisi konfigurasi sumber
            - url: URL untuk AdGuard DNS Filter

    Returns:
        Set of IP addresses untuk blacklist
    """
    url = source['url']

    try:
        logger.info(f"Fetching IPs dari AdGuard DNS Filter...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        ips = set()
        skipped_regex = 0

        for line in response.text.split('\n'):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip comments
            if line.startswith('!'):
                continue

            # Skip exception rules (whitelist)
            if line.startswith('@@'):
                continue

            # Skip badfilter rules
            if '$badfilter' in line:
                continue

            # Skip regex patterns (IP ranges) - akan di-handle nanti jika perlu
            if line.startswith('/') and line.endswith('/'):
                skipped_regex += 1
                continue

            # Parse standard AdGuard IP blocking rules: ||IP^
            if line.startswith('||') and '^' in line:
                # Extract content between || and ^
                content = line[2:line.index('^')]

                # Remove any modifiers after ^ (e.g., ^$important)
                if '$' in content:
                    content = content.split('$')[0]

                # Skip empty content
                if not content:
                    continue

                # Check if it's a valid IP address (IPv4)
                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', content):
                    # Validate IP ranges (0-255 per octet)
                    try:
                        octets = content.split('.')
                        if all(0 <= int(octet) <= 255 for octet in octets):
                            ips.add(content)
                    except ValueError:
                        continue

        logger.info(f"Berhasil mengambil {len(ips)} IPs dari AdGuard DNS Filter")
        logger.info(f"  - Skipped Regex/Ranges: {skipped_regex}")

        return ips

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error saat fetching dari AdGuard DNS Filter: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error saat parsing IPs dari AdGuard DNS Filter: {e}")
        import traceback
        traceback.print_exc()
        return set()
