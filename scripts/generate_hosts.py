#!/usr/bin/env python3
"""
Script untuk mengkonversi blacklist.txt ke format /etc/hosts
Format output: 0.0.0.0 domain.tld
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Set

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_blacklist(filepath: str) -> Set[str]:
    """
    Baca domain dari blacklist.txt dan filter wildcard

    Args:
        filepath: Path ke file blacklist.txt

    Returns:
        Set of domain names (tanpa wildcard)
    """
    domains = set()

    if not os.path.exists(filepath):
        logger.error(f"File tidak ditemukan: {filepath}")
        return domains

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Skip comments dan empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse line dengan format: "domain # Source"
                if ' # ' in line:
                    domain = line.split(' # ', 1)[0].strip()
                else:
                    domain = line

                # Skip wildcard domains
                if domain.startswith('*'):
                    continue

                # Tambahkan domain yang valid
                domains.add(domain)

        logger.info(f"Berhasil membaca {len(domains)} domain dari {filepath}")
        return domains

    except Exception as e:
        logger.error(f"Error saat membaca {filepath}: {e}")
        return set()


def write_hosts_format(domains: Set[str], output_file: str):
    """
    Tulis domain ke file dalam format /etc/hosts

    Args:
        domains: Set of domain names
        output_file: Path ke output file
    """
    # Buat direktori jika belum ada
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Sort domains untuk konsistensi
    sorted_domains = sorted(domains)

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("# Hosts file format for domain blacklist\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total entries: {len(sorted_domains)}\n")
            f.write("#\n")
            f.write("# Format: 0.0.0.0 domain.tld\n")
            f.write("# This file can be used with /etc/hosts or DNS servers\n")
            f.write("#\n\n")

            # Write domains in hosts format
            for domain in sorted_domains:
                f.write(f"0.0.0.0 {domain}\n")

        logger.info(f"Berhasil menulis {len(sorted_domains)} domain ke {output_file}")
        logger.info(f"Format: 0.0.0.0 <domain>")

    except Exception as e:
        logger.error(f"Error saat menulis ke {output_file}: {e}")


def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("Generate Hosts File from Blacklist")
    logger.info("=" * 60)

    # Path files
    project_root = Path(__file__).parent.parent
    blacklist_file = project_root / "data" / "blacklist.txt"
    output_file = project_root / "data" / "hosts.txt"

    # Read blacklist
    logger.info(f"Membaca blacklist dari: {blacklist_file}")
    domains = read_blacklist(str(blacklist_file))

    if not domains:
        logger.warning("Tidak ada domain yang ditemukan. Keluar.")
        sys.exit(1)

    # Write hosts format
    logger.info(f"Menulis hosts file ke: {output_file}")
    write_hosts_format(domains, str(output_file))

    logger.info("\n" + "=" * 60)
    logger.info("Proses selesai!")
    logger.info(f"File hosts tersimpan di: {output_file}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
