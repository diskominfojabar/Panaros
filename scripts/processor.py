#!/usr/bin/env python3
"""
Main processor untuk mengumpulkan data dari berbagai sumber dan menyimpannya
ke file yang sesuai.
"""

import os
import sys
import yaml
import importlib
import logging
from pathlib import Path
from typing import Set, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataProcessor:
    def __init__(self, config_path: str = "config.yml"):
        self.config_path = config_path
        self.config = self.load_config()
        self.fetchers_dir = Path(__file__).parent / "fetchers"

    def load_config(self) -> dict:
        """Load konfigurasi dari file YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"Konfigurasi berhasil dimuat dari {self.config_path}")
                return config
        except Exception as e:
            logger.error(f"Gagal memuat konfigurasi: {e}")
            sys.exit(1)

    def load_fetcher(self, fetcher_name: str):
        """Dinamis load fetcher module berdasarkan nama"""
        try:
            # Tambahkan current directory ke Python path
            import sys
            current_dir = Path(__file__).parent.parent
            if str(current_dir) not in sys.path:
                sys.path.insert(0, str(current_dir))

            module_path = f"scripts.fetchers.{fetcher_name}"
            module = importlib.import_module(module_path)
            return module.fetch
        except Exception as e:
            logger.error(f"Gagal memuat fetcher '{fetcher_name}': {e}")
            return None

    def read_existing_data(self, filepath: str) -> dict:
        """
        Baca data yang sudah ada dari file
        Returns dict dengan format: {entry: source_name}
        """
        data = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Parse line dengan format: "entry # Source"
                            if ' # ' in line:
                                parts = line.split(' # ', 1)
                                entry = parts[0].strip()
                                source = parts[1].strip()
                                data[entry] = source
                            else:
                                # Backward compatibility: line tanpa source comment
                                data[line] = "Unknown Source"
                logger.info(f"Membaca {len(data)} entri dari {filepath}")
            except Exception as e:
                logger.warning(f"Gagal membaca file {filepath}: {e}")
        return data

    def remove_whitelisted_domains(self, blacklist_domains: dict, whitelist_path: str) -> dict:
        """
        Hapus domain dari blacklist jika ada di whitelist
        Whitelist diprioritaskan untuk mencegah false positive

        Args:
            blacklist_domains: Dict of domain blacklist {entry: source}
            whitelist_path: Path ke file whitelist.txt

        Returns:
            Dict of filtered blacklist domains
        """
        # Baca whitelist
        whitelist = self.read_existing_data(whitelist_path)

        if not whitelist:
            logger.info("Whitelist kosong, tidak ada domain yang perlu difilter")
            return blacklist_domains

        # Konversi whitelist wildcards untuk matching
        whitelist_patterns = set()
        whitelist_exact = set()

        for entry in whitelist.keys():
            if '*' in entry:
                # Wildcard pattern
                whitelist_patterns.add(entry)
            else:
                # Exact domain
                whitelist_exact.add(entry)

        # Filter blacklist
        filtered = {}
        removed_count = 0

        for domain, source in blacklist_domains.items():
            should_remove = False

            # Check exact match
            if domain in whitelist_exact:
                should_remove = True
                logger.debug(f"Domain {domain} ada di whitelist (exact match), dihapus dari blacklist")

            # Check wildcard patterns
            if not should_remove:
                for pattern in whitelist_patterns:
                    # Simple wildcard matching
                    # *.github.com matches: api.github.com, github.com, etc.
                    pattern_regex = pattern.replace('.', r'\.').replace('*', '.*')
                    import re
                    if re.match(f"^{pattern_regex}$", domain):
                        should_remove = True
                        logger.debug(f"Domain {domain} cocok dengan whitelist pattern {pattern}, dihapus dari blacklist")
                        break

            if not should_remove:
                filtered[domain] = source
            else:
                removed_count += 1

        if removed_count > 0:
            logger.info(f"Menghapus {removed_count} domain dari blacklist karena ada di whitelist")

        return filtered

    def is_ipv6(self, ip: str) -> bool:
        """
        Check if IP address is IPv6 (contains colon)

        Args:
            ip: IP address string

        Returns:
            True if IPv6, False if IPv4
        """
        return ':' in ip

    def add_ip_prefix(self, ip: str) -> str:
        """
        Add appropriate CIDR prefix based on IP version
        - IPv4: /32 for individual IPs
        - IPv6: /128 for individual IPs

        Args:
            ip: IP address (may already have prefix)

        Returns:
            IP address with appropriate prefix
        """
        if '/' in ip:
            return ip  # Already has prefix

        return f"{ip}/128" if self.is_ipv6(ip) else f"{ip}/32"

    def ip_sort_key(self, ip_or_cidr: str):
        """
        Generate sort key untuk IP address atau CIDR (numerical sorting)
        Supports both IPv4 and IPv6

        Examples:
            IPv4:
                9.255.255.255 → (4, 9, 255, 255, 255, 32)
                10.0.0.0/24 → (4, 10, 0, 0, 0, 24)
            IPv6:
                2001:4860::/32 → (6, 0x2001, 0x4860, 0, 0, 0, 0, 0, 0, 32)
        """
        try:
            # Split IP and CIDR
            if '/' in ip_or_cidr:
                ip_part, cidr_part = ip_or_cidr.split('/')
                cidr = int(cidr_part)
            else:
                ip_part = ip_or_cidr
                # Detect default CIDR based on IP version
                cidr = 128 if self.is_ipv6(ip_part) else 32

            # IPv6 sorting
            if self.is_ipv6(ip_part):
                # Expand IPv6 to full form and parse segments
                # Split by colons and convert hex to int
                segments = ip_part.split(':')
                # Handle :: abbreviation by padding with zeros
                if '' in segments:
                    idx = segments.index('')
                    missing = 8 - len([s for s in segments if s])
                    segments = segments[:idx] + ['0'] * missing + segments[idx+1:]

                # Convert hex segments to integers, pad to 8 segments
                int_segments = []
                for seg in segments:
                    if seg:
                        int_segments.append(int(seg, 16))
                    else:
                        int_segments.append(0)

                # Pad to 8 segments if needed
                while len(int_segments) < 8:
                    int_segments.append(0)

                # Return tuple: (6, segment1, segment2, ..., segment8, cidr)
                return tuple([6] + int_segments[:8] + [cidr])

            # IPv4 sorting
            else:
                # Parse octets
                octets = tuple(int(octet) for octet in ip_part.split('.'))
                # Return tuple: (4, octet1, octet2, octet3, octet4, cidr)
                return tuple([4] + list(octets) + [cidr])
        except:
            # Fallback ke string sorting jika parsing gagal
            # Put errors at the end
            return tuple([9] + [0] * 8 + [0])

    def write_data(self, filepath: str, data: dict, mode: str = "append", category: str = ""):
        """
        Tulis data ke file dengan source comments

        Args:
            filepath: Path ke output file
            data: Dict dengan format {entry: source_name}
            mode: "append" atau "replace"
            category: Kategori data (untuk special processing)
        """
        # Buat direktori jika belum ada
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        if mode == "append":
            # Gabungkan dengan data yang sudah ada
            existing_data = self.read_existing_data(filepath)
            # Merge: data baru override data lama jika entry sama
            existing_data.update(data)
            data = existing_data

        # Proses khusus untuk domain blacklist
        if category == "domain_blacklist":
            # Cross-check dengan whitelist (prioritas whitelist)
            output_config = self.config.get('output', {})
            whitelist_path = output_config.get('domain_whitelist', 'data/whitelist.txt')

            original_count = len(data)
            data = self.remove_whitelisted_domains(data, whitelist_path)
            removed_count = original_count - len(data)

            if removed_count > 0:
                logger.info(f"Cross-check whitelist: {removed_count} domain dihapus dari blacklist")

        # Add appropriate CIDR prefix untuk IP individual (specific categories)
        # IPv4 gets /32, IPv6 gets /128
        if category in ['ip_blacklist_specific', 'ip_whitelist_specific']:
            processed_data = {}
            ipv4_count = 0
            ipv6_count = 0

            for entry, source in data.items():
                # Add appropriate prefix based on IP version
                prefixed_entry = self.add_ip_prefix(entry)
                processed_data[prefixed_entry] = source

                # Count by version
                if self.is_ipv6(entry):
                    ipv6_count += 1
                else:
                    ipv4_count += 1

            data = processed_data
            logger.info(f"Added CIDR prefix: {ipv4_count} IPv4 (/32), {ipv6_count} IPv6 (/128)")

        # Sort data by entry
        if self.config['settings'].get('sort_output', True):
            # Numerical sorting untuk IP categories
            if category in ['ip_blacklist_specific', 'ip_blacklist_segment',
                           'ip_whitelist_specific', 'ip_whitelist_segment']:
                sorted_items = sorted(data.items(), key=lambda x: self.ip_sort_key(x[0]))
            else:
                # Alphabetical sorting untuk domains
                sorted_items = sorted(data.items(), key=lambda x: x[0])
        else:
            sorted_items = list(data.items())

        # Tulis ke file dengan source comments
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Last updated: {self.get_timestamp()}\n")
                f.write(f"# Total entries: {len(sorted_items)}\n")
                f.write(f"# Format: <entry> # <source>\n")
                f.write("#\n")

                for entry, source in sorted_items:
                    f.write(f"{entry} # {source}\n")

            logger.info(f"Berhasil menulis {len(sorted_items)} entri ke {filepath}")
        except Exception as e:
            logger.error(f"Gagal menulis ke file {filepath}: {e}")

    def get_timestamp(self) -> str:
        """Dapatkan timestamp saat ini"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

    def process_sources(self, category: str, output_file: str):
        """Process semua sumber dalam kategori tertentu"""
        sources = self.config['sources'].get(category, [])
        if not sources:
            logger.warning(f"Tidak ada sumber untuk kategori '{category}'")
            return

        logger.info(f"\n{'='*60}")
        logger.info(f"Memproses kategori: {category}")
        logger.info(f"Output file: {output_file}")
        logger.info(f"{'='*60}")

        # Dictionary untuk menyimpan data dengan source info: {entry: source_name}
        all_data = {}

        for source in sources:
            name = source.get('name')
            url = source.get('url')
            fetcher_name = source.get('fetcher')
            requires_api_key = source.get('requires_api_key', False)

            logger.info(f"\nMemproses sumber: {name}")
            logger.info(f"URL: {url}")
            logger.info(f"Fetcher: {fetcher_name}")

            # Check API key jika diperlukan
            if requires_api_key:
                api_key_env = source.get('api_key_env')
                api_key = os.getenv(api_key_env)
                if not api_key:
                    logger.warning(f"API key tidak ditemukan untuk {name} (env: {api_key_env}). Skipping...")
                    continue
                source['api_key'] = api_key

            # Load dan jalankan fetcher
            fetcher = self.load_fetcher(fetcher_name)
            if fetcher:
                try:
                    data = fetcher(source)
                    if data:
                        logger.info(f"Berhasil mengambil {len(data)} entri dari {name}")
                        # Simpan data dengan source info
                        for entry in data:
                            all_data[entry] = name
                    else:
                        logger.warning(f"Tidak ada data dari {name}")
                except Exception as e:
                    logger.error(f"Error saat fetching dari {name}: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                logger.error(f"Fetcher '{fetcher_name}' tidak ditemukan untuk {name}")

        # Tulis semua data ke file
        if all_data:
            mode = self.config['settings'].get('mode', 'append')
            self.write_data(output_file, all_data, mode, category)
        else:
            logger.warning(f"Tidak ada data yang berhasil dikumpulkan untuk kategori {category}")

    def run(self):
        """Jalankan semua proses fetching"""
        logger.info("=" * 60)
        logger.info("Memulai Data Fetching Process")
        logger.info("=" * 60)

        output_config = self.config.get('output', {})

        # Process setiap kategori dengan urutan yang benar
        categories = [
            ('ip_blacklist_specific', output_config.get('ip_blacklist_specific', 'data/blacklist-specific.txt')),
            ('ip_blacklist_segment', output_config.get('ip_blacklist_segment', 'data/drop.txt')),
            ('ip_whitelist_specific', output_config.get('ip_whitelist_specific', 'data/whitelist-specific.txt')),
            ('ip_whitelist_segment', output_config.get('ip_whitelist_segment', 'data/pass.txt')),
            ('domain_whitelist', output_config.get('domain_whitelist', 'data/whitelist.txt')),
            ('domain_blacklist', output_config.get('domain_blacklist', 'data/blacklist.txt'))
        ]

        for category, output_file in categories:
            try:
                self.process_sources(category, output_file)
            except Exception as e:
                logger.error(f"Error saat memproses kategori {category}: {e}")
                import traceback
                traceback.print_exc()

        logger.info("\n" + "=" * 60)
        logger.info("Proses selesai!")
        logger.info("=" * 60)


if __name__ == "__main__":
    processor = DataProcessor()
    processor.run()
