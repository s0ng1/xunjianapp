import Link from "next/link";
import type { ReactNode } from "react";

const NAV_ITEMS = [
  { href: "/", label: "首页 / 操作台" },
  { href: "/assets", label: "资产列表" },
  { href: "/alerts", label: "告警列表" },
  { href: "/inspections", label: "巡检记录" },
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
        <nav className={`site-nav${isWorkspace ? " site-nav-workspace" : ""}`} aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-item ${item.href === activePath ? "is-active" : ""}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

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
    </main>
  );
}
