#!/usr/bin/env python3
"""
Auto-update WHOIS cache for new IPs
Dipanggil setelah processor.py atau resolve_*.py selesai

Strategy:
1. Check which IPs are new (not in whois.txt)
2. Query only new IPs to save API quota
3. Use batch processing with rate limiting
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from whois_manager import WhoisManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Update WHOIS cache for blacklist and whitelist IPs"""
    logger.info("=" * 80)
    logger.info("WHOIS Cache Auto-Update")
    logger.info("=" * 80)

    manager = WhoisManager()

    # Files to process
    ip_files = [
        'data/blacklist-specific.txt',
        'data/whitelist-specific.txt',
    ]

    # Check initial cache size
    initial_size = len(manager.cache)
    logger.info(f"Initial cache size: {initial_size} entries")

    # Process each file (limited queries to avoid hitting API limit)
    total_queries = 0
    max_queries_per_file = 500  # Limit to 500 new IPs per file per run

    for filepath in ip_files:
        if not Path(filepath).exists():
            logger.warning(f"File not found: {filepath}")
            continue

        logger.info(f"\nProcessing {filepath}...")

        # Get IPs from file
        ips = set()
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    if ' # ' in line:
                        ip = line.split(' # ')[0].strip()
                    else:
                        ip = line.split()[0] if line else None

                    if ip:
                        clean_ip = ip.split('/')[0]
                        ips.add(clean_ip)

            # Count new IPs
            new_ips = [ip for ip in ips if ip not in manager.cache]
            logger.info(f"  Total IPs: {len(ips)}")
            logger.info(f"  In cache: {len(ips) - len(new_ips)}")
            logger.info(f"  New IPs: {len(new_ips)}")

            if new_ips:
                # Limit queries
                limited_ips = new_ips[:max_queries_per_file]
                if len(new_ips) > max_queries_per_file:
                    logger.info(f"  Limiting to {max_queries_per_file} queries")

                # Batch update
                manager.batch_update_from_file(filepath, max_queries=max_queries_per_file)
                total_queries += len(limited_ips)

        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")

    # Final stats
    final_size = len(manager.cache)
    new_entries = final_size - initial_size

    logger.info("\n" + "=" * 80)
    logger.info("Update Complete")
    logger.info("=" * 80)
    logger.info(f"Initial cache size: {initial_size}")
    logger.info(f"Final cache size: {final_size}")
    logger.info(f"New entries added: {new_entries}")
    logger.info(f"Total API queries: {total_queries}")
    logger.info(f"API quota remaining: ~{50000 - total_queries} (estimate)")
    logger.info("=" * 80)

    if new_entries == 0:
        logger.info("✅ Cache is up to date, no new queries needed")
    else:
        logger.info(f"✅ Added {new_entries} new WHOIS records")


if __name__ == "__main__":
    main()
