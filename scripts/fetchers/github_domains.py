"""
Fetcher untuk GitHub domains (whitelist)
Mengambil domain dari GitHub Meta API
"""

import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)


def fetch(source: dict) -> Set[str]:
    """
    Fetch domains dari GitHub Meta API

    Args:
        source: Dictionary berisi konfigurasi sumber
            - url: URL untuk GitHub Meta API

    Returns:
        Set of domain patterns dari berbagai kategori GitHub
    """
    url = source['url']

    try:
        logger.info(f"Fetching domains dari GitHub Meta API...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        domains = set()

        # GitHub Meta API memiliki field 'domains' yang berisi berbagai kategori
        domains_data = data.get('domains', {})

        if domains_data:
            # Ambil domain dari semua kategori
            for category, domain_list in domains_data.items():
                if isinstance(domain_list, list):
                    # Kategori seperti 'website', 'codespaces', 'copilot', 'packages', 'actions'
                    for domain in domain_list:
                        if domain:
                            domains.add(domain)
                elif isinstance(domain_list, dict):
                    # Kategori seperti 'actions_inbound' yang memiliki subcategories
                    for subkey, subdomain_list in domain_list.items():
                        if isinstance(subdomain_list, list):
                            for domain in subdomain_list:
                                if domain:
                                    domains.add(domain)

        logger.info(f"Berhasil mengambil {len(domains)} domains dari GitHub")
        return domains

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error saat fetching dari GitHub: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error saat parsing data dari GitHub: {e}")
        return set()
