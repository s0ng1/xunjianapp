type RiskSeverityKey = "high" | "medium" | "low" | "normal";

export type FocusRiskDistributionEntry = {
  key: RiskSeverityKey;
  label: string;
  value: number;
};

export type FocusRiskTopDeviceEntry = {
  name: string;
  ip: string;
  total: number;
  high: number;
  medium: number;
  changes: number;
  manual: number;
};

export type FocusRiskTrendEntry = {
  date: string;
  shortLabel: string;
  highFailCount: number;
};

export type FocusRiskOverviewData = {
  distribution: FocusRiskDistributionEntry[];
  topDevices: FocusRiskTopDeviceEntry[];
  trend: FocusRiskTrendEntry[];
};

type FocusRiskOverviewProps = {
  overview: FocusRiskOverviewData;
};

const RISK_TONE_CLASS: Record<RiskSeverityKey, string> = {
  high: "high",
  medium: "medium",
  low: "low",
  normal: "normal",
};

export function FocusRiskOverview({ overview }: FocusRiskOverviewProps) {
  const totalRiskCount = overview.distribution.reduce((sum, entry) => sum + entry.value, 0);
  const highEntry = overview.distribution.find((entry) => entry.key === "high");
  const mediumEntry = overview.distribution.find((entry) => entry.key === "medium");
  const topTotal = Math.max(overview.topDevices[0]?.total ?? 0, 1);
  const maxTrendValue = Math.max(...overview.trend.map((entry) => entry.highFailCount), 0);
  const latestTrend = overview.trend.at(-1)?.highFailCount ?? 0;
  const earliestTrend = overview.trend[0]?.highFailCount ?? 0;
  const trendDelta = latestTrend - earliestTrend;

  return (
    <section className="insight-board" aria-label="辅助视图">
      <div className="section-head">
        <div>
          <h3>辅助视图</h3>
          <p>放在工作列表之后，只提供判断背景，不抢占处理优先级。</p>
        </div>
        <div className="section-meta">辅助信息</div>
      </div>

      <div className="insight-grid">
        <article className="insight-card">
          <div className="insight-card-head">
            <div>
              <h4>风险摘要</h4>
              <p>基于各设备最近一次基线结果。</p>
            </div>
            <div className="insight-total">
              <strong>{totalRiskCount}</strong>
              <span>当前计数</span>
            </div>
          </div>

          <div className="risk-pill-list">
            {overview.distribution.map((entry) => (
              <div key={entry.key} className={`risk-pill tone-${RISK_TONE_CLASS[entry.key]}`}>
                <span>{entry.label}</span>
                <strong>{entry.value}</strong>
              </div>
            ))}
          </div>

          <p className="insight-footnote">
            {highEntry && highEntry.value > 0
              ? `当前仍有 ${highEntry.value} 项高危基线问题，需要优先结合“今日必须处理”核对闭环。`
              : mediumEntry && mediumEntry.value > 0
                ? `当前没有高危项，主要以 ${mediumEntry.value} 项中危问题和变化项为主。`
                : "当前整体风险密度较低，可优先清理积压与人工确认项。"}
          </p>
        </article>

        <article className="insight-card">
          <div className="insight-card-head">
            <div>
              <h4>高关注设备</h4>
              <p>按总风险量排序，辅助复核设备优先级。</p>
            </div>
            <div className="section-meta">{`Top ${Math.min(overview.topDevices.length, 5)}`}</div>
          </div>

          {overview.topDevices.length > 0 ? (
            <div className="insight-device-list">
              {overview.topDevices.map((device) => (
                <div key={`${device.ip}-${device.name}`} className="insight-device-row">
                  <div className="insight-device-main">
                    <div className="insight-device-title">
                      <strong>{device.name}</strong>
                      <span>{device.ip}</span>
                    </div>
                    <div className="insight-device-bar-track" aria-hidden="true">
                      <div
                        className="insight-device-bar-fill"
                        style={{ width: `${Math.max((device.total / topTotal) * 100, 8)}%` }}
                      />
                    </div>
                  </div>
                  <div className="insight-device-metrics">
                    <span>{`高危 ${device.high}`}</span>
                    <span>{`变化 ${device.changes}`}</span>
                    <strong>{`${device.total} 项`}</strong>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="insight-empty">当前没有进入优先级列表的设备。</div>
          )}
        </article>

        <article className="insight-card insight-card-trend">
          <div className="insight-card-head">
            <div>
              <h4>近 7 天高危走势</h4>
              <p>只看变化方向，不在首页做复杂图表解释。</p>
            </div>
            <div className="section-meta">最近 7 天</div>
          </div>

          <div className="trend-mini-chart" aria-label="近 7 天高危走势">
            {overview.trend.map((entry) => (
              <div key={entry.date} className="trend-mini-column">
                <span
                  className={`trend-mini-bar${entry.highFailCount > 0 ? " has-value" : ""}`}
                  style={{
                    height: `${maxTrendValue > 0 ? Math.max((entry.highFailCount / maxTrendValue) * 100, entry.highFailCount > 0 ? 18 : 8) : 8}%`,
                  }}
                />
                <strong>{entry.highFailCount}</strong>
                <label>{entry.shortLabel}</label>
              </div>
            ))}
          </div>

          <p className="insight-footnote">
            {maxTrendValue === 0
              ? "最近 7 天没有新增高危 fail，趋势保持在低位。"
              : trendDelta > 0
                ? `高危 fail 相比 7 天前增加 ${trendDelta} 项，建议优先核查新增变化来源。`
                : trendDelta < 0
                  ? `高危 fail 相比 7 天前下降 ${Math.abs(trendDelta)} 项，处理节奏在改善。`
                  : `高危 fail 与 7 天前持平，当前为 ${latestTrend} 项，需要继续观察是否停滞。`}
          </p>
        </article>
      </div>
    </section>
  );
}
