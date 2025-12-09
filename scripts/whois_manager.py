#!/usr/bin/env python3
"""
WHOIS Manager - IPinfo Integration
Mengelola data kepemilikan IP/domain menggunakan IPinfo.io API

Features:
- Query IP/domain ownership dari IPinfo.io
- Cache hasil ke whois.txt untuk efisiensi
- Batch update untuk IP baru
- Rate limiting dan quota tracking
"""

import os
import sys
import json
import time
import logging
import requests
from pathlib import Path
from typing import Dict, Set, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# IPinfo Configuration
IPINFO_TOKEN = "13cf963d4e732d"
IPINFO_API = "https://ipinfo.io"
MONTHLY_LIMIT = 50000
BATCH_SIZE = 100  # Process 100 IPs at a time
RATE_LIMIT_DELAY = 0.1  # 100ms between requests


class WhoisManager:
    """Manager untuk WHOIS data dengan IPinfo.io integration"""

    def __init__(self, cache_file: str = "data/whois.txt"):
        self.cache_file = Path(cache_file)
        self.cache: Dict[str, dict] = {}
        self.load_cache()

    def load_cache(self):
        """Load existing WHOIS cache from whois.txt"""
        if not self.cache_file.exists():
            logger.info("No existing whois.txt found, starting fresh")
            return

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # Format: IP|ORG|COUNTRY|CITY|ASN|HOSTNAME|CACHED_DATE
                    parts = line.split('|')
                    if len(parts) >= 7:
                        ip = parts[0]
                        self.cache[ip] = {
                            'ip': ip,
                            'org': parts[1],
                            'country': parts[2],
                            'city': parts[3],
                            'asn': parts[4],
                            'hostname': parts[5],
                            'cached': parts[6]
                        }

            logger.info(f"Loaded {len(self.cache)} WHOIS records from cache")
        except Exception as e:
            logger.error(f"Error loading cache: {e}")

    def save_cache(self):
        """Save WHOIS cache to whois.txt"""
        try:
            # Create directory if not exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Sort by IP for consistency
            sorted_ips = sorted(self.cache.keys(), key=lambda x: self._ip_sort_key(x))

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                f.write("# WHOIS Data Cache - IPinfo.io\n")
                f.write(f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                f.write(f"# Total entries: {len(self.cache)}\n")
                f.write("# Format: IP|ORG|COUNTRY|CITY|ASN|HOSTNAME|CACHED_DATE\n")
                f.write("#\n")

                for ip in sorted_ips:
                    data = self.cache[ip]
                    line = f"{data['ip']}|{data['org']}|{data['country']}|{data['city']}|{data['asn']}|{data['hostname']}|{data['cached']}\n"
                    f.write(line)

            logger.info(f"Saved {len(self.cache)} WHOIS records to {self.cache_file}")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
            raise

    def _ip_sort_key(self, ip: str):
        """Generate sort key for IP (IPv4 first, then IPv6)"""
        try:
            # Remove CIDR if present
            if '/' in ip:
                ip = ip.split('/')[0]

            # IPv6
            if ':' in ip:
                segments = ip.split(':')
                if '' in segments:
                    idx = segments.index('')
                    missing = 8 - len([s for s in segments if s])
                    segments = segments[:idx] + ['0'] * missing + segments[idx+1:]

                int_segments = []
                for seg in segments:
                    if seg:
                        int_segments.append(int(seg, 16))
                    else:
                        int_segments.append(0)

                while len(int_segments) < 8:
                    int_segments.append(0)

                return tuple([6] + int_segments[:8])

            # IPv4
            else:
                octets = tuple(int(octet) for octet in ip.split('.'))
                return tuple([4] + list(octets))
        except:
            return tuple([9] + [0] * 8)

    def query_ipinfo(self, ip: str) -> Optional[dict]:
        """
        Query IPinfo.io API for IP information

        Returns dict with: ip, org, country, city, asn, hostname
        """
        try:
            # Remove CIDR prefix if present
            clean_ip = ip.split('/')[0] if '/' in ip else ip

            url = f"{IPINFO_API}/{clean_ip}?token={IPINFO_TOKEN}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Extract ASN from org field (format: "AS15169 Google LLC")
                org_full = data.get('org', 'Unknown')
                asn = 'Unknown'
                org = org_full

                if org_full.startswith('AS'):
                    parts = org_full.split(' ', 1)
                    if len(parts) == 2:
                        asn = parts[0]
                        org = parts[1]

                return {
                    'ip': clean_ip,
                    'org': org,
                    'country': data.get('country', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'asn': asn,
                    'hostname': data.get('hostname', 'Unknown'),
                    'cached': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

            elif response.status_code == 429:
                logger.warning(f"Rate limit reached for {ip}")
                return None

            else:
                logger.warning(f"API error for {ip}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error querying {ip}: {e}")
            return None

    def get_whois(self, ip: str, use_cache: bool = True) -> Optional[dict]:
        """
        Get WHOIS data for IP

        Args:
            ip: IP address (with or without CIDR)
            use_cache: Use cached data if available

        Returns:
            dict with WHOIS data or None
        """
        clean_ip = ip.split('/')[0] if '/' in ip else ip

        # Check cache first
        if use_cache and clean_ip in self.cache:
            return self.cache[clean_ip]

        # Query API
        data = self.query_ipinfo(clean_ip)
        if data:
            self.cache[clean_ip] = data
            return data

        return None

    def batch_update_from_file(self, filepath: str, max_queries: int = None):
        """
        Update WHOIS cache from IP file (e.g., blacklist-specific.txt)

        Args:
            filepath: Path to IP file
            max_queries: Maximum number of API queries (None = unlimited)
        """
        logger.info(f"Processing IPs from {filepath}")

        # Read IPs from file
        ips = set()
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # Extract IP (format: "IP/prefix # Source")
                    if ' # ' in line:
                        ip = line.split(' # ')[0].strip()
                    else:
                        ip = line.split()[0] if line else None

                    if ip:
                        # Remove CIDR prefix
                        clean_ip = ip.split('/')[0]
                        ips.add(clean_ip)

            logger.info(f"Found {len(ips)} IPs in {filepath}")
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
            return

        # Find IPs not in cache
        new_ips = [ip for ip in ips if ip not in self.cache]
        logger.info(f"New IPs to query: {len(new_ips)}")

        if not new_ips:
            logger.info("All IPs already in cache")
            return

        # Apply query limit
        if max_queries:
            new_ips = new_ips[:max_queries]
            logger.info(f"Limited to {max_queries} queries")

        # Query in batches
        queried = 0
        failed = 0

        for i in range(0, len(new_ips), BATCH_SIZE):
            batch = new_ips[i:i+BATCH_SIZE]
            logger.info(f"Processing batch {i//BATCH_SIZE + 1}/{(len(new_ips)-1)//BATCH_SIZE + 1}")

            for ip in batch:
                data = self.query_ipinfo(ip)
                if data:
                    self.cache[ip] = data
                    queried += 1
                else:
                    failed += 1

                # Rate limiting
                time.sleep(RATE_LIMIT_DELAY)

            # Save cache after each batch
            self.save_cache()
            logger.info(f"Progress: {queried} queried, {failed} failed")

        logger.info(f"Batch update complete: {queried} new, {failed} failed")

    def search(self, query: str) -> list:
        """
        Search WHOIS data by IP, organization, country, or ASN

        Args:
            query: Search query (IP, org name, country code, or ASN)

        Returns:
            List of matching WHOIS records
        """
        query_lower = query.lower()
        results = []

        for ip, data in self.cache.items():
            # Match IP
            if query_lower in ip.lower():
                results.append(data)
                continue

            # Match organization
            if query_lower in data['org'].lower():
                results.append(data)
                continue

            # Match country
            if query_lower in data['country'].lower():
                results.append(data)
                continue

            # Match ASN
            if query_lower in data['asn'].lower():
                results.append(data)
                continue

        return results

    def get_stats(self) -> dict:
        """Get statistics about WHOIS cache"""
        total = len(self.cache)

        # Count by country
        countries = {}
        orgs = {}
        asns = {}

        for data in self.cache.values():
            country = data['country']
            org = data['org']
            asn = data['asn']

            countries[country] = countries.get(country, 0) + 1
            orgs[org] = orgs.get(org, 0) + 1
            asns[asn] = asns.get(asn, 0) + 1

        # Top 10
        top_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]
        top_orgs = sorted(orgs.items(), key=lambda x: x[1], reverse=True)[:10]
        top_asns = sorted(asns.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            'total': total,
            'top_countries': top_countries,
            'top_orgs': top_orgs,
            'top_asns': top_asns
        }


def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(
        description='WHOIS Manager - IPinfo.io Integration'
    )
    parser.add_argument(
        'action',
        choices=['query', 'update', 'search', 'stats'],
        help='Action to perform'
    )
    parser.add_argument(
        'target',
        nargs='?',
        help='IP address for query, file path for update, or search query'
    )
    parser.add_argument(
        '--max-queries',
        type=int,
        help='Maximum number of API queries for update'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Force fresh API query (ignore cache)'
    )

    args = parser.parse_args()

    # Initialize manager
    manager = WhoisManager()

    if args.action == 'query':
        if not args.target:
            print("Error: IP address required for query")
            sys.exit(1)

        print(f"Querying WHOIS for {args.target}...")
        data = manager.get_whois(args.target, use_cache=not args.no_cache)

        if data:
            print("\nWHOIS Information:")
            print(f"  IP:       {data['ip']}")
            print(f"  Org:      {data['org']}")
            print(f"  Country:  {data['country']}")
            print(f"  City:     {data['city']}")
            print(f"  ASN:      {data['asn']}")
            print(f"  Hostname: {data['hostname']}")
            print(f"  Cached:   {data['cached']}")

            # Save if new
            if args.target not in manager.cache:
                manager.save_cache()
        else:
            print("Failed to get WHOIS data")

    elif args.action == 'update':
        if not args.target:
            print("Error: File path required for update")
            sys.exit(1)

        manager.batch_update_from_file(args.target, args.max_queries)

    elif args.action == 'search':
        if not args.target:
            print("Error: Search query required")
            sys.exit(1)

        print(f"Searching for: {args.target}")
        results = manager.search(args.target)

        if results:
            print(f"\nFound {len(results)} results:")
            for data in results[:20]:  # Limit to 20 results
                print(f"  {data['ip']} - {data['org']} ({data['country']})")

            if len(results) > 20:
                print(f"  ... and {len(results) - 20} more")
        else:
            print("No results found")

    elif args.action == 'stats':
        stats = manager.get_stats()

        print(f"\nWHOIS Cache Statistics:")
        print(f"  Total IPs: {stats['total']}")

        print(f"\n  Top 10 Countries:")
        for country, count in stats['top_countries']:
            print(f"    {country}: {count}")

        print(f"\n  Top 10 Organizations:")
        for org, count in stats['top_orgs'][:10]:
            org_short = org[:50] + '...' if len(org) > 50 else org
            print(f"    {org_short}: {count}")

        print(f"\n  Top 10 ASNs:")
        for asn, count in stats['top_asns']:
            print(f"    {asn}: {count}")


if __name__ == "__main__":
    main()
