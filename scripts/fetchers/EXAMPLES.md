# Contoh Fetcher untuk Berbagai Format Data

## 1. Plain Text - Spamhaus DROP

```python
# scripts/fetchers/spamhaus_drop.py
import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)

def fetch(source: dict) -> Set[str]:
    """Fetch IP networks dari Spamhaus DROP list"""
    url = source['url']

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        ips = set()
        for line in response.text.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith(';'):
                # Format: CIDR ; details
                cidr = line.split(';')[0].strip()
                ips.add(cidr)

        logger.info(f"Got {len(ips)} networks from Spamhaus")
        return ips
    except Exception as e:
        logger.error(f"Error: {e}")
        return set()
```

Config:
```yaml
sources:
  ip_blacklist:
    - name: "Spamhaus DROP"
      url: "https://www.spamhaus.org/drop/drop.txt"
      fetcher: "spamhaus_drop"
      requires_api_key: false
```

## 2. JSON API - PhishTank

```python
# scripts/fetchers/phishtank_domains.py
import requests
import logging
from typing import Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def fetch(source: dict) -> Set[str]:
    """Fetch phishing domains dari PhishTank"""
    url = source['url']

    try:
        headers = {'User-Agent': 'phishtank/security-aggregator'}
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()

        data = response.json()
        domains = set()

        for entry in data:
            phish_url = entry.get('url', '')
            if phish_url:
                parsed = urlparse(phish_url)
                if parsed.netloc:
                    domains.add(parsed.netloc.split(':')[0])

        logger.info(f"Got {len(domains)} domains from PhishTank")
        return domains
    except Exception as e:
        logger.error(f"Error: {e}")
        return set()
```

Config:
```yaml
sources:
  domain_blacklist:
    - name: "PhishTank"
      url: "http://data.phishtank.com/data/online-valid.json"
      fetcher: "phishtank_domains"
      requires_api_key: false
```

## 3. JSON API dengan Pagination - AlienVault OTX

```python
# scripts/fetchers/alienvault_ips.py
import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)

def fetch(source: dict) -> Set[str]:
    """Fetch malicious IPs dari AlienVault OTX"""
    api_key = source.get('api_key')
    if not api_key:
        logger.error("AlienVault API key required")
        return set()

    base_url = "https://otx.alienvault.com/api/v1/pulses/subscribed"
    headers = {'X-OTX-API-KEY': api_key}

    ips = set()
    page = 1
    max_pages = 5

    try:
        while page <= max_pages:
            params = {'page': page, 'limit': 50}
            response = requests.get(base_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get('results', [])

            if not results:
                break

            for pulse in results:
                indicators = pulse.get('indicators', [])
                for indicator in indicators:
                    if indicator.get('type') == 'IPv4':
                        ips.add(indicator.get('indicator'))

            if not data.get('next'):
                break

            page += 1

        logger.info(f"Got {len(ips)} IPs from AlienVault OTX")
        return ips
    except Exception as e:
        logger.error(f"Error: {e}")
        return set()
```

Config:
```yaml
sources:
  ip_blacklist:
    - name: "AlienVault OTX"
      url: "https://otx.alienvault.com/api/v1/pulses/subscribed"
      fetcher: "alienvault_ips"
      requires_api_key: true
      api_key_env: "ALIENVAULT_API_KEY"
```

## 4. CSV - Cisco Umbrella Top 1M

```python
# scripts/fetchers/cisco_umbrella.py
import requests
import logging
import zipfile
import io
import csv
from typing import Set

logger = logging.getLogger(__name__)

def fetch(source: dict) -> Set[str]:
    """Fetch top domains dari Cisco Umbrella"""
    url = source['url']
    limit = source.get('limit', 10000)

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        domains = set()

        # Extract ZIP
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            csv_file = z.namelist()[0]
            with z.open(csv_file) as f:
                reader = csv.reader(io.TextIOWrapper(f))
                count = 0
                for row in reader:
                    if count >= limit:
                        break
                    if len(row) >= 2:
                        rank, domain = row[0], row[1]
                        domains.add(domain)
                        count += 1

        logger.info(f"Got {len(domains)} domains from Cisco Umbrella")
        return domains
    except Exception as e:
        logger.error(f"Error: {e}")
        return set()
```

Config:
```yaml
sources:
  domain_whitelist:
    - name: "Cisco Umbrella Top 1M"
      url: "http://s3-us-west-1.amazonaws.com/umbrella-static/top-1m.csv.zip"
      fetcher: "cisco_umbrella"
      requires_api_key: false
      limit: 10000
```

## 5. API dengan Authentication - VirusTotal

```python
# scripts/fetchers/virustotal_domains.py
import requests
import logging
import time
from typing import Set

logger = logging.getLogger(__name__)

def fetch(source: dict) -> Set[str]:
    """Fetch malicious domains dari VirusTotal"""
    api_key = source.get('api_key')
    if not api_key:
        logger.error("VirusTotal API key required")
        return set()

    base_url = "https://www.virustotal.com/api/v3/intelligence/search"
    headers = {'x-apikey': api_key}

    domains = set()

    try:
        # Query untuk domain berbahaya yang terdeteksi baru-baru ini
        params = {
            'query': 'type:domain positives:5+',
            'limit': 100
        }

        response = requests.get(base_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        for item in data.get('data', []):
            domain = item.get('attributes', {}).get('last_dns_records_domain')
            if domain:
                domains.add(domain)

        logger.info(f"Got {len(domains)} domains from VirusTotal")
        return domains

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning("Rate limit exceeded")
        else:
            logger.error(f"HTTP Error: {e}")
        return set()
    except Exception as e:
        logger.error(f"Error: {e}")
        return set()
```

Config:
```yaml
sources:
  domain_blacklist:
    - name: "VirusTotal"
      url: "https://www.virustotal.com/api/v3/intelligence/search"
      fetcher: "virustotal_domains"
      requires_api_key: true
      api_key_env: "VIRUSTOTAL_API_KEY"
```

## 6. GitHub Repository - Firehol Blocklists

```python
# scripts/fetchers/firehol_level1.py
import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)

def fetch(source: dict) -> Set[str]:
    """Fetch IPs dari FireHOL Level1 blocklist"""
    url = "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        ips = set()
        for line in response.text.strip().split('\n'):
            line = line.strip()
            # Skip komentar dan baris kosong
            if line and not line.startswith('#'):
                ips.add(line)

        logger.info(f"Got {len(ips)} IPs from FireHOL Level1")
        return ips
    except Exception as e:
        logger.error(f"Error: {e}")
        return set()
```

Config:
```yaml
sources:
  ip_blacklist:
    - name: "FireHOL Level1"
      url: "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset"
      fetcher: "firehol_level1"
      requires_api_key: false
```

## 7. Google Safe Browsing API

```python
# scripts/fetchers/google_safebrowsing.py
import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)

def fetch(source: dict) -> Set[str]:
    """Fetch threat lists dari Google Safe Browsing"""
    api_key = source.get('api_key')
    if not api_key:
        logger.error("Google API key required")
        return set()

    url = f"https://safebrowsing.googleapis.com/v4/threatListUpdates:fetch?key={api_key}"

    payload = {
        "client": {
            "clientId": "security-aggregator",
            "clientVersion": "1.0"
        },
        "listUpdateRequests": [{
            "threatType": "MALWARE",
            "platformType": "ANY_PLATFORM",
            "threatEntryType": "URL",
            "state": "",
            "constraints": {
                "maxUpdateEntries": 1000
            }
        }]
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        domains = set()

        # Parse response dan extract domains
        # Note: Implementasi tergantung format response API
        # Ini hanya contoh struktur

        logger.info(f"Got {len(domains)} domains from Google Safe Browsing")
        return domains
    except Exception as e:
        logger.error(f"Error: {e}")
        return set()
```

## Tips Umum

### Retry Logic

```python
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def get_session_with_retry():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session
```

### Rate Limiting

```python
import time

def fetch(source: dict) -> Set[str]:
    rate_limit_delay = source.get('rate_limit_delay', 1)  # seconds

    # Fetch data...

    time.sleep(rate_limit_delay)  # Respect rate limits
```

### Data Validation

```python
import ipaddress
import re

def is_valid_ip(ip_str: str) -> bool:
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

def is_valid_domain(domain: str) -> bool:
    pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    return bool(re.match(pattern, domain))
```
