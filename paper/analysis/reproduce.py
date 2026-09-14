"""Independent, non-destructive cached-data reproduction. Run from repository root."""
from pathlib import Path
import sys, json, hashlib, csv, platform, dataclasses
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import scipy
from scipy.optimize import least_squares
from scipy.stats import chi2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy.io import fits
import astropy
from frontier_astronomy.ingestion.fits_reader import read_fits_light_curve
from frontier_astronomy.core.types import LightCurveData
from frontier_astronomy.core.preprocessing import preprocess_light_curve, phase_fold, fold_light_curve
from frontier_astronomy.dust_tail.detector import detect_dust_tail, fit_symmetric_transit, fit_cometary_dust_tail
from frontier_astronomy.dust_tail.extinction_model import cometary_extinction_profile
from frontier_astronomy.core.math_utils import symmetric_trapezoid_transit
from frontier_astronomy.perturbations import detect_perturbations
from frontier_astronomy.perturbations.ttv_extractor import extract_ttv
from frontier_astronomy.perturbations.tdv_extractor import extract_tdv, test_orthogonal_phase_invariant
from frontier_astronomy.perturbations.trojan_detector import detect_trojan_companions

OUT=ROOT/'paper'; FIG=OUT/'figures'; TAB=OUT/'tables'
for p in [FIG,TAB,OUT/'logs',OUT/'sources']: p.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':300})
TARGETS=[9944201,8494263,10153011,8308347]
META={x['kepid']:x for name in ['usp','moon'] for x in json.loads((ROOT/f'data/nasa_candidates_{name}.json').read_text())}
SAVED=json.loads((ROOT/'results/real_nasa_discoveries.json').read_text())
def conv(x):
    if dataclasses.is_dataclass(x): return conv(dataclasses.asdict(x))
    if isinstance(x,dict): return {k:conv(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [conv(v) for v in x]
    if isinstance(x,np.ndarray): return x.tolist()
    if isinstance(x,np.generic): return x.item()
    return x
def savejson(path,x): path.write_text(json.dumps(conv(x),indent=2,allow_nan=False),encoding='utf-8')
def csvout(name,rows):
    if not rows:return
    with (TAB/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def figsave(name):
    plt.savefig(FIG/(name+'.png'),bbox_inches='tight');plt.savefig(FIG/(name+'.pdf'),bbox_inches='tight');plt.close()
def load(k):
    lcs=[]; sap=[]; manifests=[]; quarters=[]
    for p in sorted((ROOT/'data/cache/real_kepler').glob(f'kplr{k:09d}*llc.fits')):
        lc=read_fits_light_curve(p,target_id=f'KIC {k}');lcs.append(lc)
        with fits.open(p) as h:
            d=h[1].data;good=(d['SAP_QUALITY']==0)&np.isfinite(d['TIME'])&np.isfinite(d['PDCSAP_FLUX'])&np.isfinite(d['PDCSAP_FLUX_ERR'])&(d['PDCSAP_FLUX']>0)
            assert np.array_equal(lc.time,d['TIME'][good]),p
            assert np.allclose(lc.flux,d['PDCSAP_FLUX'][good]/np.median(d['PDCSAP_FLUX'][good]),rtol=0,atol=2e-7),p
            s=np.asarray(d['SAP_FLUX'][good],float);e=np.asarray(d['SAP_FLUX_ERR'][good],float); med=np.nanmedian(s)
            sap.append((s/med,e/med));q=int(h[0].header['QUARTER']);quarters.extend([q]*len(lc.time))
            manifests.append(dict(kepid=k,file=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),quarter=q,raw_rows=len(d),accepted_rows=len(lc.time),start_bkjd=float(lc.time.min()),end_bkjd=float(lc.time.max()),cadence_min=float(np.median(np.diff(lc.time))*1440),bjdrefi=h[1].header.get('BJDREFI'),timesys=h[1].header.get('TIMESYS'),creator=h[0].header.get('CREATOR'),data_rel=h[0].header.get('DATA_REL'),crowdsap=h[1].header.get('CROWDSAP'),flfrcsap=h[1].header.get('FLFRCSAP'),astropy_reader_agrees=True))
    t=np.concatenate([x.time for x in lcs]);idx=np.argsort(t)
    lc=LightCurveData(target_id=f'KIC {k}',mission='Kepler',time=t[idx],flux=np.concatenate([x.flux for x in lcs])[idx],flux_err=np.concatenate([x.flux_err for x in lcs])[idx],quality=np.concatenate([x.quality for x in lcs])[idx],ra=lcs[0].ra,dec=lcs[0].dec)
    slc=lc.copy_with(flux=np.concatenate([x[0] for x in sap])[idx],flux_err=np.concatenate([x[1] for x in sap])[idx])
    return lc,slc,np.asarray(quarters)[idx],manifests
def binned(x,y,e,edges):
    rows=[]
    for lo,hi in zip(edges[:-1],edges[1:]):
        m=(x>=lo)&(x<hi)
        if m.sum()<2:continue
        w=1/e[m]**2;v=np.sum(w*y[m])/w.sum()
        er=max(1/np.sqrt(w.sum()),np.std(y[m],ddof=1)/np.sqrt(m.sum()))
        rows.append([(lo+hi)/2,v,er,m.sum()])
    return np.array(rows)
def plotbin(ax,lc,P,t0,label,edges=np.linspace(-.5,.5,201),**kw):
    b=binned(phase_fold(lc.time,P,t0),lc.flux,lc.flux_err,edges)
    ax.errorbar(b[:,0],(b[:,1]-1)*1e6,yerr=b[:,2]*1e6,fmt='.',ms=3,label=label,**kw)
    return b

def timing(lc,P,t0,duration=None,depth=None):
    tt=extract_ttv(lc.time,lc.flux,lc.flux_err,P,t0,duration,depth)
    td=extract_tdv(lc.time,lc.flux,lc.flux_err,P,t0,duration,depth,tt.transit_times,tt.epochs)
    z=conv(tt);z['tdv']=conv(td);z['phase']=test_orthogonal_phase_invariant(tt.ttv_minutes,td.tdv_minutes)
    z['linear_chi2']=float(np.sum((tt.ttv_minutes/tt.ttv_errors_minutes)**2));z['linear_dof']=max(0,len(tt.epochs)-2)
    return z

def independent_local(lc,P,t0,D):
    """Joint local trapezoid fits with a linear continuum and cadence integration.
    Timing covariance is formal and inflated only if reduced chi2 exceeds one.
    No statistical significance is inferred from a 3-event sinusoidal fit.
    """
    fits_out=[];models=[]
    for ep in np.unique(np.rint((lc.time-t0)/P).astype(int)):
        nom=t0+ep*P;m=np.abs(lc.time-nom)<2*D
        if m.sum()<20:continue
        x=lc.time[m]-nom;y=lc.flux[m];err=lc.flux_err[m]
        if min(np.sum(x<-.65*D),np.sum(x>.65*D))<5:continue
        cad=np.median(np.diff(lc.time));xx=x[:,None]+np.linspace(-.5,.5,15)[None,:]*cad
        def model(p):
            dt,dep,dur,ing,c,b=p
            shape=symmetric_trapezoid_transit((xx-dt).ravel(),1.,dep,dur,ing).reshape(xx.shape).mean(axis=1)
            return c+b*x+shape-1
        dep=max(.001,np.percentile(y,80)-np.percentile(y,10))
        best=None
        for dt in [-.12*D,0,.12*D]:
            r=least_squares(lambda p:(y-model(p))/err,[dt,dep,D,.2,np.median(y),0],bounds=([-.45*D,0,.4*D,.03,.8,-.1],[.45*D,.2,1.6*D,.49,1.2,.1]),x_scale='jac',max_nfev=1200,ftol=1e-10,xtol=1e-10,gtol=1e-8)
            if best is None or np.sum(r.fun**2)<np.sum(best.fun**2):best=r
        r=best;chisq=float(np.sum(r.fun**2));cov=np.linalg.pinv(r.jac.T@r.jac)*max(1,chisq/(len(y)-6));errs=np.sqrt(np.diag(cov))
        fits_out.append(dict(epoch=int(ep),mid_bkjd=float(nom+r.x[0]),mid_err_min=float(errs[0]*1440),duration_hours=float(r.x[2]*24),duration_err_min=float(errs[2]*1440),depth=float(r.x[1]),chi2=chisq,dof=len(y)-6,n=len(y),jac_rank=int(np.linalg.matrix_rank(r.jac)),at_bound=bool(np.any(r.active_mask))))
        models.append((ep,x,y,err,model(r.x)))
    if len(fits_out)>=3:
        ep=np.array([r['epoch'] for r in fits_out]);mid=np.array([r['mid_bkjd'] for r in fits_out]);er=np.array([r['mid_err_min'] for r in fits_out]);p=np.polyfit(ep,mid,1,w=1/er);oc=(mid-np.polyval(p,ep))*1440
        for row,v in zip(fits_out,oc):row['oc_min']=float(v)
    return fits_out,models

def main():
    summary={};manifest=[];timingrows=[];controlrows=[]
    for saved in SAVED:
        k=saved['kepid'];meta=META[k];P=meta['koi_period'];t0=meta['koi_time0bk'];D=meta['koi_duration']/24
        lc,sap,q,man=load(k);manifest+=man
        clean=preprocess_light_curve(lc)
        dust=detect_dust_tail(clean,P,t0);pert=detect_perturbations(clean,P,t0)
        row=dict(kepid=k,n_ingested=len(lc.time),n_processed=len(clean.time),delta_bic=dust.delta_bic,asymmetry=dust.asymmetry_parameter,ttv_snr=pert.ttv_snr,moon_score=pert.p_moon_posterior,moon_flag=pert.has_exomoon_candidate,trojan_flag=pert.has_trojan_candidate,saved_delta_bic=saved['dust_tail']['delta_bic'],saved_ttv_snr=saved['perturbations']['ttv_snr'],saved_verdict=saved['verdict'])
        controlrows.append(row)
        print('REPRODUCED',k,row['n_processed'],round(dust.delta_bic,3),round(pert.ttv_snr,4),flush=True)
        if k not in TARGETS:continue
        s=dict(meta=meta,quarters=sorted(set(q.tolist())),n_ingested=len(lc.time),n_processed=len(clean.time),baseline_days=float(np.ptp(lc.time)),pipeline=row)
        protected=preprocess_light_curve(lc,period=P,t0=t0,duration_days=D)
        s['timing']={}
        for mode,data,dur in [('pipeline',clean,None),('pdc_no_extra_processing',lc,None),('pdc_no_clip_savgol',preprocess_light_curve(lc,clip_outliers=False),None),('pdc_clip_only',preprocess_light_curve(lc,detrend=False),None),('pdc_masked_default_duration',protected,None),('pdc_masked_catalog_duration',protected,meta['koi_duration']),('pdc_no_extra_catalog_duration',lc,meta['koi_duration'])]:
            z=timing(data,P,t0,dur);s['timing'][mode]=z
            for j,ep in enumerate(z['epochs']):
                jj=z['tdv']['epochs'].index(ep) if ep in z['tdv']['epochs'] else None
                timingrows.append(dict(kepid=k,method=mode,epoch=ep,mid_bkjd=z['transit_times'][j],oc_min=z['ttv_minutes'][j],timing_error_min=z['ttv_errors_minutes'][j],duration_hours=z['tdv']['durations_hours'][jj] if jj is not None else None,tdv_min=z['tdv']['tdv_minutes'][jj] if jj is not None else None,tdv_error_min=z['tdv']['tdv_errors_minutes'][jj] if jj is not None else None))
        if k in [8494263,10153011]:
            local,mods=independent_local(lc,P,t0,D);slocal,smods=independent_local(sap,P,t0,D)
            s['local_pdc']=local;s['local_sap']=slocal
            csvout(f'local_{k}_pdc.csv',local);csvout(f'local_{k}_sap.csv',slocal)
            fig,axes=plt.subplots(2,3,figsize=(12,6),gridspec_kw={'height_ratios':[1.5,1]})
            for ax,(ep,x,y,e,model) in zip(axes[0],mods):
                ax.errorbar(x*24,(y-1)*1e3,yerr=e*1e3,fmt='.',color='black',ms=3,label='PDC-SAP')
                ax.plot(x*24,(model-1)*1e3,color='#176b8a',label='Local integrated fit')
                cm=np.abs(clean.time-(t0+ep*P))<2*D
                ax.plot((clean.time[cm]-t0-ep*P)*24,(clean.flux[cm]-1)*1e3,'.',color='#be5432',ms=3,label='Pipeline')
                ax.set(xlabel='Hours from catalog mid-transit',ylabel='Relative flux − 1 (ppt)',title=f'KIC {k}, epoch {ep}, N={len(x)}')
            axes[0,0].legend(fontsize=7)
            for mode,color in [('pipeline','#be5432'),('pdc_no_extra_processing','#176b8a'),('pdc_masked_catalog_duration','#8b6f24')]:
                z=s['timing'][mode];axes[1,0].errorbar(z['epochs'],z['ttv_minutes'],yerr=z['ttv_errors_minutes'],fmt='o-',ms=3,label=mode.replace('pdc_','').replace('_',' '),color=color)
            axes[1,0].set(xlabel='Transit epoch',ylabel='O − C (min)');axes[1,0].legend(fontsize=6)
            for rows,label,col in [(local,'Local PDC','#176b8a'),(slocal,'Local SAP','#703c7c')]:
                axes[1,1].errorbar([r['epoch'] for r in rows],[r.get('oc_min',0) for r in rows],yerr=[r['mid_err_min'] for r in rows],fmt='o-',label=label,color=col)
                axes[1,2].errorbar([r['epoch'] for r in rows],[r['duration_hours'] for r in rows],yerr=[r['duration_err_min']/60 for r in rows],fmt='o-',label=label,color=col)
            axes[1,1].set(xlabel='Transit epoch',ylabel='Local-fit O − C (min)');axes[1,1].legend(fontsize=7)
            axes[1,2].set(xlabel='Transit epoch',ylabel='Local-fit duration (h)');axes[1,2].legend(fontsize=7)
            fig.tight_layout();figsave(f'timing_{k}')
        if k==9944201:
            folded=fold_light_curve(clean,P,t0,sort=True);ph=folded.phase;f=folded.flux;e=folded.flux_err
            d0=max(.005,1-np.min(f[(ph>=-.05)&(ph<=.05)]))
            ys,ps,bs,cs=fit_symmetric_transit(ph,f,e,P,d0);ya,pa,ba,ca=fit_cometary_dust_tail(ph,f,e,d0)
            s['dust_fits']=dict(n=len(ph),symmetric_parameters=ps,tail_parameters=pa,chi2_symmetric=cs,chi2_tail=ca,bic_symmetric=bs,bic_tail=ba,delta_bic_count_corrected=cs-ca-2*np.log(len(ph)))
            # An independent multistart fit of exactly the symmetric repository family.
            best=None
            for width in [.04,.08,.12,.2]:
                for offset in [-.025,0,.025]:
                    def resid(p):return (f-symmetric_trapezoid_transit(ph-p[3],P,p[0],p[1],p[2]))/e
                    r=least_squares(resid,[.022,width,.2,offset],bounds=([0,.005,.05,-.05],[.8,.35,.45,.05]),x_scale='jac',max_nfev=1500,ftol=1e-10,xtol=1e-10)
                    if best is None or np.sum(r.fun**2)<np.sum(best.fun**2):best=r
            s['dust_fits']['multistart_symmetric']=dict(parameters=best.x,chi2=float(np.sum(best.fun**2)),success=bool(best.success))
            ym=symmetric_trapezoid_transit(ph-best.x[3],P,best.x[0],best.x[1],best.x[2])
            csvout('dust_models.csv',[dict(phase=a,flux=b,flux_err=c,symmetric=d,tail=g,multistart_symmetric=h) for a,b,c,d,g,h in zip(ph,f,e,ys,ya,ym)])
            fig,axes=plt.subplots(2,2,figsize=(11,7))
            plotbin(axes[0,0],lc,P,t0,'PDC-SAP',color='#176b8a');plotbin(axes[0,0],clean,P,t0,'Pipeline',color='#be5432')
            axes[0,0].set(title=f'KIC {k}: full orbital phase',xlabel='Orbital phase',ylabel='Relative flux − 1 (ppm)');axes[0,0].legend(fontsize=8)
            b=plotbin(axes[0,1],clean,P,t0,'Pipeline bins',color='black',edges=np.linspace(-.12,.16,141))
            grid=np.linspace(-.12,.16,1500)
            dense_sym=symmetric_trapezoid_transit(grid-ps['t_offset'],P,ps['depth'],ps['duration_phase'],ps['ingress_ratio'])
            dense_tail=cometary_extinction_profile(grid,**pa)
            dense_multi=symmetric_trapezoid_transit(grid-best.x[3],P,best.x[0],best.x[1],best.x[2])
            for yy,lab,col in [(dense_sym,'Repository symmetric','#be5432'),(dense_tail,'Repository tail','#176b8a'),(dense_multi,'Multistart symmetric','#703c7c')]:
                axes[0,1].plot(grid,(yy-1)*1e6,lw=1,label=lab,color=col)
            axes[0,1].set(xlim=(-.12,.16),xlabel='Orbital phase',ylabel='Relative flux − 1 (ppm)',title=f'Models: N={len(ph)} unbinned points');axes[0,1].legend(fontsize=7)
            for yy,lab,col in [(ys,'Repository symmetric','#be5432'),(ya,'Repository tail','#176b8a'),(ym,'Multistart symmetric','#703c7c')]:
                bb=binned(ph,f-yy,e,np.linspace(-.12,.16,100));axes[1,0].errorbar(bb[:,0],bb[:,1]*1e6,yerr=bb[:,2]*1e6,fmt='.',ms=3,label=lab,color=col)
            axes[1,0].set(xlabel='Orbital phase',ylabel='Binned data − model (ppm)',title='Structured residuals');axes[1,0].axhline(0,color='gray',lw=.6)
            stats=[]
            for quarter in sorted(set(q)):
                m=q==quarter;phq=phase_fold(lc.time[m],P,t0);b=binned(phq,lc.flux[m],lc.flux_err[m],np.linspace(-.5,.5,101))
                axes[1,1].plot(b[:,0],(b[:,1]-1)*1e6,'.-',ms=2,label=f'Q{quarter}')
                # Descriptive central-minus-sideband eclipse contrast, by complete orbit.
                epochs=np.rint((lc.time[m]-t0)/P).astype(int);fq=lc.flux[m]
                for center,name in [(0.,'primary'),(.5,'secondary')]:
                    contrasts=[]
                    for ep in np.unique(epochs):
                        z=epochs==ep;dist=np.abs((phq-center+.5)%1-.5)
                        inside=z&(dist<.02);outside=z&(dist>.09)&(dist<.14)
                        if inside.sum()>=1 and outside.sum()>=3:contrasts.append(np.mean(fq[outside])-np.mean(fq[inside]))
                    stats.append(dict(quarter=int(quarter),feature=name,n_orbits=len(contrasts),contrast_ppm=float(np.mean(contrasts)*1e6),orbit_sem_ppm=float(np.std(contrasts,ddof=1)/np.sqrt(len(contrasts))*1e6)))
            s['eclipse_contrasts']=stats
            axes[1,1].set(xlabel='Orbital phase',ylabel='Relative flux − 1 (ppm)',title='Quarter-resolved PDC-SAP');axes[1,1].legend(fontsize=8)
            fig.tight_layout();figsave('morphology_9944201')
        if k==8308347:
            s['trojan']={}
            fig,axes=plt.subplots(3,1,figsize=(10,9))
            for mode,data,color in [('pdc',lc,'#176b8a'),('pipeline',clean,'#be5432'),('masked',protected,'#703c7c')]:
                tr=detect_trojan_companions(data.time,data.flux,data.flux_err,P,t0);s['trojan'][mode]=conv(tr)
                axes[0].plot(data.time,(data.flux-1)*1e3,'.',ms=1,label=mode,color=color)
                plotbin(axes[1],data,P,t0,mode,color=color)
            axes[0].set(xlabel='Time (BKJD)',ylabel='Relative flux − 1 (ppt)',title='KIC 8308347: preprocessing comparison');axes[0].legend()
            axes[1].set(xlabel='Orbital phase',ylabel='Relative flux − 1 (ppm)');axes[1].legend()
            for center in [-1/6,1/6]:axes[1].axvline(center,color='gray',ls='--',lw=.8)
            # Fixed phase aperture at the original pipeline-selected center, separate by orbit.
            center=s['trojan']['pipeline']['phase_offset'];s['trojan_epoch_apertures']=[]
            for mode,data in [('pdc',lc),('pipeline',clean),('masked',protected)]:
                ph=phase_fold(data.time,P,t0);eps=np.rint((data.time-t0)/P).astype(int)
                for ep in np.unique(eps):
                    dist=np.abs(ph-center);inside=(eps==ep)&(dist<.005);side=(eps==ep)&(dist>.01)&(dist<.025)
                    if inside.sum()<3 or side.sum()<3:continue
                    diff=np.mean(data.flux[side])-np.mean(data.flux[inside])
                    s['trojan_epoch_apertures'].append(dict(method=mode,epoch=int(ep),center_phase=center,n_in=int(inside.sum()),n_side=int(side.sum()),global_depth_ppm=float((1-np.mean(data.flux[inside]))*1e6),local_contrast_ppm=float(diff*1e6)))
            ph=phase_fold(lc.time,P,t0);eps=np.rint((lc.time-t0)/P).astype(int)
            for ep in np.unique(eps):
                m=(eps==ep)&(np.abs(ph-1/6)<.04)
                if m.sum()>2:
                    b=binned(ph[m],lc.flux[m],lc.flux_err[m],np.linspace(.125,.21,45));axes[2].errorbar(b[:,0],(b[:,1]-1)*1e6,yerr=b[:,2]*1e6,fmt='.-',ms=3,label=f'Orbit {ep}')
            axes[2].axvline(center,color='gray',ls='--',label='Pipeline-selected phase');axes[2].set(xlabel='Orbital phase',ylabel='PDC-SAP relative flux − 1 (ppm)',title='Positive-phase region, separated by orbit');axes[2].legend()
            fig.tight_layout();figsave('coorbital_8308347')
        summary[str(k)]=s
        savejson(OUT/'analysis/results.json',summary)
    csvout('fits_manifest.csv',manifest);csvout('pipeline_reproduction.csv',controlrows);csvout('timing_all_methods.csv',timingrows)
    savejson(OUT/'analysis/results.json',summary)
    savejson(OUT/'analysis/environment.json',dict(python=sys.version,platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__,astropy=astropy.__version__))
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in list((ROOT/'frontier_astronomy').rglob('*.py'))+list((ROOT/'tests').rglob('*.py'))+[ROOT/'scan_nasa_archive.py',ROOT/'results/real_nasa_discoveries.json',ROOT/'data/nasa_candidates_usp.json',ROOT/'data/nasa_candidates_moon.json']}
    savejson(OUT/'analysis/source_hashes.json',hashes)
    fig,ax=plt.subplots(figsize=(10,4));xs=np.arange(len(controlrows));ax.bar(xs,[r['ttv_snr'] for r in controlrows],color=['#777777' if r['saved_verdict']=='Symmetric Planet Transit (Standard)' else '#176b8a' for r in controlrows]);ax.set_xticks(xs,[str(r['kepid']) for r in controlrows],rotation=60,ha='right',fontsize=7);ax.set(ylabel='Pipeline timing scatter score',xlabel='KIC identifier',title='Cached campaign reproduction; gray = originally unflagged');fig.tight_layout();figsave('campaign_comparison')
if __name__=='__main__':main()
