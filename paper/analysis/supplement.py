"""Provenance extraction and descriptive orbital harmonic measurements."""
from reproduce import *
import pyarrow.parquet as pq
def main():
    meta={}
    for p in (ROOT/'data/benchmarks').glob('*.parquet'):
        m=pq.read_metadata(p).metadata
        meta[p.name]={k.decode():v.decode() for k,v in m.items() if k!=b'ARROW:schema'}
    savejson(OUT/'sources/benchmark_metadata.json',meta)
    lc,sap,q,_=load(9944201);P=META[9944201]['koi_period'];t0=META[9944201]['koi_time0bk'];rows=[]
    for quarter in sorted(set(q)):
        ph=phase_fold(lc.time,P,t0);m=(q==quarter)&(np.abs(ph)>.1)&(np.abs(ph)<.4);x=ph[m];f=lc.flux[m];e=lc.flux_err[m]
        X=np.column_stack([np.ones(len(x)),np.cos(2*np.pi*x),np.sin(2*np.pi*x),np.cos(4*np.pi*x),np.sin(4*np.pi*x)])
        A=X/e[:,None];p=np.linalg.lstsq(A,f/e,rcond=None)[0];res=f-X@p
        rows.append(dict(quarter=int(quarter),n=int(m.sum()),cos_1_ppm=p[1]*1e6,sin_1_ppm=p[2]*1e6,cos_2_ppm=p[3]*1e6,sin_2_ppm=p[4]*1e6,harmonic_2_semiamplitude_ppm=float(np.hypot(p[3],p[4])*1e6),residual_rms_ppm=float(np.std(res)*1e6)))
    csvout('orbital_harmonics.csv',rows)
if __name__=='__main__':main()
