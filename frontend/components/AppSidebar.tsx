"use client";
import {apiFetch, apiJson, reportApiError} from "../lib/api";


import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

type IconName =
  | "dashboard"
  | "workflow"
  | "opportunities"
  | "approval"
  | "send"
  | "agents"
  | "admin"
  | "responses"
  | "pipeline"
  | "chevron";

function Icon({ name }: { name: IconName }) {
  const common = {
    width: 19,
    height: 19,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  if (name === "workflow") return (<svg {...common}><path d="M4 6h5v5H4zM15 13h5v5h-5z"/><path d="M9 8.5h3a3 3 0 013 3V13M12 16H9a3 3 0 01-3-3v-2"/></svg>);

  if (name === "dashboard")
    return (
      <svg {...common}>
        <rect x="3" y="3" width="7" height="7" rx="2" />
        <rect x="14" y="3" width="7" height="7" rx="2" />
        <rect x="3" y="14" width="7" height="7" rx="2" />
        <rect x="14" y="14" width="7" height="7" rx="2" />
      </svg>
    );

  if (name === "opportunities")
    return (
      <svg {...common}>
        <path d="M12 3v18" />
        <path d="M3 12h18" />
        <circle cx="12" cy="12" r="8.5" />
      </svg>
    );

  if (name === "approval")
    return (
      <svg {...common}>
        <path d="M9 11.5l2 2 4.5-5" />
        <path d="M12 2.8l7 3.1v5.2c0 4.7-2.9 8.1-7 10.1-4.1-2-7-5.4-7-10.1V5.9L12 2.8z" />
      </svg>
    );

  if (name === "send")
    return (
      <svg {...common}>
        <path d="M21 3L10.2 13.8" />
        <path d="M21 3l-6.7 18-4.1-7.2L3 9.7 21 3z" />
      </svg>
    );

  if (name === "agents")
    return (
      <svg {...common}>
        <rect x="5" y="7" width="14" height="11" rx="3" />
        <path d="M9 11h.01M15 11h.01M9 15h6M12 7V4M9 4h6" />
      </svg>
    );

  if (name === "responses") return (<svg {...common}><path d="M4 5h16v11H8l-4 4V5z"/><path d="M8 9h8M8 12h5"/></svg>);
  if (name === "pipeline") return (<svg {...common}><path d="M5 19V9M12 19V5M19 19v-7"/><path d="M3 19h18"/></svg>);

  if (name === "admin")
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.7 1.7 0 00.34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0015 19.4a1.7 1.7 0 00-1 .6 1.7 1.7 0 00-.4 1.1V21H9.6v-.1A1.7 1.7 0 008.5 19.4a1.7 1.7 0 00-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 004.6 15a1.7 1.7 0 00-.6-1 1.7 1.7 0 00-1.1-.4H3V9.6h.1A1.7 1.7 0 004.6 8.5a1.7 1.7 0 00-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 009 4.6a1.7 1.7 0 001-.6 1.7 1.7 0 00.4-1.1V3h4v.1A1.7 1.7 0 0015.5 4.6a1.7 1.7 0 001.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0019.4 9c.16.38.4.72.7 1 .3.27.7.4 1.1.4h.1v4h-.1a1.7 1.7 0 00-1.8.6z" />
      </svg>
    );

  return (
    <svg {...common}>
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}

const primary = [
  { href: "/", label: "Dashboard", icon: "dashboard" as IconName },
  { href: "/workflow", label: "Workflow Center", icon: "workflow" as IconName },
  { href: "/opportunities", label: "Opportunities", icon: "opportunities" as IconName },
  { href: "/approval", label: "Approval Queue", icon: "approval" as IconName },
  { href: "/outreach", label: "Send Center", icon: "send" as IconName },
];

const intelligence = [
  { href: "/discovery", label: "Discovery Engine", icon: "opportunities" as IconName },
  { href: "/portfolio", label: "Portfolio Studio", icon: "workflow" as IconName },
  { href: "/responses", label: "Response Center", icon: "responses" as IconName },
  { href: "/pipeline", label: "Pipeline", icon: "pipeline" as IconName },
  { href: "/agents", label: "AI Agent Logs", icon: "agents" as IconName },
];

const system = [
  { href: "/resources", label: "Resource Library", icon: "send" as IconName },
  { href: "/templates", label: "Email Templates", icon: "responses" as IconName },
  { href: "/schedulers", label: "Schedulers", icon: "agents" as IconName },
  { href: "/job-monitor", label: "Job Monitor", icon: "pipeline" as IconName },
  { href: "/security", label: "Security Center", icon: "approval" as IconName },
  { href: "/admin", label: "Admin", icon: "admin" as IconName },
];

export default function AppSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const active = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  const group = (title: string, items: typeof primary) => (
    <div className="sidebar-nav-group">
      <div className="sidebar-section-label">{title}</div>
      <div className="sidebar-nav-list">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active(item.href) ? "page" : undefined} className={`sidebar-nav-item ${active(item.href) ? "active" : ""}`}
            title={collapsed ? item.label : undefined}
          >
            <span className="sidebar-nav-icon">
              <Icon name={item.icon} />
            </span>
            <span className="sidebar-nav-text">{item.label}</span>
            {active(item.href) && <span className="sidebar-active-dot" />}
          </Link>
        ))}
      </div>
    </div>
  );

  async function logout(){await apiFetch("/backend-api/auth/logout",{method:"POST",credentials:"include"});localStorage.removeItem("vtab_auth_token");localStorage.removeItem("vtab_token");localStorage.removeItem("vtab_auth_user");localStorage.removeItem("vtab_user");window.location.href="/login"}

  return (
    <aside className={`side premium-sidebar ${collapsed ? "is-collapsed" : ""}`}>
      <div className="sidebar-glow sidebar-glow-one" />
      <div className="sidebar-glow sidebar-glow-two" />

      <div className="sidebar-brand">
        <div className="sidebar-logo">
          <span className="sidebar-logo-spark">✦</span>
        </div>
        <div className="sidebar-brand-copy">
          <strong>VTAB AI Sales</strong>
          <span>Intelligence</span>
          <small>GLOBAL OPPORTUNITY AGENT</small>
        </div>
        <button
          type="button"
          className="sidebar-collapse-button"
          onClick={() => setCollapsed((value) => !value)}
          aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
          title={collapsed ? "Expand navigation" : "Collapse navigation"}
        >
          <span className={collapsed ? "collapse-rotate" : ""}>
            <Icon name="chevron" />
          </span>
        </button>
      </div>

      <div className="sidebar-divider" />

      <nav className="premium-nav" aria-label="Main navigation">
        {group("WORKSPACE", primary)}
        {group("INTELLIGENCE", intelligence)}
        {group("SYSTEM", system)}
      </nav>

      <div className="sidebar-spacer" />

      <div className="agent-status-card">
        <div className="agent-status-orb">
          <span className="agent-status-pulse" />
          <Icon name="agents" />
        </div>
        <div className="agent-status-copy">
          <span>AI AGENT</span>
          <strong>Human controlled</strong>
          <small>Review required before sending</small>
        </div>
        <span className="agent-live-dot" />
      </div>

      <button type="button" className="sidebar-signout" onClick={logout} aria-label="Sign out" title="Sign out">↪ <span>Sign out</span></button>

      <div className="sidebar-footer">
        <span className="sidebar-footer-mark">VTAB</span>
        <span className="sidebar-footer-version">Sales Intelligence</span>
      </div>
    </aside>
  );
}
