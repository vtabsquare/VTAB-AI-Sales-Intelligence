"use client";
import {apiFetch, apiJson, reportApiError} from "../../lib/api";
 import {useEffect,useState} from "react"; const API="/backend-api";
export default function Page(){const [sources,setSources]=useState<any[]>([]),[qs,setQs]=useState<string[]>([]),[result,setResult]=useState<any>(null),[busy,setBusy]=useState(false),[form,setForm]=useState({name:"",source_type:"RSS",base_url:""}); const load=async()=>{
  try {
    const [sr, qr] = await Promise.all([
      apiFetch(`${API}/platform/sources`, { cache: "no-store" }),
      apiFetch(`${API}/platform/discovery/queries`, { cache: "no-store" })
    ]);
    const sd = await sr.json().catch(()=>[]);
    const qd = await qr.json().catch(()=>({queries:[]}));
    setSources(sd);
    setQs(qd.queries);
  } catch(error) {
    reportApiError(error);
    setSources([]);
    setQs([]);
  }
};useEffect(()=>{load()},[]);async function run(){try{setBusy(true);const r=await apiFetch(`${API}/platform/discovery/run`,{method:"POST"});setResult(await r.json());setBusy(false)}catch(error){reportApiError(error)}finally{setBusy(false)}}async function add(){try{await apiFetch(`${API}/platform/sources`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({...form,active:true})});setForm({name:"",source_type:"RSS",base_url:""});load()}catch(error){reportApiError(error)}finally{setBusy(false)}}return <main className="nx-page"><header className="nx-hero"><div><small>LIVE OPPORTUNITY ENGINE</small><h1>Global Discovery Command Center</h1><p>Search real configured sources, retain evidence URLs, deduplicate results and match buyer intent against the VTAB portfolio.</p></div><button className="nx-primary nx-big" onClick={run} disabled={busy}>{busy?"Searching global sources…":"⌁ Run Discovery Now"}</button></header>{result?.errors?.length>0&&<div role="alert" className="vtab-alert error">{result.errors.map((e:{source:string;message:string},i:number)=><p key={i}>{e.source}: {e.message}</p>)}</div>}{result&&<div className="nx-metrics"><Metric n={result.raw_results} t="Raw results"/><Metric n={result.new_opportunities} t="New opportunities"/><Metric n={result.qualified} t="Qualified"/><Metric n={result.queries_generated} t="Queries"/></div>}<section className="nx-grid"><div className="nx-card nx-span2"><h2>Discovery connectors</h2>{(Array.isArray(sources) ? sources : []).map(x=><div className="nx-row" key={x.id}><div className="nx-icon">◎</div><div><b>{x.name}</b><p>{x.source_type} · {x.base_url||"Provider-managed endpoint"}</p></div><span className="nx-status">{x.active?"ONLINE":"OFF"}</span></div>)}</div><div className="nx-card"><h2>Add source</h2><label>Name<input value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></label><label>Type<select value={form.source_type} onChange={e=>setForm({...form,source_type:e.target.value})}><option>RSS</option><option>WEBSITE</option><option>WEB_SEARCH</option></select></label><label>Feed / website URL<input value={form.base_url} onChange={e=>setForm({...form,base_url:e.target.value})}/></label><button className="nx-primary" onClick={add}>＋ Add connector</button></div><div className="nx-card nx-span3"><h2>AI-generated search intents</h2><div className="nx-query-cloud">{(Array.isArray(qs) ? qs : []).slice(0,30).map(q=><span key={q}>{q}</span>)}</div></div></section></main>}
function Metric({n,t}:any){return <div className="nx-metric"><strong>{n??0}</strong><span>{t}</span></div>}
