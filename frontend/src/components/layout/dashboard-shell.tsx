import Link from "next/link";
import type { ReactNode } from "react";

const NAV_ITEMS = [
  { href: "/", label: "DASHBOARD", caption: "风险总览" },
  { href: "/assets", label: "ASSETS", caption: "资产台账" },
  { href: "/alerts", label: "ALERTS", caption: "告警队列" },
  { href: "/inspections", label: "INSPECTIONS", caption: "巡检历史" },
  { href: "/baseline", label: "BASELINE", caption: "基线检查" },
] as const;

export type DashboardShellPath = (typeof NAV_ITEMS)[number]["href"];

type DashboardStat = {
  label: string;
  value: string;
  conclusion: string;
  tone?: "critical" | "medium" | "low" | "normal" | "info";
  statusText?: string;
};

type DashboardShellProps = {
  activePath: DashboardShellPath;
  title: string;
  description: string;
  badge?: string;
  summary?: ReactNode;
  stats?: DashboardStat[];
  layout?: "default" | "workspace";
  actions?: ReactNode;
  children: ReactNode;
};

export function DashboardShell({
  activePath,
  title,
  description,
  badge = "安全巡检平台",
  summary,
  stats = [],
  layout = "default",
  actions,
  children,
}: DashboardShellProps) {
  const isWorkspace = layout === "workspace";

  return (
    <main className={`app-shell${isWorkspace ? " app-shell-workspace" : ""}`}>
      <div className={`app-frame${isWorkspace ? " app-frame-workspace" : ""}`}>
        <aside className={`site-nav terminal-nav${isWorkspace ? " site-nav-workspace" : ""}`} aria-label="Primary">
          <div className="nav-header" aria-label="SecInspect OS">
            <span className="text-glow">╔══════════════════╗</span>
            <span className="text-glow">║  SECINSPECT OS   ║</span>
            <span className="text-glow">╚══════════════════╝</span>
          </div>

          <nav className="nav-list">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-item ${item.href === activePath ? "is-active" : ""}`}
              >
                <span className="prompt">►</span>
                <span className="nav-copy">
                  <strong>{item.label}</strong>
                  <small>{item.caption}</small>
                </span>
              </Link>
            ))}
          </nav>

          <div className="nav-footer">
            <span className="text-dim">v2.4.1 // SECINSPECT</span>
            <strong>LINUX / SWITCH / BASELINE</strong>
          </div>
        </aside>

        <div className="workspace-panel">
          <div className="top-bar">
            <span className="top-bar-label">root@secinspect:~$ ./status --live</span>
            <span className="top-bar-pulse">{badge}</span>
          </div>

          <header className={`page-hero${isWorkspace ? " page-hero-workspace" : ""}`}>
            <div className="page-hero-main">
              <span className="page-badge">{badge}</span>
              <div className="page-copy">
                <h1 className="page-title">{title}</h1>
                <p>{description}</p>
              </div>
              {summary ? <p className="page-summary-note">{summary}</p> : null}
            </div>

            {actions ? <div className="page-hero-side">{actions}</div> : null}
          </header>

          {stats.length > 0 ? (
            <section className="stats-strip" aria-label="Page summary">
              {stats.map((stat) => (
                <article key={stat.label} className={`stat-card tone-${stat.tone ?? "info"}`}>
                  <div className="stat-card-head">
                    <span className="stat-label">{stat.label}</span>
                    {stat.statusText ? <span className="stat-state">{stat.statusText}</span> : null}
                  </div>
                  <strong className="stat-value">{stat.value}</strong>
                  <p className="stat-conclusion">{stat.conclusion}</p>
                </article>
              ))}
            </section>
          ) : null}

          <div className="page-stack">{children}</div>
        </div>
      </div>
    </main>
  );
}
