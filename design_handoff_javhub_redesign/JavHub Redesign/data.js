/* JavHub redesign — mock data (window.JH) */
(function () {
  // color-from-content cover gradients (the visual heartbeat)
  const grad = (a, b, c) =>
    `radial-gradient(120% 120% at 25% 12%, ${a}, transparent 55%),` +
    `radial-gradient(120% 120% at 85% 90%, ${b}, transparent 60%),` +
    `linear-gradient(150deg, ${c}, #0a0a10)`;

  const A = {
    kojima: { id: 1, kanji: "小岛南", romaji: "小島みなみ", color: "#FF7A59", sub: true },
    aoi:    { id: 2, kanji: "葵司", romaji: "葵つかさ", color: "#3FA9F5", sub: false },
    akari:  { id: 3, kanji: "明里䌷", romaji: "明里つむぎ", color: "#FF5A7A", sub: false },
    momono: { id: 4, kanji: "桃乃木香奈", romaji: "桃乃木かな", color: "#54D596", sub: true },
    nanami: { id: 5, kanji: "七泽米亚", romaji: "七沢みあ", color: "#A66BFF", sub: false },
    yua:    { id: 6, kanji: "三上悠亚", romaji: "三上悠亜", color: "#FFB23F", sub: true },
  };

  const V = [
    { code: "MIAA-784", type: "数字", typeKind: "info", title: "夏日之后，她把秘密留在了旅馆走廊", orig: "夏の終わり、旅館の廊下にて", date: "2026-05-06", runtime: 128, studio: "MOODYZ", series: "情热夏日", art: grad("#FF8A6B", "#3FA9F5", "#1a1226"), acts: [A.kojima, A.nanami], fav: true, genres: ["单体作品", "剧情", "巨乳", "温泉"] },
    { code: "SIVR-438", type: "DVD", typeKind: "warn", title: "清晨的车站，重逢像一场没有结束的梦", orig: "朝の駅で、終わらない夢のように", date: "2026-04-18", runtime: 152, studio: "S1 NO.1 STYLE", series: "VR臨場", art: grad("#54D596", "#3FA9F5", "#0d2018"), acts: [A.aoi], fav: false, genres: ["VR专用", "单体作品", "美少女"] },
    { code: "ABP-588", type: "租赁", typeKind: "bad", title: "被翻译成中文的名字，也可以从这里直接订阅", orig: "字幕の向こうの彼女", date: "2025-12-21", runtime: 119, studio: "Prestige", series: "絶頂", art: grad("#FFB23F", "#FF5A7A", "#241405"), acts: [A.akari, A.momono], fav: false, genres: ["单体作品", "苗条", "美乳"] },
    { code: "IPZZ-091", type: "流媒体", typeKind: "ok", title: "没有演员数据的收藏，依然保持轻量、不占太多", orig: "軽やかなコレクション", date: "2026-02-03", runtime: 140, studio: "IDEA POCKET", series: "", art: grad("#A66BFF", "#FF5A7A", "#1c0f26"), acts: [], fav: true, genres: ["单体作品", "数位马赛克"] },
    { code: "SSIS-902", type: "数字", typeKind: "info", title: "海边小镇的最后一个夏天", orig: "海辺の町の最後の夏", date: "2026-05-22", runtime: 134, studio: "S1 NO.1 STYLE", series: "", art: grad("#3FA9F5", "#54D596", "#0a1822"), acts: [A.yua], fav: false, genres: ["单体作品", "美少女", "白天"] },
    { code: "MIDV-661", type: "数字", typeKind: "info", title: "她的房间里，时钟永远停在午夜", orig: "彼女の部屋、時計は真夜中", date: "2026-03-30", runtime: 121, studio: "MOODYZ", series: "深夜", art: grad("#FF5A7A", "#A66BFF", "#1f0b1a"), acts: [A.kojima], fav: false, genres: ["单体作品", "剧情", "美乳"] },
    { code: "FSDSS-712", type: "流媒体", typeKind: "ok", title: "雨停之前，谁先开口都算输", orig: "雨が止むまでに", date: "2026-01-14", runtime: 116, studio: "FALENO", series: "", art: grad("#54D596", "#FFB23F", "#0d1e10"), acts: [A.momono, A.aoi], fav: true, genres: ["单体作品", "苗条"] },
    { code: "PRED-540", type: "DVD", typeKind: "warn", title: "周末的便利店，凌晨三点的相遇", orig: "週末のコンビニ、午前三時", date: "2025-11-08", runtime: 145, studio: "Premium", series: "深夜便", art: grad("#FFB23F", "#3FA9F5", "#241a05"), acts: [A.nanami], fav: false, genres: ["单体作品", "巨乳", "制服"] },
    { code: "CAWD-633", type: "数字", typeKind: "info", title: "学生时代没说出口的那句话", orig: "あの頃言えなかった言葉", date: "2026-04-02", runtime: 130, studio: "kawaii", series: "青春", art: grad("#FF7A59", "#FF5A7A", "#22120c"), acts: [A.akari], fav: false, genres: ["单体作品", "美少女", "学生"] },
    { code: "JUQ-455", type: "流媒体", typeKind: "ok", title: "搬家那天，旧公寓还留着她的味道", orig: "引っ越しの日", date: "2026-05-15", runtime: 138, studio: "Madonna", series: "", art: grad("#A66BFF", "#3FA9F5", "#14102a"), acts: [A.yua, A.kojima], fav: false, genres: ["人妻", "剧情"] },
    { code: "STARS-841", type: "数字", typeKind: "info", title: "便签上写着：等你回来一起看完", orig: "付箋のメッセージ", date: "2026-02-27", runtime: 124, studio: "SOD star", series: "", art: grad("#3FA9F5", "#FF7A59", "#0a1620"), acts: [A.aoi], fav: false, genres: ["单体作品", "美少女"] },
    { code: "WAAA-377", type: "租赁", typeKind: "bad", title: "末班车上，她靠在陌生人的肩膀睡着了", orig: "終電のなかで", date: "2025-10-19", runtime: 142, studio: "Wanz", series: "終電", art: grad("#FF5A7A", "#FFB23F", "#200b15"), acts: [A.momono], fav: false, genres: ["单体作品", "巨乳"] },
  ];

  // downloads in progress
  const DL = [
    { code: "SSIS-902", name: "海边小镇的最后一个夏天", art: V[4].art, pct: 67, speed: "8.4 MB/s", eta: "12 分钟", peers: 24 },
    { code: "MIDV-661", name: "她的房间里，时钟永远停在午夜", art: V[5].art, pct: 31, speed: "3.1 MB/s", eta: "41 分钟", peers: 11 },
    { code: "JUQ-455", name: "搬家那天，旧公寓还留着她的味道", art: V[9].art, pct: 92, speed: "11.2 MB/s", eta: "2 分钟", peers: 38 },
  ];

  // attention / candidate items
  const ATTN = [
    { kind: "candidate", icon: "stack", tone: "warn", title: "12 个候选待确认", desc: "演员订阅自动抓取的新片，确认后进入下载队列。", primary: "去确认", secondary: "全部通过" },
    { kind: "magnet", icon: "link", tone: "bad", title: "5 部缺磁力", desc: "已收录但还没有可用磁力链接，可批量补全。", primary: "批量补全", secondary: "查看" },
    { kind: "translate", icon: "globe", tone: "info", title: "8 条标题待翻译", desc: "原始日文标题尚未翻译，影响检索与展示。", primary: "开始翻译", secondary: null },
  ];

  // subscription updates
  const SUBS = [
    { ...A.kojima, since: 3, latest: "MIDV-661" },
    { ...A.momono, since: 2, latest: "FSDSS-712" },
    { ...A.yua, since: 1, latest: "SSIS-902" },
  ];

  window.JH = {
    grad, A, V, DL, ATTN, SUBS,
    stats: {
      library: { num: "2,418", label: "片库影片", delta: "+34 本周", up: true },
      downloading: { num: "3", label: "下载中", delta: "92% 即将完成", up: false },
      subs: { num: "6", label: "订阅演员", delta: "6 部新片", up: true },
      space: { num: "1.8 TB", label: "占用空间", delta: "可用 640 GB", up: false },
    },
    actCount: 6,
  };
})();
