"""
TEMPLATE Fetcher - Gunakan ini sebagai template untuk membuat fetcher baru

Salin file ini dan sesuaikan dengan format data dari sumber Anda.
"""

import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)


def fetch(source: dict) -> Set[str]:
    """
    Fetch data dari sumber

    Args:
        source: Dictionary berisi konfigurasi sumber
            - url: URL sumber data
            - api_key: (optional) API key jika diperlukan
            - (tambahkan parameter lain sesuai kebutuhan)

    Returns:
        Set of strings (IP addresses atau domains)
    """
    url = source['url']

    try:
        logger.info(f"Fetching dari {url}...")

        # Contoh untuk API dengan authentication
        headers = {}
        if 'api_key' in source:
            headers['Authorization'] = f"Bearer {source['api_key']}"
            # atau
            # headers['X-API-Key'] = source['api_key']

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Parse response
        data = set()

        # OPTION 1: JSON response
        # json_data = response.json()
        # for item in json_data:
        #     data.add(item['field_name'])

        # OPTION 2: Plain text (satu item per baris)
        # for line in response.text.strip().split('\n'):
        #     line = line.strip()
        #     if line and not line.startswith('#'):
        #         data.add(line)

        # OPTION 3: CSV
        # import csv
        # import io
        # reader = csv.DictReader(io.StringIO(response.text))
        # for row in reader:
        #     data.add(row['column_name'])

        # OPTION 4: XML
        # import xml.etree.ElementTree as ET
        # root = ET.fromstring(response.text)
        # for element in root.findall('.//item'):
        #     data.add(element.text)

        logger.info(f"Berhasil mengambil {len(data)} items")
        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error saat parsing data: {e}")
        import traceback
        traceback.print_exc()
        return set()
