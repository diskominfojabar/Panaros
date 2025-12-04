"""
Fetcher untuk URLhaus IP addresses (blacklist)
Mengambil IP address dari malware URLs
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
    Fetch malware IPs dari URLhaus

    Args:
        source: Dictionary berisi konfigurasi sumber
            - url: URL untuk URLhaus CSV

    Returns:
        Set of IP addresses dari malware URLs
    """
    url = source['url']

    try:
        logger.info(f"Fetching dari URLhaus (IPs)...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        ips = set()

        # Parse CSV - skip baris yang dimulai dengan #, tapi tambahkan header manual
        lines = []
        for line in response.text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                lines.append(line)

        if not lines:
            logger.warning("Tidak ada data yang valid dari URLhaus")
            return ips

        # Tambahkan header CSV
        header = "id,dateadded,url,url_status,last_online,threat,tags,urlhaus_link,reporter"
        csv_content = header + '\n' + '\n'.join(lines)

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content), delimiter=',')

        for row in reader:
            # URLhaus CSV berisi kolom 'url'
            malware_url = row.get('url', '')
            if malware_url:
                # Extract IP dari URL
                try:
                    parsed = urlparse(malware_url)
                    host = parsed.netloc
                    if host:
                        # Remove port jika ada
                        host = host.split(':')[0]
                        # Remove username jika ada (user@host)
                        if '@' in host:
                            host = host.split('@')[1]

                        # Filter: HANYA IP address, BUKAN domain
                        if host:
                            # Cek apakah ini IP address
                            parts = host.split('.')
                            is_ip = all(part.isdigit() and 0 <= int(part) <= 255 for part in parts if part) and len(parts) == 4

                            # Hanya tambahkan jika ADALAH IP
                            if is_ip:
                                ips.add(host)
                except Exception:
                    continue

        logger.info(f"Berhasil mengambil {len(ips)} malware IPs dari URLhaus")
        return ips

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error saat fetching dari URLhaus: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error saat parsing data dari URLhaus: {e}")
        return set()
