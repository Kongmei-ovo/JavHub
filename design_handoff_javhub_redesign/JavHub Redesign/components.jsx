/* JavHub redesign — shared components → window */
const { useState } = React;

/* ---------- Icons ---------- */
const PATHS = {
  home: "M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z|M9 22V12h6v10",
  today: "M8 2v4M16 2v4M3 10h18|M3 6a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2z",
  search: "M11 19a8 8 0 100-16 8 8 0 000 16z|M21 21l-4.35-4.35",
  library: "M4 19.5A2.5 2.5 0 016.5 17H20|M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z",
  heart: "M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z",
  download: "M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4|M7 10l5 5 5-5|M12 15V3",
  star: "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14l-5-4.87 6.91-1.01z",
  parse: "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z|M14 2v6h6|M16 13H8M16 17H8",
  list: "M8 6h13M8 12h13M8 18h13|M3 6h.01M3 12h.01M3 18h.01",
  inventory: "M16 3h5v5|M4 20L21 3|M21 16v5h-5M4 4l5 5",
  supplement: "M12 2L2 7l10 5 10-5z|M2 17l10 5 10-5M2 12l10 5 10-5",
  globe: "M12 22a10 10 0 100-20 10 10 0 000 20z|M2 12h20|M12 2a15 15 0 010 20 15 15 0 010-20z",
  ops: "M3 3v18h18|M7 15l3-3 3 2 5-7|M18 7h-4M18 7v4",
  settings: "M12 15a3 3 0 100-6 3 3 0 000 6z|M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09a1.65 1.65 0 001.51-1 1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z",
  play: "M6 4l14 8-14 8z",
  plus: "M12 5v14M5 12h14",
  check: "M20 6L9 17l-5-5",
  chevR: "M9 6l6 6-6 6",
  arrowR: "M5 12h14M13 6l6 6-6 6",
  link: "M10 13a5 5 0 007 0l3-3a5 5 0 00-7-7l-2 2|M14 11a5 5 0 00-7 0l-3 3a5 5 0 007 7l2-2",
  stack: "M12 2l9 5-9 5-9-5z|M3 12l9 5 9-5M3 17l9 5 9-5",
  close: "M18 6L6 18M6 6l12 12",
  bell: "M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9|M13.7 21a2 2 0 01-3.4 0",
  info: "M12 22a10 10 0 100-20 10 10 0 000 20z|M12 16v-4M12 8h.01",
  panel: "M9 3v18|M3 5a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2z",
  clock: "M12 22a10 10 0 100-20 10 10 0 000 20z|M12 6v6l4 2",
  hd: "M3 5a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2z|M7 9v6M11 9v6M7 12h4M15 9h2a2 2 0 012 2v2a2 2 0 01-2 2h-2z",
  sun: "M12 17a5 5 0 100-10 5 5 0 000 10z|M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  moon: "M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z",
};
function Icon({ name, size = 22, fill = false, style }) {
  const segs = (PATHS[name] || "").split("|");
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill={fill ? "currentColor" : "none"}
      stroke={fill ? "none" : "currentColor"} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={style}>
      {segs.map((d, i) => <path key={i} d={d} />)}
    </svg>
  );
}

/* ---------- Actress subscribe row ---------- */
function ActRow({ acts }) {
  const [state, setState] = useState(() => acts.map(a => a.sub));
  if (!acts || acts.length === 0) {
    return <div className="act-row"><div className="act-empty">暂无演员数据 · 收藏保持轻量</div></div>;
  }
  return (
    <div className="act-row" onClick={e => e.stopPropagation()}>
      {acts.map((a, i) => (
        <div className="act-line" key={a.id}>
          <div className="act-avatar" style={{ background: a.color }}>{a.kanji[0]}</div>
          <div className="act-names">
            <div className="act-name">{a.kanji}</div>
            <div className="act-name-sub">{a.romaji}</div>
          </div>
          <button className={"sub-btn " + (state[i] ? "done" : "can")}
            onClick={() => setState(s => s.map((v, j) => j === i ? !v : v))}>
            {state[i] ? <><Icon name="check" size={12} /> 已订阅</> : <><Icon name="plus" size={12} /> 订阅</>}
          </button>
        </div>
      ))}
    </div>
  );
}

/* ---------- Poster card ---------- */
function PosterCard({ v, onOpen, showActs = false, selectMode = false, selected = false, onToggleSelect }) {
  const [fav, setFav] = useState(v.fav);
  const handleClick = () => { if (selectMode) onToggleSelect(v); else onOpen(v); };
  return (
    <div className="poster-card" onClick={handleClick}>
      <div className={"poster" + (selectMode ? " selectable" : "") + (selected ? " selected" : "")}>
        <div className="poster-art" style={{ background: v.art }}></div>
        <div className="poster-scrim"></div>
        {selectMode && (
          <span className={"select-check" + (selected ? " on" : "")}>{selected && <Icon name="check" size={14} />}</span>
        )}
        <span className="poster-code">{v.code}</span>
        <span className="poster-type">{v.type}</span>
        <span className="poster-runtime">{v.runtime} 分钟</span>
        {!selectMode && (
          <button className={"poster-fav" + (fav ? " on" : "")}
            onClick={e => { e.stopPropagation(); setFav(f => !f); }} aria-label="收藏">
            <Icon name="heart" size={17} fill={fav} />
          </button>
        )}
      </div>
      <div className="poster-meta">
        <div className="poster-title">{v.title}</div>
        <div className="poster-sub">
          <span>{v.studio}</span>
          <span className="dot"></span>
          <span>{v.date.slice(0, 7)}</span>
        </div>
      </div>
      {showActs && <ActRow acts={v.acts} />}
    </div>
  );
}

/* ---------- Section header ---------- */
function SectionHead({ title, count, action, onAction }) {
  return (
    <div className="section-head">
      <h2>{title}</h2>
      {count != null && <span className="count">{count}</span>}
      <span className="grow"></span>
      {action && <button className="link" onClick={onAction}>{action} <Icon name="chevR" size={14} /></button>}
    </div>
  );
}

Object.assign(window, { Icon, ActRow, PosterCard, SectionHead });
