#!/usr/bin/env python3
"""
Fetcher for StevenBlack/hosts - Gambling & Porn domains
Source: http://sbc.io/hosts/alternates/gambling-porn-only/hosts
"""

import logging
import urllib.request
from typing import Set

logger = logging.getLogger(__name__)


def fetch(config: dict = None) -> Set[str]:
    """
    Fetch gambling and porn domains from StevenBlack hosts
    Returns: Set of domains
    """
    url = "http://sbc.io/hosts/alternates/gambling-porn-only/hosts"
    domains = set()

    try:
        logger.info(f"Fetching data from {url}")

        # Fetch using urllib
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read().decode('utf-8')

        lines = content.split('\n')

        for line in lines:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse hosts format: "0.0.0.0 domain.com"
            parts = line.split()
            if len(parts) >= 2:
                ip = parts[0]
                domain = parts[1]

                # Only process if it's the standard hosts format with 0.0.0.0
                if ip == "0.0.0.0":
                    # Basic domain validation
                    if '.' in domain and not domain.startswith('*'):
                        # Filter out IPs (shouldn't be in this list but just in case)
                        domain_parts = domain.split('.')
                        is_ip = all(part.isdigit() and 0 <= int(part) <= 255
                                  for part in domain_parts if part) and len(domain_parts) == 4

                        if not is_ip:
                            domains.add(domain.lower())

        logger.info(f"Successfully fetched {len(domains)} domains from StevenBlack hosts (gambling & porn)")
        return domains

    except urllib.error.URLError as e:
        logger.error(f"Failed to fetch from {url}: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error processing StevenBlack hosts data: {e}")
        return set()


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    result = fetch()
    print(f"Fetched {len(result)} domains")
    print("Sample domains:", list(result)[:10])
