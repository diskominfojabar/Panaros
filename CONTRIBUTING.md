# Panduan Kontribusi

## Menambahkan Sumber Data Baru

### 1. Identifikasi Tipe Data

Tentukan kategori sumber data Anda:
- **IP Blacklist** → output ke `data/drop.txt`
- **IP Whitelist** → output ke `data/pass.txt`
- **Domain Blacklist** → output ke `data/blacklist.txt`
- **Domain Whitelist** → output ke `data/whitelist.txt`

### 2. Analisis Format Data

Lihat format response dari API/URL sumber:

```bash
# Contoh menggunakan curl
curl -s "https://api.example.com/data" | head -20

# Atau dengan jq untuk JSON
curl -s "https://api.example.com/data" | jq '.'
```

Format umum:
- **JSON**: Gunakan `response.json()`
- **Plain Text**: Split by newline
- **CSV**: Gunakan `csv` module
- **XML**: Gunakan `xml.etree.ElementTree`
- **ZIP/Compressed**: Gunakan `zipfile` atau `gzip`

### 3. Buat Fetcher Script

Salin template:

```bash
cp scripts/fetchers/template.py scripts/fetchers/nama_baru.py
```

Implementasikan fungsi `fetch()`:

```python
import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)

def fetch(source: dict) -> Set[str]:
    """
    Deskripsi singkat tentang sumber data ini

    Args:
        source: Dictionary berisi konfigurasi

    Returns:
        Set of strings (IPs atau domains)
    """
    url = source['url']

    try:
        logger.info(f"Fetching dari {url}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Parse data sesuai format
        data = set()
        # ... implementasi parsing ...

        logger.info(f"Berhasil mengambil {len(data)} items")
        return data

    except Exception as e:
        logger.error(f"Error: {e}")
        return set()
```

### 4. Tambahkan ke Konfigurasi

Edit `config.yml`:

```yaml
sources:
  # Pilih kategori yang sesuai
  ip_blacklist:  # atau ip_whitelist, domain_blacklist, domain_whitelist
    - name: "Nama Sumber"
      url: "https://api.example.com/data"
      fetcher: "nama_baru"  # Nama file tanpa .py
      requires_api_key: false
      # Parameter custom (opsional)
      limit: 1000
      confidence_threshold: 90
```

### 5. Test Fetcher

Test secara lokal:

```bash
# Install dependencies
pip install -r requirements.txt

# Test run
python scripts/processor.py

# Cek hasil
cat data/drop.txt  # atau file lain sesuai kategori
```

### 6. Tips Debugging

#### Enable verbose logging:

Edit `scripts/processor.py`, ubah level logging:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Ubah dari INFO ke DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

#### Test fetcher secara individual:

```python
# test_fetcher.py
import sys
sys.path.insert(0, '.')

from scripts.fetchers.nama_baru import fetch

source = {
    'url': 'https://api.example.com/data',
    'name': 'Test Source'
}

result = fetch(source)
print(f"Got {len(result)} items")
for item in list(result)[:10]:  # Print 10 pertama
    print(item)
```

### 7. Checklist Sebelum PR

- [ ] Fetcher berhasil mengambil data
- [ ] Data di-save ke file yang benar
- [ ] Tidak ada duplikat
- [ ] Handle error dengan baik (network error, parsing error, dll)
- [ ] Logging informatif
- [ ] Dokumentasi di docstring lengkap
- [ ] Tambahkan example di config.yml (bisa di-comment)
- [ ] Update README.md jika perlu

### 8. Best Practices

#### Handle Rate Limiting

```python
import time

def fetch(source: dict) -> Set[str]:
    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 429:  # Too Many Requests
                if attempt < max_retries - 1:
                    logger.warning(f"Rate limited, waiting {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
            response.raise_for_status()
            # ... process ...
            break
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(retry_delay)
```

#### Validasi Data

```python
import ipaddress
import re

def is_valid_ip(ip_str: str) -> bool:
    """Validasi IP address"""
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

def is_valid_domain(domain: str) -> bool:
    """Validasi domain name"""
    pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    return bool(re.match(pattern, domain))

def fetch(source: dict) -> Set[str]:
    # ... fetch data ...

    # Filter hanya data valid
    validated = set()
    for item in data:
        if is_valid_ip(item):  # atau is_valid_domain(item)
            validated.add(item)
        else:
            logger.warning(f"Invalid data skipped: {item}")

    return validated
```

#### Handle Pagination

```python
def fetch(source: dict) -> Set[str]:
    all_data = set()
    page = 1
    max_pages = 10

    while page <= max_pages:
        params = {'page': page, 'per_page': 100}
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        if not data['results']:
            break  # No more data

        for item in data['results']:
            all_data.add(item['ip'])

        page += 1

    return all_data
```

## Menambahkan API Key Baru

### 1. Untuk Development Lokal

```bash
export NEW_API_KEY="your-key-here"
```

Atau buat file `.env`:

```bash
# .env
NEW_API_KEY=your-key-here
```

### 2. Untuk GitHub Actions

1. Repository Settings → Secrets and variables → Actions
2. New repository secret:
   - Name: `NEW_API_KEY`
   - Value: your-key-here

3. Update workflow `.github/workflows/update-data.yml`:

```yaml
- name: Run data fetcher
  env:
    ABUSEIPDB_API_KEY: ${{ secrets.ABUSEIPDB_API_KEY }}
    NEW_API_KEY: ${{ secrets.NEW_API_KEY }}  # Tambahkan ini
  run: |
    python scripts/processor.py
```

4. Update config:

```yaml
sources:
  ip_blacklist:
    - name: "New Source"
      url: "https://api.new-source.com/data"
      fetcher: "new_source"
      requires_api_key: true
      api_key_env: "NEW_API_KEY"  # Nama environment variable
```

## Testing

### Test Lokal

```bash
# Install dependencies
pip install -r requirements.txt

# Run processor
python scripts/processor.py

# Cek output
ls -lh data/
head -20 data/drop.txt
```

### Test di GitHub Actions

1. Commit dan push changes
2. Manual trigger workflow:
   - Actions tab → "Update Security Data" → "Run workflow"
3. Monitor execution dan cek logs
4. Verify output files di-commit

## Questions?

Jika ada pertanyaan atau butuh bantuan, buka issue di repository.
