"use client";

import Link from "next/link";

const stages = [
  { n:"01", title:"Discover Opportunities", tag:"AI AGENT", href:"/opportunities", text:"Find and review global opportunities from permitted sources." },
  { n:"02", title:"Qualify & Research", tag:"AI AGENT", href:"/opportunities", text:"Score fit, research the organization and prepare contact context." },
  { n:"03", title:"Human Approval", tag:"HUMAN GATE", href:"/approval", text:"Review outreach drafts before anything can progress to delivery." },
  { n:"04", title:"Controlled Send", tag:"CONTROLLED", href:"/outreach", text:"Verify recipient, confirm final content and send only after approval." },
  { n:"05", title:"Microsoft 365", tag:"INTEGRATION", href:"/admin", text:"Validate the governed Outlook / Microsoft Graph connection." },
  { n:"06", title:"Inbox Sync", tag:"READ ONLY", href:"/responses", text:"Synchronize inbound mailbox messages without moving or deleting mail." },
  { n:"07", title:"Smart Intelligence", tag:"AI AGENT", href:"/responses", text:"Filter automation, procurement, bounces and marketing from customer replies." },
  { n:"08", title:"Response Matching", tag:"AI AGENT", href:"/responses", text:"Match genuine replies to known contacts, outreach drafts and opportunities." },
  { n:"09", title:"Follow-up Approval", tag:"HUMAN GATE", href:"/responses", text:"Review AI-suggested responses and approve or dismiss the next action." },
  { n:"10", title:"Pipeline & Audit", tag:"CONTROL", href:"/pipeline", text:"Track pipeline state and inspect agent activity and governed outcomes." },
];

const shortcuts = [
  ["Dashboard","/","Executive KPIs and operating guardrails"],
  ["Discovery Engine","/discovery","Live sources, search intents and discovery runs"],
  ["Portfolio Studio","/portfolio","Services, keywords and buyer-fit knowledge"],
  ["Schedulers","/schedulers","Periodic discovery and inbox workflows"],
  ["Resource Library","/resources","Drive decks, demos, case studies and company links"],
  ["Email Templates","/templates","Reusable governed outreach content"],
  ["Opportunities","/opportunities","Discovery, qualification and research"],
  ["Approval Queue","/approval","Human review of outbound drafts"],
  ["Send Center","/outreach","Verified, confirmed outbound delivery"],
  ["Response Center","/responses","Inbox intelligence and follow-ups"],
  ["Pipeline","/pipeline","Opportunity and engagement progression"],
  ["AI Agent Logs","/agents","Automation activity and audit trail"],
  ["Admin","/admin","Microsoft 365 and governance controls"],
] as const;

export default function WorkflowCenter(){
  return <div className="wf-page">
    <header className="wf-hero">
      <div><div className="wf-kicker"><i/> OPERATING WORKFLOW</div><h1>AI Sales Workflow Center</h1><p>One governed journey from opportunity discovery to customer response, with direct access to every operating stage.</p></div>
      <div className="wf-status"><span>● SYSTEM READY</span><strong>Human-in-the-loop</strong><small>Microsoft 365 · Smart inbound · Controlled send</small></div>
    </header>

    <section className="wf-overview">
      <div className="wf-overview-copy"><span>END-TO-END JOURNEY</span><h2>How VTAB AI Sales Intelligence operates</h2><p>AI accelerates research and intelligence. Human gates remain mandatory before outbound actions. Inbox synchronization remains read-only.</p></div>
      <div className="wf-legend"><span><i className="ai"/>AI Agent</span><span><i className="human"/>Human Gate</span><span><i className="control"/>Controlled</span></div>
    </section>

    <div className="wf-flow">
      {stages.map((s,i)=><div className="wf-stage-wrap" key={s.n}>
        <Link href={s.href} className="wf-stage">
          <div className="wf-stage-top"><span className="wf-num">{s.n}</span><span className={`wf-tag ${s.tag.replaceAll(" ","-").toLowerCase()}`}>{s.tag}</span></div>
          <h3>{s.title}</h3><p>{s.text}</p><div className="wf-open">Open workspace <b>→</b></div>
        </Link>{i<stages.length-1&&<div className="wf-arrow">→</div>}
      </div>)}
    </div>

    <section className="wf-shortcuts">
      <div className="wf-section-head"><div><span>QUICK ACCESS</span><h2>Workspace shortcuts</h2></div><p>Jump directly to the page you need without stepping through the entire workflow.</p></div>
      <div className="wf-shortcut-grid">{shortcuts.map(([title,href,text])=><Link href={href} className="wf-shortcut" key={href+title}><div className="wf-shortcut-icon">↗</div><div><strong>{title}</strong><span>{text}</span></div><b>→</b></Link>)}</div>
    </section>

    <section className="wf-safety"><div><span>GOVERNANCE</span><h2>Safety controls remain enforced</h2></div><div className="wf-safety-items"><span>✓ Human approval before send</span><span>✓ Verified recipient required</span><span>✓ Read-only inbox sync</span><span>✓ No automatic customer reply</span><span>✓ Final send confirmation</span></div></section>
  </div>
}
