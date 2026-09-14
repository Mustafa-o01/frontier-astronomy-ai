"""Read-only online catalog query and MAST byte verification; caches evidence."""
from pathlib import Path
from datetime import datetime, timezone
import requests,json,hashlib,concurrent.futures
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'paper/sources';OUT.mkdir(exist_ok=True)
query="select kepid,kepoi_name,koi_disposition,koi_pdisposition,koi_score,koi_period,koi_time0bk,koi_duration,koi_depth,koi_teq,koi_prad,koi_srad,koi_steff from cumulative where kepid in (9944201,8494263,10153011,8308347)"
url='https://exoplanetarchive.ipac.caltech.edu/TAP/sync'
meta=dict(retrieved_utc=datetime.now(timezone.utc).isoformat(),endpoint=url,query=query)
try:
    r=requests.get(url,params=dict(query=query,format='json'),timeout=60);r.raise_for_status()
    data=r.json();(OUT/'nasa_catalog.json').write_text(json.dumps(data,indent=2));meta.update(success=True,url=r.url)
except Exception as e:meta.update(success=False,error=str(e))
(OUT/'nasa_query.json').write_text(json.dumps(meta,indent=2))
def check(k):
    rows=[]
    for p in sorted((ROOT/'data/cache/real_kepler').glob(f'kplr{k:09d}*llc.fits')):
        ks=f'{k:09d}';url=f'https://archive.stsci.edu/missions/kepler/lightcurves/{ks[:4]}/{ks}/{p.name}'
        row=dict(kepid=k,file=p.name,url=url,local_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        try:
            r=requests.get(url,timeout=45);r.raise_for_status();row.update(remote_sha256=hashlib.sha256(r.content).hexdigest(),status=r.status_code,bytes=len(r.content));row['identical']=row['local_sha256']==row['remote_sha256']
        except Exception as e:row['error']=str(e)
        rows.append(row)
    return rows
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    rows=[row for batch in ex.map(check,[9944201,8494263,10153011,8308347]) for row in batch]
(OUT/'mast_verification.json').write_text(json.dumps(dict(retrieved_utc=datetime.now(timezone.utc).isoformat(),files=rows),indent=2))
print(json.dumps(meta,indent=2));print([(x['file'],x.get('identical'),x.get('error')) for x in rows])
