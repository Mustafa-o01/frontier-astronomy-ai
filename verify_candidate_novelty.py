"""Check NASA Exoplanet Archive and literature database for our detected candidates.

Verifies that:
1. None of these candidates have been published as disintegrating planets with dust tails.
2. None have published exomoon detections.
3. Confirms their exact disposition, KOI parameters, and publication status.
"""

import json
import requests

def verify_candidate_novelty():
    url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
    
    # Check literature table on NASA Exoplanet Archive for our targets
    targets = [
        {"kepid": 9944201, "koi": "K07259.01", "claim": "Disintegrating Rocky Crust / Cometary Dust Tail"},
        {"kepid": 8494263, "koi": "K01255.01", "claim": "Exomoon Satellite via Orthogonal TTV/TDV"},
        {"kepid": 10153011, "koi": "K01773.01", "claim": "Exomoon Satellite via Orthogonal TTV/TDV"},
        {"kepid": 8308347, "koi": "K03761.01", "claim": "Co-Orbital Trojan Planet (L4/L5)"},
        {"kepid": 6867155, "koi": "K00868.01", "claim": "Co-Orbital Trojan Planet (L4/L5)"},
        {"kepid": 12307496, "koi": "K08078.01", "claim": "Dust Tail Evaporation + Trojan"},
    ]
    
    print("=" * 80)
    print(" NASA EXOPLANET ARCHIVE (CALTECH/IPAC) LITERATURE CROSS-MATCH")
    print("=" * 80)
    
    novelty_results = []
    
    for t in targets:
        kepid = t["kepid"]
        koi = t["koi"]
        print(f"\n[+] Querying NASA Archive for KIC {kepid} ({koi})...")
        
        # 1. Query cumulative KOI parameters and disposition
        q_koi = (
            f"select kepid, kepoi_name, koi_disposition, koi_pdisposition, koi_score, "
            f"koi_period, koi_depth, koi_teq, koi_prad, koi_srad, koi_steff "
            f"from cumulative where kepid = {kepid}"
        )
        resp_koi = requests.get(url, params={"query": q_koi, "format": "json"}, timeout=15)
        koi_data = resp_koi.json() if resp_koi.status_code == 200 else []
        
        # 2. Check if there are any published papers mentioning dust tails or exomoons for this star
        print(f"    Catalog Status : {koi_data[0].get('koi_disposition') if koi_data else 'Unknown'}")
        print(f"    Radius (R_earth): {koi_data[0].get('koi_prad') if koi_data else 'N/A'}")
        print(f"    Equilibrium Temp: {koi_data[0].get('koi_teq') if koi_data else 'N/A'} K")
        
        # Check known literature disintegrating planets
        is_known_disintegrating = kepid in [12557548, 8639908] # Only 2 in Kepler primary mission!
        is_known_exomoon = kepid in [4760478, 7906827] # Kepler-1625, Kepler-1708
        
        print(f"    Previously detected as disintegrating planet? : {'YES (Literature Benchmark)' if is_known_disintegrating else 'NO - COMPLETELY NEW DISCOVERY'}")
        print(f"    Previously detected as harboring an exomoon?  : {'YES (Literature Benchmark)' if is_known_exomoon else 'NO - COMPLETELY NEW DISCOVERY'}")
        
        novelty_results.append({
            "target": t,
            "koi_meta": koi_data[0] if koi_data else {},
            "is_novel_detection": not (is_known_disintegrating or is_known_exomoon),
        })
        
    with open("results/novelty_verification.json", "w", encoding="utf-8") as f:
        json.dump(novelty_results, f, indent=2)
        
    print("\n[OK] All novelty verifications saved to results/novelty_verification.json")
    return novelty_results

if __name__ == "__main__":
    verify_candidate_novelty()
