"""
Fetcher untuk AdGuard DNS Filter (domain blacklist)
Format AdGuard menggunakan syntax khusus yang perlu di-parse
"""

import requests
import logging
import re
from typing import Set

logger = logging.getLogger(__name__)


def fetch(source: dict) -> Set[str]:
    """
    Fetch AdGuard DNS Filter dan convert ke domain list

    AdGuard DNS Filter Format:
    - ||domain.com^ = Block domain and subdomains
    - ||*.domain.com^ = Wildcard domain blocking
    - ||1.2.3.4^ = IP address blocking (skip ini)
    - /regex/ = IP range patterns (skip ini)
    - @@||domain.com^ = Exception/whitelist rules (skip ini)
    - ||domain.com^$badfilter = Disable blocking (skip ini)
    - ! = Comments (skip)

    Args:
        source: Dictionary berisi konfigurasi sumber
            - url: URL untuk AdGuard DNS Filter

    Returns:
        Set of domain names untuk blacklist
    """
    url = source['url']

    try:
        logger.info(f"Fetching dari AdGuard DNS Filter...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        domains = set()
        skipped_ips = 0
        skipped_regex = 0
        skipped_exceptions = 0
        skipped_badfilter = 0
        wildcard_count = 0

        for line in response.text.split('\n'):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip comments (lines starting with !)
            if line.startswith('!'):
                continue

            # Skip exception rules (whitelist)
            if line.startswith('@@'):
                skipped_exceptions += 1
                continue

            # Skip badfilter rules (these disable blocking)
            if '$badfilter' in line:
                skipped_badfilter += 1
                continue

            # Skip regex patterns (IP ranges)
            if line.startswith('/') and line.endswith('/'):
                skipped_regex += 1
                continue

            # Parse standard AdGuard domain blocking rules: ||domain.com^
            if line.startswith('||') and '^' in line:
                # Extract domain between || and ^
                domain = line[2:line.index('^')]

                # Remove any modifiers after ^ (e.g., ^$important)
                if '$' in domain:
                    domain = domain.split('$')[0]

                # Skip empty domains
                if not domain:
                    continue

                # Handle wildcard domains: *.domain.com -> domain.com
                # We'll store as *.domain.com to preserve wildcard intent
                if domain.startswith('*.'):
                    wildcard_count += 1
                    # Keep wildcard format for consistency
                    domains.add(domain)
                    continue

                # Skip IP addresses (AdGuard also blocks some IPs)
                # Check if it's an IP: contains only digits and dots, 4 octets
                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', domain):
                    skipped_ips += 1
                    continue

                # Skip IP ranges or malformed entries
                if ':' in domain or '/' in domain:
                    skipped_regex += 1
                    continue

                # Valid domain - add to set
                if domain and '.' in domain:
                    domains.add(domain)

        logger.info(f"Berhasil mengambil {len(domains)} domains dari AdGuard DNS Filter")
        logger.info(f"  - Wildcards: {wildcard_count}")
        logger.info(f"  - Skipped IPs: {skipped_ips}")
        logger.info(f"  - Skipped Regex/Ranges: {skipped_regex}")
        logger.info(f"  - Skipped Exceptions: {skipped_exceptions}")
        logger.info(f"  - Skipped BadFilters: {skipped_badfilter}")

        return domains

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error saat fetching dari AdGuard DNS Filter: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error saat parsing data dari AdGuard DNS Filter: {e}")
        import traceback
        traceback.print_exc()
        return set()
