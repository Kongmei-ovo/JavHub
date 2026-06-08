/* JavHub redesign — extended screens (ops / library-org / settings) → window */
const { useState: useState2 } = React;

/* ============================================================
   Operations overview
   ============================================================ */
function OpsScreen() {
  const sources = [
    { name: "JavInfoApi", desc: "元数据主源", status: "ok", latency: "42ms" },
    { name: "Sukebei", desc: "磁力源 · torznab", status: "ok", latency: "118ms" },
    { name: "openlist", desc: "115 网盘挂载", status: "ok", latency: "67ms" },
    { name: "Emby", desc: "媒体库核对", status: "warn", latency: "1.2s" },
    { name: "DeepL", desc: "翻译服务", status: "ok", latency: "204ms" },
    { name: "Telegram Bot", desc: "通知 · 命令", status: "bad", latency: "超时" },
  ];
  const through = [
    { x: "周一", v: 38 }, { x: "周二", v: 62 }, { x: "周三", v: 45 },
    { x: "周四", v: 81 }, { x: "周五", v: 73 }, { x: "周六", v: 96 }, { x: "今日", v: 54, now: true },
  ];
  const maxV = Math.max(...through.map(t => t.v));
  const storage = [
    { label: "影片文件", v: 1480, color: "var(--accent)" },
    { label: "封面 / 缩略图", v: 142, color: "var(--info)" },
    { label: "导入数据库", v: 98, color: "var(--ok)" },
    { label: "缓存", v: 61, color: "var(--warn)" },
  ];
  const totalGB = storage.reduce((s, x) => s + x.v, 0);
  const jobs = [
    { t: "演员订阅扫描", time: "12 分钟前 · 抓取 6 部新片", icon: "star", tone: "ok" },
    { t: "磁力补全作业", time: "1 小时前 · 完成 23/28", icon: "link", tone: "info" },
    { t: "Emby 增量核对", time: "2 小时前 · 警告 1 项超时", icon: "inventory", tone: "warn" },
    { t: "翻译批处理", time: "今天 06:00 · 翻译 41 条", icon: "globe", tone: "ok" },
  ];
  const toneColor = { ok: "var(--ok)", warn: "var(--warn)", bad: "var(--bad)", info: "var(--info)" };

  return (
    <>
      <div className="topbar solid"><div><h1>运营总览</h1><div className="sub">系统健康 · 自动化任务 · 资源占用</div></div></div>
      <div className="page page-wide">
        {/* top KPI */}
        <div className="stat-strip" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
          {[
            { num: "99.2%", label: "近 7 日可用率", delta: "稳定", up: true, icon: "ops" },
            { num: "5/6", label: "数据源在线", delta: "1 项告警", up: false, icon: "stack" },
            { num: "1.8 TB", label: "占用空间", delta: "可用 640 GB", up: false, icon: "inventory" },
            { num: "128", label: "今日任务", delta: "+12% vs 昨日", up: true, icon: "today" },
          ].map((s, i) => (
            <div className="stat-card" key={i}>
              <div className="stat-top"><span className="stat-label" style={{ marginTop: 0 }}>{s.label}</span><Icon name={s.icon} size={18} /></div>
              <div className="stat-num">{s.num}</div>
              <div className={"stat-delta " + (s.up ? "up" : "flat")}>{s.delta}</div>
            </div>
          ))}
        </div>

        <div className="grid-2" style={{ marginTop: "var(--s6)" }}>
          {/* source health */}
          <div className="panel">
            <div className="panel-head"><h3>数据源健康</h3><span className="grow"></span><span className="badge ok dot">5 在线</span></div>
            {sources.map(s => (
              <div className="health-row" key={s.name}>
                <span className={"status-dot " + s.status}></span>
                <div className="health-name">{s.name}<small>{s.desc}</small></div>
                <span className="health-latency" style={s.status === "bad" ? { color: "var(--bad)" } : null}>{s.latency}</span>
              </div>
            ))}
          </div>

          {/* throughput chart */}
          <div className="panel">
            <div className="panel-head"><h3>下载吞吐</h3><span className="grow"></span><span className="sub">部 / 天</span></div>
            <div className="chart">
              {through.map(t => (
                <div className="chart-col" key={t.x}>
                  <div className={"chart-bar" + (t.now ? "" : "")} style={{ height: (t.v / maxV * 100) + "%", opacity: t.now ? 1 : 0.85 }}></div>
                  <span className="chart-x" style={t.now ? { color: "var(--accent)", fontWeight: 700 } : null}>{t.x}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid-2" style={{ marginTop: "var(--s4)" }}>
          {/* storage */}
          <div className="panel">
            <div className="panel-head"><h3>存储分布</h3><span className="grow"></span><span className="sub">共 {(totalGB / 1024).toFixed(1)} TB</span></div>
            <div className="storage-bar">
              {storage.map(s => <div className="storage-seg" key={s.label} style={{ width: (s.v / totalGB * 100) + "%", background: s.color }}></div>)}
            </div>
            <div className="storage-legend">
              {storage.map(s => (
                <div className="legend-row" key={s.label}>
                  <span className="legend-dot" style={{ background: s.color }}></span>
                  <span>{s.label}</span><span className="grow"></span>
                  <b>{s.v >= 1024 ? (s.v / 1024).toFixed(1) + " TB" : s.v + " GB"}</b>
                </div>
              ))}
            </div>
          </div>

          {/* job activity */}
          <div className="panel">
            <div className="panel-head"><h3>近期任务</h3><span className="grow"></span><button className="link" style={{ color: "var(--accent)", fontSize: "var(--t-cap)", fontWeight: 600 }}>全部日志</button></div>
            {jobs.map((j, i) => (
              <div className="job-row" key={i}>
                <div className="job-icon" style={{ background: `rgba(var(--${j.tone}-rgb), 0.16)`, color: toneColor[j.tone] }}><Icon name={j.icon} size={17} /></div>
                <div className="job-body"><div className="job-title">{j.t}</div><div className="job-time">{j.time}</div></div>
                <Icon name="chevR" size={16} style={{ color: "var(--tx-3)" }} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

/* ============================================================
   Library organize — scan / duplicates / normalize
   ============================================================ */
function LibraryOrgScreen() {
  const { V } = window.JH;
  const [tab, setTab] = useState2("重复");
  const [keep, setKeep] = useState2({ 0: 0, 1: 1 });
  const dupes = [
    { code: "MIAA-784", art: V[0].art, items: [
      { path: "/115/AV/MIAA-784/MIAA-784-FHD.mp4", size: "5.84 GB", res: "1920×1080", added: "2026-05-06" },
      { path: "/115/AV/旧/MIAA784.mkv", size: "3.10 GB", res: "1280×720", added: "2025-11-02" },
    ]},
    { code: "SIVR-438", art: V[1].art, items: [
      { path: "/115/VR/SIVR-438.mp4", size: "12.4 GB", res: "3840×1920", added: "2026-04-18" },
      { path: "/downloads/SIVR-438-leftover.mp4", size: "12.4 GB", res: "3840×1920", added: "2026-04-18" },
    ]},
  ];
  const norms = [
    { from: "miaa784.mp4", to: "MIAA-784", reason: "番号大写规范" },
    { from: "[字幕组]ABP_588.mkv", to: "ABP-588", reason: "去除前缀 · 统一分隔符" },
    { from: "SSIS902 (1).mp4", to: "SSIS-902", reason: "去重后缀 · 插入连字符" },
    { from: "fsdss-712-c.mp4", to: "FSDSS-712 [中文字幕]", reason: "识别字幕标记" },
  ];

  return (
    <>
      <div className="topbar solid"><div><h1>片库整理</h1><div className="sub">扫描 · 去重 · 命名规范化</div></div></div>
      <div className="page page-wide">
        <div className="scan-banner">
          <div className="scan-ring" style={{ "--p": "64%" }}><span>64%</span></div>
          <div className="scan-info">
            <h3>正在扫描片库 · 2,418 个文件</h3>
            <p>已比对 1,548 个 · 发现 2 组重复、4 处命名待规范、3 个孤立文件</p>
          </div>
          <button className="btn btn-ghost">暂停</button>
          <button className="btn btn-primary"><Icon name="check" size={16} /> 应用全部建议</button>
        </div>

        <div className="segmented" style={{ marginBottom: "var(--s5)" }}>
          {[["重复", 2], ["命名规范", 4], ["孤立文件", 3]].map(([k, n]) => (
            <button key={k} className={tab === k ? "active" : ""} onClick={() => setTab(k)}>{k} <span className="count">{n}</span></button>
          ))}
        </div>

        {tab === "重复" && dupes.map((g, gi) => (
          <div className="dupe-group" key={g.code}>
            <div className="dupe-head">
              <span className="code">{g.code}</span>
              <span className="chip">{g.items.length} 个文件</span>
              <span className="grow"></span>
              <span className="muted" style={{ fontSize: "var(--t-cap)" }}>保留选中 · 其余移入回收站</span>
            </div>
            <div className="dupe-items">
              {g.items.map((it, ii) => (
                <div className="dupe-item" key={ii}>
                  <button className={"radio-keep" + (keep[gi] === ii ? " on" : "")} onClick={() => setKeep(k => ({ ...k, [gi]: ii }))} aria-label="保留此文件"></button>
                  <div className="dupe-thumb" style={{ background: g.art }}></div>
                  <div className="dupe-detail">
                    <div className="dupe-path">{it.path}</div>
                    <div className="dupe-attrs"><span>{it.size}</span><span>{it.res}</span><span>入库 {it.added}</span>{keep[gi] === ii && <span className="badge ok" style={{ padding: "1px 6px" }}>保留</span>}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {tab === "命名规范" && norms.map((n, i) => (
          <div className="norm-row" key={i}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="row" style={{ gap: "var(--s2)", flexWrap: "wrap" }}>
                <span className="norm-from">{n.from}</span>
                <span className="norm-arrow"><Icon name="arrowR" size={15} /></span>
                <span className="norm-to">{n.to}</span>
              </div>
              <div className="muted" style={{ fontSize: "var(--t-micro)", marginTop: 5 }}>{n.reason}</div>
            </div>
            <button className="btn btn-ghost" style={{ height: 34 }}>跳过</button>
            <button className="btn btn-primary" style={{ height: 34 }}>应用</button>
          </div>
        ))}

        {tab === "孤立文件" && (
          <div className="panel" style={{ textAlign: "center", padding: "var(--s9)" }}>
            <div style={{ color: "var(--tx-3)", marginBottom: "var(--s3)" }}><Icon name="parse" size={32} /></div>
            <div style={{ fontWeight: 600 }}>3 个孤立文件未匹配到元数据</div>
            <p className="muted" style={{ fontSize: "var(--t-cap)", marginTop: 6 }}>可手动指定番号，或交给补全管理识别。</p>
            <button className="btn btn-primary" style={{ marginTop: "var(--s4)" }}>去识别</button>
          </div>
        )}
      </div>
    </>
  );
}

/* ============================================================
   Settings / Config center
   ============================================================ */
function Switch({ on, onClick }) {
  return <button className={"switch" + (on ? " on" : "")} onClick={onClick} role="switch" aria-checked={on}><span></span></button>;
}
function SettingsScreen() {
  const tabs = [
    { k: "通用", icon: "settings" }, { k: "数据源", icon: "stack" }, { k: "下载", icon: "download" },
    { k: "整理", icon: "inventory" }, { k: "通知", icon: "bell" },
  ];
  const [tab, setTab] = useState2("通用");
  const [sw, setSw] = useState2({ dark: true, auto: true, sub: true, dedupe: false, tg: false, nsfw: true });
  const t = (k) => setSw(s => ({ ...s, [k]: !s[k] }));

  return (
    <>
      <div className="topbar solid"><div><h1>配置中心</h1><div className="sub">config.yaml · 实时生效</div></div></div>
      <div className="page">
        <div className="settings-layout">
          <nav className="settings-tabs">
            {tabs.map(x => (
              <button key={x.k} className={"settings-tab" + (tab === x.k ? " active" : "")} onClick={() => setTab(x.k)}>
                <Icon name={x.icon} size={19} /> {x.k}
              </button>
            ))}
          </nav>

          <div>
            {tab === "通用" && (
              <div className="set-group">
                <h3>外观</h3>
                <p>这些偏好保存在浏览器，立即生效。</p>
                <div className="set-card">
                  <div className="set-row"><div className="k">深色主题<small>跟随系统或手动锁定</small></div><span className="grow"></span><Switch on={sw.dark} onClick={() => t("dark")} /></div>
                  <div className="set-row"><div className="k">界面语言</div><span className="grow"></span>
                    <div className="segmented"><button className="active">简体中文</button><button>English</button><button>日本語</button></div>
                  </div>
                  <div className="set-row"><div className="k">默认落地页<small>打开应用时显示的页面</small></div><span className="grow"></span>
                    <select className="set-input"><option>今日</option><option>影库</option><option>私人策展</option><option>下载任务</option></select>
                  </div>
                </div>
              </div>
            )}
            {tab === "数据源" && (
              <div className="set-group">
                <h3>JavInfoApi</h3>
                <p>元数据主源。修改后会重新校验连接。</p>
                <div className="set-card">
                  <div className="set-row"><div className="k">API 地址</div><span className="grow"></span><input className="set-input mono" defaultValue="http://javinfoapi:18080" /></div>
                  <div className="set-row"><div className="k">每页条数</div><span className="grow"></span><input className="set-input" defaultValue="30" style={{ minWidth: 100 }} /></div>
                  <div className="set-row"><div className="k">补全管理员令牌</div><span className="grow"></span><input className="set-input mono" type="password" defaultValue="change-me-xxxx" /></div>
                  <div className="set-row"><div className="k">自动补全缺失元数据<small>新片入库时自动从主源拉取</small></div><span className="grow"></span><Switch on={sw.auto} onClick={() => t("auto")} /></div>
                </div>
              </div>
            )}
            {tab === "下载" && (
              <div className="set-group">
                <h3>下载与订阅</h3>
                <p>控制候选抓取与默认下载行为。</p>
                <div className="set-card">
                  <div className="set-row"><div className="k">默认下载器</div><span className="grow"></span><select className="set-input"><option>qBittorrent</option><option>Transmission</option><option>Aria2</option></select></div>
                  <div className="set-row"><div className="k">演员订阅自动抓取<small>定时扫描订阅演员的新作品</small></div><span className="grow"></span><Switch on={sw.sub} onClick={() => t("sub")} /></div>
                  <div className="set-row"><div className="k">候选自动通过阈值<small>种子数高于此值的候选自动入队</small></div><span className="grow"></span><input className="set-input" defaultValue="100" style={{ minWidth: 100 }} /></div>
                  <div className="set-row"><div className="k">磁力偏好</div><span className="grow"></span><div className="segmented"><button className="active">高清优先</button><button>中文字幕优先</button><button>体积优先</button></div></div>
                </div>
              </div>
            )}
            {tab === "整理" && (
              <div className="set-group">
                <h3>片库整理</h3>
                <p>扫描与规范化规则。</p>
                <div className="set-card">
                  <div className="set-row"><div className="k">扫描后自动去重<small>发现重复时自动保留最高画质</small></div><span className="grow"></span><Switch on={sw.dedupe} onClick={() => t("dedupe")} /></div>
                  <div className="set-row"><div className="k">命名模板</div><span className="grow"></span><input className="set-input mono" defaultValue="{番号} {标题}" /></div>
                  <div className="set-row"><div className="k">媒体库路径</div><span className="grow"></span><input className="set-input mono" defaultValue="/115/AV" /></div>
                </div>
              </div>
            )}
            {tab === "通知" && (
              <div className="set-group">
                <h3>Telegram</h3>
                <p>任务完成与告警推送。</p>
                <div className="set-card">
                  <div className="set-row"><div className="k">启用 Telegram 通知</div><span className="grow"></span><Switch on={sw.tg} onClick={() => t("tg")} /></div>
                  <div className="set-row"><div className="k">Bot Token</div><span className="grow"></span><input className="set-input mono" type="password" defaultValue="" placeholder="未配置" /></div>
                  <div className="set-row"><div className="k">仅推送告警<small>关闭则每个任务完成都通知</small></div><span className="grow"></span><Switch on={sw.nsfw} onClick={() => t("nsfw")} /></div>
                </div>
              </div>
            )}

            <div className="row" style={{ justifyContent: "flex-end", marginTop: "var(--s5)" }}>
              <button className="btn btn-ghost">恢复默认</button>
              <button className="btn btn-primary"><Icon name="check" size={16} /> 保存更改</button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

Object.assign(window, { OpsScreen, LibraryOrgScreen, SettingsScreen });
