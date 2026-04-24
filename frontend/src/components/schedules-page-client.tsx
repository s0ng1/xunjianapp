"use client";

export function SchedulesPageClient() {
  return (
    <section
      className="panel-card"
      style={{
        background: "linear-gradient(180deg, var(--surface-raised), var(--surface))",
        borderColor: "var(--border-strong)",
      }}
    >
      <div className="section-head">
        <div>
          <h3>任务编排工作区</h3>
          <p>后续将在这里配置巡检、扫描和基线任务的执行周期、目标资产与触发方式。</p>
        </div>
        <div className="section-meta">Phase 3 / Step 1</div>
      </div>

      <div
        style={{
          padding: "28px",
          border: "1px dashed var(--border-strong)",
          borderRadius: "var(--radius-md)",
          background:
            "radial-gradient(circle at top, rgba(136, 192, 208, 0.12), transparent 38%), var(--surface-muted)",
          color: "var(--text)",
        }}
      >
        <strong
          style={{
            display: "block",
            marginBottom: "10px",
            color: "var(--accent)",
            fontFamily: "var(--font-display)",
            letterSpacing: "0.04em",
          }}
        >
          Schedules Page - Coming Soon
        </strong>
        <p style={{ margin: 0, color: "var(--text-muted)" }}>
          当前阶段先提供页面骨架，下一步再补任务列表、执行频率配置和启停控制。
        </p>
      </div>
    </section>
  );
}
