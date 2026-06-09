/* JavHub redesign — root app */
const { useState: useStateA, useEffect: useEffectA } = React;

const ACCENTS = {
  靛蓝: { hex: "#7C8CFF", rgb: "124, 140, 255" },
  珊瑚: { hex: "#FF7A66", rgb: "255, 122, 102" },
  翡翠: { hex: "#46CE96", rgb: "70, 206, 150" },
  品红: { hex: "#FF6FA5", rgb: "255, 111, 165" },
  纯白: { hex: "#EDEDF2", rgb: "237, 237, 242" },
};

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "靛蓝",
  "theme": "dark",
  "density": "comfortable",
  "glassChrome": true
}/*EDITMODE-END*/;

const NAV = [
  { group: "浏览", items: [
    { k: "today", label: "今日", icon: "today" },
    { k: "library", label: "影库", icon: "library" },
    { k: "curation", label: "私人策展", icon: "heart", badge: "42" },
    { k: "explore", label: "随机探索", icon: "search" },
  ]},
  { group: "自动化", items: [
    { k: "downloads", label: "下载任务", icon: "download", badge: "3" },
    { k: "subs", label: "演员订阅", icon: "star", badge: "6", badgeMuted: true },
    { k: "candidates", label: "候选确认", icon: "stack", badge: "12" },
    { k: "supplement", label: "补全管理", icon: "supplement", badge: "4", badgeMuted: true },
    { k: "library-org", label: "片库整理", icon: "inventory" },
  ]},
  { group: "系统", items: [
    { k: "ops", label: "运营总览", icon: "ops" },
    { k: "settings", label: "配置中心", icon: "settings" },
  ]},
];

function ComingSoon({ label }) {
  return (
    <>
      <div className="topbar solid"><h1>{label}</h1></div>
      <div className="page" style={{ display: "grid", placeItems: "center", minHeight: "60vh", textAlign: "center" }}>
        <div>
          <div style={{ width: 64, height: 64, borderRadius: 18, background: "var(--card)", border: "1px solid var(--hairline)", display: "grid", placeItems: "center", margin: "0 auto var(--s4)", color: "var(--tx-3)" }}>
            <Icon name="panel" size={28} />
          </div>
          <div style={{ fontSize: "var(--t-h3)", fontWeight: 600 }}>{label}</div>
          <div className="muted" style={{ fontSize: "var(--t-cap)", marginTop: 6, maxWidth: 360 }}>
            这一屏沿用同一套设计语言——玻璃 chrome、实底内容、poster-first。原型聚焦演示了今日 / 影库 / 私人策展三屏。
          </div>
        </div>
      </div>
    </>
  );
}

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [screen, setScreen] = useStateA("today");
  const [collapsed, setCollapsed] = useStateA(false);
  const [modal, setModal] = useStateA(null);
  const [moreOpen, setMoreOpen] = useStateA(false);

  // apply accent + theme + density to :root
  useEffectA(() => {
    const a = ACCENTS[t.accent] || ACCENTS.靛蓝;
    const r = document.documentElement.style;
    r.setProperty("--accent", a.hex);
    r.setProperty("--accent-rgb", a.rgb);
    r.setProperty("--accent-glow", `rgba(${a.rgb}, 0.4)`);
    document.documentElement.dataset.theme = t.theme;
    document.documentElement.dataset.density = t.density;
  }, [t.accent, t.theme, t.density]);

  const onOpen = v => setModal(v);
  const onNav = dir => {
    const { V } = window.JH;
    const i = V.findIndex(x => x.code === modal.code);
    setModal(V[(i + dir + V.length) % V.length]);
  };
  const go = s => { setScreen(s); setMoreOpen(false); document.querySelector(".canvas")?.scrollTo({ top: 0 }); };

  const labelOf = k => NAV.flatMap(g => g.items).find(i => i.k === k)?.label || k;
  const allItems = NAV.flatMap(g => g.items);
  const bottomItems = [allItems[0], allItems[1], allItems[2], allItems[4]]; // 今日/影库/策展/下载
  const moreItems = allItems.filter(i => !bottomItems.includes(i));
  const isMoreActive = moreItems.some(i => i.k === screen);

  let body;
  if (screen === "today") body = <TodayScreen onOpen={onOpen} go={go} />;
  else if (screen === "library") body = <LibraryScreen onOpen={onOpen} />;
  else if (screen === "curation") body = <CurationScreen onOpen={onOpen} />;
  else if (screen === "ops") body = <OpsScreen />;
  else if (screen === "library-org") body = <LibraryOrgScreen />;
  else if (screen === "settings") body = <SettingsScreen />;
  else if (screen === "explore") body = <ExploreScreen onOpen={onOpen} />;
  else if (screen === "candidates") body = <CandidatesScreen onOpen={onOpen} />;
  else if (screen === "supplement") body = <SupplementScreen onOpen={onOpen} />;
  else if (screen === "subs") body = <SubsScreen />;
  else if (screen === "downloads") body = <DownloadsScreen />;
  else body = <ComingSoon label={labelOf(screen)} />;

  return (
    <div className="app">
      <aside className={"sidebar" + (collapsed ? " collapsed" : "")}
        style={!t.glassChrome ? { background: "var(--card)", backdropFilter: "none", WebkitBackdropFilter: "none" } : null}>
        <div className="side-head">
          <div className="brand-mark"><Icon name="supplement" size={19} /></div>
          <span className="brand-name">Jav<b>Hub</b></span>
        </div>
        <nav className="side-nav scroll">
          {NAV.map(g => (
            <div className="nav-group" key={g.group}>
              <div className="nav-group-label">{g.group}</div>
              {g.items.map(it => (
                <button key={it.k} className={"nav-item" + (screen === it.k ? " active" : "")}
                  onClick={() => go(it.k)} title={it.label}>
                  <Icon name={it.icon} size={21} />
                  <span className="nav-label">{it.label}</span>
                  {it.badge && <span className={"nav-badge" + (it.badgeMuted ? " muted" : "")}>{it.badge}</span>}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className="side-foot">
          <a href="设计语言.html" style={{ color: "var(--tx-3)", textDecoration: "none" }}>v2.0 · 设计文档 ↗</a>
          <button className="icon-btn" style={{ width: 30, height: 30 }} onClick={() => setCollapsed(c => !c)} aria-label="折叠侧栏">
            <Icon name="chevR" size={16} style={{ transform: collapsed ? "" : "scaleX(-1)" }} />
          </button>
        </div>
      </aside>

      <main className="canvas scroll">{body}</main>

      {/* Mobile floating tab bar */}
      <nav className="bottom-nav">
        {bottomItems.map(it => (
          <button key={it.k} className={"bnav-item" + (screen === it.k ? " active" : "")} onClick={() => go(it.k)}>
            <Icon name={it.icon} size={22} />
            <span>{it.label}</span>
            {it.badge && <span className="bnav-pip"></span>}
          </button>
        ))}
        <button className={"bnav-item" + (isMoreActive || moreOpen ? " active" : "")} onClick={() => setMoreOpen(o => !o)}>
          <Icon name="list" size={22} />
          <span>更多</span>
        </button>
      </nav>

      {moreOpen && (
        <div className="more-scrim" onClick={() => setMoreOpen(false)}>
          <div className="more-sheet" onClick={e => e.stopPropagation()}>
            <div className="more-grabber"></div>
            <div className="more-head"><h2>更多功能</h2><button className="icon-btn" onClick={() => setMoreOpen(false)}><Icon name="close" size={19} /></button></div>
            <div className="more-grid">
              {moreItems.map(it => (
                <button key={it.k} className={"more-item" + (screen === it.k ? " active" : "")} onClick={() => go(it.k)}>
                  <Icon name={it.icon} size={24} />
                  <span>{it.label}</span>
                  {it.badge && <span className={"nav-badge" + (it.badgeMuted ? " muted" : "")}>{it.badge}</span>}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {modal && <VideoModal v={modal} onClose={() => setModal(null)} onNav={onNav} onPick={setModal} />}

      <TweaksPanel title="Tweaks">
        <TweakSection label="主色" />
        <TweakColor label="Accent" value={t.accent ? ACCENTS[t.accent].hex : "#7C8CFF"}
          options={Object.values(ACCENTS).map(a => a.hex)}
          onChange={hex => {
            const name = Object.keys(ACCENTS).find(k => ACCENTS[k].hex === hex) || "靛蓝";
            setTweak("accent", name);
          }} />
        <TweakSection label="主题" />
        <TweakRadio label="明暗" value={t.theme} options={["dark", "light"]} onChange={v => setTweak("theme", v)} />
        <TweakToggle label="玻璃 chrome" value={t.glassChrome} onChange={v => setTweak("glassChrome", v)} />
        <TweakSection label="密度" />
        <TweakRadio label="海报密度" value={t.density} options={["cozy", "comfortable", "spacious"]} onChange={v => setTweak("density", v)} />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
