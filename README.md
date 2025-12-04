# Security Data Aggregator

Sistem otomatis untuk mengumpulkan dan memperbarui data keamanan (IP blacklist/whitelist, domain blacklist/whitelist) dari berbagai sumber upstream.

## Fitur

- ✅ **Single Workflow**: Satu workflow GitHub Actions untuk semua sumber data
- ✅ **Modular**: Setiap sumber data memiliki fetcher terpisah
- ✅ **Konfigurasi Mudah**: Tambahkan sumber baru hanya dengan mengedit `config.yml`
- ✅ **Append Mode**: Data baru ditambahkan tanpa menghapus data lama
- ✅ **Deduplikasi**: Otomatis menghapus duplikat
- ✅ **Scheduled**: Berjalan otomatis setiap bulan
- ✅ **Manual Trigger**: Bisa dijalankan manual kapan saja

## Struktur File

```
.
├── .github/
│   └── workflows/
│       └── update-data.yml          # GitHub Actions workflow
├── scripts/
│   ├── processor.py                 # Main orchestrator
│   └── fetchers/
│       ├── __init__.py
│       ├── abuseipdb_ip.py         # Fetcher untuk AbuseIPDB IPs
│       ├── cloudflare_ips.py       # Fetcher untuk Cloudflare IPs
│       ├── tranco_domains.py       # Fetcher untuk Tranco domains
│       ├── urlhaus_domains.py      # Fetcher untuk URLhaus domains
│       └── template.py             # Template untuk fetcher baru
├── data/
│   ├── drop.txt                    # IP Blacklist
│   ├── pass.txt                    # IP Whitelist
│   ├── blacklist.txt               # Domain Blacklist
│   └── whitelist.txt               # Domain Whitelist
├── config.yml                      # Konfigurasi sumber data
├── requirements.txt                # Python dependencies
└── README.md                       # Dokumentasi ini
```

## Output Files

| File | Deskripsi |
|------|-----------|
| `data/drop.txt` | Daftar IP yang diblokir (blacklist) |
| `data/pass.txt` | Daftar IP yang diizinkan (whitelist) |
| `data/blacklist.txt` | Daftar domain yang diblokir (blacklist) |
| `data/whitelist.txt` | Daftar domain yang dipercaya (whitelist) |

## Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd Pangrosan
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Konfigurasi API Keys

Jika Anda menggunakan sumber yang memerlukan API key (seperti AbuseIPDB):

**Untuk local development:**
```bash
export ABUSEIPDB_API_KEY="your-api-key-here"
```

**Untuk GitHub Actions:**
1. Buka repository Settings → Secrets and variables → Actions
2. Tambahkan secret baru:
   - Name: `ABUSEIPDB_API_KEY`
   - Value: API key Anda

### 4. Jalankan Manual (Opsional)

```bash
python scripts/processor.py
```

## Cara Menambahkan Sumber Data Baru

### Langkah 1: Buat Fetcher Script

Salin template dan sesuaikan dengan format data sumber Anda:

```bash
cp scripts/fetchers/template.py scripts/fetchers/nama_sumber_baru.py
```

Edit file tersebut dan implementasikan fungsi `fetch()`:

```python
def fetch(source: dict) -> Set[str]:
    url = source['url']
    # Implementasi fetching sesuai format data
    # Return set of strings (IP atau domain)
    return data_set
```

### Langkah 2: Tambahkan ke config.yml

Edit `config.yml` dan tambahkan sumber baru di kategori yang sesuai:

```yaml
sources:
  ip_blacklist:
    - name: "Nama Sumber Baru"
      url: "https://example.com/api/blacklist"
      fetcher: "nama_sumber_baru"  # Nama file tanpa .py
      requires_api_key: false       # true jika perlu API key
      # parameter custom lainnya sesuai kebutuhan
```

### Langkah 3: Test

```bash
python scripts/processor.py
```

Cek apakah data berhasil ditambahkan ke file output yang sesuai.

## Contoh Fetcher

### Contoh 1: Plain Text (satu item per baris)

```python
def fetch(source: dict) -> Set[str]:
    url = source['url']
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = set()
    for line in response.text.strip().split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            data.add(line)
    return data
```

### Contoh 2: JSON API

```python
def fetch(source: dict) -> Set[str]:
    url = source['url']
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    json_data = response.json()
    data = set()
    for item in json_data['results']:
        data.add(item['ip_address'])
    return data
```

### Contoh 3: CSV

```python
import csv
import io

def fetch(source: dict) -> Set[str]:
    url = source['url']
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = set()
    reader = csv.DictReader(io.StringIO(response.text))
    for row in reader:
        data.add(row['domain'])
    return data
```

## Sumber Data Default

### IP Blacklist (drop.txt)
- **AbuseIPDB**: Database IP yang dilaporkan melakukan abuse
  - Requires API key (gratis di https://www.abuseipdb.com/)

### IP Whitelist (pass.txt)
- **Cloudflare IPs**: IP ranges dari Cloudflare CDN

### Domain Whitelist (whitelist.txt)
- **Tranco Top Sites**: Top 10,000 website terpercaya

### Domain Blacklist (blacklist.txt)
- **URLhaus**: Database domain yang menyebarkan malware

## Konfigurasi Workflow

Workflow berjalan setiap bulan pada tanggal 1 jam 00:00 UTC. Untuk mengubah schedule:

Edit `.github/workflows/update-data.yml`:

```yaml
schedule:
  - cron: '0 0 1 * *'  # Menit Jam Tanggal Bulan HariDalamSeminggu
```

Contoh schedule lain:
- Setiap minggu: `0 0 * * 0` (setiap hari Minggu)
- Setiap hari: `0 0 * * *` (setiap hari jam 00:00)
- Setiap 6 jam: `0 */6 * * *`

## Mode Operasi

### Append Mode (Default)
Data baru ditambahkan ke data yang sudah ada, lalu deduplikasi.

```yaml
settings:
  mode: "append"
  remove_duplicates: true
  sort_output: true
```

### Replace Mode
Data lama dihapus dan diganti dengan data baru.

```yaml
settings:
  mode: "replace"
```

## Manual Trigger

Untuk menjalankan workflow secara manual:

1. Buka repository di GitHub
2. Actions tab → "Update Security Data"
3. Klik "Run workflow"

## Logging

Script akan menampilkan log detail saat berjalan:

```
2024-01-01 00:00:00 - INFO - Memulai Data Fetching Process
2024-01-01 00:00:01 - INFO - Memproses kategori: ip_blacklist
2024-01-01 00:00:02 - INFO - Memproses sumber: AbuseIPDB
2024-01-01 00:00:05 - INFO - Berhasil mengambil 10000 entri dari AbuseIPDB
2024-01-01 00:00:06 - INFO - Berhasil menulis 10000 entri ke data/drop.txt
```

## Troubleshooting

### Error: "API key tidak ditemukan"
- Pastikan API key sudah ditambahkan di GitHub Secrets
- Untuk local: pastikan environment variable sudah di-set

### Error: "Fetcher tidak ditemukan"
- Pastikan nama fetcher di `config.yml` sama dengan nama file (tanpa .py)
- Pastikan file fetcher ada di `scripts/fetchers/`

### Data tidak ter-update
- Cek workflow run di GitHub Actions
- Lihat log untuk error messages
- Pastikan permissions `contents: write` sudah diset di workflow

## Keamanan

- **Jangan commit API keys** ke repository
- Gunakan GitHub Secrets untuk menyimpan API keys
- Review data yang di-fetch sebelum digunakan di production
- Gunakan HTTPS untuk semua sumber data

## Lisensi

[Tambahkan lisensi Anda di sini]

## Kontribusi

Pull requests welcome! Untuk perubahan besar, mohon buka issue terlebih dahulu.
