#!/usr/bin/env python3
"""
Script untuk generate monthly statistics dan update README.md
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def count_entries(filepath: str) -> int:
    """Count non-comment entries in a file"""
    count = 0
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    count += 1
    return count


def get_current_stats(data_dir: Path) -> Dict[str, int]:
    """Get current statistics from all data files"""
    return {
        'blacklist': count_entries(str(data_dir / 'blacklist.txt')),
        'drop': count_entries(str(data_dir / 'drop.txt')),
        'whitelist': count_entries(str(data_dir / 'whitelist.txt')),
        'pass': count_entries(str(data_dir / 'pass.txt')),
        'hosts': count_entries(str(data_dir / 'hosts.txt')),
    }


def load_history(stats_file: Path) -> Dict:
    """Load historical statistics"""
    if stats_file.exists():
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load history: {e}")
    return {'monthly': []}


def save_history(stats_file: Path, history: Dict):
    """Save statistics history"""
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)


def update_readme(readme_file: Path, history: Dict):
    """Update README.md with statistics table"""

    # Generate statistics table
    stats_table = "## 📊 Monthly Statistics History\n\n"
    stats_table += "| Month | Blacklist | Drop (IPs) | Whitelist | Pass (IPs) | Hosts | Total |\n"
    stats_table += "|-------|-----------|------------|-----------|------------|-------|-------|\n"

    # Show last 12 months
    for entry in history['monthly'][-12:]:
        month = entry['month']
        stats = entry['stats']
        total = sum(stats.values())

        stats_table += f"| {month} | "
        stats_table += f"{stats['blacklist']:,} | "
        stats_table += f"{stats['drop']:,} | "
        stats_table += f"{stats['whitelist']:,} | "
        stats_table += f"{stats['pass']:,} | "
        stats_table += f"{stats['hosts']:,} | "
        stats_table += f"**{total:,}** |\n"

    # Read existing README
    if readme_file.exists():
        with open(readme_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find and replace statistics section
        start_marker = "## 📊 Monthly Statistics History"
        end_marker = "\n## "

        start_idx = content.find(start_marker)
        if start_idx != -1:
            # Find next section
            end_idx = content.find(end_marker, start_idx + len(start_marker))
            if end_idx != -1:
                # Replace existing table
                content = content[:start_idx] + stats_table + "\n" + content[end_idx:]
            else:
                # Append to end
                content = content[:start_idx] + stats_table
        else:
            # Append new section
            content += "\n\n" + stats_table
    else:
        # Create new README
        content = "# Pangrosan - Security Data Aggregator\n\n"
        content += stats_table

    # Write updated README
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info("README.md updated with statistics")


def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("Generate Monthly Statistics")
    logger.info("=" * 60)

    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    stats_file = project_root / "stats_history.json"
    readme_file = project_root / "README.md"

    # Get current month (YYYY-MM format)
    current_month = datetime.now().strftime("%Y-%m")

    # Get current statistics
    current_stats = get_current_stats(data_dir)
    total = sum(current_stats.values())

    logger.info(f"Current statistics for {current_month}:")
    logger.info(f"  - blacklist.txt: {current_stats['blacklist']:,} entries")
    logger.info(f"  - drop.txt: {current_stats['drop']:,} entries")
    logger.info(f"  - whitelist.txt: {current_stats['whitelist']:,} entries")
    logger.info(f"  - pass.txt: {current_stats['pass']:,} entries")
    logger.info(f"  - hosts.txt: {current_stats['hosts']:,} entries")
    logger.info(f"  - TOTAL: {total:,} entries")

    # Load history
    history = load_history(stats_file)

    # Check if we already have stats for this month
    existing_entry = None
    for entry in history['monthly']:
        if entry['month'] == current_month:
            existing_entry = entry
            break

    if existing_entry:
        # Update existing entry
        existing_entry['stats'] = current_stats
        existing_entry['updated'] = datetime.now().isoformat()
        logger.info(f"Updated statistics for {current_month}")
    else:
        # Add new entry
        history['monthly'].append({
            'month': current_month,
            'stats': current_stats,
            'updated': datetime.now().isoformat()
        })
        logger.info(f"Added new statistics for {current_month}")

    # Save history
    save_history(stats_file, history)
    logger.info(f"Statistics saved to {stats_file}")

    # Update README
    update_readme(readme_file, history)

    logger.info("\n" + "=" * 60)
    logger.info("Statistics generation complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
