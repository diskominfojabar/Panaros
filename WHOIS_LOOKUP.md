# WHOIS Lookup & IP/Domain Security Check

Fitur untuk mengecek kepemilikan IP/domain dan status keamanan (blacklist/whitelist) menggunakan IPinfo.io API.

## 📋 Features

1. **IP/Domain Lookup** - Cek status blokir dan kepemilikan
2. **WHOIS Manager** - Kelola cache data kepemilikan IP
3. **Auto-Update** - Update cache otomatis untuk IP baru
4. **Batch Processing** - Process ribuan IPs dengan rate limiting
5. **Smart Caching** - Hemat API quota dengan caching lokal

## 🔑 API Configuration

**Provider:** IPinfo.io
**Plan:** Lite (Free)
**Token:** Set via environment variable `IPINFO_TOKEN` (or defaults to embedded token)
**Monthly Limit:** 50,000 requests
**Current Usage:** ~5 requests
**Remaining:** ~49,995 requests

### Setting API Token (Recommended for Production)

**Local Development:**
```bash
export IPINFO_TOKEN="13cf963d4e732d"
```

**GitHub Actions Secret:**
1. Go to Repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `IPINFO_TOKEN`
4. Value: `13cf963d4e732d`
5. Click "Add secret"

**GitHub Actions Workflow:**
```yaml
- name: Update WHOIS Cache
  env:
    IPINFO_TOKEN: ${{ secrets.IPINFO_TOKEN }}
  run: python3 scripts/update_whois_cache.py
```

The script will automatically use the environment variable if set, otherwise falls back to the embedded token.

### API Capabilities

```json
{
  "requests": {
    "day": 5,
    "month": 5,
    "limit": 50000,
    "remaining": 49995
  },
  "features": {
    "core": {
      "daily": unlimited,
      "monthly": 50000
    }
  }
}
```

## 🚀 Usage

### 1. Lookup IP atau Domain

**Syntax:**
```bash
python3 scripts/lookup.py <IP_or_DOMAIN> [--no-whois]
```

**Examples:**

```bash
# Cek IP
python3 scripts/lookup.py 8.8.8.8

# Cek domain
python3 scripts/lookup.py github.com

# Cek tanpa WHOIS info (lebih cepat)
python3 scripts/lookup.py 1.1.1.1 --no-whois
```

**Output Example (IP):**
```
================================================================================
Security Lookup: 8.8.8.8
================================================================================
Type: IP Address

📋 Status:
  ✅ WHITELISTED
     Priority: Level 1
     List: Whitelist Ips
     Entry: 8.8.8.8/32
     Source: Google DNS Primary (Infrastructure Protection)

🎯 Effective Action:
   ✅ ALLOWED (Priority Level 1)

================================================================================
WHOIS Information (IPinfo.io)
================================================================================
  Organization: Google LLC
  Country:      US
  City:         Mountain View
  ASN:          AS15169
  Hostname:     dns.google
  Cached:       2025-12-09 18:38:01
```

**Output Example (Domain):**
```
================================================================================
Security Lookup: github.com
================================================================================
Type: Domain Name

📋 Domain Status:
  ✅ WHITELISTED
     Priority: Level 5
     List: Whitelist Domains
     Entry: *.github.com
     Source: GitHub Domains

🎯 Effective Action for Domain:
   ✅ ALLOWED (Priority Level 5)

📡 Resolving github.com...
   Found 1 IP address(es):
     - 20.205.243.166

================================================================================
IP Resolution Check
================================================================================

[1/1] Checking IP: 20.205.243.166
--------------------------------------------------------------------------------
   ✅ Whitelist Subnets: 20.205.243.166/32
   → ALLOWED (Level 4)

   WHOIS for 20.205.243.166:
     Organization: Microsoft Corporation
     Country:      SG
     ASN:          AS8075
```

### 2. WHOIS Manager

**Query single IP:**
```bash
python3 scripts/whois_manager.py query 1.2.3.4
```

**Batch update from file:**
```bash
# Update WHOIS cache for all IPs in blacklist-specific.txt
python3 scripts/whois_manager.py update data/blacklist-specific.txt

# Limit to 100 queries
python3 scripts/whois_manager.py update data/blacklist-specific.txt --max-queries 100
```

**Search WHOIS data:**
```bash
# Search by IP
python3 scripts/whois_manager.py search 8.8.8.8

# Search by organization
python3 scripts/whois_manager.py search Google

# Search by country
python3 scripts/whois_manager.py search US

# Search by ASN
python3 scripts/whois_manager.py search AS15169
```

**View statistics:**
```bash
python3 scripts/whois_manager.py stats
```

**Output:**
```
WHOIS Cache Statistics:
  Total IPs: 1234

  Top 10 Countries:
    US: 456
    CN: 234
    GB: 123
    ...

  Top 10 Organizations:
    Google LLC: 89
    Amazon.com, Inc.: 67
    Cloudflare, Inc.: 45
    ...

  Top 10 ASNs:
    AS15169: 89
    AS16509: 67
    AS13335: 45
    ...
```

### 3. Auto-Update WHOIS Cache

**Run after data updates:**
```bash
python3 scripts/update_whois_cache.py
```

**What it does:**
1. Checks `blacklist-specific.txt` and `whitelist-specific.txt`
2. Identifies new IPs not in cache
3. Queries IPinfo.io API for new IPs only
4. Limits to 500 IPs per file per run (1,000 total)
5. Saves to `data/whois.txt`

**Output:**
```
================================================================================
WHOIS Cache Auto-Update
================================================================================
Initial cache size: 5 entries

Processing data/blacklist-specific.txt...
  Total IPs: 86973
  In cache: 5
  New IPs: 86968
  Limiting to 500 queries
[Batch processing...]

================================================================================
Update Complete
================================================================================
Initial cache size: 5
Final cache size: 505
New entries added: 500
Total API queries: 500
API quota remaining: ~49500 (estimate)
================================================================================
✅ Added 500 new WHOIS records
```

## 📁 Data Files

### whois.txt Format

**Location:** `data/whois.txt`

**Format:** `IP|ORG|COUNTRY|CITY|ASN|HOSTNAME|CACHED_DATE`

**Example:**
```
# WHOIS Data Cache - IPinfo.io
# Last updated: 2025-12-09 18:38:01 UTC
# Total entries: 505
# Format: IP|ORG|COUNTRY|CITY|ASN|HOSTNAME|CACHED_DATE
#
1.1.1.1|Cloudflare, Inc.|US|San Francisco|AS13335|one.one.one.one|2025-12-09 18:38:01
8.8.8.8|Google LLC|US|Mountain View|AS15169|dns.google|2025-12-09 18:38:01
20.205.243.166|Microsoft Corporation|SG|Singapore|AS8075|Unknown|2025-12-09 18:38:15
```

**Benefits:**
- ✅ Cached locally (no repeated API calls)
- ✅ Searchable by IP, org, country, ASN
- ✅ Human-readable format
- ✅ Automatically maintained

## 🔄 Integration with Data Pipeline

### Recommended Workflow

**1. After processor.py:**
```bash
python3 scripts/processor.py
python3 scripts/update_whois_cache.py  # Auto-update new IPs
```

**2. After resolve_blacklist.py:**
```bash
python3 scripts/resolve_blacklist.py
python3 scripts/update_whois_cache.py  # Update newly resolved IPs
```

**3. Manual batch update (first time):**
```bash
# Process all blacklist IPs (may take ~30 minutes for 86K IPs)
python3 scripts/whois_manager.py update data/blacklist-specific.txt --max-queries 10000

# Process in chunks to stay under daily limit
for i in {1..9}; do
  python3 scripts/whois_manager.py update data/blacklist-specific.txt --max-queries 5000
  echo "Batch $i complete, waiting 1 hour..."
  sleep 3600
done
```

## 📊 Priority Levels

Sistem security menggunakan 5-level priority (lowest number = highest priority):

| Priority | Type | File | Description |
|----------|------|------|-------------|
| **1** | Whitelist IP Specific | whitelist-specific.txt | Individual trusted IPs |
| **2** | Blacklist IP Specific | blacklist-specific.txt | Individual malicious IPs |
| **3** | Blacklist IP Segment | drop.txt | Malicious IP subnets |
| **4** | Whitelist IP Segment | pass.txt | Trusted IP subnets |
| **5** | Whitelist Domains | whitelist.txt | Trusted domains |
| **6** | Blacklist Domains | blacklist.txt | Malicious domains |

**Effective Action:**
- Highest priority (lowest number) wins
- Example: If IP is in both whitelist (Level 1) and blacklist (Level 2), it's **ALLOWED**

## 🔍 Search Capabilities

### IP Lookup
- ✅ Exact match with or without CIDR
- ✅ Checks all 6 security files
- ✅ Shows effective action (allowed/blocked)
- ✅ Displays WHOIS data (org, country, ASN)

### Domain Lookup
- ✅ Exact domain match
- ✅ Wildcard support (`*.example.com` matches `sub.example.com`)
- ✅ DNS resolution to IPs
- ✅ Check each resolved IP
- ✅ WHOIS for first IP

### WHOIS Search
- ✅ Search by IP address
- ✅ Search by organization name
- ✅ Search by country code
- ✅ Search by ASN number
- ✅ Partial matching supported

## ⚙️ Rate Limiting & Quota Management

### API Limits
- **Monthly Limit:** 50,000 requests
- **Rate Limit:** 100ms delay between requests
- **Batch Size:** 100 IPs per batch
- **Auto-save:** After each batch

### Strategies to Save Quota

1. **Smart Caching**
   - Only query new IPs
   - Cache results permanently
   - Use cached data by default

2. **Batch Limiting**
   - `--max-queries` flag limits queries
   - Default: 500 per file for auto-update
   - Recommended: 1,000-5,000 per day

3. **Progressive Updates**
   - Start with 500 most recent IPs
   - Gradually update older IPs
   - Prioritize blacklist over whitelist

4. **Selective Updates**
   - Only run after significant data changes
   - Skip if < 100 new IPs
   - Manual control with `whois_manager.py`

### Quota Tracking

**Check current usage:**
```bash
curl -s "https://ipinfo.io/me?token=13cf963d4e732d" | jq '.requests'
```

**Output:**
```json
{
  "day": 5,
  "month": 505,
  "limit": 50000,
  "remaining": 49495
}
```

## 🛠️ Advanced Features

### Custom Cache Location

```python
from whois_manager import WhoisManager

# Use custom cache file
manager = WhoisManager(cache_file="custom/path/whois.txt")
```

### Programmatic Usage

```python
from lookup import SecurityLookup

# Initialize
lookup = SecurityLookup(data_dir="data")

# Check IP
lookup.lookup("8.8.8.8", show_whois=True)

# Check domain
lookup.lookup("github.com", show_whois=False)
```

### Search Programmatically

```python
from whois_manager import WhoisManager

manager = WhoisManager()

# Search by organization
results = manager.search("Google")
for result in results:
    print(f"{result['ip']} - {result['org']}")

# Get statistics
stats = manager.get_stats()
print(f"Total IPs: {stats['total']}")
print(f"Top country: {stats['top_countries'][0]}")
```

## 📈 Statistics & Analytics

### WHOIS Cache Stats

```bash
python3 scripts/whois_manager.py stats
```

**Provides:**
- Total cached IPs
- Top 10 countries by IP count
- Top 10 organizations by IP count
- Top 10 ASNs by IP count

**Use Cases:**
- Identify major threat actors (top orgs in blacklist)
- Geographic distribution of threats
- ASN-based blocking decisions
- Infrastructure protection validation

## 🚨 Troubleshooting

### Issue: "WHOIS data not available"

**Solution:**
```bash
# Update cache for the IP
python3 scripts/whois_manager.py query 1.2.3.4

# Or batch update
python3 scripts/update_whois_cache.py
```

### Issue: "Rate limit reached"

**Solution:**
- Wait 1 minute and retry
- Use smaller `--max-queries` value
- Check monthly quota: `curl "https://ipinfo.io/me?token=13cf963d4e732d"`

### Issue: "API key invalid"

**Solution:**
- Verify token in `scripts/whois_manager.py`
- Check IPinfo dashboard: https://ipinfo.io/account

### Issue: Slow lookups

**Solution:**
```bash
# Use --no-whois for faster lookups
python3 scripts/lookup.py 1.2.3.4 --no-whois

# Pre-populate cache
python3 scripts/update_whois_cache.py
```

## 📝 Examples

### Example 1: Check if IP is safe

```bash
$ python3 scripts/lookup.py 1.1.1.1

Output:
✅ WHITELISTED (Priority Level 1)
Organization: Cloudflare, Inc.
→ ALLOWED
```

### Example 2: Check suspicious domain

```bash
$ python3 scripts/lookup.py malware-site.com

Output:
🚫 BLACKLISTED (Priority Level 6)
Source: URLhaus Malware Domains
→ BLOCKED
```

### Example 3: Bulk WHOIS update

```bash
# Update 1000 IPs from blacklist
$ python3 scripts/whois_manager.py update data/blacklist-specific.txt --max-queries 1000

Output:
Processing batch 1/10...
Progress: 100 queried, 0 failed
[...]
Batch update complete: 1000 new, 0 failed
```

### Example 4: Search for Chinese IPs

```bash
$ python3 scripts/whois_manager.py search CN

Output:
Found 234 results:
  1.14.225.56 - Shenzhen Tencent Computer Systems (CN)
  42.1.111.150 - Beijing Baidu Netcom (CN)
  [...]
```

## 🔐 Security Best Practices

1. **Protect API Token**
   - Don't commit token to public repos
   - Use environment variables for production
   - Rotate token if exposed

2. **Cache Management**
   - Review `whois.txt` periodically
   - Remove outdated entries (> 90 days)
   - Re-query critical IPs monthly

3. **Quota Management**
   - Monitor monthly usage
   - Set alerts at 80% quota
   - Use batch limiting for automation

4. **Data Validation**
   - Verify WHOIS data accuracy
   - Cross-reference with other sources
   - Flag suspicious entries (Unknown org, country)

## 📚 API Documentation

**IPinfo.io API Docs:** https://ipinfo.io/developers

**Available Fields:**
- `ip` - IP address
- `hostname` - Reverse DNS hostname
- `city` - City name
- `region` - Region/state
- `country` - Country code (ISO 3166-1 alpha-2)
- `loc` - Latitude/longitude
- `org` - Organization (AS number + name)
- `postal` - Postal/ZIP code
- `timezone` - Timezone
- `anycast` - Boolean (for anycast IPs)

**Response Example:**
```json
{
  "ip": "8.8.8.8",
  "hostname": "dns.google",
  "city": "Mountain View",
  "region": "California",
  "country": "US",
  "loc": "37.4056,-122.0775",
  "org": "AS15169 Google LLC",
  "postal": "94043",
  "timezone": "America/Los_Angeles",
  "anycast": true
}
```

## 🌐 Web Interface Integration (index.html)

### Features Added (2025-12-09)

**1. CIDR Range Checking**
- ✅ Automatically detects if IP falls within blacklisted/whitelisted CIDR ranges
- ✅ Example: IP `10.1.2.3` now correctly matches `10.0.0.0/8` in drop.txt
- ✅ Works for both blacklist and whitelist subnet files

**2. WHOIS Display in UI**
- ✅ Shows organization, country, city, ASN for checked IPs
- ✅ Displays for BOTH blocked and allowed IPs
- ✅ Data fetched from whois.txt cache
- ✅ Automatically updates display based on theme (light/dark mode)

**3. Enhanced IP File Coverage**
- ✅ Now checks whitelist-specific.txt and pass.txt for IP whitelisting
- ✅ Priority system: Whitelist IPs → Blacklist IPs → DROP subnets → PASS subnets

### Technical Implementation

**CIDR Range Checking:**
```javascript
function isIPInCIDR(ip, cidr) {
    const [range, bits] = cidr.split('/');
    const mask = ~(2 ** (32 - parseInt(bits, 10)) - 1);
    return (ipToInt(ip) & mask) === (ipToInt(range) & mask);
}
```

**WHOIS Lookup:**
```javascript
async function fetchWhoisInfo(query) {
    // Fetches from whois.txt cache on GitHub
    // Returns: {ip, org, country, city, asn, hostname, cached}
}
```

**Usage:**
1. Visit index.html
2. Enter IP address (e.g., `8.8.8.8` or `10.1.2.3`)
3. Click "Periksa Sekarang"
4. Result shows:
   - Security status (Blocked/Safe)
   - WHOIS information (if available)
   - Source file that triggered the match

## 🎯 Future Enhancements

**Planned Features:**
- [ ] Reverse DNS lookup integration
- [ ] ASN-based bulk blocking
- [ ] Geographic heatmap visualization
- [ ] Threat intelligence scoring
- [ ] Automated threat actor profiling
- [ ] Integration with abuse.ch API
- [ ] Historical data tracking
- [ ] Alert system for high-risk ASNs
- [ ] Real-time IPinfo.io API fallback in index.html

---

**Version:** 1.1
**Last Updated:** 2025-12-09
**API Provider:** IPinfo.io
**License:** Internal Use
