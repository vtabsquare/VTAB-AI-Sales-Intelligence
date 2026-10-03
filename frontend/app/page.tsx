export const dynamic="force-dynamic";
import {serverGet} from "../lib/serverApi";

const API =
  process.env.API_BASE_URL ||
  "http://127.0.0.1:8001";

async function getData() {
  try {
    const r = await serverGet("/api/dashboard");

    if (!r.ok) throw new Error();

    return await r.json();
  } catch {
    throw new Error('Dashboard data is unavailable.');
  }
}

function Icon({ type }: { type: string }) {
  const icons: Record<string, string> = {
    opp: "◎",
    qual: "✦",
    approval: "✓",
    sent: "↗",
  };

  return (
    <span className={`vtab-kpi-icon vtab-kpi-icon-${type}`}>
      {icons[type] || "◈"}
    </span>
  );
}

type JourneyStage = {
  step: string;
  title: string;
  description: string;
  icon: string;
  badge: string;
  kind: "ai" | "human" | "controlled" | "monitor";
};

const journey: JourneyStage[] = [
  {
    step: "01",
    title: "Discover",
    description: "Find relevant global opportunities from configured sources.",
    icon: "⌕",
    badge: "AI AGENT",
    kind: "ai",
  },
  {
    step: "02",
    title: "Qualify",
    description: "Score business fit, capability match and commercial relevance.",
    icon: "✦",
    badge: "AI AGENT",
    kind: "ai",
  },
  {
    step: "03",
    title: "Research",
    description: "Build organization, requirement and contact intelligence.",
    icon: "◫",
    badge: "AI AGENT",
    kind: "ai",
  },
  {
    step: "04",
    title: "Human Approve",
    description: "Review the outreach recommendation before communication.",
    icon: "✓",
    badge: "HUMAN GATE",
    kind: "human",
  },
  {
    step: "05",
    title: "Send",
    description: "Release approved communication through controlled delivery.",
    icon: "↗",
    badge: "CONTROLLED",
    kind: "controlled",
  },
  {
    step: "06",
    title: "Track Response",
    description: "Monitor replies, engagement and customer intent.",
    icon: "◌",
    badge: "AI MONITOR",
    kind: "monitor",
  },
  {
    step: "07",
    title: "Follow-up",
    description: "Review the recommended next action before further outreach.",
    icon: "↻",
    badge: "HUMAN GATE",
    kind: "human",
  },
];

export default async function Page() {
  const d = await getData();

  const metrics = [
    [
      "Opportunities",
      d.opportunities,
      "opp",
      "Global opportunities tracked",
    ],
    [
      "Qualified",
      d.qualified,
      "qual",
      "AI-qualified business fit",
    ],
    [
      "Awaiting Approval",
      d.waiting_approval,
      "approval",
      "Human review required",
    ],
    [
      d.demo_mode?"Simulated Sent":"Sent",
      d.sent,
      "sent",
      "Controlled outbound activity",
    ],
  ];

  return (
    <div className="vtab-page">
      <header className="vtab-hero">
        <div>
          <div className="vtab-eyebrow">
            <span />
            COMMAND CENTER
          </div>

          <h1>Global Opportunity Dashboard</h1>

          <p>
            Human-controlled AI sales intelligence for opportunity discovery,
            qualification and outreach.
          </p>
        </div>

        <div className="vtab-live-badge">
          <i />
          {d.demo_mode?"DEMO MODE":"LIVE MODE"}
        </div>
      </header>

      <section className="vtab-kpi-grid">
        {metrics.map(([label, value, type, sub]: any) => (
          <article className="vtab-kpi-card" key={label}>
            <div className="vtab-kpi-top">
              <Icon type={type} />
              <span className="vtab-kpi-trend">{d.demo_mode ? "DEMO" : "LIVE"}</span>
            </div>

            <div className="vtab-kpi-value">{value}</div>
            <strong>{label}</strong>
            <small>{sub}</small>
          </article>
        ))}
      </section>

      <section className="vtab-command-grid">
        <article className="vtab-glass-panel vtab-guardrail">
          <div className="vtab-panel-heading">
            <div>
              <span>GOVERNANCE</span>
              <h2>Operating Guardrails</h2>
            </div>
            <div className="vtab-shield">◇</div>
          </div>

          <div className="vtab-rule-list">
            <div>
              <b>01</b>
              <p>
                <strong>Human approval required</strong>
                <span>
                  Every outbound draft requires explicit review before
                  communication can proceed.
                </span>
              </p>
            </div>

            <div>
              <b>02</b>
              <p>
                <strong>Verified recipients only</strong>
                <span>
                  Unverified contacts are never automatically mailed by the
                  agent.
                </span>
              </p>
            </div>

            <div>
              <b>03</b>
              <p>
                <strong>Safe simulation mode</strong>
                <span>
                  Demo mode performs simulated sends while preserving the
                  complete control flow.
                </span>
              </p>
            </div>
          </div>
        </article>

        <article className="vtab-glass-panel vtab-agent-pulse">
          <div className="vtab-panel-heading">
            <div>
              <span>AI OPERATIONS</span>
              <h2>Agent Activity</h2>
            </div>

            <div className="vtab-orbit">
              <i />
              <i />
              <i />
            </div>
          </div>

          <div className="vtab-agent-count">
            {d.agent_runs ?? 0}
          </div>

          <p>Agent executions recorded</p>

          <div className="vtab-health-line">
            <span>
              <i />
              Opportunity engine
            </span>
            <strong>ONLINE</strong>
          </div>

          <div className="vtab-health-line">
            <span>
              <i />
              Human control layer
            </span>
            <strong>PROTECTED</strong>
          </div>
        </article>
      </section>

      <section className="vtab-journey-panel">
        <div className="vtab-journey-header">
          <div>
            <div className="vtab-journey-eyebrow">
              CONTROLLED SALES JOURNEY
            </div>

            <h2>Human-in-the-loop Flow</h2>

            <p>
              Autonomous intelligence progresses the opportunity while
              outbound authority remains explicitly human controlled.
            </p>
          </div>

          <div className="vtab-journey-status">
            <span className="vtab-status-dot" />
            GOVERNED WORKFLOW
          </div>
        </div>

        <div className="vtab-journey-legend">
          <span>
            <i className="legend-ai" />
            AI Autonomous
          </span>
          <span>
            <i className="legend-human" />
            Human Decision
          </span>
          <span>
            <i className="legend-controlled" />
            Controlled Action
          </span>
          <span>
            <i className="legend-monitor" />
            AI Monitoring
          </span>
        </div>

        <div className="vtab-journey-scroll">
          <div className="vtab-journey-track">
            {journey.map((stage, index) => (
              <div className="vtab-journey-item" key={stage.step}>
                <article
                  className={`vtab-stage-card vtab-stage-${stage.kind}`}
                >
                  <div className="vtab-stage-top">
                    <span className="vtab-stage-number">
                      {stage.step}
                    </span>

                    <span
                      className={`vtab-stage-icon vtab-stage-icon-${stage.kind}`}
                      aria-hidden="true"
                    >
                      {stage.icon}
                    </span>
                  </div>

                  <div className="vtab-stage-content">
                    <h3>{stage.title}</h3>
                    <p>{stage.description}</p>
                  </div>

                  <div
                    className={`vtab-stage-badge vtab-stage-badge-${stage.kind}`}
                  >
                    <i />
                    {stage.badge}
                  </div>
                </article>

                {index < journey.length - 1 && (
                  <div className="vtab-stage-connector" aria-hidden="true">
                    <span />
                    <b>›</b>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="vtab-journey-footer">
          <div>
            <span className="vtab-footer-icon">◇</span>
            <p>
              <strong>Autonomy is separated from authority.</strong>
              AI can discover, qualify, research and monitor. Human approval
              remains the control point for outbound communication.
            </p>
          </div>

          <span className="vtab-governance-chip">
            HUMAN CONTROL ACTIVE
          </span>
        </div>
      </section>
    </div>
  );
}
