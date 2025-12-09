# Quick Start - WHOIS Lookup

## 🚀 Basic Commands

### Check IP or Domain
```bash
python3 scripts/lookup.py 8.8.8.8
python3 scripts/lookup.py github.com
python3 scripts/lookup.py jabarprov.go.id
```

### Update WHOIS Cache (After Data Changes)
```bash
python3 scripts/update_whois_cache.py
```

### Search WHOIS Data
```bash
python3 scripts/whois_manager.py search Google
python3 scripts/whois_manager.py search CN
python3 scripts/whois_manager.py search AS15169
```

### View Statistics
```bash
python3 scripts/whois_manager.py stats
```

## 📊 Priority Levels (Lower = Higher Priority)

1. ✅ Whitelist IP Specific (whitelist-specific.txt)
2. 🚫 Blacklist IP Specific (blacklist-specific.txt)
3. 🚫 Blacklist IP Segment (drop.txt)
4. ✅ Whitelist IP Segment (pass.txt)
5. ✅ Whitelist Domains (whitelist.txt)
6. 🚫 Blacklist Domains (blacklist.txt)

## 💡 Tips

- **Cache first:** WHOIS data disimpan ke `data/whois.txt`
- **Quota saving:** Max 500 IPs per auto-update run
- **Full docs:** Read `WHOIS_LOOKUP.md` for complete guide

## 🔗 API Dashboard

https://ipinfo.io/account (token: 13cf963d4e732d)
