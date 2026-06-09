/* JavHub redesign — discovery / candidates / subscriptions → window */
const { useState: useState3 } = React;

/* ============================================================
   Explore — shuffle discovery
   ============================================================ */
function ExploreScreen({ onOpen }) {
  const { V } = window.JH;
  const genres = ["全部", "单体作品", "剧情", "巨乳", "美少女", "VR专用", "人妻", "温泉", "制服"];
  const [g, setG] = useState3("全部");
  const [seed, setSeed] = useState3(0);
  const [spin, setSpin] = useState3(false);

  const pool = V.filter(v => g === "全部" || v.genres.includes(g));
  const rnd = (str) => { let h = (seed + 1) * 2654435761 >>> 0; for (const c of str) h = ((h ^ c.charCodeAt(0)) * 16777619) >>> 0; return h; };
  const shuffled = [...pool].sort((a, b) => rnd(a.code) - rnd(b.code));
  const featured = shuffled[0] || V[0];
  const picks = shuffled.slice(1, 11);
  const reshuffle = () => { setSpin(true); setSeed(s => s + 1); setTimeout(() => setSpin(false), 500); };

  return (
    <>
      <div className="topbar solid"><div><h1>随机探索</h1><div className="sub">从片库里翻出被遗忘的好片</div></div></div>
      <div className="page page-wide">
        <div className="genre-chips">
          {genres.map(x => <span key={x} className={"chip" + (g === x ? " on" : "")} onClick={() => { setG(x); }}>{x}</span>)}
        </div>

        <div className="shuffle-hero">
          <div className="shuffle-poster" onClick={() => onOpen(featured)} style={{ background: featured.art }}>
            <div className="poster-scrim"></div>
            <span className="poster-code">{featured.code}</span>
          </div>
          <div className="shuffle-info">
            <div className="hero-kicker" style={{ color: "var(--accent)" }}><Icon name="star" size={13} fill /> 今日推荐</div>
            <h2>{featured.title}</h2>
            <div className="code">{featured.code} · {featured.studio} · {featured.runtime} 分钟</div>
            <p>{featured.acts.length ? featured.acts.map(a => a.kanji).join(" / ") : "未知演员"} · {featured.genres.slice(0, 3).join(" · ")}</p>
            <div className="shuffle-actions">
              <button className="btn btn-primary" onClick={() => onOpen(featured)}><Icon name="play" size={16} fill /> 查看详情</button>
              <button className="btn btn-ghost" onClick={reshuffle}>
                <span className={spin ? "dice-spin" : ""} style={{ display: "inline-flex" }}><Icon name="search" size={16} /></span> 换一个
              </button>
            </div>
          </div>
        </div>

        <SectionHead title="再看看这些" count={`${picks.length} 部随机`} action="刷新整批" onAction={reshuffle} />
        <div className="poster-grid">
          {picks.map(v => <PosterCard key={v.code} v={v} onOpen={onOpen} />)}
        </div>
      </div>
    </>
  );
}

/* ============================================================
   Candidates — real batch review flow
   ============================================================ */
const CAND_SOURCES = ["全部来源", "订阅", "库存", "补全", "手动"];

function CandidatesScreen({ onOpen }) {
  const { V, A } = window.JH;
  const initial = [
    { id: 1, code: "MIDV-661", title: "她的房间里，时钟永远停在午夜", orig: "彼女の部屋、時計は真夜中", art: V[5].art, act: A.kojima, source: "订阅", date: "2026-03-30", time: "8 分钟前", seeds: 142, magnet: true, status: "candidate" },
    { id: 2, code: "FSDSS-712", title: "雨停之前，谁先开口都算输", orig: "雨が止むまでに", art: V[6].art, act: A.momono, source: "订阅", date: "2026-01-14", time: "12 分钟前", seeds: 88, magnet: true, status: "candidate" },
    { id: 3, code: "SSIS-902", title: "海边小镇的最后一个夏天", orig: "海辺の町の最後の夏", art: V[4].art, act: A.yua, source: "库存", date: "2026-05-22", time: "1 小时前", seeds: 0, magnet: false, status: "candidate" },
    { id: 4, code: "CAWD-633", title: "学生时代没说出口的那句话", orig: "あの頃言えなかった言葉", art: V[8].art, act: A.akari, source: "手动", date: "2026-04-02", time: "2 小时前", seeds: 211, magnet: true, status: "candidate" },
    { id: 5, code: "PRED-540", title: "周末的便利店，凌晨三点的相遇", orig: "週末のコンビニ、午前三時", art: V[7].art, act: A.nanami, source: "补全", date: "2025-11-08", time: "3 小时前", seeds: 0, magnet: false, status: "candidate" },
    { id: 6, code: "STARS-841", title: "便签上写着：等你回来一起看完", orig: "付箋のメッセージ", art: V[10].art, act: A.aoi, source: "订阅", date: "2026-02-27", time: "今天 06:12", seeds: 56, magnet: true, status: "candidate" },
    { id: 7, code: "WAAA-377", title: "末班车上，她靠在陌生人的肩膀睡着了", orig: "終電のなかで", art: V[11].art, act: A.momono, source: "订阅", date: "2025-10-19", time: "今天 04:00", seeds: 30, magnet: true, status: "sent", taskId: 4821 },
    { id: 8, code: "JUQ-455", title: "搬家那天，旧公寓还留着她的味道", orig: "引っ越しの日", art: V[9].art, act: A.yua, source: "库存", date: "2026-05-15", time: "今天 03:42", seeds: 18, magnet: true, status: "failed", reason: "下载器连接超时 · qBittorrent" },
  ];
  const [items, setItems] = useState3(initial);
  const [sel, setSel] = useState3([]);
  const [filter, setFilter] = useState3("待确认");
  const [src, setSrc] = useState3("全部来源");
  const nextTask = React.useRef(4830);

  const isCand = i => i.status === "candidate";
  const FILTERS = {
    待确认: i => isCand(i),
    待补磁力: i => isCand(i) && !i.magnet,
    可批准: i => isCand(i) && i.magnet,
    已下发: i => i.status === "sent",
    失败: i => i.status === "failed",
    已拒绝: i => i.status === "rejected",
  };
  const counts = Object.fromEntries(Object.entries(FILTERS).map(([k, f]) => [k, items.filter(f).length]));
  const bySource = src === "全部来源" ? items : items.filter(i => i.source === src);
  const srcCounts = Object.fromEntries(CAND_SOURCES.slice(1).map(s => [s, items.filter(i => i.source === s && isCand(i)).length]));
  const visible = bySource.filter(FILTERS[filter]);
  const approvable = visible.filter(i => isCand(i) && i.magnet);

  const patch = (ids, fn) => { setItems(its => its.map(i => ids.includes(i.id) ? fn(i) : i)); setSel(s => s.filter(x => !ids.includes(x))); };
  const approve = ids => patch(ids, i => ({ ...i, status: "sent", taskId: nextTask.current++ }));
  const reject = ids => patch(ids, i => ({ ...i, status: "rejected" }));
  const restore = ids => patch(ids, i => ({ ...i, status: "candidate" }));
  const enrich = id => patch([id], i => ({ ...i, magnet: true, seeds: 40 + (i.id * 17) % 180 }));
  const toggle = id => setSel(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);

  return (
    <>
      <div className="topbar solid">
        <div><h1>候选确认</h1><div className="sub">订阅 / 库存 / 补全自动抓取 · 批准后进入下载队列</div></div>
        <span className="grow"></span>
        <button className="btn btn-ghost"><Icon name="download" size={16} /> 下载队列</button>
      </div>
      <div className="page">
        {/* review summary band */}
        <div className="cand-summary">
          <div className="cs-head">
            <div className="cs-num">{counts.待确认}</div>
            <div className="cs-cap"><b>个候选等待确认</b><span>批准即生成下载任务，缺磁力的需先补磁力</span></div>
          </div>
          <span className="grow"></span>
          <div className="cs-stats">
            <div className="cs-stat"><span className="v" style={{ color: counts.可批准 ? "var(--ok)" : "var(--tx-2)" }}>{counts.可批准}</span><span className="l">可批准</span></div>
            <div className="cs-stat"><span className="v" style={{ color: counts.待补磁力 ? "var(--bad)" : "var(--tx-2)" }}>{counts.待补磁力}</span><span className="l">待补磁力</span></div>
            <div className="cs-stat"><span className="v">{counts.已下发}</span><span className="l">已下发</span></div>
          </div>
        </div>

        <div className="row" style={{ marginBottom: "var(--s3)", flexWrap: "wrap" }}>
          <div className="segmented">
            {Object.keys(FILTERS).map(k => (
              <button key={k} className={filter === k ? "active" : ""} onClick={() => setFilter(k)}>
                {k} <span className="count">{counts[k]}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="row cand-srcrow" style={{ marginBottom: "var(--s5)", flexWrap: "wrap" }}>
          <div className="src-chips">
            {CAND_SOURCES.map(s => (
              <button key={s} className={"chip" + (src === s ? " on" : "")} onClick={() => setSrc(s)}>
                {s}{s !== "全部来源" && <span className="src-n"> {srcCounts[s]}</span>}
              </button>
            ))}
          </div>
          <span className="grow"></span>
          {approvable.length > 0 && (
            <button className="btn btn-quiet" onClick={() => setSel(sel.length === approvable.length ? [] : approvable.map(i => i.id))}>
              {sel.length === approvable.length ? "清空" : `选择当前页 ${approvable.length} 项`}
            </button>
          )}
        </div>

        {visible.length === 0 && (
          <div className="cand-empty">
            <div className="ce-ring"><Icon name="download" size={28} /></div>
            <div style={{ fontWeight: 650, fontSize: "var(--t-h3)" }}>暂无下载候选</div>
            <p className="muted" style={{ fontSize: "var(--t-cap)", marginTop: 6 }}>订阅检查和库存对比会把缺失影片写到这里。</p>
          </div>
        )}

        {visible.map(i => {
          const v = V.find(x => x.code === i.code);
          const pickable = isCand(i) && i.magnet;
          return (
            <div className={"cand-card status-" + i.status + (!i.magnet && isCand(i) ? " nomag" : "") + (sel.includes(i.id) ? " picked" : "")} key={i.id}>
              <div className="cc-poster" style={{ background: i.art }} onClick={() => v && onOpen(v)}>
                <div className="cc-scrim"></div>
                <span className="cc-code">{i.code}</span>
                {pickable && (
                  <button className={"cc-check" + (sel.includes(i.id) ? " on" : "")} onClick={e => { e.stopPropagation(); toggle(i.id); }} aria-label="选择">
                    {sel.includes(i.id) && <Icon name="check" size={14} />}
                  </button>
                )}
              </div>
              <div className="cc-main">
                <div className="cc-srcline">
                  <span className="src-pill">{i.source}</span>
                  <span className={"mag-state" + (i.magnet ? "" : " empty")}>{i.magnet ? "已有 magnet" : "待补磁力"}</span>
                  <span className="cc-time">{i.time}</span>
                </div>
                <div className="cc-title" onClick={() => v && onOpen(v)}>{i.title}</div>
                <div className="cc-orig">{i.orig}</div>
                <div className="cc-actor">
                  <span className="av" style={{ background: i.act.color }}>{i.act.kanji[0]}</span>
                  <span className="nm">{i.act.kanji}</span>
                  <span className="rm">· {i.date}</span>
                </div>
                {i.status === "failed" && <div className="cc-reason"><Icon name="info" size={12} /> {i.reason}</div>}
                {i.status === "sent" && <div className="cc-tasklink">已关联任务 #{i.taskId} · 下载中</div>}
                <div className="cc-links">
                  <button className="link-btn" onClick={() => v && onOpen(v)}>详情</button>
                  <button className="link-btn">演员</button>
                  {i.source === "补全" && <button className="link-btn">补全</button>}
                </div>
              </div>
              <div className="cc-decide">
                {isCand(i) && i.magnet && (<>
                  <div className="cc-seed"><span className="status-dot ok" style={{ width: 7, height: 7 }}></span>{i.seeds} 种子 · 可批准</div>
                  <div className="cc-btn-row">
                    <button className="btn cc-approve" onClick={() => approve([i.id])}><Icon name="check" size={15} /> 批准</button>
                    <button className="btn btn-ghost" title="按下载策略自动处理">策略处理</button>
                  </div>
                  <div className="cc-quiet"><button className="link-btn">填磁力</button><span>·</span><button className="link-btn danger" onClick={() => reject([i.id])}>拒绝</button></div>
                </>)}
                {isCand(i) && !i.magnet && (<>
                  <div className="cc-warn"><Icon name="info" size={13} /> 待补磁力 · 暂不可批准</div>
                  <div className="cc-btn-row">
                    <button className="btn cc-supplement" onClick={() => enrich(i.id)}><Icon name="link" size={15} /> 补磁力</button>
                    <button className="btn btn-ghost">填磁力</button>
                  </div>
                  <div className="cc-quiet"><button className="link-btn danger" onClick={() => reject([i.id])}>拒绝</button></div>
                </>)}
                {i.status === "sent" && <span className="badge ok dot">已下发</span>}
                {i.status === "failed" && (<>
                  <div className="cc-btn-row">
                    <button className="btn cc-approve" onClick={() => approve([i.id])}><Icon name="download" size={15} /> 重试</button>
                  </div>
                  <div className="cc-quiet"><button className="link-btn danger" onClick={() => reject([i.id])}>拒绝</button></div>
                </>)}
                {i.status === "rejected" && (<>
                  <span className="badge bad dot">已拒绝</span>
                  <button className="link-btn" onClick={() => restore([i.id])}>恢复</button>
                </>)}
              </div>
            </div>
          );
        })}

        {sel.length > 0 && (
          <div className="batch-bar">
            <span className="count-pill">已选 <b>{sel.length}</b> 个</span>
            <span className="divider"></span>
            <button className="btn btn-quiet" style={{ color: "var(--ok)" }} onClick={() => approve(sel)}><Icon name="check" size={16} /> 批准</button>
            <button className="btn btn-quiet"><Icon name="settings" size={16} /> 按策略处理</button>
            <button className="btn btn-quiet" style={{ color: "var(--bad)" }} onClick={() => reject(sel)}><Icon name="close" size={16} /> 批量拒绝</button>
            <span className="divider"></span>
            <button className="btn btn-ghost" onClick={() => setSel([])}>取消</button>
          </div>
        )}
      </div>
    </>
  );
}

/* ============================================================
   Subscriptions — artist grid
   ============================================================ */
function SubsScreen() {
  const { A } = window.JH;
  const base = [
    { ...A.kojima, since: "2024-03", count: 48, neu: 3, cadence: "约 2 部/月" },
    { ...A.momono, since: "2024-08", count: 31, neu: 2, cadence: "约 1 部/月" },
    { ...A.yua, since: "2023-11", count: 62, neu: 1, cadence: "约 2 部/月" },
    { ...A.aoi, since: null, count: 29, neu: 0, cadence: "约 1 部/月" },
    { ...A.akari, since: null, count: 24, neu: 0, cadence: "约 1 部/月" },
    { ...A.nanami, since: null, count: 18, neu: 0, cadence: "约 1 部/月" },
  ];
  const [subs, setSubs] = useState3(base.map(a => ({ ...a, on: !!a.since })));
  const [tab, setTab] = useState3("全部");
  const toggle = id => setSubs(s => s.map(a => a.id === id ? { ...a, on: !a.on, neu: a.on ? a.neu : a.neu } : a));
  const list = tab === "已订阅" ? subs.filter(a => a.on) : tab === "推荐" ? subs.filter(a => !a.on) : subs;

  return (
    <>
      <div className="topbar solid"><div><h1>演员订阅</h1><div className="sub">订阅后自动抓取新作品到候选</div></div></div>
      <div className="page page-wide">
        <div className="stat-strip" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: "var(--s6)" }}>
          {[
            { num: subs.filter(a => a.on).length, label: "已订阅演员", icon: "star" },
            { num: subs.reduce((s, a) => s + (a.on ? a.neu : 0), 0), label: "本期新片", icon: "download" },
            { num: subs.reduce((s, a) => s + a.count, 0), label: "累计收录", icon: "library" },
          ].map((s, i) => (
            <div className="stat-card" key={i}>
              <div className="stat-top"><span className="stat-label" style={{ marginTop: 0 }}>{s.label}</span><Icon name={s.icon} size={18} /></div>
              <div className="stat-num">{s.num}</div>
            </div>
          ))}
        </div>

        <div className="segmented" style={{ marginBottom: "var(--s5)" }}>
          {[["全部", subs.length], ["已订阅", subs.filter(a => a.on).length], ["推荐", subs.filter(a => !a.on).length]].map(([k, n]) => (
            <button key={k} className={tab === k ? "active" : ""} onClick={() => setTab(k)}>{k} <span className="count">{n}</span></button>
          ))}
        </div>

        <div className="artist-grid">
          {list.map(a => (
            <div className="artist-card" key={a.id}>
              <div className="artist-avatar" style={{ background: a.color }}>
                {a.kanji[0]}
                {a.on && a.neu > 0 && <span className="new-pip">+{a.neu}</span>}
              </div>
              <div className="artist-name">{a.kanji}</div>
              <div className="artist-romaji">{a.romaji}</div>
              <div className="artist-stats">
                <span className="chip">{a.count} 部</span>
                <span className="chip">{a.cadence}</span>
              </div>
              <button className={"sub-btn " + (a.on ? "done" : "can")} onClick={() => toggle(a.id)}>
                {a.on ? <><Icon name="check" size={13} /> 已订阅</> : <><Icon name="plus" size={13} /> 订阅</>}
              </button>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

Object.assign(window, { ExploreScreen, CandidatesScreen, SubsScreen });
