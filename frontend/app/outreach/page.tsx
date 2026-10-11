"use client";

import {useEffect,useMemo,useState} from "react";
import {apiJson} from "../../lib/api";

type Recipient={name?:string|null;title?:string|null;email?:string|null;verification?:string|null;verified?:boolean;do_not_contact?:boolean;source?:string|null};
type Item={
  id:string;opportunity_id:string;contact_id?:string|null;subject:string;body_text:string;status:string;created_at?:string|null;
  human_approved?:boolean;send_allowed?:boolean;blocked_reason?:string|null;
  recipient?:Recipient|null;
  opportunity?:{title?:string|null;country?:string|null;source_name?:string|null;source_url?:string|null;qualification_score?:number|null}|null;
  company?:{name?:string|null;website?:string|null}|null;
  evidence?:{status?:string|null;published_emails?:string[];published_phones?:string[];source_url?:string|null}|null;
};
type Provider={demo_mode:boolean;provider:string;configured:boolean;sender?:string|null;live_send_enabled:boolean};

function Icon({name}:{name:"send"|"shield"|"user"|"check"|"refresh"|"search"|"mail"|"spark"}){
  const p:Record<string,string>={
    send:"M22 2 11 13",shield:"M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z",user:"M20 21a8 8 0 0 0-16 0 M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z",check:"m20 6-11 11 11-5-5",refresh:"M20 11a8 8 0 1 0-2.34 5.66 M20 4v7h-7",search:"m21 21-4.35-4.35 M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z",mail:"M4 4h16v16H4z M22 6l-10 7L2 6",spark:"M12 3l1.9 4.1L18 9l-4.1 1.9L12 15l-1.9-4.1L6 9l4.1-1.9L12 3Z"
  };
  return <svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d={p[name]}/></svg>;
}

export default function SendCenter(){
  const [items,setItems]=useState<Item[]>([]);
  const [provider,setProvider]=useState<Provider|null>(null);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState<string|null>(null);
  const [message,setMessage]=useState<{kind:"success"|"error"|"info";text:string}|null>(null);
  const [query,setQuery]=useState("");
  const [selected,setSelected]=useState<Item|null>(null);
  const [confirming,setConfirming]=useState<Item|null>(null);

  async function load(){
    setLoading(true);
    try{
      const [rows,p]=await Promise.all([
        apiJson<Item[]>("/outreach/send-center-v2"),
        apiJson<Provider>("/outreach/provider-status")
      ]);
      setItems(rows);setProvider(p);setMessage(null);
    }catch(e:any){setMessage({kind:"error",text:e?.message||"Unable to load Send Center."});}
    finally{setLoading(false);}
  }
  useEffect(()=>{load();},[]);

  const filtered=useMemo(()=>{
    const q=query.trim().toLowerCase();
    if(!q)return items;
    return items.filter(x=>[x.subject,x.recipient?.email,x.company?.name,x.opportunity?.country,x.opportunity?.title].some(v=>(v||"").toLowerCase().includes(q)));
  },[items,query]);
  const ready=items.filter(x=>x.send_allowed).length;
  const verified=items.filter(x=>x.recipient?.verified).length;
  const blocked=items.length-ready;

  async function resolve(item:Item){
    setBusy(item.id);setMessage(null);
    try{
      const r=await apiJson<any>(`/outreach/${item.id}/resolve-recipient`,{method:"POST"});
      setMessage({kind:r.resolved?"success":"info",text:r.resolved?`Recipient resolved: ${r.email||"contact found"}`:(r.message||"No published recipient found.")});
      await load();
    }catch(e:any){setMessage({kind:"error",text:e?.message||"Recipient resolution failed."});}
    finally{setBusy(null);}
  }

  async function verifyPublished(item:Item){
    const email=item.recipient?.email;
    if(!email){setMessage({kind:"info",text:"Resolve a published recipient before verification."});return;}
    setBusy(item.id);setMessage(null);
    try{
      const r=await apiJson<any>(`/outreach/${item.id}/human-verify-published-recipient`,{
        method:"POST",body:JSON.stringify({confirmation:true,evidence_note:`Human review confirmed ${email} against the opportunity's published source evidence.`})
      });
      setMessage({kind:"success",text:r.message||"Recipient verified against published evidence."});
      await load();
    }catch(e:any){setMessage({kind:"error",text:e?.message||"Published-evidence verification failed."});}
    finally{setBusy(null);}
  }

  async function sendNow(item:Item){
    setBusy(item.id);setMessage(null);
    try{
      const r=await apiJson<any>(`/outreach/${item.id}/send`,{method:"POST",body:JSON.stringify({confirmed:true})});
      setConfirming(null);
      setMessage({kind:"success",text:r.message||((r.demo_mode||provider?.demo_mode)?"Simulated send completed.":"Message accepted for delivery.")});
      await load();
    }catch(e:any){setMessage({kind:"error",text:e?.message||"Send failed."});}
    finally{setBusy(null);}
  }

  return <div className="vtab-premium-page">
    <div className="vtab-hero" style={{marginBottom:18}}>
      <div style={{display:"flex",justifyContent:"space-between",gap:20,alignItems:"flex-start",position:"relative",zIndex:1}}>
        <div>
          <div className="vtab-eyebrow">Controlled outbound communication</div>
          <h1 className="vtab-title">Send Center</h1>
          <p className="vtab-subtitle">A human-controlled delivery cockpit. Only approved messages with a verified, non-suppressed recipient can be released.</p>
        </div>
        <div style={{display:"flex",gap:10,alignItems:"center",flexWrap:"wrap",justifyContent:"flex-end"}}>
          <span className="vtab-pill"><span className="vtab-dot" style={{background:provider?.demo_mode?"#f59e0b":"#10b981"}}/>{provider?.demo_mode?"DEMO · simulated delivery":"LIVE · Microsoft Graph"}</span>
          <button className="vtab-btn vtab-btn-ghost" onClick={load} disabled={loading}><Icon name="refresh"/>{loading?"Refreshing":"Refresh"}</button>
        </div>
      </div>
    </div>

    {message&&<div className={`vtab-message vtab-message-${message.kind}`}>{message.text}</div>}

    <div className="vtab-grid vtab-grid-4" style={{marginBottom:18}}>
      <div className="vtab-stat"><div className="vtab-stat-label">Approved queue</div><div className="vtab-stat-value">{items.length}</div><div className="vtab-stat-note">Human-approved messages</div></div>
      <div className="vtab-stat"><div className="vtab-stat-label">Verified recipients</div><div className="vtab-stat-value">{verified}</div><div className="vtab-stat-note">Evidence-backed contacts</div></div>
      <div className="vtab-stat"><div className="vtab-stat-label">Ready to send</div><div className="vtab-stat-value" style={{color:"#047857"}}>{ready}</div><div className="vtab-stat-note">All guardrails passed</div></div>
      <div className="vtab-stat"><div className="vtab-stat-label">Protected</div><div className="vtab-stat-value" style={{color:blocked?"#b45309":"#047857"}}>{blocked}</div><div className="vtab-stat-note">Blocked until requirements are met</div></div>
    </div>

    <div className="vtab-card">
      <div className="vtab-card-head">
        <div><div className="vtab-eyebrow">Delivery workspace</div><div style={{fontSize:20,fontWeight:900,marginTop:5}}>Approved outreach</div></div>
        <div style={{position:"relative",minWidth:280,maxWidth:380,flex:1}}>
          <span style={{position:"absolute",left:12,top:11,color:"#64748b"}}><Icon name="search"/></span>
          <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search company, subject, country or email" style={{width:"100%",height:42,padding:"0 12px 0 38px",border:"1px solid #dbe3ee"}}/>
        </div>
      </div>

      <div className="vtab-card-body">
        {loading?<div className="vtab-empty" style={{minHeight:260,display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",gap:14,textAlign:"center",padding:"40px 24px"}}><div className="vtab-empty-icon" style={{flex:"0 0 auto"}}><Icon name="spark"/></div><b style={{fontSize:18,lineHeight:1.35}}>Loading controlled delivery queue…</b></div>:
        filtered.length===0?<div className="vtab-empty" style={{minHeight:300,display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",gap:14,textAlign:"center",padding:"48px 24px",width:"100%",boxSizing:"border-box"}}><div className="vtab-empty-icon" style={{flex:"0 0 auto",margin:0}}><Icon name="check"/></div><div style={{fontSize:"clamp(20px,2.2vw,26px)",lineHeight:1.2,fontWeight:900,color:"#183153",maxWidth:560,width:"100%",whiteSpace:"normal",wordBreak:"normal"}}>No approved outreach waiting</div><p style={{margin:0,maxWidth:620,fontSize:"clamp(13px,1.2vw,15px)",lineHeight:1.65,color:"#718096",whiteSpace:"normal"}}>Messages appear here after human approval. Nothing is released automatically.</p></div>:
        <div style={{display:"grid",gap:14}}>{filtered.map(item=>{
          const recipient=item.recipient||{};const isBusy=busy===item.id;
          return <article key={item.id} style={{border:"1px solid rgba(148,163,184,.27)",borderRadius:18,padding:18,background:"linear-gradient(180deg,#fff,#fbfdff)",boxShadow:"0 8px 24px rgba(15,23,42,.055)"}}>
            <div style={{display:"flex",justifyContent:"space-between",gap:16,alignItems:"flex-start",flexWrap:"wrap"}}>
              <div style={{minWidth:0,flex:1}}>
                <div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap",marginBottom:8}}>
                  <span className="vtab-status vtab-status-info"><Icon name="shield"/> Approved</span>
                  {item.send_allowed?<span className="vtab-status vtab-status-ready"><Icon name="check"/> Ready</span>:<span className="vtab-status vtab-status-warn">Protected</span>}
                  {item.opportunity?.qualification_score!=null&&<span className="vtab-pill">AI fit {item.opportunity.qualification_score}</span>}
                </div>
                <h3 style={{fontSize:18,fontWeight:900,margin:"0 0 5px",color:"#12213a"}}>{item.subject}</h3>
                <div style={{fontSize:13,color:"#718096"}}>{item.company?.name||"Organization pending"}{item.opportunity?.country?` · ${item.opportunity.country}`:""}</div>
              </div>
              <button className="vtab-btn vtab-btn-ghost" onClick={()=>setSelected(item)}>Review message</button>
            </div>

            <div className="vtab-grid vtab-grid-2" style={{marginTop:16}}>
              <div style={{border:"1px solid #e5ebf3",borderRadius:14,padding:14,background:"#fbfdff"}}>
                <div className="vtab-stat-label">Recipient intelligence</div>
                <div style={{display:"flex",gap:10,alignItems:"center",marginTop:9}}><span style={{width:34,height:34,borderRadius:10,display:"grid",placeItems:"center",background:"#eef2ff",color:"#4f46e5"}}><Icon name="user"/></span><div><b>{recipient.name||"Recipient not identified"}</b><div style={{fontSize:12,color:"#718096"}}>{recipient.email||"No email captured"}</div></div></div>
                <div style={{marginTop:10,display:"flex",gap:7,flexWrap:"wrap"}}>
                  <span className={`vtab-status ${recipient.verified?"vtab-status-ready":"vtab-status-warn"}`}>{recipient.verification||"UNVERIFIED"}</span>
                  {recipient.do_not_contact&&<span className="vtab-status vtab-status-blocked">Do not contact</span>}
                </div>
              </div>
              <div style={{border:"1px solid #e5ebf3",borderRadius:14,padding:14,background:"#fbfdff"}}>
                <div className="vtab-stat-label">Published evidence</div>
                <div style={{fontSize:13,marginTop:9,color:"#334155"}}>{item.evidence?.status||"Not captured"}</div>
                <div style={{fontSize:12,color:"#718096",marginTop:5}}>{item.evidence?.published_emails?.length||0} published email candidate(s)</div>
                {item.blocked_reason&&<div style={{fontSize:12,color:"#b45309",marginTop:8,fontWeight:700}}>{item.blocked_reason}</div>}
              </div>
            </div>

            <div style={{display:"flex",gap:9,flexWrap:"wrap",marginTop:16,justifyContent:"flex-end"}}>
              {!recipient.email&&<button className="vtab-btn" disabled={isBusy} onClick={()=>resolve(item)}><Icon name="search"/>{isBusy?"Resolving…":"Resolve recipient"}</button>}
              {recipient.email&&!recipient.verified&&<button className="vtab-btn" disabled={isBusy} onClick={()=>verifyPublished(item)}><Icon name="shield"/>{isBusy?"Verifying…":"Verify published evidence"}</button>}
              <button className="vtab-btn vtab-btn-primary" disabled={!item.send_allowed||isBusy} onClick={()=>setConfirming(item)}><Icon name="send"/>Release message</button>
            </div>
          </article>
        })}</div>}
      </div>
    </div>

    {selected&&<div onClick={()=>setSelected(null)} style={{position:"fixed",inset:0,zIndex:1000,background:"rgba(15,23,42,.48)",backdropFilter:"blur(7px)",display:"grid",placeItems:"center",padding:20}}>
      <div onClick={e=>e.stopPropagation()} className="vtab-card" style={{width:"min(820px,96vw)",maxHeight:"86vh",overflow:"auto"}}>
        <div className="vtab-card-head"><div><div className="vtab-eyebrow">Human review</div><div style={{fontSize:20,fontWeight:900,marginTop:4}}>{selected.subject}</div></div><button className="vtab-btn" onClick={()=>setSelected(null)}>Close</button></div>
        <div className="vtab-card-body"><pre style={{whiteSpace:"pre-wrap",fontFamily:"inherit",lineHeight:1.7,color:"#334155",margin:0}}>{selected.body_text}</pre></div>
      </div>
    </div>}

    {confirming&&<div onClick={()=>setConfirming(null)} style={{position:"fixed",inset:0,zIndex:1001,background:"rgba(15,23,42,.56)",backdropFilter:"blur(8px)",display:"grid",placeItems:"center",padding:20}}>
      <div onClick={e=>e.stopPropagation()} className="vtab-card" style={{width:"min(560px,96vw)"}}>
        <div className="vtab-card-body" style={{padding:28}}>
          <div style={{width:52,height:52,borderRadius:16,display:"grid",placeItems:"center",background:"linear-gradient(135deg,#eff6ff,#eef2ff)",color:"#2563eb",marginBottom:16}}><Icon name="send"/></div>
          <div className="vtab-eyebrow">Final human confirmation</div>
          <h2 style={{fontSize:23,margin:"7px 0 8px"}}>Release this approved message?</h2>
          <p style={{color:"#64748b",lineHeight:1.6}}>Recipient: <b>{confirming.recipient?.email}</b>. {provider?.demo_mode?"Demo mode is active, so this delivery will be simulated and no real email will be sent.":"This will submit the message to Microsoft Graph for delivery."}</p>
          <div style={{display:"flex",gap:10,justifyContent:"flex-end",marginTop:22}}><button className="vtab-btn" onClick={()=>setConfirming(null)}>Cancel</button><button className="vtab-btn vtab-btn-primary" disabled={busy===confirming.id} onClick={()=>sendNow(confirming)}><Icon name="send"/>{busy===confirming.id?"Releasing…":"Confirm release"}</button></div>
        </div>
      </div>
    </div>}
  </div>;
}