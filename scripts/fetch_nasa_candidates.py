"""Query NASA Exoplanet Archive TAP API for unconfirmed candidate systems."""
import json
import requests

url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

# 1. Ultra-short period candidates (< 1 day) - prime candidates for disintegrating rocky bodies
query_usp = (
    "select kepid, kepoi_name, koi_period, koi_time0bk, koi_depth, koi_duration "
    "from cumulative "
    "where koi_period < 1.0 and koi_period > 0.2 and koi_disposition = 'CANDIDATE' "
    "order by koi_period asc"
)

# 2. Long-period candidates (Period > 50 days) - prime candidates for exomoons (large Hill spheres!)
query_exomoon = (
    "select kepid, kepoi_name, koi_period, koi_time0bk, koi_depth, koi_duration "
    "from cumulative "
    "where koi_period > 50.0 and koi_period < 300.0 and koi_disposition = 'CANDIDATE' "
    "order by koi_period asc"
)

print("Connecting to NASA Exoplanet Archive (Caltech/IPAC)...")

# Fetch Ultra-Short Period targets
resp_usp = requests.get(url, params={"query": query_usp, "format": "json"}, timeout=20)
usp_targets = resp_usp.json()

# Fetch Long-Period Exomoon targets
resp_moon = requests.get(url, params={"query": query_exomoon, "format": "json"}, timeout=20)
moon_targets = resp_moon.json()

print(f"\n[+] Retrieved {len(usp_targets)} Ultra-Short Period candidates from NASA!")
print(f"[+] Retrieved {len(moon_targets)} Long-Period candidates from NASA!")

with open("data/nasa_candidates_usp.json", "w", encoding="utf-8") as f:
    json.dump(usp_targets, f, indent=2)

with open("data/nasa_candidates_moon.json", "w", encoding="utf-8") as f:
    json.dump(moon_targets, f, indent=2)

print("\nTop 5 Ultra-Short-Period candidates for Dust Tail / Disintegration Scan:")
for t in usp_targets[:5]:
    print(f"  Target: KIC {t['kepid']} ({t['kepoi_name']}) | Period = {t['koi_period']:.5f} d | Depth = {t['koi_depth']:.1f} ppm | T0 = {t['koi_time0bk']:.4f}")

print("\nTop 5 Long-Period candidates for Exomoon / TTV Perturbation Scan:")
for t in moon_targets[:5]:
    print(f"  Target: KIC {t['kepid']} ({t['kepoi_name']}) | Period = {t['koi_period']:.3f} d | Depth = {t['koi_depth']:.1f} ppm | T0 = {t['koi_time0bk']:.4f}")
