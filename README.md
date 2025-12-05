# Security Data Aggregator

Sistem otomatis untuk mengumpulkan dan memperbarui data keamanan (IP & domain blacklist/whitelist) dari berbagai sumber upstream, dengan GitHub Actions untuk update bulanan.

## 📋 Deskripsi Program

Sistem ini mengumpulkan data keamanan dari berbagai sumber terpercaya dan menyimpannya dalam 4 kategori:

| File | Kategori | Sumber | Entries |
|------|----------|--------|---------|
| `drop.txt` | IP Blacklist | AbuseIPDB | 10,000 |
| `pass.txt` | IP Whitelist | Cloudflare, Google, GitHub, AWS | 16,971 |
| `blacklist.txt` | Domain Blacklist | URLhaus | 4,294 |
| `whitelist.txt` | Domain Whitelist | (kosong) | 0 |

**Total: 31,265 entries** diupdate otomatis setiap bulan

## 🎯 Fitur Utama

- ✅ **Modular** - Setiap sumber memiliki fetcher terpisah
- ✅ **Automated** - GitHub Actions berjalan otomatis bulanan
- ✅ **Append Mode** - Data baru ditambahkan, data lama dipertahankan
- ✅ **Deduplikasi** - Otomatis menghapus duplikat
- ✅ **Extensible** - Mudah menambah sumber baru

## 📊 Sumber Data

### IP Whitelist (16,971 ranges)
- **Cloudflare** (22) - CDN IP ranges
- **Google** (1,963) - Googlebot, crawlers, fetchers
- **GitHub** (5,531) - All GitHub services
- **AWS** (9,455) - AWS IP ranges

### IP Blacklist (10,000 IPs)
- **AbuseIPDB** - Reported malicious IPs (confidence ≥90%)

### Domain Blacklist (4,294 domains)
- **URLhaus** - Malware distribution domains (IPs filtered)

## 🚀 Quick Start

Lihat **[QUICKSTART.md](QUICKSTART.md)** untuk panduan lengkap.

### Install & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Setup API key
export ABUSEIPDB_API_KEY="your-key"

# 3. Run
python3 scripts/processor.py

# 4. Check results
ls -lh data/
```

## 🤖 GitHub Actions

### Setup
1. Push ke GitHub
2. Add secret: `ABUSEIPDB_API_KEY`
3. Run workflow dari Actions tab

### Schedule
- Otomatis: Setiap bulan tanggal 1
- Manual: Kapan saja via Actions tab

## 🔧 Menambah Sumber Baru

### 1. Buat Fetcher
```bash
cp scripts/fetchers/template.py scripts/fetchers/my_source.py
```

### 2. Edit Config
```yaml
sources:
  ip_blacklist:
    - name: "My Source"
      url: "https://example.com/data"
      fetcher: "my_source"
      requires_api_key: false
```

### 3. Test
```bash
python3 scripts/processor.py
```

## 📁 Struktur

```
Pangrosan/
├── .github/workflows/
│   └── update-data.yml      # GitHub Actions
├── scripts/
│   ├── processor.py         # Main orchestrator
│   └── fetchers/            # Fetcher modules
│       ├── abuseipdb_ip.py
│       ├── aws_ips.py
│       ├── cloudflare_ips.py
│       ├── github_ips.py
│       ├── google_ips.py
│       ├── urlhaus_domains.py
│       └── template.py      # Template
├── data/                    # Output files
│   ├── drop.txt
│   ├── pass.txt
│   ├── blacklist.txt
│   └── whitelist.txt
├── config.yml               # Configuration
├── requirements.txt
├── README.md               # This file
└── QUICKSTART.md           # Quick guide
```

## ⚙️ Konfigurasi

Edit `config.yml` untuk customize:

```yaml
sources:
  ip_whitelist:
    - name: "Cloudflare IPs"
      fetcher: "cloudflare_ips"
      requires_api_key: false

  ip_blacklist:
    - name: "AbuseIPDB"
      fetcher: "abuseipdb_ip"
      requires_api_key: true
      api_key_env: "ABUSEIPDB_API_KEY"

settings:
  mode: "append"           # atau "replace"
  remove_duplicates: true
  sort_output: true
```

## 🛠️ Troubleshooting

### Rate Limit (429)
AbuseIPDB ter-rate limit saat testing lokal. Solusi:
- Gunakan di GitHub Actions (IP berbeda)
- Atau tunggu 24 jam

### File Kosong
Cek:
1. API key sudah benar
2. Workflow logs untuk error
3. Internet connection

### Workflow Failed
Verifikasi:
- Permissions: Read and write
- Secrets sudah ditambahkan
- Lihat detailed logs

## 🔒 Security Notes

- ⚠️ **JANGAN** commit API keys
- ✅ Gunakan GitHub Secrets
- ✅ File `.env` di-ignore
- ✅ Review data sebelum production

## 📊 Statistics

```
Total: 31,265 entries
├─ IP Whitelist: 16,971
├─ IP Blacklist: 10,000
├─ Domain Blacklist: 4,294
└─ Domain Whitelist: 0
```

## 📝 License

[Your License Here]

## 📞 Support

- Issues: GitHub Issues
- Documentation: QUICKSTART.md
- Template: `scripts/fetchers/template.py`

---

**Built for automated security data aggregation** 🛡️


## 📊 Monthly Statistics History

| Month | Blacklist Domains | Blacklist IPs | Drop (Segments) | Whitelist Domains | Whitelist IPs | Pass (Segments) | Hosts | Total |
|-------|-------------------|---------------|-----------------|-------------------|---------------|-----------------|-------|-------|
| 2025-12 | 4,234 | 280 | 17,510 | 116 | 85 | 16,995 | 4,234 | **43,454** |
