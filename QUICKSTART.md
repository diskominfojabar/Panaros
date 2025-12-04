# Quick Start Guide

Panduan cepat untuk memulai menggunakan Security Data Aggregator.

## Setup dalam 5 Menit

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. (Opsional) Setup API Key

Jika ingin menggunakan AbuseIPDB:

```bash
# Dapatkan API key gratis di: https://www.abuseipdb.com/
export ABUSEIPDB_API_KEY="your-api-key-here"
```

### 3. Test Run

```bash
python scripts/processor.py
```

### 4. Lihat Hasil

```bash
ls -lh data/
cat data/drop.txt       # IP blacklist
cat data/pass.txt       # IP whitelist
cat data/blacklist.txt  # Domain blacklist
cat data/whitelist.txt  # Domain whitelist
```

## Setup GitHub Actions

### 1. Push ke GitHub

```bash
git init
git add .
git commit -m "Initial commit: Security Data Aggregator"
git branch -M main
git remote add origin https://github.com/username/repo.git
git push -u origin main
```

### 2. Tambahkan Secrets

1. Buka repository di GitHub
2. Settings → Secrets and variables → Actions
3. Klik "New repository secret"
4. Tambahkan:
   - Name: `ABUSEIPDB_API_KEY`
   - Value: API key Anda

### 3. Manual Run Pertama

1. Buka tab "Actions"
2. Pilih "Update Security Data"
3. Klik "Run workflow"
4. Tunggu sampai selesai (biasanya 1-2 menit)

### 4. Verifikasi

Cek apakah file di folder `data/` sudah ter-update.

## Menambahkan Sumber Baru (Contoh)

### Contoh: Menambahkan Spamhaus DROP List

**1. Buat fetcher baru:**

```bash
cat > scripts/fetchers/spamhaus_drop.py << 'EOF'
import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)

def fetch(source: dict) -> Set[str]:
    url = source['url']

    try:
        logger.info(f"Fetching dari Spamhaus DROP...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        ips = set()
        for line in response.text.strip().split('\n'):
            line = line.strip()
            # Skip komentar
            if line and not line.startswith(';'):
                # Format: CIDR ; details
                if ';' in line:
                    cidr = line.split(';')[0].strip()
                    ips.add(cidr)

        logger.info(f"Berhasil mengambil {len(ips)} networks dari Spamhaus")
        return ips

    except Exception as e:
        logger.error(f"Error: {e}")
        return set()
EOF
```

**2. Edit config.yml:**

```yaml
sources:
  ip_blacklist:
    # ... sumber yang sudah ada ...

    # Tambahkan ini:
    - name: "Spamhaus DROP"
      url: "https://www.spamhaus.org/drop/drop.txt"
      fetcher: "spamhaus_drop"
      requires_api_key: false
```

**3. Test:**

```bash
python scripts/processor.py
cat data/drop.txt | grep -c "^[^#]"  # Hitung jumlah IP
```

## Tips

### Melihat Log Detail

```bash
python scripts/processor.py 2>&1 | tee fetch.log
```

### Test Satu Fetcher Saja

```python
# test.py
from scripts.fetchers.cloudflare_ips import fetch

source = {
    'url': 'https://www.cloudflare.com/ips-v4',
    'name': 'Test'
}

result = fetch(source)
print(f"Got {len(result)} IPs")
for ip in list(result)[:5]:
    print(ip)
```

```bash
python test.py
```

### Mengubah Schedule Workflow

Edit `.github/workflows/update-data.yml`:

```yaml
schedule:
  # Setiap minggu (hari Minggu)
  - cron: '0 0 * * 0'

  # Atau setiap hari
  # - cron: '0 0 * * *'

  # Atau setiap 6 jam
  # - cron: '0 */6 * * *'
```

## Troubleshooting

### Problem: "Module not found"

```bash
# Pastikan struktur folder benar
ls scripts/fetchers/

# Install dependencies lagi
pip install -r requirements.txt
```

### Problem: "API key tidak ditemukan"

```bash
# Cek environment variable
echo $ABUSEIPDB_API_KEY

# Set ulang
export ABUSEIPDB_API_KEY="your-key"
```

### Problem: File kosong

- Cek log untuk error messages
- Pastikan URL masih valid (coba buka di browser)
- Cek apakah API key masih aktif

### Problem: GitHub Actions gagal

- Cek tab "Actions" untuk error log
- Pastikan secrets sudah ditambahkan
- Cek permissions: Settings → Actions → General → Workflow permissions

## Next Steps

- Baca [README.md](README.md) untuk dokumentasi lengkap
- Baca [CONTRIBUTING.md](CONTRIBUTING.md) untuk panduan development
- Tambahkan sumber data sesuai kebutuhan Anda
- Customize schedule di workflow

## Bantuan

Butuh bantuan? Buka issue di GitHub repository.
