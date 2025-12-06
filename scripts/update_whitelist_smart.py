#!/usr/bin/env python3
"""
Smart Whitelist Update Script
Adds new entries to whitelist.txt with verification and conflict detection

Features:
1. Legitimacy verification via DNS resolution
2. Conflict detection (whitelist vs blacklist)
3. Duplicate detection
4. Manual entry protection
5. Smart update (only add new entries)
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Set, Tuple, List
from datetime import datetime

# Import DNS resolver
sys.path.insert(0, str(Path(__file__).parent))
from dns_resolver import DNSResolver

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_existing_whitelist(filepath: str) -> Dict[str, str]:
    """
    Load existing whitelist.txt entries
    Returns: {domain: source}
    """
    entries = {}
    if not os.path.exists(filepath):
        return entries

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if ' # ' in line:
                        domain, source = line.split(' # ', 1)
                        entries[domain.strip()] = source.strip()
                    else:
                        # Entry without source marker = manual entry
                        entries[line] = "Manual Entry"
        logger.info(f"Loaded {len(entries)} existing whitelist entries")
    except Exception as e:
        logger.error(f"Error loading whitelist: {e}")

    return entries


def load_existing_blacklist(filepath: str) -> Set[str]:
    """
    Load existing blacklist.txt entries
    Returns: Set of blacklisted domains
    """
    entries = set()
    if not os.path.exists(filepath):
        return entries

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if ' # ' in line:
                        domain = line.split(' # ', 1)[0].strip()
                        entries.add(domain)
                    else:
                        entries.add(line)
        logger.info(f"Loaded {len(entries)} existing blacklist entries")
    except Exception as e:
        logger.error(f"Error loading blacklist: {e}")

    return entries


def parse_simple_yaml(yaml_file: str) -> Dict[str, List[str]]:
    """
    Simple YAML parser for repository data (no external dependency)
    Returns: {source_name: [domain1, domain2, ...]}
    """
    repositories = {}
    current_section = None
    current_subsection = None

    with open(yaml_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip()

            # Skip comments and empty lines
            if not line or line.strip().startswith('#'):
                continue

            # Count indentation
            indent = len(line) - len(line.lstrip())

            # Level 0: Section (distro name)
            if indent == 0 and ':' in line:
                current_section = line.split(':')[0].strip()
                current_subsection = None

            # Level 2: Subsection (official, regional_mirrors, etc)
            elif indent == 2 and ':' in line and current_section:
                current_subsection = line.split(':')[0].strip()

                # Create repository key
                if current_subsection == 'official':
                    repo_key = f"{current_section.title()} Official"
                elif current_subsection == 'regional_mirrors':
                    repo_key = f"{current_section.title()} Mirrors"
                else:
                    repo_key = current_section.title()

                if repo_key not in repositories:
                    repositories[repo_key] = []

            # Level 4: Domain entry (- domain)
            elif indent == 4 and line.strip().startswith('- '):
                domain = line.strip()[2:].strip()

                # Determine which repository to add to
                if current_subsection and current_section:
                    if current_subsection == 'official':
                        repo_key = f"{current_section.title()} Official"
                    elif current_subsection == 'regional_mirrors':
                        repo_key = f"{current_section.title()} Mirrors"
                    else:
                        repo_key = current_section.title()

                    if repo_key not in repositories:
                        repositories[repo_key] = []
                    repositories[repo_key].append(domain)

    return repositories


def load_repository_data(yaml_file: str) -> Dict[str, List[str]]:
    """
    Load repository data from YAML file
    Returns: {source_name: [domain1, domain2, ...]}
    """
    return parse_simple_yaml(yaml_file)


def verify_domain_legitimacy(domain: str, resolver: DNSResolver) -> Tuple[bool, List[str]]:
    """
    Verify domain legitimacy via DNS resolution
    Returns: (is_legitimate, [resolved_ips])
    """
    # Remove path components if present
    domain_only = domain.split('/')[0]

    try:
        resolved = resolver.resolve_domains([domain_only], show_progress=False)
        ips = resolved.get(domain_only, [])

        if ips:
            # Check if resolved to valid public IPs (not bogon)
            valid_ips = []
            for ip in ips:
                # Simple check: not 127.x.x.x, not 0.0.0.0, not 10.x.x.x, etc.
                if not (ip.startswith('127.') or ip.startswith('0.') or
                        ip.startswith('10.') or ip.startswith('192.168.') or
                        ip.startswith('172.16.') or ip.startswith('172.17.') or
                        ip.startswith('172.18.') or ip.startswith('172.19.') or
                        ip.startswith('172.2') or ip.startswith('172.30.') or
                        ip.startswith('172.31.')):
                    valid_ips.append(ip)

            if valid_ips:
                logger.debug(f"✓ {domain_only} → {valid_ips[:3]}")
                return True, valid_ips

        logger.warning(f"✗ {domain_only} → DNS resolution failed or returned bogon IPs")
        return False, []

    except Exception as e:
        logger.warning(f"✗ {domain_only} → Verification error: {e}")
        return False, []


def detect_conflicts(
    new_entries: Dict[str, str],
    existing_whitelist: Dict[str, str],
    existing_blacklist: Set[str]
) -> Tuple[Dict[str, str], List[str]]:
    """
    Detect conflicts and filter new entries

    Returns: (safe_entries, conflict_reports)
    """
    safe_entries = {}
    conflicts = []

    for domain, source in new_entries.items():
        domain_base = domain.split('/')[0]  # Remove path component

        # Check 1: Already in whitelist?
        if domain in existing_whitelist:
            logger.debug(f"⊙ {domain} already in whitelist (source: {existing_whitelist[domain]})")
            continue

        # Check 2: Conflict with blacklist? (CRITICAL!)
        if domain_base in existing_blacklist or domain in existing_blacklist:
            conflict_msg = f"⚠️  CONFLICT: {domain} (NEW: {source}) vs BLACKLIST"
            logger.warning(conflict_msg)
            conflicts.append(conflict_msg)
            # Don't add conflicting entries - needs manual review
            continue

        # Check 3: Wildcard pattern already covers this?
        wildcard_pattern = f"*.{'.'.join(domain_base.split('.')[1:])}"
        if wildcard_pattern in existing_whitelist:
            logger.debug(f"⊙ {domain} already covered by {wildcard_pattern}")
            continue

        # Safe to add
        safe_entries[domain] = source

    return safe_entries, conflicts


def update_whitelist_file(
    filepath: str,
    new_entries: Dict[str, str],
    existing_entries: Dict[str, str]
):
    """
    Update whitelist.txt with new entries while preserving existing ones
    """
    # Merge entries (existing + new)
    all_entries = {**existing_entries, **new_entries}

    # Count original entries (to preserve header count)
    total_entries = len(all_entries)

    # Write to file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"# Whitelist Domains - Trusted Sites & Infrastructure\n")
            f.write(f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total entries: {total_entries}\n")
            f.write(f"# Format: <domain> # <source>\n")
            f.write(f"#\n")
            f.write(f"# PRIORITAS: Level 4 - Domain Whitelist\n")
            f.write(f"# Domain dengan marker akan di-update otomatis\n")
            f.write(f"# Domain manual (tanpa marker) tidak akan dihapus otomatis\n")
            f.write(f"#\n\n")

            # Group entries by source
            grouped = {}
            for domain, source in sorted(all_entries.items()):
                if source not in grouped:
                    grouped[source] = []
                grouped[source].append(domain)

            # Write entries grouped by source
            for source in sorted(grouped.keys()):
                if len(grouped[source]) > 0:
                    f.write(f"# {source}\n")
                    for domain in sorted(grouped[source]):
                        f.write(f"{domain} # {source}\n")
                    f.write(f"\n")

        logger.info(f"✓ Updated {filepath}")
        logger.info(f"  - Total entries: {total_entries}")
        logger.info(f"  - New entries added: {len(new_entries)}")

    except Exception as e:
        logger.error(f"Error writing whitelist: {e}")
        raise


def main():
    """Main function"""
    logger.info("=" * 80)
    logger.info("Smart Whitelist Update - Linux/Unix Repository Protection")
    logger.info("=" * 80)

    project_root = Path(__file__).parent.parent
    whitelist_file = project_root / "data" / "whitelist.txt"
    blacklist_file = project_root / "data" / "blacklist.txt"
    repo_data_file = Path(__file__).parent / "data" / "linux_repositories.yml"

    # Step 1: Load existing whitelist
    logger.info("\nStep 1: Loading existing whitelist...")
    existing_whitelist = load_existing_whitelist(str(whitelist_file))

    # Step 2: Load existing blacklist
    logger.info("\nStep 2: Loading existing blacklist...")
    existing_blacklist = load_existing_blacklist(str(blacklist_file))

    # Step 3: Load repository data
    logger.info("\nStep 3: Loading repository data...")
    if not repo_data_file.exists():
        logger.error(f"Repository data file not found: {repo_data_file}")
        return

    repo_data = load_repository_data(str(repo_data_file))
    logger.info(f"Loaded {len(repo_data)} repository sources")

    # Step 4: Collect and verify new entries
    logger.info("\nStep 4: Verifying repository domains...")
    resolver = DNSResolver(max_workers=50, timeout=5.0, cache_enabled=True)

    verified_entries = {}
    verification_stats = {"total": 0, "verified": 0, "failed": 0}

    for source_name, domains in repo_data.items():
        logger.info(f"\n  Verifying {source_name}...")
        for domain in domains:
            verification_stats["total"] += 1

            # Verify legitimacy
            is_legit, ips = verify_domain_legitimacy(domain, resolver)

            if is_legit:
                verified_entries[domain] = source_name
                verification_stats["verified"] += 1
            else:
                verification_stats["failed"] += 1

    logger.info(f"\nVerification Statistics:")
    logger.info(f"  - Total domains: {verification_stats['total']}")
    logger.info(f"  - Verified: {verification_stats['verified']} ✓")
    logger.info(f"  - Failed: {verification_stats['failed']} ✗")

    # Step 5: Detect conflicts
    logger.info("\nStep 5: Detecting conflicts...")
    safe_entries, conflicts = detect_conflicts(
        verified_entries,
        existing_whitelist,
        existing_blacklist
    )

    logger.info(f"  - New entries to add: {len(safe_entries)}")
    logger.info(f"  - Conflicts detected: {len(conflicts)}")

    if conflicts:
        logger.warning("\n⚠️  CONFLICTS DETECTED (need manual review):")
        for conflict in conflicts:
            logger.warning(f"  {conflict}")

    # Step 6: Update whitelist file
    if safe_entries:
        logger.info("\nStep 6: Updating whitelist.txt...")
        update_whitelist_file(
            str(whitelist_file),
            safe_entries,
            existing_whitelist
        )
    else:
        logger.info("\nStep 6: No new entries to add (all already in whitelist)")

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("Summary:")
    logger.info(f"  - Existing whitelist entries: {len(existing_whitelist)}")
    logger.info(f"  - Verified repository domains: {verification_stats['verified']}")
    logger.info(f"  - New entries added: {len(safe_entries)}")
    logger.info(f"  - Conflicts detected: {len(conflicts)}")
    logger.info(f"  - Total whitelist entries: {len(existing_whitelist) + len(safe_entries)}")
    logger.info("=" * 80)
    logger.info("✅ Smart whitelist update complete!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
