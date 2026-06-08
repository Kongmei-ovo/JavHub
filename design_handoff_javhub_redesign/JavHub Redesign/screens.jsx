/* JavHub redesign — screens → window */
const { useState: useStateS, useEffect: useEffectS } = React;

/* ============================================================
   Today / Overview dashboard  (the new landing page)
   ============================================================ */
function TodayScreen({ onOpen, go }) {
  const { V, DL, ATTN, SUBS, stats } = window.JH;
  const hero = V[0];
  const toneBg = { warn: "var(--warn)", bad: "var(--bad)", info: "var(--info)", ok: "var(--ok)" };
  const statItems = [
    { ...stats.library, icon: "library" },
    { ...stats.downloading, icon: "download" },
    { ...stats.subs, icon: "star" },
    { ...stats.space, icon: "inventory" },
  ];
  return (
    <>
      <div className="topbar">
        <div>
          <h1>今日</h1>
          <div className="sub">6 月 7 日 · 周日 · 6 部新片等待处理</div>
        </div>
        <span className="grow"></span>
        <div className="search-field" style={{ maxWidth: 240 }}>
          <Icon name="search" size={17} />
          <input placeholder="搜索影片 / 番号 / 演员" onFocus={() => go("library")} readOnly />
        </div>
        <button className="icon-btn" aria-label="通知"><Icon name="bell" size={19} /></button>
      </div>

      <div className="page">
        {/* HERO — continue / featured */}
        <div className="hero" onClick={() => onOpen(hero)} style={{ cursor: "pointer" }}>
          <div className="hero-art" style={{ background: hero.art }}></div>
          <div className="hero-scrim"></div>
          <div className="hero-body">
            <div className="hero-kicker"><Icon name="clock" size={13} /> 继续观看</div>
            <div className="hero-title">{hero.title}</div>
            <div className="hero-sub">{hero.code} · {hero.studio} · 上次看到 48 分钟</div>
            <div className="hero-progress"><span style={{ width: "38%" }}></span></div>
            <div className="hero-actions">
              <button className="btn btn-primary" onClick={e => { e.stopPropagation(); onOpen(hero); }}>
                <Icon name="play" size={16} fill /> 继续播放
              </button>
              <button className="btn btn-ghost" onClick={e => { e.stopPropagation(); onOpen(hero); }}>详情</button>
            </div>
          </div>
        </div>

        {/* STAT STRIP */}
        <div className="section">
          <div className="stat-strip">
            {statItems.map((s, i) => (
              <button className="stat-card" key={i} onClick={() => go(i === 0 ? "library" : i === 2 ? "curation" : "today")}>
                <div className="stat-top">
                  <span className="stat-label" style={{ marginTop: 0 }}>{s.label}</span>
                  <Icon name={s.icon} size={18} />
                </div>
                <div className="stat-num">{s.num}</div>
                <div className={"stat-delta " + (s.up ? "up" : "flat")}>{s.delta}</div>
              </button>
            ))}
          </div>
        </div>

        {/* NEEDS ATTENTION */}
        <div className="section">
          <SectionHead title="待处理" count={`${ATTN.length} 项`} />
          <div className="attn-grid">
            {ATTN.map((a, i) => (
              <div className="attn-card" key={i}>
                <div className="top">
                  <div className="attn-icon" style={{ background: `rgba(var(--${a.tone}-rgb), 0.16)`, color: toneBg[a.tone] }}>
                    <Icon name={a.icon} size={19} />
                  </div>
                  <div className="attn-title">{a.title}</div>
                </div>
                <div className="attn-desc">{a.desc}</div>
                <div className="attn-actions">
                  <button className="btn btn-primary">{a.primary}</button>
                  {a.secondary && <button className="btn btn-ghost">{a.secondary}</button>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* DOWNLOADS IN PROGRESS */}
        <div className="section">
          <SectionHead title="下载中" count={`${DL.length} 个任务`} action="下载队列" onAction={() => go("today")} />
          <div className="dl-list">
            {DL.map((d, i) => (
              <div className="dl-row" key={i}>
                <div className="dl-thumb" style={{ background: d.art }}></div>
                <div className="dl-info">
                  <div className="dl-name">{d.name}</div>
                  <div className="dl-meta"><span style={{ fontFamily: "var(--font-mono)" }}>{d.code}</span><span>{d.peers} peers</span><span>剩余 {d.eta}</span></div>
                  <div className="dl-bar"><span style={{ width: d.pct + "%" }}></span></div>
                </div>
                <div className="dl-right">
                  <div className="dl-pct">{d.pct}%</div>
                  <div className="dl-speed">{d.speed}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SUBSCRIPTION UPDATES */}
        <div className="section">
          <SectionHead title="订阅更新" action="演员订阅" onAction={() => go("curation")} />
          <div className="poster-grid">
            {V.filter(v => v.acts.some(a => a.sub)).slice(0, 6).map(v => (
              <PosterCard key={v.code} v={v} onOpen={onOpen} />
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

/* ============================================================
   Library / Search — poster-first grid
   ============================================================ */
function LibraryScreen({ onOpen }) {
  const { V } = window.JH;
  const [q, setQ] = useStateS("");
  const filters = ["全部", "数字", "DVD", "流媒体", "租赁"];
  const [f, setF] = useStateS("全部");
  const [sort, setSort] = useStateS("最新");
  const [selectMode, setSelectMode] = useStateS(false);
  const [sel, setSel] = useStateS([]);
  let list = V.filter(v => (f === "全部" || v.type === f) &&
    (q === "" || v.code.toLowerCase().includes(q.toLowerCase()) || v.title.includes(q) || v.acts.some(a => a.kanji.includes(q))));
  if (sort === "最新") list = [...list].sort((a, b) => b.date.localeCompare(a.date));
  if (sort === "时长") list = [...list].sort((a, b) => b.runtime - a.runtime);

  const toggleSel = v => setSel(s => s.includes(v.code) ? s.filter(c => c !== v.code) : [...s, v.code]);
  const exitSelect = () => { setSelectMode(false); setSel([]); };
  const selectAll = () => setSel(list.map(v => v.code));

  return (
    <>
      <div className="topbar solid">
        <h1>影库</h1>
        <span className="grow"></span>
        <div className="search-field" style={{ minWidth: 280 }}>
          <Icon name="search" size={17} />
          <input placeholder="番号 / 标题 / 演员" value={q} onChange={e => setQ(e.target.value)} autoFocus />
        </div>
        <button className={"btn " + (selectMode ? "btn-primary" : "btn-ghost")} onClick={() => selectMode ? exitSelect() : setSelectMode(true)}>
          <Icon name={selectMode ? "close" : "check"} size={16} /> {selectMode ? "退出多选" : "多选"}
        </button>
      </div>
      <div className="page page-wide">
        <div className="row" style={{ marginBottom: "var(--s6)", flexWrap: "wrap" }}>
          <div className="segmented">
            {filters.map(x => (
              <button key={x} className={f === x ? "active" : ""} onClick={() => setF(x)}>
                {x} {x !== "全部" && <span className="count">{V.filter(v => v.type === x).length}</span>}
              </button>
            ))}
          </div>
          <span className="grow"></span>
          {selectMode
            ? <button className="btn btn-quiet" onClick={selectAll}>全选 {list.length} 项</button>
            : <div className="segmented">
                {["最新", "时长"].map(x => (
                  <button key={x} className={sort === x ? "active" : ""} onClick={() => setSort(x)}>{x}</button>
                ))}
              </div>}
        </div>
        <div className="poster-grid">
          {list.map(v => <PosterCard key={v.code} v={v} onOpen={onOpen}
            selectMode={selectMode} selected={sel.includes(v.code)} onToggleSelect={toggleSel} />)}
        </div>
        {list.length === 0 && <div style={{ textAlign: "center", padding: "var(--s10) 0", color: "var(--tx-3)" }}>没有匹配 “{q}” 的影片</div>}

        {selectMode && sel.length > 0 && (
          <div className="batch-bar">
            <span className="count-pill">已选 <b>{sel.length}</b> 项</span>
            <span className="divider"></span>
            <button className="btn btn-quiet"><Icon name="download" size={16} /> 下载</button>
            <button className="btn btn-quiet"><Icon name="heart" size={16} /> 收藏</button>
            <button className="btn btn-quiet"><Icon name="globe" size={16} /> 翻译</button>
            <button className="btn btn-quiet" style={{ color: "var(--bad)" }}><Icon name="close" size={16} /> 移除</button>
            <span className="divider"></span>
            <button className="btn btn-ghost" onClick={exitSelect}>完成</button>
          </div>
        )}
      </div>
    </>
  );
}

/* ============================================================
   Curation / Favorites — matches your mockup direction
   ============================================================ */
function CurationScreen({ onOpen }) {
  const { V } = window.JH;
  const tabs = [
    { k: "全部", n: V.length }, { k: "影片", n: V.filter(v => v.fav).length },
    { k: "演员", n: 6 }, { k: "题材", n: 9 }, { k: "系列", n: 4 },
  ];
  const [tab, setTab] = useStateS("全部");
  const list = tab === "影片" ? V.filter(v => v.fav) : V;
  return (
    <>
      <div className="topbar solid">
        <h1>私人策展</h1>
        <span className="grow"></span>
        <span className="muted" style={{ fontSize: "var(--t-cap)" }}>共 {V.length} 个收藏项</span>
      </div>
      <div className="page page-wide">
        <div className="segmented" style={{ marginBottom: "var(--s5)" }}>
          {tabs.map(t => (
            <button key={t.k} className={tab === t.k ? "active" : ""} onClick={() => setTab(t.k)}>
              {t.k} <span className="count">{t.n}</span>
            </button>
          ))}
        </div>
        <div className="hint-banner">
          <Icon name="info" size={18} />
          <p><b>演员订阅入口放在每张卡片下方。</b> 卡片仍然打开影片详情；下方演员条负责订阅。翻译名优先显示，原名做辅助，避免你为了订阅去猜日文／罗马字。<b style={{ color: "var(--ok)" }}> 绿色</b>是已订阅，灰色是可订阅。</p>
        </div>
        <div className="poster-grid">
          {list.map(v => <PosterCard key={v.code} v={v} onOpen={onOpen} showActs />)}
        </div>
      </div>
    </>
  );
}

/* ============================================================
   Video detail modal — Photos-app style
   ============================================================ */
function VideoModal({ v, onClose, onNav, onPick }) {
  useEffectS(() => {
    const h = e => { if (e.key === "Escape") onClose(); if (e.key === "ArrowRight") onNav(1); if (e.key === "ArrowLeft") onNav(-1); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [v, onClose, onNav]);

  const { V } = window.JH;
  const related = V.filter(x => x.code !== v.code && (x.studio === v.studio || x.acts.some(a => v.acts.some(b => b.id === a.id)))).slice(0, 6);
  const relatedList = related.length ? related : V.filter(x => x.code !== v.code).slice(0, 6);

  const magnets = [
    { q: "FHD", res: "1080p", size: "5.84 GB", seed: 128, best: true },
    { q: "FHD-C", res: "1080p 中文字幕", size: "6.12 GB", seed: 64, best: false },
    { q: "HD", res: "720p", size: "2.91 GB", seed: 212, best: false },
  ];
  return (
    <div className="modal-scrim" onClick={onClose}>
      <div className="modal scroll" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="关闭"><Icon name="close" size={19} /></button>
        <button className="modal-nav prev" onClick={() => onNav(-1)} aria-label="上一个"><Icon name="chevR" size={20} style={{ transform: "scaleX(-1)" }} /></button>
        <button className="modal-nav next" onClick={() => onNav(1)} aria-label="下一个"><Icon name="chevR" size={20} /></button>
        <div className="modal-hero">
          <div className="modal-hero-art" style={{ background: v.art }}></div>
          <div className="modal-hero-scrim"></div>
          <div className="modal-hero-body">
            <span className="badge info">{v.type}</span>
            <div className="modal-code" style={{ marginTop: 8 }}>{v.code} · {v.studio}</div>
            <div className="modal-title">{v.title}</div>
            <div className="modal-orig">{v.orig}</div>
          </div>
        </div>
        <div className="modal-body">
          <div className="modal-actions">
            <button className="btn btn-primary"><Icon name="play" size={16} fill /> 播放</button>
            <button className="btn btn-ghost"><Icon name="download" size={16} /> 下载</button>
            <button className="btn btn-ghost"><Icon name="heart" size={16} fill={v.fav} /> {v.fav ? "已收藏" : "收藏"}</button>
          </div>

          <div className="meta-grid">
            <div className="meta-item"><div className="k">发行日期</div><div className="v">{v.date}</div></div>
            <div className="meta-item"><div className="k">时长</div><div className="v">{v.runtime} 分钟</div></div>
            <div className="meta-item"><div className="k">制作商</div><div className="v">{v.studio}</div></div>
            <div className="meta-item"><div className="k">系列</div><div className="v">{v.series || "—"}</div></div>
          </div>

          {v.acts.length > 0 && (<>
            <div className="modal-section-title">出演演员</div>
            <ActRow acts={v.acts} />
          </>)}

          <div className="modal-section-title">题材标签</div>
          <div className="tag-cloud">{v.genres.map(g => <span className="chip" key={g}>{g}</span>)}</div>

          <div className="modal-section-title">可用磁力</div>
          <div className="magnet-list">
            {magnets.map((m, i) => (
              <div className="magnet-row" key={i}>
                <div className="magnet-info">
                  <div className="magnet-q">{m.q} {m.best && <span className="badge ok dot">推荐</span>}</div>
                  <div className="magnet-meta"><span>{m.res}</span><span>{m.size}</span><span>{m.seed} 种子</span></div>
                </div>
                <button className="btn btn-ghost" style={{ height: 36 }}><Icon name="download" size={15} /> 下载</button>
              </div>
            ))}
          </div>

          <div className="modal-section-title">相关推荐</div>
          <div className="rail">
            {relatedList.map(r => <PosterCard key={r.code} v={r} onOpen={onPick} />)}
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { TodayScreen, LibraryScreen, CurationScreen, VideoModal });
