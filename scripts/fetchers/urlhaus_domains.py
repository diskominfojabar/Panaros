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

        # Parse CSV - skip baris yang dimulai dengan #, tapi tambahkan header manual
        lines = []
        for line in response.text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                lines.append(line)

        if not lines:
            logger.warning("Tidak ada data yang valid dari URLhaus")
            return domains

        # Tambahkan header CSV
        header = "id,dateadded,url,url_status,last_online,threat,tags,urlhaus_link,reporter"
        csv_content = header + '\n' + '\n'.join(lines)

        # Parse CSV
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
                        # Remove username jika ada (user@domain)
                        if '@' in domain:
                            domain = domain.split('@')[1]

                        # Filter: HANYA domain, BUKAN IP address
                        # Skip jika berupa IP address (cek apakah semua bagian adalah digit)
                        if domain:
                            # Cek apakah ini IP address
                            parts = domain.split('.')
                            is_ip = all(part.isdigit() and 0 <= int(part) <= 255 for part in parts if part) and len(parts) == 4

                            # Hanya tambahkan jika BUKAN IP
                            if not is_ip:
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
