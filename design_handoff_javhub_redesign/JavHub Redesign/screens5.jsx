/* JavHub redesign — 补全管理 actor workspace (grounded in real Vue structure) → window */
const { useState: useState5 } = React;

const STATUS_LABEL = { queued: "排队中", running: "运行中", succeeded: "已完成", failed: "失败", idle: "待开始" };
const MATCH = { matched: { label: "已匹配", cls: "ok" }, candidate: { label: "候选待确认", cls: "warn" }, unmatched: { label: "未匹配", cls: "bad" } };
const FIELDS = ["封面", "标题", "时长", "系列", "分类", "剧照", "简介"];

/* recent supplement actors */
function supActors() {
  const { A } = window.JH;
  return [
    { ...A.kojima, gaps: 6, supMovies: 48, matched: 41, supOnly: 7, resolved: 12, last: "succeeded", jobTime: "今天 06:12", recent: "3 部新作已补全字段" },
    { ...A.yua,    gaps: 11, supMovies: 62, matched: 50, supOnly: 12, resolved: 9, last: "running",   jobTime: "正在运行 · 第 8/14 步", recent: "封面与剧照补全中" },
    { ...A.momono, gaps: 3, supMovies: 31, matched: 28, supOnly: 3, resolved: 6,  last: "succeeded", jobTime: "1 小时前", recent: "标签与简介已对齐" },
    { ...A.aoi,    gaps: 8, supMovies: 29, matched: 22, supOnly: 7, resolved: 4,  last: "failed",     jobTime: "2 小时前 · dmm 超时", recent: "2 个字段来源失败，待重试" },
    { ...A.akari,  gaps: 5, supMovies: 24, matched: 20, supOnly: 4, resolved: 5,  last: "queued",     jobTime: "排队中 · 等待空闲来源", recent: "等待 javdb 预算释放" },
    { ...A.nanami, gaps: 9, supMovies: 18, matched: 12, supOnly: 6, resolved: 3,  last: "idle",       jobTime: "尚未补全", recent: "选择后进入补全工作台" },
  ];
}

/* per-actor movie field pool — each movie carries field values (or null = 缺失) + a match state */
function supMovies(actor) {
  const { V } = window.JH;
  const own = V.filter(v => v.acts.some(a => a.id === actor.id));
  const pool = (own.length >= 4 ? own : [...own, ...V.filter(v => !own.includes(v))]).slice(0, 6);
  const presets = [
    { match: "candidate", miss: ["剧照", "简介"] },
    { match: "unmatched", miss: ["封面", "标题", "时长", "系列", "分类", "剧照", "简介"] },
    { match: "matched", miss: [] },
    { match: "matched", miss: ["分类"] },
    { match: "candidate", miss: ["封面", "剧照"] },
    { match: "matched", miss: ["简介"] },
  ];
  return pool.map((v, i) => {
    const p = presets[i % presets.length];
    const fields = {};
    FIELDS.forEach(f => {
      if (p.miss.includes(f)) { fields[f] = null; return; }
      fields[f] = f === "封面" ? "官方版" : f === "标题" ? v.title : f === "时长" ? `${v.runtime} 分钟`
        : f === "系列" ? (v.series || "无系列") : f === "分类" ? v.genres.slice(0, 2).join("·") : f === "剧照" ? "12 张" : "已写入";
    });
    return { v, match: p.match, fields, missing: p.miss };
  });
}

/* field-level source candidates for the diagnostics lane */
const FIELD_SOURCES = {
  封面: [{ src: "dmm", label: "1920×1080 官方版" }, { src: "javbus", label: "800×538 备用" }],
  标题: [{ src: "javdb", label: "中文标题" }, { src: "javbus", label: "日文原文" }],
  时长: [{ src: "javdb", label: "128 分钟" }],
  系列: [{ src: "javdb", label: "情热夏日" }, { src: "javlibrary", label: "情熱の夏" }],
  分类: [{ src: "javdb", label: "9 个标签" }, { src: "javbus", label: "6 个标签" }],
  剧照: [{ src: "javbus", label: "12 张" }, { src: "javdb", label: "8 张" }],
  简介: [{ src: "dmm", label: "日文原文 + 机翻" }],
};

function jobsFor(actor) {
  return [
    { id: 3318, t: `${actor.kanji} · 字段补全`, attempt: `补全 ${actor.supOnly} 个新增字段 · 命中 javdb/javbus`, time: actor.jobTime, status: actor.last },
    { id: 3304, t: `${actor.kanji} · 封面与剧照`, attempt: "javbus → 本地缓存 · 写入 9 张", time: "1 小时前", status: "succeeded" },
    { id: 3291, t: `${actor.kanji} · 头像回填`, attempt: "gfriends · 匹配 1 位主演", time: "今天 04:00", status: "succeeded" },
    { id: 3277, t: `${actor.kanji} · 简介拉取`, attempt: "dmm 限速命中 · 已排队重试", time: "今天 03:42", status: "queued" },
  ];
}

const SOURCES = [
  { name: "javdb", role: "主元数据来源", tone: "ok", state: "可参与字段补全", failures: 0, error: "—", next: "保持主来源", latency: "在线 · 240ms", budget: "预算 82%" },
  { name: "javbus", role: "封面与剧照", tone: "ok", state: "可参与字段补全", failures: 0, error: "—", next: "保持封面来源", latency: "在线 · 410ms", budget: "预算 67%" },
  { name: "dmm", role: "官方简介与高清封面", tone: "warn", state: "降级 · 限速重试", failures: 2, error: "429 限速", next: "降低并发后重试", latency: "慢 · 1.8s", budget: "预算 23%" },
  { name: "gfriends", role: "演员头像来源", tone: "ok", state: "可参与字段补全", failures: 0, error: "—", next: "保持头像来源", latency: "在线 · 180ms", budget: "预算 91%" },
  { name: "javlibrary", role: "标签与系列校验", tone: "bad", state: "隔离模式 · 暂停 24h", failures: 6, error: "连续超时", next: "等待隔离窗口结束", latency: "连续失败 6 次", budget: "预算冻结" },
];

/* ---------- actor picker ---------- */
function SupActorPicker({ onPick }) {
  const [q, setQ] = useState5("");
  const actors = supActors();
  const list = q ? actors.filter(a => a.kanji.includes(q) || a.romaji.includes(q)) : actors;
  return (
    <>
      <div className="topbar solid">
        <div><h1>补全管理</h1><div className="sub">选择演员 · 进入字段补全工作台</div></div>
      </div>
      <div className="page page-wide">
        <div className="sup-pick-head">
          <div className="search-field" style={{ maxWidth: 340 }}>
            <Icon name="search" size={17} />
            <input placeholder="演员名 / 罗马音" value={q} onChange={e => setQ(e.target.value)} />
          </div>
          <button className="btn btn-ghost">筛选</button>
          <span className="grow"></span>
          <span className="muted" style={{ fontSize: "var(--t-cap)" }}>{q ? "搜索结果" : "最近补全"} · {list.length} 位</span>
        </div>

        <div className="sup-actor-grid">
          {list.map(a => (
            <button className="sup-actor-card" key={a.id} onClick={() => onPick(a)}>
              <span className="sa-av" style={{ background: a.color }}>{a.kanji[0]}</span>
              <div className="sa-meta">
                <div className="sa-name">{a.kanji}</div>
                <div className="sa-romaji">编号 {String(a.id).padStart(5, "0")}</div>
                <div className="sa-foot">
                  <span className={"status-pill " + a.last}>{STATUS_LABEL[a.last]}</span>
                  {a.gaps > 0 && <span className="sa-gap">{a.gaps} 字段缺口</span>}
                </div>
              </div>
              <span className="btn btn-quiet sa-pick">选择</span>
            </button>
          ))}
          {list.length === 0 && (
            <div className="cand-empty" style={{ gridColumn: "1 / -1" }}>
              <div className="ce-ring"><Icon name="search" size={28} /></div>
              <div style={{ fontWeight: 650 }}>没有匹配演员</div>
              <p className="muted" style={{ fontSize: "var(--t-cap)", marginTop: 6 }}>换一个日文名或罗马音继续搜索，或清除搜索回到最近补全列表。</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

/* ---------- 作品字段 tab ---------- */
function MoviesTab({ movies, onOpen, onDiagnose }) {
  const ledger = FIELDS.map(f => ({ f, missing: movies.filter(m => m.fields[f] === null).length }));
  const total = ledger.reduce((s, r) => s + r.missing, 0);
  return (
    <div className="workspace-panel">
      <div className="wp-head">
        <h3>作品字段</h3>
        <span className="grow"></span>
        <button className="btn btn-primary btn-sm">批量补详情</button>
        <button className="btn btn-ghost btn-sm">生成下载候选</button>
      </div>
      <div className="filter-bar">
        <div className="segmented sm"><button className="active">全部匹配</button><button>仅候选</button><button>未匹配</button></div>
        <div className="segmented sm"><button className="active">全部质量</button><button>有缺口</button></div>
        <div className="search-field" style={{ maxWidth: 200, height: 36 }}><Icon name="search" size={15} /><input placeholder="番号 / 标题" /></div>
      </div>
      <div className="field-ledger">
        <div className="fl-sum"><strong>{total}</strong><span>当前页字段缺口</span></div>
        <div className="fl-chips">
          {ledger.map(r => (
            <span key={r.f} className={"fl-chip" + (r.missing ? "" : " clear")}><b>{r.f}</b><em>{r.missing ? `${r.missing} 个缺口` : "已齐"}</em></span>
          ))}
        </div>
      </div>
      <div className="field-list">
        {movies.map((m, i) => (
          <div className="field-card" key={i}>
            <div className="fc-poster" style={{ background: m.v.art }} onClick={() => onOpen(m.v)}><span className="cc-code">{m.v.code}</span></div>
            <div className="fc-main">
              <div className="fc-title">{m.v.title}</div>
              <div className="fc-meta">{m.v.date} · {m.v.runtime} 分钟 · {m.v.studio} · {m.v.genres.slice(0, 2).join("·")}</div>
              <div className="fc-fieldgrid">
                {FIELDS.map(f => (
                  <span key={f} className={"field-chip" + (m.fields[f] === null ? " miss" : "")}>
                    <b>{f}</b><em>{m.fields[f] === null ? "缺失" : (f === "封面" || f === "剧照" || f === "时长" ? m.fields[f] : "已就绪")}</em>
                  </span>
                ))}
              </div>
            </div>
            <div className="fc-act">
              <span className={"status-pill " + MATCH[m.match].cls + " match"}>{MATCH[m.match].label}</span>
              {m.missing.length
                ? <button className="btn btn-primary btn-sm" onClick={() => onDiagnose(m)}>补详情</button>
                : <span className="badge ok"><Icon name="check" size={12} /> 字段已齐</span>}
              <button className="btn btn-ghost btn-sm" onClick={() => onDiagnose(m)}>诊断</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- 任务队列 tab ---------- */
function JobsTab({ actor }) {
  const jobs = jobsFor(actor);
  const summary = [
    { k: "running", label: "运行中", n: jobs.filter(j => j.status === "running").length },
    { k: "queued", label: "排队中", n: jobs.filter(j => j.status === "queued").length },
    { k: "succeeded", label: "已完成", n: jobs.filter(j => j.status === "succeeded").length },
    { k: "failed", label: "失败", n: jobs.filter(j => j.status === "failed").length },
  ];
  return (
    <div className="workspace-panel">
      <div className="wp-head"><h3>任务队列</h3><span className="grow"></span><span className="wp-sub">{actor.kanji} · 最近 {jobs.length} 次</span></div>
      <div className="job-ledger">
        <div className="fl-sum"><strong>{jobs.length}</strong><span>当前页任务</span></div>
        <div className="job-ledger-cards">
          {summary.map(s => <span key={s.k} className={"jl-card " + s.k}><b>{s.label}</b><em>{s.n} 项</em></span>)}
        </div>
      </div>
      <div className="field-list">
        {jobs.map(j => (
          <div className="job-card" key={j.id}>
            <span className="job-avatar" style={{ background: actor.color }}>{actor.kanji[0]}</span>
            <div className="jc-copy">
              <strong>{j.t}</strong>
              <span className="jc-id">#{j.id} · {j.time}</span>
              <small className="jc-meta">{j.attempt}</small>
            </div>
            <span className={"status-pill " + j.status}>{STATUS_LABEL[j.status]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- 来源诊断 tab (launchpad + inline field diagnostics) ---------- */
function DiagnosticsTab({ movies, focus, setFocus, onOpen }) {
  const candidateCount = movies.filter(m => m.match === "candidate").length;
  const fieldGap = movies.reduce((s, m) => s + m.missing.length, 0);
  const detailTargets = movies.filter(m => m.missing.length).length;
  const launch = [
    { v: candidateCount, label: "待确认候选", hint: "先确认高风险匹配" },
    { v: fieldGap, label: "字段缺口", hint: "定位缺封面、时长、系列和分类" },
    { v: detailTargets, label: "可补详情", hint: "可继续抓取详情来源" },
  ];
  const badges = focus
    ? [...(focus.match === "candidate" ? ["候选待确认"] : []), ...(focus.missing.length ? [`${focus.missing.length} 个字段缺口`] : []), "可追溯来源", ...(focus.missing.length ? [] : ["字段已齐"])]
    : ["暂无影片"];
  return (
    <div className="workspace-panel">
      <div className="wp-head"><h3>来源诊断</h3></div>
      <div className="diag-launch">
        {launch.map((r, i) => (
          <div className="diag-launch-card" key={i}><strong>{r.v}</strong><span>{r.label}</span><small>{r.hint}</small></div>
        ))}
      </div>

      <div className="diag-focus">
        <div className="rp-thumb" style={{ background: focus.v.art }} onClick={() => onOpen(focus.v)}><span className="cc-code">{focus.v.code}</span></div>
        <div className="df-id">
          <span className="status-pill" style={{ background: "var(--card-2)", color: "var(--tx-2)" }}>诊断入口</span>
          <div className="df-title">{focus.v.code} · {focus.v.title}</div>
          <div className="df-badges">{badges.map(b => <span key={b}>{b}</span>)}</div>
        </div>
        <span className="grow"></span>
        <div className="df-actions">
          <button className="btn btn-quiet">匹配</button>
          <button className="btn btn-quiet">取消匹配</button>
          <button className="btn btn-quiet">忽略</button>
        </div>
      </div>

      <div className="rr-rail">
        <span className="rr-label">待诊断作品</span>
        {movies.filter(m => m.missing.length).map((m, i) => (
          <button key={i} className={"rr-pill" + (focus === m ? " on" : "")} onClick={() => setFocus(m)}>
            <span className="rr-thumb sm" style={{ background: m.v.art }}></span>
            <b>{m.v.code}</b><small>{m.missing.length} 缺口</small>
          </button>
        ))}
      </div>

      <div className="repair-fields">
        {FIELDS.map(f => {
          const has = focus.fields[f] !== null;
          const cands = FIELD_SOURCES[f] || [];
          return (
            <div className={"repair-field" + (has ? "" : " state-gap")} key={f}>
              <div className="rf-left">
                <span className={"rf-dot " + (has ? "ok" : "bad")}></span>
                <span className="rf-name">{f}</span>
                <span className="rf-state">{has ? "已就绪" : "缺失"}</span>
              </div>
              {has
                ? <div className="rf-value">{f === "标题" ? focus.fields[f] : (cands[0] ? cands[0].label : focus.fields[f])}<span className="rf-from">{cands[0] ? cands[0].src : "本地"} · 已采用</span></div>
                : <div className="rf-cands">
                    {cands.map((c, j) => (
                      <div className={"rf-cand" + (j === 0 ? " best" : "")} key={j}>
                        <span className="rf-src">{c.src}</span><span className="rf-clabel">{c.label}</span>
                        <button className={"btn btn-sm " + (j === 0 ? "cc-approve" : "btn-quiet")}>{j === 0 ? "采用" : "改用"}</button>
                      </div>
                    ))}
                  </div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ---------- 来源状态 tab ---------- */
function SourcesTab() {
  const isolated = SOURCES.filter(s => s.tone === "bad").length;
  return (
    <div className="workspace-panel">
      <div className="wp-head">
        <h3>来源状态</h3><span className="grow"></span>
        <button className="btn btn-ghost btn-sm">查看头像任务</button>
        <button className="btn btn-primary btn-sm">运行诊断</button>
      </div>
      <div className="src-summary">
        <div className="ss-card"><strong>{SOURCES.length}</strong><span>接入来源</span></div>
        <div className="ss-card"><strong style={{ color: "var(--ok)" }}>{SOURCES.filter(s => s.tone === "ok").length}</strong><span>可参与补全</span></div>
        <div className="ss-card"><strong style={{ color: "var(--warn)" }}>{SOURCES.filter(s => s.tone === "warn").length}</strong><span>降级限速</span></div>
        <div className="ss-card"><strong style={{ color: "var(--bad)" }}>{isolated}</strong><span>隔离中</span></div>
      </div>
      <div className="field-list">
        {SOURCES.map((s, i) => (
          <div className="source-card" key={i}>
            <span className={"status-dot " + s.tone}></span>
            <div className="sc-main">
              <div className="sc-name">{s.name}<small>{s.role}</small></div>
              <div className="sc-state">{s.state}</div>
            </div>
            <div className="sc-stat"><b>{s.failures}</b><span>连续失败</span></div>
            <div className="sc-stat"><b className="err">{s.error}</b><span>最近错误</span></div>
            <div className="sc-next"><span>下一步</span>{s.next}</div>
          </div>
        ))}
      </div>
      <div className="src-runbook"><Icon name="info" size={15} /><div><b>隔离 runbook</b>连续失败或预算异常的来源先暂停 24h，避免污染字段补全；窗口结束后自动恢复并重新参与诊断。</div></div>
    </div>
  );
}

/* ---------- workspace shell ---------- */
function SupWorkspace({ actor, onBack, onOpen }) {
  const [tab, setTab] = useState5("movies");
  const [running, setRunning] = useState5(actor.last === "running");
  const movies = supMovies(actor);
  const gapMovies = movies.filter(m => m.missing.length);
  const [focus, setFocus] = useState5(gapMovies[0] || movies[0]);
  const status = running ? "running" : actor.last;

  const tabs = [
    { k: "movies", label: "作品字段", n: movies.length },
    { k: "jobs", label: "任务队列", n: jobsFor(actor).length },
    { k: "diagnostics", label: "来源诊断", n: gapMovies.length },
    { k: "sources", label: "来源状态", n: SOURCES.length },
  ];
  const metrics = [
    { label: "补全来源", value: actor.supMovies, icon: "supplement" },
    { label: "已匹配片库", value: actor.matched, icon: "library" },
    { label: "补全新增", value: actor.supOnly, icon: "plus" },
    { label: "含版本条目", value: actor.resolved, icon: "stack" },
  ];
  const goDiag = m => { setFocus(m); setTab("diagnostics"); };

  return (
    <>
      <div className="topbar solid">
        <div><h1>补全演员</h1><div className="sub">字段补全工作台</div></div>
        <span className="grow"></span>
        <button className="btn btn-ghost" onClick={onBack}>更换演员</button>
        <button className="btn btn-ghost" onClick={() => setTab("sources")}>来源状态</button>
        <button className="btn btn-ghost" onClick={onBack}>全局队列</button>
      </div>
      <div className="page page-wide">
        <div className="sup-hero">
          <span className="sup-hero-av" style={{ background: actor.color }}>{actor.kanji[0]}</span>
          <div className="sup-hero-id">
            <h2>{actor.kanji}</h2>
            <div className="sh-sub">编号 {String(actor.id).padStart(5, "0")}</div>
            <div className="sh-status">
              <span className={"status-pill " + status}>{running ? "运行中" : STATUS_LABEL[actor.last]}</span>
              <span className="sh-recent">{actor.recent}</span>
            </div>
          </div>
          <span className="grow"></span>
          <div className="sup-hero-actions">
            <button className={"btn btn-primary" + (running ? " is-running" : "")} onClick={() => setRunning(r => !r)}>
              {running ? <><span className="spin-ring"></span> 补全中…</> : <><Icon name="supplement" size={16} /> 补全作品</>}
            </button>
            <button className="btn btn-ghost"><Icon name="stack" size={15} /> 刷新版本条目</button>
          </div>
        </div>

        <div className="stat-strip sup-metrics">
          {metrics.map((m, i) => (
            <div className="stat-card" key={i}>
              <div className="stat-top"><span className="stat-label" style={{ marginTop: 0 }}>{m.label}</span><Icon name={m.icon} size={17} /></div>
              <div className="stat-num">{m.value}</div>
            </div>
          ))}
        </div>

        <div className="segmented" style={{ marginBottom: "var(--s5)" }}>
          {tabs.map(t => (
            <button key={t.k} className={tab === t.k ? "active" : ""} onClick={() => setTab(t.k)}>{t.label} <span className="count">{t.n}</span></button>
          ))}
        </div>

        {tab === "movies" && <MoviesTab movies={movies} onOpen={onOpen} onDiagnose={goDiag} />}
        {tab === "jobs" && <JobsTab actor={actor} />}
        {tab === "diagnostics" && <DiagnosticsTab movies={movies} focus={focus} setFocus={setFocus} onOpen={onOpen} />}
        {tab === "sources" && <SourcesTab />}
      </div>
    </>
  );
}

function SupplementScreen({ onOpen }) {
  const [actor, setActor] = useState5(null);
  return actor
    ? <SupWorkspace actor={actor} onBack={() => setActor(null)} onOpen={onOpen} />
    : <SupActorPicker onPick={setActor} />;
}

Object.assign(window, { SupplementScreen });
