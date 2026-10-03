"use client";
import {apiFetch, apiJson, reportApiError} from "../../lib/api";


import { useCallback, useEffect, useMemo, useState } from "react";

const API = "/backend-api";

type ResponseItem = { id:string; sender_name?:string|null; sender_email?:string|null; subject?:string|null; body_text?:string|null; summary?:string|null; classification?:string|null; suggested_action?:string|null; suggested_reply?:string|null; received_at?:string|null; sentiment?:string|null; confidence?:number|null; matched?:boolean; is_customer_response?:boolean };
type FollowUp = { id:string; action_type?:string|null; draft_subject?:string|null; reason?:string|null; status?:string|null; due_at?:string|null; draft_body?:string|null };
type Pipeline = { opportunities_total?:number; inbox_messages_total?:number; responses_total?:number; filtered_messages_total?:number; matched_responses_total?:number; follow_ups_pending?:number; follow_ups_approved?:number };

async function json<T>(path:string, init?:RequestInit):Promise<T>{
  const r=await apiFetch(`${API}${path}`,{...init,cache:"no-store"});
  const body=await r.json().catch(()=>null);
  if(!r.ok) throw new Error(body?.detail||body?.message||`${r.status} ${r.statusText}`);
  return body as T;
}

export default function ResponsesPage(){
  const [responses,setResponses]=useState<ResponseItem[]>([]);
  const [followups,setFollowups]=useState<FollowUp[]>([]);
  const [pipeline,setPipeline]=useState<Pipeline>({});
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [acting,setActing]=useState<string|null>(null);
  const [notice,setNotice]=useState("");
  const [filter,setFilter]=useState<string>("ALL");
  const [error,setError]=useState("");
  const [selected,setSelected]=useState<ResponseItem|null>(null);

  const load=useCallback(async()=>{
    setLoading(true);setError("");
    const results=await Promise.allSettled([
      json<ResponseItem[]>("/responses"),json<FollowUp[]>("/follow-ups"),json<Pipeline>("/pipeline")
    ]);
    const errs:string[]=[];
    if(results[0].status==="fulfilled") setResponses(Array.isArray(results[0].value)?results[0].value:[]); else errs.push(`Responses: ${results[0].reason?.message||"failed"}`);
    if(results[1].status==="fulfilled") setFollowups(Array.isArray(results[1].value)?results[1].value:[]); else errs.push(`Follow-ups: ${results[1].reason?.message||"failed"}`);
    if(results[2].status==="fulfilled") setPipeline(results[2].value||{}); else errs.push(`Pipeline: ${results[2].reason?.message||"failed"}`);
    setError(errs.join(" • "));setLoading(false);
  },[]);
  useEffect(()=>{void load()},[load]);

  async function sync(){setBusy(true);setError("");setNotice("");try{const d=await json<any>("/responses/sync",{method:"POST"});setNotice(d?.message||`Inbox sync completed. ${d?.processed??0} new message(s).`);await load()}catch(e:any){setError(e?.message||"Microsoft 365 synchronization failed.")}finally{setBusy(false)}}
  async function reprocess(){setBusy(true);setError("");setNotice("");try{const d=await json<any>("/responses/reprocess",{method:"POST"});setNotice(d?.message||"Existing inbox intelligence reprocessed.");await load()}catch(e:any){setError(e?.message||"Reprocessing failed.")}finally{setBusy(false)}}
  async function act(id:string,action:"approve"|"dismiss"|"prepare-outreach"){setActing(id);setError("");try{const d=await json<{message?:string}>(`/follow-ups/${id}/${action}`,{method:"POST"});setNotice(d.message|| (action==="approve"?"Follow-up approved for the next human-controlled step.":action==="prepare-outreach"?"Follow-up draft prepared for approval.":"Follow-up dismissed."));await load()}catch(e:any){setError(e?.message||"Follow-up update failed.")}finally{setActing(null)}}

  const pending=useMemo(()=>pipeline.follow_ups_pending??followups.filter(x=>x.status==="PENDING").length,[pipeline,followups]);
  const visible=useMemo(()=>responses.filter(x=>{
    if(filter==="ALL") return true;
    if(filter==="CUSTOMER") return x.is_customer_response;
    if(filter==="FILTERED") return !x.is_customer_response;
    return x.classification===filter;
  }),[responses,filter]);
  return <div className="vtab-sales-page">
    <header className="vtab-sales-hero"><div><div className="vtab-sales-kicker"><i/> AI RESPONSE INTELLIGENCE</div><h1>Response &amp; Follow-up Center</h1><p>Turn customer replies into structured intelligence while keeping every outbound action under human control.</p></div><div className="vtab-hero-actions"><span className="vtab-live-chip"><i/> Microsoft 365 channel</span><button onClick={reprocess} disabled={busy}>Reprocess Intelligence</button><button className="vtab-primary-action" onClick={sync} disabled={busy}>{busy?"Processing…":"↻ Sync Microsoft 365"}</button></div></header>
    {error&&<div className="vtab-alert error"><div><b>Response intelligence needs attention</b><span>{error}</span></div><button onClick={()=>void load()}>Retry</button></div>}
    {notice&&<div className="vtab-alert success"><div><b>Operation completed</b><span>{notice}</span></div></div>}
    <div className="vtab-sales-kpis">
      <Kpi icon="◇" label="OPPORTUNITIES" value={pipeline.opportunities_total??0} sub="Tracked pipeline" />
      <Kpi icon="✉" label="INBOX MESSAGES" value={pipeline.inbox_messages_total??responses.length} sub="Read-only synchronized" />
      <Kpi icon="↩" label="QUALIFIED RESPONSES" value={pipeline.responses_total??responses.filter(x=>x.is_customer_response).length} sub={`${pipeline.matched_responses_total??0} matched to outreach`} />
      <Kpi icon="◷" label="PENDING FOLLOW-UPS" value={pending} sub="Human review required" tone="amber" />

    </div>
    <div className="vtab-sales-grid">
      <section className="vtab-sales-panel"><div className="vtab-panel-head"><div><span>INBOUND INTELLIGENCE</span><h2>Customer Responses</h2><p>AI-classified replies synchronized from your communication channel.</p></div><div className="vtab-filter-row">{[
        ["ALL","All"],["CUSTOMER","Customer Replies"],["PROCUREMENT_UPDATE","Procurement"],["AUTOMATED_NOTIFICATION","Automated"],["BOUNCE_NDR","Bounces"],["INTERNAL","Internal"],["NEWSLETTER_MARKETING","Marketing"],["NEEDS_REVIEW","Needs Review"]
      ].map(([key,label])=><button key={key} className={filter===key?"active":""} onClick={()=>setFilter(key)}>{label}</button>)} <span className="vtab-count-chip">{visible.length} shown</span></div></div>
      {loading?<Skeleton/>:visible.length===0?<Empty icon="↩" title="No customer responses yet" text="Once Microsoft 365 is synchronized, customer replies and AI classifications will appear here."/>:<div className="vtab-response-list">{visible.map(x=><article className="vtab-response-item clickable" key={x.id} onClick={()=>setSelected(x)} role="button" tabIndex={0} onKeyDown={e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();setSelected(x)}}}><div className="vtab-response-avatar">{(x.sender_name||x.sender_email||"?").slice(0,1).toUpperCase()}</div><div className="vtab-response-copy"><div><strong>{x.sender_name||x.sender_email||"Unknown sender"}</strong><small>{x.sender_email} {x.matched?"· MATCHED TO OUTREACH":"· UNMATCHED"}</small></div><h3>{x.subject||"Customer response"}</h3><p>{x.summary||"Awaiting AI summary."}</p><div className="vtab-next-action"><b>AI suggested action</b><span>{x.suggested_action||"Human review required"}</span></div></div><div className="vtab-response-meta"><span className={`vtab-intent ${String(x.classification||"review").toLowerCase()}`}>{String(x.classification||"NEEDS REVIEW").replaceAll("_"," ")}</span>{x.received_at&&<small>{new Date(x.received_at).toLocaleString()}</small>}</div></article>)}</div>}</section>
      <section className="vtab-sales-panel"><div className="vtab-panel-head"><div><span>HUMAN-CONTROLLED AUTOMATION</span><h2>Follow-up Queue</h2><p>AI recommendations remain blocked until a person approves them.</p></div><span className="vtab-count-chip amber">{pending} pending</span></div>
      {loading?<Skeleton/>:followups.length===0?<Empty icon="✓" title="Follow-up queue is clear" text="Recommended next actions will appear here when response intelligence creates them."/>:<div className="vtab-followup-list">{followups.map(x=><article className="vtab-followup-item" key={x.id}><div><span className="vtab-action-type">{x.action_type||"FOLLOW-UP"}</span><h3>{x.draft_subject||"Follow-up action"}</h3><p>{x.reason||"Recommended by response intelligence."}</p><pre>{x.draft_body}</pre><small>Status: {x.status||"PENDING"} · Due: {x.due_at?new Date(x.due_at).toLocaleString():"Not scheduled"}</small></div>{x.status==='APPROVED'&&<button onClick={()=>act(x.id,'prepare-outreach')} disabled={acting===x.id}>Prepare follow-up draft</button>}{x.status==="PENDING"&&<div className="vtab-inline-actions"><button onClick={()=>act(x.id,"dismiss")} disabled={acting===x.id}>Dismiss</button><button className="primary" onClick={()=>act(x.id,"approve")} disabled={acting===x.id}>{acting===x.id?"Processing…":"Approve Follow-up"}</button></div>}</article>)}</div>}</section>
    </div>
    {selected&&<div className="response-modal-backdrop" onClick={()=>setSelected(null)}><section className="response-modal" onClick={e=>e.stopPropagation()}><header><div><span>INBOUND MESSAGE DETAIL</span><h2>{selected.subject||"Customer response"}</h2><p>{selected.sender_name||selected.sender_email} · {selected.sender_email}</p></div><button className="icon-button" onClick={()=>setSelected(null)} aria-label="Close">×</button></header><div className="response-detail-grid"><div><small>CLASSIFICATION</small><b>{String(selected.classification||"NEEDS_REVIEW").replaceAll("_"," ")}</b></div><div><small>RECEIVED</small><b>{selected.received_at?new Date(selected.received_at).toLocaleString():"—"}</b></div><div><small>SENTIMENT</small><b>{selected.sentiment||"—"}</b></div><div><small>CONFIDENCE</small><b>{selected.confidence??0}%</b></div></div><div className="response-body-card"><div className="detail-label">COMPLETE MESSAGE</div><pre>{selected.body_text||selected.summary||"No message body was stored."}</pre></div><div className="response-body-card accent"><div className="detail-label">AI SUMMARY & NEXT ACTION</div><p>{selected.summary}</p><b>{selected.suggested_action}</b></div>{selected.suggested_reply&&<div className="response-body-card"><div className="detail-label">SUGGESTED REPLY · HUMAN APPROVAL REQUIRED</div><pre>{selected.suggested_reply}</pre></div>}</section></div>}
  </div>
}
function Kpi({icon,label,value,sub,tone="blue"}:{icon:string,label:string,value:number,sub:string,tone?:string}){return <div className={`vtab-sales-kpi ${tone}`}><div className="vtab-sales-kpi-icon">{icon}</div><div><span>{label}</span><strong>{value}</strong><small>{sub}</small></div></div>}
function Empty({icon,title,text}:{icon:string,title:string,text:string}){return <div className="vtab-sales-empty"><div>{icon}</div><h3>{title}</h3><p>{text}</p></div>}
function Skeleton(){return <div className="vtab-loading"><i/><i/><i/></div>}
