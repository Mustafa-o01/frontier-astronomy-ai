"""Inspect NASA Candidate parameters to select best candidates for scanning."""
import json

def inspect_candidates():
    with open("data/nasa_candidates_usp.json", "r", encoding="utf-8") as f:
        usp_candidates = json.load(f)
    
    with open("data/nasa_candidates_moon.json", "r", encoding="utf-8") as f:
        moon_candidates = json.load(f)
        
    print(f"Loaded {len(usp_candidates)} USP candidates, {len(moon_candidates)} Moon candidates.")
    
    # Sort USP by depth descending (deepest transits have highest S/N)
    usp_sorted = sorted(usp_candidates, key=lambda x: x.get("koi_depth") or 0.0, reverse=True)
    print("\n--- TOP USP CANDIDATES (by transit depth) ---")
    for c in usp_sorted[:10]:
        print(f"KIC {c['kepid']} | KOI: {c['kepoi_name']} | P = {c['koi_period']:.5f} d | Depth = {c['koi_depth']:.1f} ppm | Dur = {c['koi_duration']:.2f} h")
        
    # Sort Moon candidates by duration and depth
    moon_sorted = sorted(moon_candidates, key=lambda x: (x.get("koi_depth") or 0.0), reverse=True)
    print("\n--- TOP LONG-PERIOD MOON CANDIDATES (by transit depth) ---")
    for c in moon_sorted[:10]:
        print(f"KIC {c['kepid']} | KOI: {c['kepoi_name']} | P = {c['koi_period']:.2f} d | Depth = {c['koi_depth']:.1f} ppm | Dur = {c['koi_duration']:.2f} h")

if __name__ == "__main__":
    inspect_candidates()
