#!/usr/bin/env python3
"""
IP/Domain Lookup Tool
Mencari status blokir dan kepemilikan IP/domain di Pangrosan Security System

Features:
- Check if IP/domain is blacklisted or whitelisted
- Show WHOIS information from IPinfo.io
- Display priority level and source
- Support for both IPv4 and IPv6
"""

import os
import sys
import socket
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from whois_manager import WhoisManager
except ImportError:
    print("Error: whois_manager.py not found")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings/errors
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecurityLookup:
    """Lookup tool untuk memeriksa status IP/domain di security system"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.whois = WhoisManager()

        # File mappings
        self.files = {
            'whitelist_domains': self.data_dir / 'whitelist.txt',
            'blacklist_domains': self.data_dir / 'blacklist.txt',
            'whitelist_ips': self.data_dir / 'whitelist-specific.txt',
            'blacklist_ips': self.data_dir / 'blacklist-specific.txt',
            'whitelist_subnets': self.data_dir / 'pass.txt',
            'blacklist_subnets': self.data_dir / 'drop.txt',
        }

        # Priority levels
        self.priorities = {
            'whitelist_ips': 1,
            'blacklist_ips': 2,
            'blacklist_subnets': 3,
            'whitelist_subnets': 4,
            'whitelist_domains': 5,
            'blacklist_domains': 6,
        }

    def is_ip(self, query: str) -> bool:
        """Check if query is an IP address"""
        # Remove CIDR if present
        ip = query.split('/')[0]

        # Check IPv4
        if '.' in ip:
            parts = ip.split('.')
            if len(parts) == 4:
                try:
                    return all(0 <= int(p) <= 255 for p in parts)
                except ValueError:
                    return False

        # Check IPv6
        if ':' in ip:
            try:
                socket.inet_pton(socket.AF_INET6, ip)
                return True
            except:
                return False

        return False

    def resolve_domain(self, domain: str) -> List[str]:
        """Resolve domain to IP addresses"""
        try:
            # Get all IP addresses for domain
            addr_info = socket.getaddrinfo(domain, None)
            ips = list(set([info[4][0] for info in addr_info]))
            return ips
        except Exception as e:
            logger.warning(f"Failed to resolve {domain}: {e}")
            return []

    def search_in_file(self, filepath: Path, query: str, is_domain: bool = False) -> Optional[Tuple[str, str]]:
        """
        Search for query in file

        Returns: (matched_entry, source) or None
        """
        if not filepath.exists():
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # Parse: "entry # Source"
                    if ' # ' in line:
                        entry, source = line.split(' # ', 1)
                        entry = entry.strip()
                        source = source.strip()
                    else:
                        entry = line
                        source = "Unknown"

                    # For domains: check exact match or wildcard
                    if is_domain:
                        # Exact match
                        if entry.lower() == query.lower():
                            return (entry, source)

                        # Wildcard match (*.example.com matches sub.example.com)
                        if entry.startswith('*.'):
                            wildcard_domain = entry[2:]  # Remove *.
                            if query.lower().endswith('.' + wildcard_domain.lower()) or query.lower() == wildcard_domain.lower():
                                return (entry, source)

                    # For IPs: exact match (with or without CIDR)
                    else:
                        # Remove CIDR for comparison
                        entry_ip = entry.split('/')[0]
                        query_ip = query.split('/')[0]

                        if entry_ip == query_ip:
                            return (entry, source)

        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")

        return None

    def lookup(self, query: str, show_whois: bool = True):
        """
        Lookup IP or domain in security system

        Args:
            query: IP address or domain name
            show_whois: Show WHOIS information
        """
        print("=" * 80)
        print(f"Security Lookup: {query}")
        print("=" * 80)

        # Determine if IP or domain
        is_ip_query = self.is_ip(query)

        if is_ip_query:
            print(f"Type: IP Address")
            self._lookup_ip(query, show_whois)
        else:
            print(f"Type: Domain Name")
            self._lookup_domain(query, show_whois)

    def _lookup_ip(self, ip: str, show_whois: bool = True):
        """Lookup IP address"""
        results = []

        # Check all IP files
        for file_key, filepath in self.files.items():
            if 'domains' in file_key:
                continue  # Skip domain files

            match = self.search_in_file(filepath, ip, is_domain=False)
            if match:
                entry, source = match
                priority = self.priorities[file_key]
                results.append({
                    'type': file_key,
                    'priority': priority,
                    'entry': entry,
                    'source': source
                })

        # Sort by priority (lowest number = highest priority)
        results.sort(key=lambda x: x['priority'])

        # Display results
        if results:
            print("\n📋 Status:")
            for result in results:
                status_type = result['type'].replace('_', ' ').title()
                priority = result['priority']

                # Color coding
                if 'whitelist' in result['type']:
                    status_icon = "✅"
                    status_color = "WHITELISTED"
                else:
                    status_icon = "🚫"
                    status_color = "BLACKLISTED"

                print(f"  {status_icon} {status_color}")
                print(f"     Priority: Level {priority}")
                print(f"     List: {status_type}")
                print(f"     Entry: {result['entry']}")
                print(f"     Source: {result['source']}")

            # Show effective action
            effective = results[0]  # Highest priority
            print(f"\n🎯 Effective Action:")
            if 'whitelist' in effective['type']:
                print(f"   ✅ ALLOWED (Priority Level {effective['priority']})")
            else:
                print(f"   🚫 BLOCKED (Priority Level {effective['priority']})")

        else:
            print("\n✅ Status: NOT LISTED (Allowed by default)")

        # WHOIS information
        if show_whois:
            print("\n" + "=" * 80)
            print("WHOIS Information (IPinfo.io)")
            print("=" * 80)

            whois_data = self.whois.get_whois(ip)
            if whois_data:
                print(f"  Organization: {whois_data['org']}")
                print(f"  Country:      {whois_data['country']}")
                print(f"  City:         {whois_data['city']}")
                print(f"  ASN:          {whois_data['asn']}")
                print(f"  Hostname:     {whois_data['hostname']}")
                print(f"  Cached:       {whois_data['cached']}")
            else:
                print("  ⚠️  WHOIS data not available")
                print("  Run: python3 scripts/whois_manager.py update data/blacklist-specific.txt")

    def _lookup_domain(self, domain: str, show_whois: bool = True):
        """Lookup domain name"""
        results = []

        # Check domain files
        for file_key, filepath in self.files.items():
            if 'ips' in file_key or 'subnets' in file_key:
                continue  # Skip IP files

            match = self.search_in_file(filepath, domain, is_domain=True)
            if match:
                entry, source = match
                priority = self.priorities[file_key]
                results.append({
                    'type': file_key,
                    'priority': priority,
                    'entry': entry,
                    'source': source
                })

        # Sort by priority
        results.sort(key=lambda x: x['priority'])

        # Display domain results
        if results:
            print("\n📋 Domain Status:")
            for result in results:
                status_type = result['type'].replace('_', ' ').title()
                priority = result['priority']

                if 'whitelist' in result['type']:
                    status_icon = "✅"
                    status_color = "WHITELISTED"
                else:
                    status_icon = "🚫"
                    status_color = "BLACKLISTED"

                print(f"  {status_icon} {status_color}")
                print(f"     Priority: Level {priority}")
                print(f"     List: {status_type}")
                print(f"     Entry: {result['entry']}")
                print(f"     Source: {result['source']}")

            # Show effective action
            effective = results[0]
            print(f"\n🎯 Effective Action for Domain:")
            if 'whitelist' in effective['type']:
                print(f"   ✅ ALLOWED (Priority Level {effective['priority']})")
            else:
                print(f"   🚫 BLOCKED (Priority Level {effective['priority']})")

        else:
            print("\n✅ Domain Status: NOT LISTED (Allowed by default)")

        # Resolve domain to IPs
        print(f"\n📡 Resolving {domain}...")
        ips = self.resolve_domain(domain)

        if ips:
            print(f"   Found {len(ips)} IP address(es):")
            for ip in ips:
                print(f"     - {ip}")

            # Check each IP
            print("\n" + "=" * 80)
            print("IP Resolution Check")
            print("=" * 80)

            for i, ip in enumerate(ips, 1):
                print(f"\n[{i}/{len(ips)}] Checking IP: {ip}")
                print("-" * 80)

                ip_results = []
                for file_key, filepath in self.files.items():
                    if 'domains' in file_key:
                        continue

                    match = self.search_in_file(filepath, ip, is_domain=False)
                    if match:
                        entry, source = match
                        priority = self.priorities[file_key]
                        ip_results.append({
                            'type': file_key,
                            'priority': priority,
                            'entry': entry,
                            'source': source
                        })

                ip_results.sort(key=lambda x: x['priority'])

                if ip_results:
                    for result in ip_results:
                        status_type = result['type'].replace('_', ' ').title()
                        if 'whitelist' in result['type']:
                            print(f"   ✅ {status_type}: {result['entry']}")
                        else:
                            print(f"   🚫 {status_type}: {result['entry']}")

                    effective_ip = ip_results[0]
                    if 'whitelist' in effective_ip['type']:
                        print(f"   → ALLOWED (Level {effective_ip['priority']})")
                    else:
                        print(f"   → BLOCKED (Level {effective_ip['priority']})")
                else:
                    print("   ✅ NOT LISTED")

                # WHOIS for first IP only
                if show_whois and i == 1:
                    print(f"\n   WHOIS for {ip}:")
                    whois_data = self.whois.get_whois(ip)
                    if whois_data:
                        print(f"     Organization: {whois_data['org']}")
                        print(f"     Country:      {whois_data['country']}")
                        print(f"     ASN:          {whois_data['asn']}")
                    else:
                        print(f"     ⚠️  WHOIS data not available")

        else:
            print("   ⚠️  Failed to resolve domain")

        print("\n" + "=" * 80)


def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(
        description='IP/Domain Lookup Tool - Check security status and ownership'
    )
    parser.add_argument(
        'query',
        help='IP address or domain name to lookup'
    )
    parser.add_argument(
        '--no-whois',
        action='store_true',
        help='Skip WHOIS information'
    )

    args = parser.parse_args()

    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Perform lookup
    lookup = SecurityLookup()
    lookup.lookup(args.query, show_whois=not args.no_whois)


if __name__ == "__main__":
    main()
