"use client";
import Link from "next/link";
import {useEffect, useState} from "react";
import {apiJson, reportApiError} from "../../lib/api";

type Policy={enabled:boolean;auto_initial_outreach:boolean;auto_acknowledge:boolean;daily_limit:number;batch_size:number};
type Review={id:string;status:string;draft_subject:string;draft_body:string;content_hash:string;scheduled_send_approved:boolean;analysis:{provider?:string;requested_details?:string[];missing_information?:string[];requires_manual_revision?:boolean}};
type Case={id:string;company_name:string;status:string;event_count:number;owner_notes:string};
const time=(s:string)=>new Date(s.endsWith("Z")||/[+-]\d\d:\d\d$/.test(s)?s:s+"Z").toLocaleString();

function ReviewCard({item, busy, action}:{item:Review;busy:boolean;action:(path:string,payload?:unknown)=>Promise<void>}){
 const [subject,setSubject]=useState(item.draft_subject),[body,setBody]=useState(item.draft_body),[feedback,setFeedback]=useState(""),[deliveryEvidence,setDeliveryEvidence]=useState("");
 useEffect(()=>{setSubject(item.draft_subject);setBody(item.draft_body)},[item.draft_subject,item.draft_body]);
 const dirty=subject!==item.draft_subject||body!==item.draft_body;
 const editable=item.status==='PENDING'||item.status==='APPROVED';
 return <article className="sales-review"><div className="panel-title"><h3>Client response review</h3><span className="status-pill">{item.status}</span></div>
  {item.analysis.provider&&<p>Writer: {item.analysis.provider}{item.analysis.provider==="LOCAL_STARTER"?" · Starter text; live AI is not configured":""}</p>}
  {(item.analysis.requested_details||[]).map((x,i)=><p key={i}><b>Client request:</b> {x}</p>)}
  {(item.analysis.missing_information||[]).map((x,i)=><p key={i}><b>Needs confirmation:</b> {x}</p>)}
  {item.analysis.requires_manual_revision&&<p role="status">AI revision is unavailable. Apply your suggestions in the editor before approving.</p>}
  <label>Subject<input value={subject} onChange={e=>setSubject(e.target.value)} maxLength={255} disabled={busy||!editable}/></label>
  <label>Response for owner review<textarea value={body} onChange={e=>setBody(e.target.value)} rows={9} maxLength={12000} disabled={busy||!editable}/></label>
  <label>Your suggestions<textarea value={feedback} onChange={e=>setFeedback(e.target.value)} rows={2} maxLength={4000} placeholder="For example: focus on Fabric adoption and ask about their current reporting stack." disabled={busy||!editable}/></label>
  <div className="sales-actions">
   <button className="btn-secondary" disabled={busy||!editable||!dirty||!body.trim()||!subject.trim()} onClick={()=>action(`/reviews/${item.id}/revise`,{subject,body_text:body,feedback})}>Save edited response</button>
   <button className="btn-secondary" disabled={busy||!editable||dirty} onClick={()=>action(`/reviews/${item.id}/revise`,{feedback})}>{item.analysis.provider?"Revise with AI":"Analyze & draft"}</button>
   <button className="btn-primary" disabled={busy||dirty||item.status!=="PENDING"||!body.trim()||item.analysis.requires_manual_revision===true} onClick={()=>action(`/reviews/${item.id}/approve`,{content_hash:item.content_hash})}>Approve for next cycle</button>
  </div>
  {!editable&&<div className="safety-note"><p>Delivery needs review. Check Microsoft Sent Items and provider records before requesting another attempt. A running worker must finish before reconciliation.</p><label>Evidence from your delivery check<textarea value={deliveryEvidence} onChange={e=>setDeliveryEvidence(e.target.value)} rows={2} maxLength={2000}/></label><div className="sales-actions"><button className="btn-secondary" disabled={busy||deliveryEvidence.trim().length<20} onClick={()=>action(`/reviews/${item.id}/reconcile`,{resolution:'SENT_CONFIRMED',evidence:deliveryEvidence})}>Confirm already sent</button><button className="btn-secondary" disabled={busy||deliveryEvidence.trim().length<20} onClick={()=>action(`/reviews/${item.id}/reconcile`,{resolution:'NOT_SENT_CONFIRMED',evidence:deliveryEvidence})}>Confirm not sent · review again</button></div></div>}
  {dirty&&<small>Save your changes before approval.</small>}
  <p>{item.scheduled_send_approved?"The reviewed version is approved for delivery in the next enabled cycle.":"Detailed responses require your approval. Approval authorizes the next enabled cycle to send this version."}</p>
 </article>;
}

export default function Page(){
 const [asset,setAsset]=useState({name:"",asset_type:"COMPANY_WEBSITE",url:""});
 const [status,setStatus]=useState<any>(null),[policy,setPolicy]=useState<Policy|null>(null),[reviews,setReviews]=useState<Review[]>([]),[cases,setCases]=useState<Case[]>([]),[selected,setSelected]=useState<any>(null),[sources,setSources]=useState<any>(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState(""),[notes,setNotes]=useState(""),[stage,setStage]=useState("ENGAGED");
 async function load(){const [s,r,c,i]=await Promise.all([apiJson<any>("/sales-manager/status"),apiJson<{items:Review[]}>("/sales-manager/reviews"),apiJson<{items:Case[]}>("/sales-manager/cases"),apiJson<any>("/sales-manager/sources/status")]);setStatus(s);setPolicy({enabled:s.policy.enabled,auto_initial_outreach:s.policy.auto_initial_outreach,auto_acknowledge:s.policy.auto_acknowledge,daily_limit:s.policy.daily_limit,batch_size:s.policy.batch_size});setReviews(r.items);setCases(c.items);setSources(i)}
 useEffect(()=>{load().catch(reportApiError)},[]);
 async function action(path:string,payload?:unknown){setBusy(true);setNotice("");try{const result=await apiJson<any>("/sales-manager"+path,{method:"POST",body:payload===undefined?undefined:JSON.stringify(payload)});setNotice(result.message||`Completed: ${result.result?.status||result.status||"saved"}`);await load()}catch(e){reportApiError(e)}finally{setBusy(false)}}
 async function addAsset(){setBusy(true);try{await apiJson("/platform/assets",{method:"POST",body:JSON.stringify({...asset,active:true})});setAsset({name:"",asset_type:"COMPANY_WEBSITE",url:""});setNotice("Source saved. Sync materials, then review imported knowledge.")}catch(e){reportApiError(e)}finally{setBusy(false)}}
 async function savePolicy(){setBusy(true);try{const result=await apiJson<any>("/sales-manager/policy",{method:"PUT",body:JSON.stringify(policy)});setNotice(result.message);await load()}catch(e){reportApiError(e)}finally{setBusy(false)}}
 async function openCase(id:string){setBusy(true);try{const d=await apiJson<any>("/sales-manager/cases/"+id);setSelected(d);setNotes(d.case.owner_notes);setStage(d.case.status)}catch(e){reportApiError(e)}finally{setBusy(false)}}
 async function saveCase(){setBusy(true);try{await apiJson<any>("/sales-manager/cases/"+selected.case.id,{method:"PATCH",body:JSON.stringify({status:stage,owner_notes:notes})});const d=await apiJson<any>("/sales-manager/cases/"+selected.case.id);setSelected(d);await load();setNotice("Casebook updated.")}catch(e){reportApiError(e)}finally{setBusy(false)}}
 return <main className="ops-page sales-manager"><header className="ops-hero"><div><small>VTAB SQUARE · SALES AGENT</small><h1>Sales Manager</h1><p>Discover requirements, prepare outreach, monitor replies and manage client cases.</p></div><Link className="btn-secondary" href="/schedulers">Set schedules →</Link></header>
  {notice&&<p role="status" className="safety-note">{notice}</p>}
  {!status||!policy?<p>Loading sales manager…</p>:<>
   <div className="ops-grid"><section className="ops-panel create-panel"><h2>Automation controls</h2><p><b>{status.demo_mode?"DEMO · All sends simulated":"LIVE · Real Microsoft email"}</b></p><p>Sender: {status.sender}<br/>Outbound attempts today: {status.attempts_today} / {status.effective_daily_limit}</p>
    <label className="sales-toggle"><input type="checkbox" checked={policy.enabled} onChange={e=>setPolicy({...policy,enabled:e.target.checked})}/> Enable sales agent</label>
    <label className="sales-toggle"><input type="checkbox" checked={policy.auto_initial_outreach} onChange={e=>setPolicy({...policy,auto_initial_outreach:e.target.checked})}/> Automatically send initial EOI to verified recipients</label>
    <label className="sales-toggle"><input type="checkbox" checked={policy.auto_acknowledge} onChange={e=>setPolicy({...policy,auto_acknowledge:e.target.checked})}/> Automatically acknowledge matched client replies</label>
    <div className="form-two"><label>Daily attempt limit<input type="number" min={1} max={100} value={policy.daily_limit} onChange={e=>setPolicy({...policy,daily_limit:Number(e.target.value)})}/></label><label>Leads per cycle<input type="number" min={1} max={50} value={policy.batch_size} onChange={e=>setPolicy({...policy,batch_size:Number(e.target.value)})}/></label></div>
    <div className="sales-actions"><button className="btn-primary" disabled={busy} onClick={savePolicy}>Save automation policy</button><button className="btn-secondary" disabled={busy||!status.policy.enabled} onClick={()=>action("/run")}>{busy?"Working…":"Run saved policy now"}</button></div>
    <p>Scheduler: {status.scheduler_recently_observed?"Recent heartbeat observed":"No recent heartbeat · check the always-on worker"}{status.scheduler_last_seen?` · ${time(status.scheduler_last_seen)}`:""}</p><p>Recipients need reviewed source evidence. Detailed answers always require your approval. Saves apply to later cycles.</p>
   </section><section className="ops-panel"><h2>Company materials</h2><label>Company source name<input value={asset.name} onChange={e=>setAsset({...asset,name:e.target.value})}/></label><label>Source type<select aria-label="Source type" value={asset.asset_type} onChange={e=>setAsset({...asset,asset_type:e.target.value})}><option value="COMPANY_WEBSITE">Company website</option><option value="GITHUB_REPOSITORY">GitHub repository README</option></select></label><label>Source URL<input type="url" value={asset.url} onChange={e=>setAsset({...asset,url:e.target.value})}/></label><button className="btn-secondary" disabled={busy||!asset.name.trim()||!asset.url.trim()} onClick={addAsset}>Add company source</button><p>Google Drive: {sources?.google_drive_configured?"Configured":"Requires read-only OAuth and folder IDs"}</p><p>GitHub private access: {sources?.github_private_read_configured?"Configured":"Read token not configured"}</p><p>AI writer: {status.ai_provider}{status.ai_configured?" · Credential configured":" · No AI credential"}</p>
    <div className="sales-actions"><button className="btn-secondary" disabled={busy} onClick={()=>action("/sources/sync")}>Sync configured materials</button><Link className="btn-secondary" href="/resources">Presentations & demo links</Link><Link className="btn-secondary" href="/knowledge">Review imported knowledge</Link><Link className="btn-secondary" href="/portfolio">Configure services</Link><Link className="btn-secondary" href="/discovery">Discovery sources</Link></div>
    <p>Imports need knowledge approval. Drive catalogs presentations and videos; add reviewed text summaries for AI use. Check sharing permissions before sending any material.</p>
   </section></div>
   <section className="ops-panel"><div className="panel-title"><h2>Responses awaiting owner review</h2><b>{reviews.length}</b></div>{reviews.length?reviews.map(item=><ReviewCard key={item.id} item={item} busy={busy} action={action}/>):<p>No pending responses. Matched client replies create review tasks after inbox sync.</p>}</section>
   <section className="ops-panel"><h2>Client casebooks</h2><p>The first matched external client reply opens a casebook. System notifications do not create cases.</p><div className="sales-case-list">{cases.map(c=><button className="btn-secondary" key={c.id} disabled={busy} onClick={()=>openCase(c.id)}>{c.company_name} · {c.status} · {c.event_count} events</button>)}{!cases.length&&<p>No client cases yet.</p>}</div>
    {selected&&<article className="sales-review"><h3>{selected.company.name}</h3><p>{selected.contacts.map((c:any)=>[c.full_name,c.email].filter(Boolean).join(" · ")).join(" | ")}</p>
     <label>Lead status<select value={stage} onChange={e=>setStage(e.target.value)}>{["RESPONDED","ENGAGED","PROPOSAL","NEGOTIATION","WON","LOST","CLOSED"].map(s=><option key={s}>{s}</option>)}</select></label>
     <label>Owner notes<textarea rows={3} value={notes} onChange={e=>setNotes(e.target.value)} maxLength={10000}/></label><button className="btn-primary" disabled={busy} onClick={saveCase}>Update casebook</button>
     {selected.research?.map((r:any)=><div className="sales-event" key={r.opportunity_id}><h4>Published contact candidates</h4><p>Emails: {r.published_emails.join(", ")||"None found"}<br/>Phone numbers: {r.published_phones.join(", ")||"None found"}</p><p>Evidence: {r.evidence_status} · {r.source_url}</p><small>Source extraction requires recipient and organization review.</small></div>)}<h3>Conversation & decision history</h3>{selected.events.map((e:any)=><article className="sales-event" key={e.id}><small>{time(e.created_at)} · {e.kind}</small><h4>{e.subject}</h4><p style={{whiteSpace:"pre-wrap"}}>{e.body}</p>{e.details?.delivery_status&&<small>Delivery: {e.details.delivery_status}</small>}</article>)}
    </article>}
   </section>
  </>}
 </main>;
}
