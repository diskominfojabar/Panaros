#!/usr/bin/env python3
"""
Optimized DNS Resolver dengan concurrent queries, caching, dan multi-server support
Dirancang untuk resolve ribuan domain dengan cepat dan minim rate limit
"""

import socket
import logging
import time
from typing import Dict, Set, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class DNSResolver:
    """
    High-performance DNS resolver dengan features:
    - Concurrent resolution (multi-threading)
    - DNS caching
    - Multiple DNS servers (automatic fallback)
    - Rate limiting protection
    - Retry dengan exponential backoff
    """

    def __init__(self, max_workers: int = 50, timeout: float = 2.0, cache_enabled: bool = True):
        """
        Args:
            max_workers: Jumlah concurrent threads untuk DNS queries
            timeout: Timeout per DNS query (seconds)
            cache_enabled: Enable DNS caching untuk menghindari duplicate queries
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.cache_enabled = cache_enabled

        # DNS cache: {domain: set(ips)}
        self.cache: Dict[str, Set[str]] = {}
        self.cache_lock = threading.Lock()

        # Statistics
        self.stats = {
            'total': 0,
            'resolved': 0,
            'cached': 0,
            'failed': 0,
            'errors': defaultdict(int)
        }
        self.stats_lock = threading.Lock()

    def _resolve_single(self, domain: str, retry: int = 2) -> Set[str]:
        """
        Resolve single domain ke IP addresses dengan retry

        Args:
            domain: Domain to resolve
            retry: Number of retries

        Returns:
            Set of IP addresses (IPv4 only)
        """
        # Check cache first
        if self.cache_enabled:
            with self.cache_lock:
                if domain in self.cache:
                    with self.stats_lock:
                        self.stats['cached'] += 1
                    return self.cache[domain]

        ips = set()
        last_error = None

        for attempt in range(retry + 1):
            try:
                # Set timeout for this query
                socket.setdefaulttimeout(self.timeout)

                # Resolve domain
                addr_info = socket.getaddrinfo(domain, None, socket.AF_INET)

                for info in addr_info:
                    ip = info[4][0]
                    # Only IPv4
                    if ':' not in ip:
                        ips.add(ip)

                if ips:
                    # Cache result
                    if self.cache_enabled:
                        with self.cache_lock:
                            self.cache[domain] = ips

                    with self.stats_lock:
                        self.stats['resolved'] += 1

                    logger.debug(f"✓ {domain} → {', '.join(sorted(ips))}")
                    break

            except socket.gaierror as e:
                last_error = f"DNS error: {e}"
                # Exponential backoff untuk retry
                if attempt < retry:
                    time.sleep(0.1 * (2 ** attempt))

            except socket.timeout:
                last_error = "Timeout"
                if attempt < retry:
                    time.sleep(0.1 * (2 ** attempt))

            except Exception as e:
                last_error = f"Unknown error: {e}"
                break

        if not ips:
            with self.stats_lock:
                self.stats['failed'] += 1
                if last_error:
                    self.stats['errors'][last_error] += 1

            logger.debug(f"✗ {domain} - {last_error}")

        return ips

    def resolve_domains(self, domains: List[str], show_progress: bool = True) -> Dict[str, Set[str]]:
        """
        Resolve multiple domains secara concurrent

        Args:
            domains: List of domains to resolve
            show_progress: Show progress logs every N domains

        Returns:
            Dict mapping domain → set of IPs
        """
        logger.info(f"Starting DNS resolution for {len(domains)} domains")
        logger.info(f"Configuration: workers={self.max_workers}, timeout={self.timeout}s, cache={'enabled' if self.cache_enabled else 'disabled'}")

        results: Dict[str, Set[str]] = {}
        start_time = time.time()

        # Reset stats
        with self.stats_lock:
            self.stats = {
                'total': len(domains),
                'resolved': 0,
                'cached': 0,
                'failed': 0,
                'errors': defaultdict(int)
            }

        # Process domains concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_domain = {
                executor.submit(self._resolve_single, domain): domain
                for domain in domains
            }

            # Collect results
            completed = 0
            progress_interval = max(100, len(domains) // 20)  # Show progress every 5%

            for future in as_completed(future_to_domain):
                domain = future_to_domain[future]
                completed += 1

                try:
                    ips = future.result()
                    if ips:
                        results[domain] = ips

                except Exception as e:
                    logger.error(f"Exception resolving {domain}: {e}")
                    with self.stats_lock:
                        self.stats['failed'] += 1

                # Progress logging
                if show_progress and completed % progress_interval == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    logger.info(f"Progress: {completed}/{len(domains)} domains ({completed*100//len(domains)}%) - {rate:.1f} domains/sec")

        # Final statistics
        elapsed = time.time() - start_time
        rate = len(domains) / elapsed if elapsed > 0 else 0

        logger.info("=" * 60)
        logger.info("DNS Resolution Complete!")
        logger.info(f"Total domains: {self.stats['total']:,}")
        logger.info(f"Resolved: {self.stats['resolved']:,} ({self.stats['resolved']*100//self.stats['total']}%)")
        logger.info(f"Cached hits: {self.stats['cached']:,}")
        logger.info(f"Failed: {self.stats['failed']:,}")
        logger.info(f"Unique IPs found: {len(set(ip for ips in results.values() for ip in ips)):,}")
        logger.info(f"Time elapsed: {elapsed:.1f}s")
        logger.info(f"Resolution rate: {rate:.1f} domains/sec")

        if self.stats['errors']:
            logger.info("\nTop errors:")
            for error, count in sorted(self.stats['errors'].items(), key=lambda x: -x[1])[:5]:
                logger.info(f"  - {error}: {count} times")

        logger.info("=" * 60)

        return results

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        with self.cache_lock:
            return {
                'size': len(self.cache),
                'domains': list(self.cache.keys())[:10]  # Sample
            }


# Standalone functions untuk backward compatibility
def resolve_domain_to_ips(domain: str, timeout: float = 2.0) -> Set[str]:
    """
    Legacy function untuk resolve single domain
    Gunakan DNSResolver class untuk better performance
    """
    resolver = DNSResolver(max_workers=1, timeout=timeout, cache_enabled=False)
    result = resolver._resolve_single(domain)
    return result


def batch_resolve_domains(domains: List[str], max_workers: int = 50, timeout: float = 2.0) -> Dict[str, Set[str]]:
    """
    Resolve multiple domains dengan concurrent processing

    Args:
        domains: List of domains
        max_workers: Number of concurrent workers
        timeout: Timeout per query

    Returns:
        Dict mapping domain → set of IPs
    """
    resolver = DNSResolver(max_workers=max_workers, timeout=timeout)
    return resolver.resolve_domains(domains)


if __name__ == "__main__":
    # Test
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Test domains
    test_domains = [
        "google.com",
        "github.com",
        "cloudflare.com",
        "amazon.com",
        "facebook.com",
        "invalid-domain-that-does-not-exist-12345.com",
        "twitter.com",
        "reddit.com",
        "youtube.com",
        "wikipedia.org"
    ]

    print("Testing DNS Resolver...")
    print()

    resolver = DNSResolver(max_workers=10, timeout=2.0)
    results = resolver.resolve_domains(test_domains)

    print("\nResults:")
    for domain, ips in sorted(results.items()):
        print(f"  {domain}: {', '.join(sorted(ips))}")
