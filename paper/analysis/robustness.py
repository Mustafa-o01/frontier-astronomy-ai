"""Additional measurements that isolate preprocessing, coverage and morphology."""
from reproduce import *
def shape(lc,P,t0,asym=False):
    ph=phase_fold(lc.time,P,t0);m=np.abs(ph)<.12;x=ph[m];f=lc.flux[m];e=lc.flux_err[m]
    cad=np.median(np.diff(lc.time))/P;xx=x[:,None]+np.linspace(-.5,.5,21)[None,:]*cad
    def model(p,z=xx):
        dep,dur,ing,dt,c,b=p[:6];sk=p[6] if len(p)==7 else 0
        shifted=z-dt;warp=shifted/np.where(shifted<0,1-sk,1+sk)
        sh=symmetric_trapezoid_transit(warp.ravel(),1,dep,dur,ing).reshape(z.shape).mean(axis=1)
        return c+b*z.mean(axis=1)+sh-1
    best=None
    for width in [.075,.1,.14]:
        p=[.023,width,.25,0,1,0]+([0] if asym else [])
        lo=[0,.03,.03,-.035,.95,-.1]+([-.6] if asym else [])
        hi=[.1,.2,.49,.035,1.05,.1]+([.6] if asym else [])
        r=least_squares(lambda p:(f-model(p))/e,p,bounds=(lo,hi),x_scale='jac',max_nfev=1500,ftol=1e-10,xtol=1e-10)
        if best is None or np.sum(r.fun**2)<np.sum(best.fun**2):best=r
    r=best;chi=float(np.sum(r.fun**2));cov=np.linalg.pinv(r.jac.T@r.jac)*max(1,chi/(len(f)-len(r.x)))
    return dict(n=len(f),k=len(r.x),chi2=chi,bic=chi+len(r.x)*np.log(len(f)),reduced_chi2=chi/(len(f)-len(r.x)),params=r.x,formal_scaled_errors=np.sqrt(np.diag(cov)),at_bound=bool(np.any(r.active_mask))), (x,f,e,model(r.x))

def main():
    results={};cliprows=[];coverage=[];shaperows=[]
    for k in TARGETS:
        lc,sap,q,man=load(k);meta=META[k];P=meta['koi_period'];t0=meta['koi_time0bk'];D=meta['koi_duration']/24
        clean=preprocess_light_curve(lc);kept=np.isin(lc.time,clean.time)
        ph=phase_fold(lc.time,P,t0);core=np.abs(ph)<D/(2*P)
        cliprows.append(dict(kepid=k,core_before=int(core.sum()),core_after=int((core&kept).sum()),core_removed=int((core&~kept).sum()),all_before=len(lc.time),all_after=len(clean.time)))
        for ep in range(int(np.floor((lc.time.min()-t0)/P)),int(np.ceil((lc.time.max()-t0)/P))+1):
            nom=t0+ep*P
            if k==9944201:continue
            if nom<lc.time.min()-2*D or nom>lc.time.max()+2*D:continue
            m=np.abs(lc.time-nom)<2*D
            coverage.append(dict(kepid=k,epoch=ep,nominal_bkjd=nom,n_within_half_catalog_duration=int(np.sum(np.abs(lc.time-nom)<D/2)),n_within_default_window=int(np.sum(np.abs(lc.time-nom)<.25)),n_within_1p5_catalog_duration=int(np.sum(np.abs(lc.time-nom)<1.5*D)),nearest_good_cadence_hours=float(np.min(np.abs(lc.time-nom))*24)))
        if k==9944201:
            fig,axes=plt.subplots(2,2,figsize=(11,7));shapeout={}
            for column,data in [('pdc',lc),('sap',sap)]:
                for quarter in [0]+sorted(set(q)):
                    z=data if quarter==0 else data.copy_with(time=data.time[q==quarter],flux=data.flux[q==quarter],flux_err=data.flux_err[q==quarter],quality=data.quality[q==quarter])
                    sy,sd=shape(z,P,t0,False);ay,ad=shape(z,P,t0,True)
                    key=f'{column}_'+('all' if quarter==0 else f'Q{quarter}');shapeout[key]=dict(symmetric=sy,asymmetric=ay,delta_bic=sy['bic']-ay['bic'])
                    shaperows.append(dict(method=column,quarter=quarter,n=sy['n'],delta_bic=sy['bic']-ay['bic'],skew=ay['params'][-1],skew_formal_scaled_error=ay['formal_scaled_errors'][-1],symmetric_reduced_chi2=sy['reduced_chi2'],asymmetric_reduced_chi2=ay['reduced_chi2']))
                    if column=='pdc':
                        ax=axes.ravel()[[0,1,2,3][[0,1,2,3].index(quarter)]]
                        x,f,e,ym=sd;b=binned(x,f,e,np.linspace(-.12,.12,100));ax.errorbar(b[:,0],(b[:,1]-1)*1e3,yerr=b[:,2]*1e3,fmt='.',ms=3,color='black',label='PDC-SAP')
                        for dat,label,col in [(sd,'Symmetric','#176b8a'),(ad,'Asymmetric','#be5432')]:
                            order=np.argsort(dat[0]);ax.plot(dat[0][order],(dat[3][order]-1)*1e3,lw=1,label=label,color=col)
                        ax.set(xlabel='Orbital phase',ylabel='Relative flux − 1 (ppt)',title=f'{key}, N={sy["n"]}, ΔBIC={sy["bic"]-ay["bic"]:.1f}');ax.legend(fontsize=7)
            fig.tight_layout();figsave('primary_9944201');results['primary_shapes']=shapeout
        if k in [8494263,10153011]:
            z=json.loads((OUT/'analysis/results.json').read_text())[str(k)]
            results[str(k)]={}
            for mode in ['local_pdc','local_sap']:
                rows=z[mode];oc=np.array([x['oc_min'] for x in rows]);e=np.array([x['mid_err_min'] for x in rows]);cs=float(np.sum((oc/e)**2));results[str(k)][mode]=dict(linear_chi2=cs,dof=len(rows)-2,formal_p=float(chi2.sf(cs,len(rows)-2)))
    csvout('clipping_counts.csv',cliprows);csvout('epoch_coverage.csv',coverage);csvout('primary_shape_comparison.csv',shaperows);savejson(OUT/'analysis/robustness.json',results)
    print(json.dumps(conv(results),indent=2))
if __name__=='__main__':main()
