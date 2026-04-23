import { DashboardShell } from "@/components/layout/dashboard-shell";
import { StatePanel } from "@/components/state-panel";
import { fetchBaselineRuns, type BaselineCheckResult, type BaselineRun } from "@/lib/api";
import { formatDateTime } from "@/lib/inspection-view";

type RuleSummary = {
  key: string;
  ruleId: string;
  ruleName: string;
  category: string;
  severity: string;
  total: number;
  pass: number;
  fail: number;
  unknown: number;
  passRate: number;
  latestAt: string;
};

export default async function BaselinePage() {
  try {
    const runs = await fetchBaselineRuns();
    const rules = buildRuleSummaries(runs);
    const totalChecks = rules.reduce((sum, rule) => sum + rule.total, 0);
    const failedRules = rules.filter((rule) => rule.fail > 0).length;
    const averagePassRate =
      rules.length > 0
        ? Math.round(rules.reduce((sum, rule) => sum + rule.passRate, 0) / rules.length)
        : 0;
    const highRiskRules = rules.filter((rule) => rule.fail > 0 && normalize(rule.severity) === "high").length;

    return (
      <DashboardShell
        activePath="/baseline"
        badge="基线检查"
        title="基线检查"
        description="从规则维度汇总 Linux 与交换机基线结果，快速定位低通过率、高危失败和需要人工确认的规则。"
        summary={
          rules.length > 0
            ? `当前聚合 ${rules.length} 条基线规则、${totalChecks} 次规则结论，平均通过率 ${averagePassRate}%。`
            : "当前还没有基线执行记录，资产执行基线检查后会在这里形成规则视角。"
        }
        stats={[
          {
            label: "规则数",
            value: String(rules.length),
            conclusion: "按 rule_id 聚合最近基线结果",
            tone: rules.length > 0 ? "info" : "medium",
            statusText: rules.length > 0 ? "已加载" : "空",
          },
          {
            label: "高危失败规则",
            value: String(highRiskRules),
            conclusion: highRiskRules > 0 ? "需要优先核查整改建议" : "当前没有高危失败规则",
            tone: highRiskRules > 0 ? "critical" : "normal",
            statusText: highRiskRules > 0 ? "优先" : "清空",
          },
          {
            label: "失败规则",
            value: String(failedRules),
            conclusion: failedRules > 0 ? "存在未通过基线项" : "当前规则均无失败聚合",
            tone: failedRules > 0 ? "medium" : "normal",
            statusText: failedRules > 0 ? "待处理" : "稳定",
          },
          {
            label: "平均通过率",
            value: rules.length > 0 ? `${averagePassRate}%` : "--",
            conclusion: "按每条规则的历史结论平均计算",
            tone: averagePassRate >= 90 ? "normal" : averagePassRate >= 70 ? "medium" : "critical",
            statusText: rules.length > 0 ? "规则视角" : "无数据",
          },
        ]}
      >
        <section className="panel-card primary-table-card">
          <div className="section-head">
            <div>
              <h3>规则检查结果</h3>
              <p>展示规则 ID、规则名、分类、严重程度和通过率，数据来自真实基线执行记录。</p>
            </div>
            <div className="section-meta">共 {rules.length} 条规则</div>
          </div>

          {rules.length > 0 ? (
            <div className="table-shell">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>规则 ID</th>
                    <th>规则名</th>
                    <th>分类</th>
                    <th>严重程度</th>
                    <th>通过率</th>
                    <th>结论分布</th>
                    <th>最近检查</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr key={rule.key}>
                      <td className="mono">{rule.ruleId}</td>
                      <td>
                        <div className="cell-primary">
                          <span className="cell-link-static">{rule.ruleName}</span>
                          <span>{rule.total} 次检查结论</span>
                        </div>
                      </td>
                      <td>{formatCategory(rule.category)}</td>
                      <td>
                        <span className={`badge tone-${mapSeverityBadge(rule.severity)}`}>
                          {formatSeverity(rule.severity)}
                        </span>
                      </td>
                      <td>
                        <div className="baseline-rate">
                          <strong>{rule.passRate}%</strong>
                          <span className="baseline-rate-track">
                            <span
                              className="baseline-rate-fill"
                              style={{ width: `${Math.max(rule.passRate, 4)}%` }}
                            />
                          </span>
                        </div>
                      </td>
                      <td>
                        <div className="cell-primary">
                          <span className="text-glow">✓ PASS {rule.pass}</span>
                          <span className={rule.fail > 0 ? "text-glow-red" : "text-dim"}>✗ FAIL {rule.fail}</span>
                          <span>? UNKNOWN {rule.unknown}</span>
                        </div>
                      </td>
                      <td>{formatDateTime(rule.latestAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <StatePanel
              tone="empty"
              title="没有基线结果"
              description="请先在资产页面对 Linux 或交换机资产执行基线检查。"
            />
          )}
        </section>
      </DashboardShell>
    );
  } catch (error) {
    const description = error instanceof Error ? error.message : "当前无法获取基线检查记录。";

    return (
      <DashboardShell
        activePath="/baseline"
        badge="基线检查"
        title="基线检查"
        description="从规则维度汇总 Linux 与交换机基线结果。"
      >
        <StatePanel tone="error" title="基线检查加载失败" description={description} />
      </DashboardShell>
    );
  }
}

function buildRuleSummaries(runs: BaselineRun[]): RuleSummary[] {
  const groups = new Map<string, Array<{ check: BaselineCheckResult; createdAt: string }>>();

  for (const run of runs) {
    for (const check of run.baseline_results) {
      const key = check.rule_id || check.rule_name;
      groups.set(key, [...(groups.get(key) ?? []), { check, createdAt: run.created_at }]);
    }
  }

  return Array.from(groups.entries())
    .map(([key, items]) => {
      const latest = items.reduce((current, item) =>
        new Date(item.createdAt).getTime() > new Date(current.createdAt).getTime() ? item : current,
      );
      const pass = items.filter((item) => item.check.status === "pass").length;
      const fail = items.filter((item) => item.check.status === "fail").length;
      const unknown = items.filter((item) => item.check.status === "unknown").length;
      const total = items.length;

      return {
        key,
        ruleId: latest.check.rule_id,
        ruleName: latest.check.rule_name,
        category: latest.check.category,
        severity: latest.check.risk_level,
        total,
        pass,
        fail,
        unknown,
        passRate: total > 0 ? Math.round((pass / total) * 100) : 0,
        latestAt: latest.createdAt,
      };
    })
    .sort((left, right) => {
      if (right.fail !== left.fail) {
        return right.fail - left.fail;
      }
      if (left.passRate !== right.passRate) {
        return left.passRate - right.passRate;
      }
      return new Date(right.latestAt).getTime() - new Date(left.latestAt).getTime();
    });
}

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

function mapSeverityBadge(severity: string): "critical" | "medium" | "low" | "info" {
  const normalized = normalize(severity);
  if (normalized === "high") {
    return "critical";
  }
  if (normalized === "medium") {
    return "medium";
  }
  if (normalized === "low") {
    return "low";
  }
  return "info";
}

function formatSeverity(severity: string): string {
  const normalized = normalize(severity);
  if (normalized === "high") {
    return "高危";
  }
  if (normalized === "medium") {
    return "中危";
  }
  if (normalized === "low") {
    return "低危";
  }
  return severity || "--";
}

function formatCategory(category: string): string {
  const normalized = normalize(category);
  if (normalized === "identity_authentication") {
    return "身份鉴别";
  }
  if (normalized === "security_audit") {
    return "安全审计";
  }
  if (normalized === "access_control") {
    return "访问控制";
  }
  if (normalized === "security_protection") {
    return "安全保护";
  }
  if (normalized === "malware_protection") {
    return "恶意代码防范";
  }
  return category || "--";
}
