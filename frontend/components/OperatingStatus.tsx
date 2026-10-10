"use client";
import Link from "next/link";
import {useEffect, useState} from "react";
import {apiJson} from "../lib/api";
interface Status {demo_mode:boolean; configured:boolean; inbox_sync_enabled:boolean; send_enabled:boolean;}
export default function OperatingStatus(){
 const [status,setStatus]=useState<Status|null>(null);
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 async function refresh(){setBusy(true);try{const data=await apiJson<Status>("/integrations/microsoft/status");if(typeof data.demo_mode!=="boolean")throw new Error("Operating mode response is invalid.");setStatus(data);setError("");}catch{setStatus(null);setError("Operating mode unavailable. Refresh status before sending.");}finally{setBusy(false);}}
 useEffect(()=>{void refresh();const onFocus=()=>void refresh();window.addEventListener("focus",onFocus);return()=>window.removeEventListener("focus",onFocus);},[]);
 return <section className={`operating-status ${status?.demo_mode ? "demo" : status ? "live" : "unknown"}`} aria-label="Operating mode" aria-live="polite">
  <strong>{status ? status.demo_mode ? "DEMO MODE" : "LIVE MODE" : busy ? "CHECKING MODE" : "MODE UNKNOWN"}</strong>
  <span>{error || (status ? status.demo_mode ? "Customer sends are simulated. Configured inbox sync remains available." : "Microsoft 365 sends follow owner approvals and the saved sales agent policy." : "Checking backend configuration…")}</span>
  <Link href="/admin">Integration settings</Link>
  <button type="button" disabled={busy} onClick={()=>void refresh()}>{busy ? "Checking…" : "Refresh mode"}</button>
 </section>;
}
