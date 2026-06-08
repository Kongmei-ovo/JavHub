/* JavHub redesign — downloads queue → window */
const { useState: useState4 } = React;

function DownloadsScreen() {
  const { V } = window.JH;
  const initial = [
    { id: 1, code: "SSIS-902", name: "海边小镇的最后一个夏天", art: V[4].art, state: "active", pct: 67, speed: "8.4 MB/s", eta: "12 分钟", peers: 24, size: "5.84 GB" },
    { id: 2, code: "JUQ-455", name: "搬家那天，旧公寓还留着她的味道", art: V[9].art, state: "active", pct: 92, speed: "11.2 MB/s", eta: "2 分钟", peers: 38, size: "4.91 GB" },
    { id: 3, code: "MIDV-661", name: "她的房间里，时钟永远停在午夜", art: V[5].art, state: "paused", pct: 31, speed: "—", eta: "已暂停", peers: 0, size: "5.12 GB" },
    { id: 4, code: "CAWD-633", name: "学生时代没说出口的那句话", art: V[8].art, state: "queued", pct: 0, speed: "—", eta: "排队中", peers: 0, size: "4.30 GB" },
    { id: 5, code: "FSDSS-712", name: "雨停之前，谁先开口都算输", art: V[6].art, state: "queued", pct: 0, speed: "—", eta: "排队中", peers: 0, size: "3.88 GB" },
    { id: 6, code: "MIAA-784", name: "夏日之后，她把秘密留在了旅馆走廊", art: V[0].art, state: "done", pct: 100, speed: "—", eta: "今天 09:14", peers: 0, size: "5.84 GB" },
    { id: 7, code: "IPZZ-091", name: "没有演员数据的收藏，依然保持轻量", art: V[3].art, state: "done", pct: 100, speed: "—", eta: "昨天 22:03", peers: 0, size: "6.20 GB" },
    { id: 8, code: "WAAA-377", name: "末班车上，她靠在陌生人的肩膀睡着了", art: V[11].art, state: "failed", pct: 14, speed: "—", eta: "失败", peers: 0, size: "—", err: "磁力无活跃做种者 · 已重试 3 次" },
  ];
  const [tasks, setTasks] = useState4(initial);
  const [tab, setTab] = useState4("下载中");

  const map = { 下载中: t => t.state === "active" || t.state === "paused", 排队: t => t.state === "queued", 已完成: t => t.state === "done", 失败: t => t.state === "failed" };
  const counts = Object.fromEntries(Object.entries(map).map(([k, fn]) => [k, tasks.filter(fn).length]));
  const visible = tasks.filter(map[tab]);

  const pauseToggle = id => setTasks(ts => ts.map(t => t.id === id ? { ...t, state: t.state === "active" ? "paused" : "active", speed: t.state === "active" ? "—" : "6.0 MB/s", eta: t.state === "active" ? "已暂停" : "15 分钟" } : t));
  const remove = id => setTasks(ts => ts.filter(t => t.id !== id));
  const retry = id => setTasks(ts => ts.map(t => t.id === id ? { ...t, state: "active", pct: 1, speed: "2.1 MB/s", eta: "计算中", err: null } : t));

  const activeTasks = tasks.filter(t => t.state === "active");
  const totalDown = activeTasks.reduce((s, t) => s + parseFloat(t.speed), 0).toFixed(1);

  return (
    <>
      <div className="topbar solid">
        <div><h1>下载任务</h1><div className="sub">{counts["下载中"]} 个进行中 · {counts["排队"]} 个排队</div></div>
        <span className="grow"></span>
        <span className="speed-pill"><Icon name="download" size={15} /> <span className="down">↓ {totalDown} MB/s</span> · <span className="up">↑ 0.8 MB/s</span></span>
      </div>
      <div className="page">
        <div className="downloader-pills">
          <span className="dler-pill"><span className="status-dot ok"></span> qBittorrent · 默认</span>
          <span className="dler-pill"><span className="status-dot ok"></span> Transmission</span>
          <span className="dler-pill"><span className="status-dot warn"></span> Aria2 · 离线</span>
        </div>

        <div className="segmented" style={{ marginBottom: "var(--s5)" }}>
          {Object.keys(map).map(k => (
            <button key={k} className={tab === k ? "active" : ""} onClick={() => setTab(k)}>{k} <span className="count">{counts[k]}</span></button>
          ))}
        </div>

        {visible.length === 0 && (
          <div className="panel" style={{ textAlign: "center", padding: "var(--s10)" }}>
            <div style={{ color: "var(--tx-3)", marginBottom: "var(--s3)" }}><Icon name="download" size={32} /></div>
            <div style={{ fontWeight: 600 }}>「{tab}」没有任务</div>
          </div>
        )}

        <div className="dl-list">
          {visible.map(t => (
            <div className={"dl-row " + t.state} key={t.id}>
              <div className="dl-thumb" style={{ background: t.art }}></div>
              <div className="dl-info">
                <div className="dl-name">{t.name}</div>
                <div className="dl-meta">
                  <span style={{ fontFamily: "var(--font-mono)" }}>{t.code}</span>
                  <span>{t.size}</span>
                  {t.peers > 0 && <span>{t.peers} peers</span>}
                  <span>{t.eta}</span>
                </div>
                {t.state !== "done" && t.state !== "failed" && <div className="dl-bar"><span style={{ width: t.pct + "%" }}></span></div>}
                {t.state === "done" && <div className="dl-bar"><span style={{ width: "100%" }}></span></div>}
                {t.err && <div className="dl-err">{t.err}</div>}
              </div>
              <div className="dl-right" style={{ minWidth: 64 }}>
                {t.state === "done"
                  ? <span className="badge ok dot">完成</span>
                  : t.state === "failed"
                    ? <span className="badge bad dot">失败</span>
                    : <><div className="dl-pct">{t.pct}%</div><div className="dl-speed">{t.speed}</div></>}
              </div>
              <div className="dl-actions">
                {(t.state === "active" || t.state === "paused") && (
                  <button className="icon-act" title={t.state === "active" ? "暂停" : "继续"} onClick={() => pauseToggle(t.id)}>
                    {t.state === "active"
                      ? <svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>
                      : <Icon name="play" size={16} fill />}
                  </button>
                )}
                {t.state === "done" && <button className="icon-act" title="在片库整理"><Icon name="inventory" size={16} /></button>}
                {t.state === "failed" && <button className="icon-act" title="重试" onClick={() => retry(t.id)}><Icon name="download" size={16} /></button>}
                <button className="icon-act danger" title="移除" onClick={() => remove(t.id)}><Icon name="close" size={16} /></button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

Object.assign(window, { DownloadsScreen });
