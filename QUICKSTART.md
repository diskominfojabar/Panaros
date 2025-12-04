# Quick Start Guide - Security Data Aggregator

Panduan cepat untuk setup dan menggunakan Security Data Aggregator.

## 📦 Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Dependencies yang dibutuhkan:
- `requests>=2.31.0` - HTTP requests
- `PyYAML>=6.0.1` - Config parsing

### 2. Setup API Key (Optional)

Hanya diperlukan untuk AbuseIPDB. Dapatkan API key gratis di: https://www.abuseipdb.com/

**Option A: Environment Variable**
```bash
export ABUSEIPDB_API_KEY="your-api-key-here"
```

**Option B: File .env**
```bash
cp .env.example .env
# Edit .env dan isi API key Anda
```

## 🚀 Local Testing

### Test Run
```bash
python3 scripts/processor.py
```

Output yang diharapkan:
```
Memproses kategori: ip_blacklist
  Berhasil mengambil 10000 IP dari AbuseIPDB
Memproses kategori: ip_whitelist
  Berhasil mengambil 22 IP dari Cloudflare
  Berhasil mengambil 1963 IP dari Google
  Berhasil mengambil 5531 IP dari GitHub
  Berhasil mengambil 9455 IP dari AWS
Memproses kategori: domain_blacklist
  Berhasil mengambil 4294 domains dari URLhaus
```

### Verify Results
```bash
# List files
ls -lh data/

# Check contents
head -20 data/pass.txt
head -20 data/blacklist.txt
wc -l data/*.txt
```

## 🤖 GitHub Actions Setup

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

### Step 2: Add API Key Secret

1. Buka repository di GitHub
2. **Settings** → **Secrets and variables** → **Actions**
3. Klik **New repository secret**
4. Isi:
   - Name: `ABUSEIPDB_API_KEY`
   - Secret: (API key dari .env.example atau AbuseIPDB)
5. **Add secret**

### Step 3: Enable Workflow Permissions

1. **Settings** → **Actions** → **General**
2. Scroll ke **Workflow permissions**
3. Pilih **Read and write permissions**
4. **Save**

### Step 4: Manual Trigger (First Time)

1. Buka tab **Actions**
2. Pilih **Update Security Data**
3. Klik **Run workflow** (button hijau)
4. Pilih branch `main`
5. **Run workflow**

### Step 5: Verify Results

Setelah workflow selesai (~2-3 menit):
1. Cek status: ✅ green = success
2. Browse `data/` folder
3. Verify files:
   - `drop.txt` - should have 10,000 lines
   - `pass.txt` - should have 16,971 lines
   - `blacklist.txt` - should have 4,294 lines
   - `whitelist.txt` - should be empty

## 🔧 Adding New Source

### Example: Adding Spamhaus DROP

**1. Create Fetcher**

```bash
cat > scripts/fetchers/spamhaus_drop.py << 'EOF'
import requests
import logging
from typing import Set

logger = logging.getLogger(__name__)

def fetch(source: dict) -> Set[str]:
    url = source['url']
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    ips = set()
    for line in response.text.strip().split('\n'):
        line = line.strip()
        if line and not line.startswith(';'):
            cidr = line.split(';')[0].strip()
            ips.add(cidr)

    logger.info(f"Got {len(ips)} IPs from Spamhaus")
    return ips
EOF
```

**2. Update Config**

Edit `config.yml`:
```yaml
sources:
  ip_blacklist:
    # Existing sources...

    - name: "Spamhaus DROP"
      url: "https://www.spamhaus.org/drop/drop.txt"
      fetcher: "spamhaus_drop"
      requires_api_key: false
```

**3. Test**

```bash
python3 scripts/processor.py
cat data/drop.txt | grep -c "^[^#]"
```

## 📅 Schedule Configuration

Edit `.github/workflows/update-data.yml`:

```yaml
schedule:
  # Current: Monthly (1st day, midnight UTC)
  - cron: '0 0 1 * *'

  # Other options:
  # - cron: '0 0 * * 0'    # Weekly (Sunday)
  # - cron: '0 0 * * *'    # Daily
  # - cron: '0 */6 * * *'  # Every 6 hours
```

## 🛠️ Troubleshooting

### Problem: Rate Limit (429)

**Symptom:**
```
HTTP Error: 429 Too Many Requests
```

**Cause:** Too many requests from same IP

**Solution:**
- Local: Wait 24 hours or use different IP
- GitHub Actions: Won't happen (different IP)

### Problem: Module Not Found

**Symptom:**
```
ModuleNotFoundError: No module named 'scripts'
```

**Solution:** Already fixed in `processor.py`

### Problem: Empty Files

**Symptom:** Output files are empty

**Solutions:**
1. Check API key is correct
2. Check internet connection
3. Look at logs for errors:
   ```bash
   python3 scripts/processor.py 2>&1 | tee output.log
   ```

### Problem: Workflow Failed

**Symptom:** Red X in GitHub Actions

**Solutions:**
1. Check workflow logs (Actions → failed run → details)
2. Verify secrets added correctly
3. Check permissions (Settings → Actions → Read/Write)
4. Look for error messages in logs

## 📊 Output Format

All output files follow this format:

```
# Last updated: 2024-12-04 08:00:00 UTC
# Total entries: 16971
103.21.244.0/22
103.22.200.0/22
example.com
...
```

## 🔍 Useful Commands

```bash
# Count entries per file
wc -l data/*.txt

# Count non-comment lines
grep -v '^#' data/pass.txt | wc -l

# Search for specific IP
grep "1.2.3.4" data/drop.txt

# View logs
python3 scripts/processor.py 2>&1 | tee fetch.log

# Check for duplicates
sort data/pass.txt | uniq -d
```

## 📝 Tips

1. **Testing Fetcher Individually:**
   ```python
   # test_fetcher.py
   from scripts.fetchers.cloudflare_ips import fetch

   source = {'url': 'https://www.cloudflare.com/ips-v4', 'name': 'Test'}
   result = fetch(source)
   print(f"Got {len(result)} IPs")
   for ip in list(result)[:5]:
       print(ip)
   ```

2. **Debug Mode:**
   Edit `scripts/processor.py` line 16:
   ```python
   level=logging.DEBUG  # Change from INFO
   ```

3. **Faster Testing:**
   Comment out slow sources in `config.yml` while testing

4. **Backup Data:**
   ```bash
   cp -r data/ data_backup_$(date +%Y%m%d)/
   ```

## 📖 Next Steps

- Read full documentation: [README.md](README.md)
- Check template: `scripts/fetchers/template.py`
- Review config: `config.yml`
- Explore examples: `scripts/fetchers/EXAMPLES.md` (if exists)

## 🤝 Need Help?

- Check logs first
- Review error messages
- Test individual fetchers
- Create GitHub issue with:
  - Error message
  - Steps to reproduce
  - Environment (OS, Python version)

---

**Happy Automating! 🚀**
