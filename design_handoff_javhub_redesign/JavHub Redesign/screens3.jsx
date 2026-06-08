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
function CandidatesScreen({ onOpen }) {
  const { V, A } = window.JH;
  const initial = [
    { id: 1, code: "MIDV-661", title: "她的房间里，时钟永远停在午夜", art: V[5].art, act: A.kojima, source: "订阅抓取", seeds: 142, magnet: true },
    { id: 2, code: "FSDSS-712", title: "雨停之前，谁先开口都算输", art: V[6].art, act: A.momono, source: "订阅抓取", seeds: 88, magnet: true },
    { id: 3, code: "SSIS-902", title: "海边小镇的最后一个夏天", art: V[4].art, act: A.yua, source: "订阅抓取", seeds: 0, magnet: false },
    { id: 4, code: "CAWD-633", title: "学生时代没说出口的那句话", art: V[8].art, act: A.akari, source: "手动添加", seeds: 211, magnet: true },
    { id: 5, code: "PRED-540", title: "周末的便利店，凌晨三点的相遇", art: V[7].art, act: A.nanami, source: "订阅抓取", seeds: 0, magnet: false },
    { id: 6, code: "STARS-841", title: "便签上写着：等你回来一起看完", art: V[10].art, act: A.aoi, source: "订阅抓取", seeds: 56, magnet: true },
  ];
  const [items, setItems] = useState3(initial.map(i => ({ ...i, state: "pending" })));
  const [sel, setSel] = useState3([]);
  const [filter, setFilter] = useState3("待确认");

  const counts = {
    待确认: items.filter(i => i.state === "pending").length,
    已通过: items.filter(i => i.state === "approved").length,
    已拒绝: items.filter(i => i.state === "rejected").length,
    缺磁力: items.filter(i => !i.magnet && i.state === "pending").length,
  };
  const map = { 待确认: i => i.state === "pending", 已通过: i => i.state === "approved", 已拒绝: i => i.state === "rejected", 缺磁力: i => !i.magnet && i.state === "pending" };
  const visible = items.filter(map[filter]);

  const setState = (ids, state) => { setItems(its => its.map(i => ids.includes(i.id) ? { ...i, state } : i)); setSel(s => s.filter(x => !ids.includes(x))); };
  const toggle = id => setSel(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);

  return (
    <>
      <div className="topbar solid"><div><h1>候选确认</h1><div className="sub">订阅自动抓取 · 确认后进入下载队列</div></div></div>
      <div className="page">
        <div className="row" style={{ marginBottom: "var(--s5)", flexWrap: "wrap" }}>
          <div className="segmented">
            {Object.keys(map).map(k => (
              <button key={k} className={filter === k ? "active" : ""} onClick={() => setFilter(k)}>
                {k} <span className="count">{counts[k]}</span>
              </button>
            ))}
          </div>
          <span className="grow"></span>
          {visible.length > 0 && filter === "待确认" && (
            <button className="btn btn-quiet" onClick={() => setSel(sel.length === visible.length ? [] : visible.map(i => i.id))}>
              {sel.length === visible.length ? "取消全选" : `全选 ${visible.length} 项`}
            </button>
          )}
        </div>

        {visible.length === 0 && (
          <div className="panel" style={{ textAlign: "center", padding: "var(--s10)" }}>
            <div style={{ color: "var(--tx-3)", marginBottom: "var(--s3)" }}><Icon name="check" size={32} /></div>
            <div style={{ fontWeight: 600 }}>没有「{filter}」的候选</div>
            <p className="muted" style={{ fontSize: "var(--t-cap)", marginTop: 6 }}>订阅扫描会持续把新片放到这里。</p>
          </div>
        )}

        {visible.map(i => (
          <div className={"cand-row" + (i.state !== "pending" ? " resolved" : "")} key={i.id}>
            {filter === "待确认" && (
              <button className={"cand-check" + (sel.includes(i.id) ? " on" : "")} onClick={() => toggle(i.id)} aria-label="选择">
                {sel.includes(i.id) && <Icon name="check" size={13} />}
              </button>
            )}
            <div className="cand-thumb" style={{ background: i.art }} onClick={() => onOpen(V.find(v => v.code === i.code))}></div>
            <div className="cand-body">
              <div className="cand-title">{i.title}</div>
              <div className="cand-meta">
                <span className="code">{i.code}</span>
                <span>{i.act.kanji}</span>
                <span className="chip" style={{ padding: "1px 7px" }}>{i.source}</span>
                {i.magnet ? <span className="badge ok dot">{i.seeds} 种子</span> : <span className="badge bad dot">缺磁力</span>}
              </div>
            </div>
            {i.state === "pending" ? (
              <div className="cand-actions">
                {!i.magnet && <button className="icon-act neutral" title="补全磁力"><Icon name="link" size={17} /></button>}
                <button className="icon-act neutral" title="编辑磁力"><Icon name="parse" size={17} /></button>
                <button className="icon-act reject" title="拒绝" onClick={() => setState([i.id], "rejected")}><Icon name="close" size={17} /></button>
                <button className="icon-act approve" title="通过" onClick={() => setState([i.id], "approved")} disabled={!i.magnet} style={!i.magnet ? { opacity: 0.4, cursor: "not-allowed" } : null}><Icon name="check" size={17} /></button>
              </div>
            ) : (
              <span className={"badge " + (i.state === "approved" ? "ok" : "bad")}>{i.state === "approved" ? "已通过" : "已拒绝"}</span>
            )}
          </div>
        ))}

        {sel.length > 0 && (
          <div className="batch-bar">
            <span className="count-pill">已选 <b>{sel.length}</b> 项</span>
            <span className="divider"></span>
            <button className="btn btn-quiet" style={{ color: "var(--ok)" }} onClick={() => setState(sel, "approved")}><Icon name="check" size={16} /> 全部通过</button>
            <button className="btn btn-quiet" style={{ color: "var(--bad)" }} onClick={() => setState(sel, "rejected")}><Icon name="close" size={16} /> 全部拒绝</button>
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
