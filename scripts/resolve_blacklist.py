#!/usr/bin/env python3
"""
Script untuk resolve DNS dari blacklist domains ke IP addresses
Menyimpan hasil ke blacklist-specific.txt (IP Spesifik dari domain blacklist)
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Set
from datetime import datetime

# Import optimized DNS resolver
try:
    from dns_resolver import DNSResolver
except ImportError:
    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent))
    from dns_resolver import DNSResolver

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_blacklist_domains(filepath: str) -> Dict[str, str]:
    """
    Baca domain dari blacklist.txt
    Returns: {domain: source}
    """
    domains = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Parse: "domain # Source"
                        if ' # ' in line:
                            domain, source = line.split(' # ', 1)
                            domain = domain.strip()
                            # Skip wildcards
                            if not domain.startswith('*'):
                                domains[domain] = source
                        else:
                            if not line.startswith('*'):
                                domains[line] = "Unknown Source"
            logger.info(f"Loaded {len(domains)} domains from blacklist.txt")
        except Exception as e:
            logger.error(f"Error reading blacklist: {e}")
    return domains


def read_specific_ips(filepath: str) -> Dict[str, str]:
    """
    Baca IP dari blacklist-specific.txt
    Returns: {ip: source}
    """
    ips = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Parse: "ip # Source"
                        if ' # ' in line:
                            ip, source = line.split(' # ', 1)
                            ips[ip.strip()] = source.strip()
                        else:
                            ips[line] = "Unknown Source"
            logger.info(f"Loaded {len(ips)} IPs from {os.path.basename(filepath)}")
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
    return ips


def generate_domain_ip_mappings(blacklist_domains: Dict[str, str]) -> Dict[str, str]:
    """
    Resolve semua domain di blacklist ke IP menggunakan optimized resolver
    Returns: {ip: "Berasal dari IP domain xxxx (Original Source)"}
    """
    logger.info(f"Resolving {len(blacklist_domains)} blacklist domains...")

    # Use optimized DNS resolver dengan concurrent queries
    resolver = DNSResolver(
        max_workers=100,  # 100 concurrent threads untuk speed
        timeout=3.0,      # 3 detik timeout per domain
        cache_enabled=True  # Enable caching
    )

    # Resolve all domains concurrently
    domain_list = list(blacklist_domains.keys())
    resolved_ips = resolver.resolve_domains(domain_list, show_progress=True)

    # Map IPs to sources
    domain_ips = {}
    for domain, ips in resolved_ips.items():
        source = blacklist_domains[domain]
        for ip in ips:
            # Format: "Berasal dari IP domain xxxx (URLhaus Malware Domains)"
            # Jika IP sudah ada, simpan yang pertama (FIFO)
            if ip not in domain_ips:
                domain_ips[ip] = f"Berasal dari IP domain {domain} ({source})"

    return domain_ips


def cleanup_old_domain_ips(existing_data: Dict[str, str], current_domain_ips: Dict[str, str]) -> Dict[str, str]:
    """
    Hapus IP dari domain yang sudah tidak ada di blacklist
    Hanya hapus yang memiliki marker "Berasal dari IP domain"
    IP manual (tanpa marker) tidak akan dihapus
    """
    cleaned = {}
    removed_count = 0

    for ip, source in existing_data.items():
        # Check if this is a domain-resolved IP
        if source.startswith("Berasal dari IP domain "):
            # Check if still valid (IP masih di current_domain_ips)
            if ip in current_domain_ips:
                # Update dengan source terbaru
                cleaned[ip] = current_domain_ips[ip]
            else:
                # IP tidak lagi resolve dari domain di blacklist - hapus
                removed_count += 1
                logger.debug(f"Removing outdated IP {ip} ({source})")
        else:
            # IP manual, keep as is (tidak akan dihapus otomatis)
            cleaned[ip] = source

    if removed_count > 0:
        logger.info(f"Cleaned up {removed_count} outdated domain-resolved IPs")

    return cleaned


def merge_domain_ips(existing_data: Dict[str, str], domain_ips: Dict[str, str]) -> Dict[str, str]:
    """
    Merge domain-resolved IPs dengan data yang sudah ada
    Domain-resolved IPs akan override jika IP sama
    """
    # Start with cleaned existing data
    merged = dict(existing_data)

    # Add/update domain-resolved IPs
    added_count = 0
    updated_count = 0

    for ip, source in domain_ips.items():
        if ip in merged:
            # Check if different source
            if merged[ip] != source:
                updated_count += 1
                merged[ip] = source
        else:
            added_count += 1
            merged[ip] = source

    logger.info(f"Merged blacklist domain IPs:")
    logger.info(f"  - New IPs: {added_count}")
    logger.info(f"  - Updated IPs: {updated_count}")

    return merged


def write_specific_txt(filepath: str, data: Dict[str, str]):
    """Write blacklist-specific.txt dengan sorted data"""
    try:
        sorted_items = sorted(data.items(), key=lambda x: x[0])

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Blacklist IP Spesifik - IP dari domain blacklist.txt\n")
            f.write(f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total entries: {len(sorted_items)}\n")
            f.write(f"# Format: <ip> # <source>\n")
            f.write("#\n")
            f.write("# PRIORITAS: Level 2 - Blacklist IP Spesifik\n")
            f.write("# IP dengan marker 'Berasal dari IP domain' akan di-update otomatis\n")
            f.write("# IP manual (tanpa marker) tidak akan dihapus otomatis\n")
            f.write("#\n")

            for ip, source in sorted_items:
                f.write(f"{ip} # {source}\n")

        logger.info(f"Successfully wrote {len(sorted_items)} entries to {filepath}")
    except Exception as e:
        logger.error(f"Error writing {filepath}: {e}")
        raise


def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("Blacklist Domain to IP Resolution")
    logger.info("=" * 60)

    project_root = Path(__file__).parent.parent
    blacklist_file = project_root / "data" / "blacklist.txt"
    specific_file = project_root / "data" / "blacklist-specific.txt"

    # 1. Load blacklist domains
    logger.info("Step 1: Loading blacklist domains...")
    blacklist_domains = read_blacklist_domains(str(blacklist_file))

    if not blacklist_domains:
        logger.warning("No domains found in blacklist!")
        return

    # 2. Load existing blacklist-specific.txt
    logger.info("\nStep 2: Loading existing blacklist-specific.txt...")
    existing_data = read_specific_ips(str(specific_file))

    # 3. Resolve all blacklist domains to IPs
    logger.info("\nStep 3: Resolving domains to IPs...")
    domain_ips = generate_domain_ip_mappings(blacklist_domains)

    # 4. Cleanup old domain-resolved IPs (keep manual IPs)
    logger.info("\nStep 4: Cleaning up outdated domain IPs...")
    cleaned_data = cleanup_old_domain_ips(existing_data, domain_ips)

    # 5. Merge dengan domain IPs yang baru
    logger.info("\nStep 5: Merging domain IPs...")
    final_data = merge_domain_ips(cleaned_data, domain_ips)

    # 6. Write back to blacklist-specific.txt
    logger.info("\nStep 6: Writing to blacklist-specific.txt...")
    write_specific_txt(str(specific_file), final_data)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Summary:")
    logger.info(f"  - Blacklist domains: {len(blacklist_domains)}")
    logger.info(f"  - Domain-resolved IPs: {len(domain_ips)}")
    logger.info(f"  - Total IPs in blacklist-specific.txt: {len(final_data)}")
    logger.info("=" * 60)
    logger.info("Blacklist DNS Resolution complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
