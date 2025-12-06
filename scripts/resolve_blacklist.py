#!/usr/bin/env python3
"""
Script untuk resolve DNS dari blacklist domains ke IP addresses
Menyimpan hasil ke blacklist-specific.txt (IP Spesifik dari domain blacklist)

CRITICAL PROTECTION:
- Infrastructure IPs (DNS servers, root servers, etc) are NEVER blacklisted
- Bogon/Reserved IPs (0.0.0.0, 127.0.0.1, private ranges) are filtered
- Protection against fake DNS records from malicious domains
"""

import os
import sys
import logging
import ipaddress
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


def is_bogon_ip(ip: str) -> bool:
    """
    Check if IP is a bogon/reserved/invalid IP

    Bogon IPs include:
    - 0.0.0.0 (invalid/unspecified)
    - 127.0.0.0/8 (loopback)
    - 10.0.0.0/8 (private Class A)
    - 172.16.0.0/12 (private Class B)
    - 192.168.0.0/16 (private Class C)
    - 169.254.0.0/16 (link-local/APIPA)
    - 224.0.0.0/4 (multicast)
    - 240.0.0.0/4 (reserved)
    - 255.255.255.255 (broadcast)

    Returns: True if bogon, False if routable public IP
    """
    try:
        ip_obj = ipaddress.ip_address(ip)

        # Check for special/reserved addresses
        if (ip_obj.is_private or
            ip_obj.is_loopback or
            ip_obj.is_link_local or
            ip_obj.is_multicast or
            ip_obj.is_reserved or
            ip_obj.is_unspecified):
            return True

        # Additional check for broadcast
        if str(ip) == '255.255.255.255':
            return True

        return False
    except ValueError:
        logger.warning(f"Invalid IP format: {ip}")
        return True  # Treat invalid IPs as bogon


def is_protected_ip(ip: str, protected_ips: Set[str]) -> bool:
    """
    Check if IP is in protected infrastructure list (whitelist-specific.txt)

    Returns: True if protected, False otherwise
    """
    return ip in protected_ips


def read_whitelist_domains(filepath: str) -> Set[str]:
    """
    Baca domain dari whitelist.txt (untuk shared IP protection)
    Returns: Set of domains (non-wildcard saja untuk resolving)
    """
    domains = set()
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Parse: "domain # Source"
                        if ' # ' in line:
                            domain = line.split(' # ', 1)[0].strip()
                        else:
                            domain = line
                        # Skip wildcards untuk resolve, tapi simpan untuk matching nanti
                        if not domain.startswith('*'):
                            domains.add(domain.lower())
            logger.info(f"Loaded {len(domains)} non-wildcard domains from whitelist.txt")
        except Exception as e:
            logger.error(f"Error reading whitelist: {e}")
    return domains


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


def get_whitelist_shared_ips(whitelist_domains: Set[str]) -> Set[str]:
    """
    Resolve whitelist domains untuk mendapatkan shared IPs
    IP ini TIDAK BOLEH masuk blacklist-specific (shared IP protection)
    Returns: Set of IPs used by whitelist domains
    """
    if not whitelist_domains:
        return set()

    logger.info(f"Resolving {len(whitelist_domains)} whitelist domains for shared IP protection...")

    resolver = DNSResolver(
        max_workers=100,
        timeout=3.0,
        cache_enabled=True
    )

    domain_list = list(whitelist_domains)
    resolved_ips = resolver.resolve_domains(domain_list, show_progress=True)

    # Collect all IPs
    shared_ips = set()
    for domain, ips in resolved_ips.items():
        shared_ips.update(ips)

    logger.info(f"Found {len(shared_ips)} shared IPs from whitelist domains")
    return shared_ips


def generate_domain_ip_mappings(
    blacklist_domains: Dict[str, str],
    whitelist_shared_ips: Set[str] = None,
    protected_infrastructure_ips: Set[str] = None
) -> Dict[str, str]:
    """
    Resolve semua domain di blacklist ke IP menggunakan optimized resolver

    PROTECTIONS:
    1. SKIP IPs yang ada di whitelist_shared_ips (shared IP protection)
    2. SKIP infrastructure IPs (DNS servers, root servers, etc) - CRITICAL!
    3. SKIP bogon/reserved IPs (0.0.0.0, 127.0.0.1, private ranges, etc)

    Returns: {ip: "Berasal dari IP domain xxxx (Original Source)"}
    """
    if whitelist_shared_ips is None:
        whitelist_shared_ips = set()
    if protected_infrastructure_ips is None:
        protected_infrastructure_ips = set()

    logger.info(f"Resolving {len(blacklist_domains)} blacklist domains...")
    if whitelist_shared_ips:
        logger.info(f"Shared IP protection enabled: {len(whitelist_shared_ips)} IPs will be skipped")
    if protected_infrastructure_ips:
        logger.info(f"Infrastructure protection enabled: {len(protected_infrastructure_ips)} IPs/ranges protected")

    # Use optimized DNS resolver dengan concurrent queries
    resolver = DNSResolver(
        max_workers=100,  # 100 concurrent threads untuk speed
        timeout=3.0,      # 3 detik timeout per domain
        cache_enabled=True  # Enable caching
    )

    # Resolve all domains concurrently
    domain_list = list(blacklist_domains.keys())
    resolved_ips = resolver.resolve_domains(domain_list, show_progress=True)

    # Map IPs to sources (with TRIPLE PROTECTION)
    domain_ips = {}
    skipped_shared = 0
    skipped_infrastructure = 0
    skipped_bogon = 0

    for domain, ips in resolved_ips.items():
        source = blacklist_domains[domain]
        for ip in ips:
            # PROTECTION 1: SKIP if IP is used by whitelist domains (shared IP protection)
            if ip in whitelist_shared_ips:
                skipped_shared += 1
                logger.debug(f"Skipping shared IP {ip} from {domain} (used by whitelist domains)")
                continue

            # PROTECTION 2: SKIP if IP is protected infrastructure (CRITICAL!)
            if is_protected_ip(ip, protected_infrastructure_ips):
                skipped_infrastructure += 1
                logger.warning(f"🚨 PROTECTED: Skipping infrastructure IP {ip} from {domain} (DNS/critical service)")
                continue

            # PROTECTION 3: SKIP if IP is bogon/reserved
            if is_bogon_ip(ip):
                skipped_bogon += 1
                logger.debug(f"Skipping bogon IP {ip} from {domain} (reserved/private)")
                continue

            # Format: "Berasal dari IP domain xxxx (URLhaus Malware Domains)"
            # Jika IP sudah ada, simpan yang pertama (FIFO)
            if ip not in domain_ips:
                domain_ips[ip] = f"Berasal dari IP domain {domain} ({source})"

    # Log protection statistics
    logger.info(f"Protection Statistics:")
    logger.info(f"  - Shared IPs skipped: {skipped_shared}")
    logger.info(f"  - Infrastructure IPs skipped: {skipped_infrastructure} 🛡️")
    logger.info(f"  - Bogon/Reserved IPs skipped: {skipped_bogon}")
    logger.info(f"  - Total protected: {skipped_shared + skipped_infrastructure + skipped_bogon}")

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


def remove_whitelisted_ips(blacklist_data: Dict[str, str]) -> Dict[str, str]:
    """
    Remove IPs yang ada di whitelist-specific.txt dari blacklist
    Whitelist memiliki prioritas lebih tinggi
    """
    project_root = Path(__file__).parent.parent
    whitelist_file = project_root / "data" / "whitelist-specific.txt"

    whitelist_ips = set()
    if whitelist_file.exists():
        try:
            with open(whitelist_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if ' # ' in line:
                            ip = line.split(' # ')[0].strip()
                            whitelist_ips.add(ip)
        except Exception as e:
            logger.warning(f"Error reading whitelist-specific.txt: {e}")

    if not whitelist_ips:
        return blacklist_data

    # Remove whitelisted IPs
    cleaned = {}
    removed_count = 0

    for ip, source in blacklist_data.items():
        if ip in whitelist_ips:
            removed_count += 1
            logger.debug(f"Removing whitelisted IP: {ip}")
        else:
            cleaned[ip] = source

    if removed_count > 0:
        logger.info(f"Removed {removed_count} IPs that are in whitelist (whitelist priority)")

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
    """Main function with TRIPLE PROTECTION"""
    logger.info("=" * 80)
    logger.info("🛡️  Blacklist Domain to IP Resolution with Infrastructure Protection")
    logger.info("=" * 80)

    project_root = Path(__file__).parent.parent
    blacklist_file = project_root / "data" / "blacklist.txt"
    whitelist_file = project_root / "data" / "whitelist.txt"
    whitelist_specific_file = project_root / "data" / "whitelist-specific.txt"
    specific_file = project_root / "data" / "blacklist-specific.txt"

    # 1. Load whitelist-specific.txt for infrastructure protection (CRITICAL!)
    logger.info("Step 1: Loading whitelist-specific.txt (includes infrastructure protection)...")
    whitelist_specific_data = read_specific_ips(str(whitelist_specific_file))
    protected_infrastructure_ips = set(whitelist_specific_data.keys())
    logger.info(f"Loaded {len(protected_infrastructure_ips)} protected IPs from whitelist-specific.txt")

    # 2. Load whitelist domains for shared IP protection
    logger.info("\nStep 2: Loading whitelist domains for shared IP protection...")
    whitelist_domains = read_whitelist_domains(str(whitelist_file))

    # 3. Resolve whitelist domains to get shared IPs
    logger.info("\nStep 3: Resolving whitelist domains to get shared IPs...")
    whitelist_shared_ips = get_whitelist_shared_ips(whitelist_domains)

    # 4. Load blacklist domains
    logger.info("\nStep 4: Loading blacklist domains...")
    blacklist_domains = read_blacklist_domains(str(blacklist_file))

    if not blacklist_domains:
        logger.warning("No domains found in blacklist!")
        return

    # 5. Load existing blacklist-specific.txt
    logger.info("\nStep 5: Loading existing blacklist-specific.txt...")
    existing_data = read_specific_ips(str(specific_file))

    # 6. Resolve all blacklist domains to IPs (TRIPLE PROTECTION!)
    logger.info("\nStep 6: Resolving blacklist domains to IPs (with TRIPLE protection)...")
    logger.info("  🛡️  Protection 1: Shared IP Protection (CDN/Hosting)")
    logger.info("  🛡️  Protection 2: Infrastructure Protection (DNS/Root Servers)")
    logger.info("  🛡️  Protection 3: Bogon/Reserved IP Filtering")
    domain_ips = generate_domain_ip_mappings(
        blacklist_domains,
        whitelist_shared_ips,
        protected_infrastructure_ips
    )

    # 7. Cleanup old domain-resolved IPs (keep manual IPs)
    logger.info("\nStep 7: Cleaning up outdated domain IPs...")
    cleaned_data = cleanup_old_domain_ips(existing_data, domain_ips)

    # 8. Merge dengan domain IPs yang baru
    logger.info("\nStep 8: Merging domain IPs...")
    final_data = merge_domain_ips(cleaned_data, domain_ips)

    # 9. Remove whitelisted IPs (whitelist priority)
    logger.info("\nStep 9: Removing whitelisted IPs...")
    final_data = remove_whitelisted_ips(final_data)

    # 10. Write back to blacklist-specific.txt
    logger.info("\nStep 10: Writing to blacklist-specific.txt...")
    write_specific_txt(str(specific_file), final_data)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("Summary:")
    logger.info(f"  - Protected infrastructure IPs: {len(protected_infrastructure_ips)} 🛡️")
    logger.info(f"  - Whitelist domains resolved: {len(whitelist_domains)}")
    logger.info(f"  - Shared IPs protected: {len(whitelist_shared_ips)}")
    logger.info(f"  - Blacklist domains: {len(blacklist_domains)}")
    logger.info(f"  - Domain-resolved IPs (after TRIPLE protection): {len(domain_ips)}")
    logger.info(f"  - Total IPs in blacklist-specific.txt: {len(final_data)}")
    logger.info("=" * 80)
    logger.info("✅ Blacklist DNS Resolution complete with Infrastructure Protection!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
