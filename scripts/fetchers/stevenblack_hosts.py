"""
Fetcher untuk StevenBlack hosts file (blacklist)
Mengambil domain dari format /etc/hosts
"""

import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)


def fetch(source: dict) -> Set[str]:
    """
    Fetch domains dari StevenBlack hosts file

    Args:
        source: Dictionary berisi konfigurasi sumber
            - url: URL untuk hosts file

    Returns:
        Set of domain names dari hosts file
    """
    url = source['url']

    try:
        logger.info(f"Fetching dari StevenBlack hosts file...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        domains = set()

        # Parse hosts file format: 0.0.0.0 domain.com
        for line in response.text.split('\n'):
            line = line.strip()

            # Skip comments dan empty lines
            if not line or line.startswith('#'):
                continue

            # Split by whitespace
            parts = line.split()

            # Format hosts: IP domain
            # We want the domain part (second element)
            if len(parts) >= 2:
                ip = parts[0]
                domain = parts[1]

                # Skip localhost entries dan IP-only entries
                if domain and domain not in ['localhost', 'localhost.localdomain', 'local', 'broadcasthost',
                                             'ip6-localhost', 'ip6-loopback', 'ip6-localnet',
                                             'ip6-mcastprefix', 'ip6-allnodes', 'ip6-allrouters', 'ip6-allhosts']:
                    # Skip jika domain adalah IP address
                    if not all(c.isdigit() or c == '.' for c in domain.replace(':', '')):
                        domains.add(domain)

        logger.info(f"Berhasil mengambil {len(domains)} domains dari StevenBlack hosts")
        return domains

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error saat fetching dari StevenBlack: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error saat parsing data dari StevenBlack: {e}")
        return set()
