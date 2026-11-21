/* 매장경영노트 수익화 대시보드
   UI는 이 파일에, 데이터는 data.json에 있습니다.
   data.json만 갱신해서 배포하면 웹·앱이 같은 내용을 표시합니다. */
(function () {
  "use strict";

  var state = { data: null, view: "overview", channel: null, radarFilter: "all" };
  var STATUS = {
    operating: { label: "운영 중", color: "#0f9d58" },
    preparing: { label: "준비 중", color: "#f59e0b" },
    waiting: { label: "대기", color: "#64748b" }
  };

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var main = $("#main");
  var nav = $("#nav");
  var mobileNav = $("#mobileNav");

  function esc(v) {
    return String(v == null ? "" : v)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function statusOf(key) { return STATUS[key] || STATUS.waiting; }
  function sum(a) { return a.reduce(function (x, y) { return x + y; }, 0); }

  function toast(msg) {
    var t = $("#toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(t._h);
    t._h = setTimeout(function () { t.classList.remove("show"); }, 2200);
  }

  /* ---------------- data ---------------- */
  function loadData(bust) {
    var url = "./data.json" + (bust ? "?t=" + Date.now() : "");
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  function renderError(err) {
    main.innerHTML =
      '<div class="error-card"><h2>데이터를 불러오지 못했습니다</h2>' +
      '<p><code>data.json</code>을 읽을 수 없습니다. 같은 폴더에 <code>data.json</code>이 있는지 확인해 주세요.</p>' +
      '<p style="color:#94a3b8;font-size:12px">' + esc(err && err.message ? err.message : "") + '</p>' +
      '<button class="link-btn" id="retryBtn">다시 시도</button></div>';
    var b = $("#retryBtn");
    if (b) b.addEventListener("click", boot);
  }

  /* ---------------- navigation ---------------- */
  function renderNav() {
    var d = state.data;
    var overview = '<a class="nav-item' + (state.view === "overview" ? " is-active" : "") +
      '" href="#/overview" data-nav="overview"><span class="nav-dot" style="background:#0b1220"></span>' +
      '<span class="nav-name">통합 대시보드</span></a>';
    var items = d.channels.map(function (ch) {
      var st = statusOf(ch.status);
      return '<a class="nav-item' + (state.view === "channel" && state.channel === ch.id ? " is-active" : "") +
        '" href="#/' + esc(ch.id) + '">' +
        '<span class="nav-dot" style="background:' + esc(ch.accent) + '"></span>' +
        '<span class="nav-name">' + esc(ch.name) + '</span>' +
        '<span class="nav-state" style="background:' + st.color + '"></span></a>';
    }).join("");
    var radarN = radarOpenCount(d);
    var tools = '<div class="nav-label">도구</div>' +
      '<a class="nav-item' + (state.view === "radar" ? " is-active" : "") + '" href="#/radar">' +
      '<span class="nav-dot" style="background:#e11d48"></span><span class="nav-name">수익화 레이더</span>' +
      (radarN ? '<span class="nav-count">' + radarN + '</span>' : '') + '</a>' +
      '<a class="nav-item' + (state.view === "board" ? " is-active" : "") + '" href="#/board">' +
      '<span class="nav-dot" style="background:#2563eb"></span><span class="nav-name">진행 작업 보드</span>' +
      (boardCount(d, "doing") ? '<span class="nav-count">' + boardCount(d, "doing") + '</span>' : '') + '</a>' +
      '<a class="nav-item" href="./generator.html">' +
      '<span class="nav-dot" style="background:#f97316"></span><span class="nav-name">상세·마진 생성기</span>' +
      '<span class="nav-ext">↗</span></a>';
    nav.innerHTML = '<div class="nav-label">통합</div>' + overview +
      '<div class="nav-label">채널</div>' + items + tools;

    mobileNav.innerHTML =
      '<a class="m-pill' + (state.view === "overview" ? " is-active" : "") + '" href="#/overview">통합</a>' +
      '<a class="m-pill' + (state.view === "radar" ? " is-active" : "") + '" href="#/radar">레이더</a>' +
      '<a class="m-pill' + (state.view === "board" ? " is-active" : "") + '" href="#/board">작업 보드</a>' +
      '<a class="m-pill" href="./generator.html">마진 생성기</a>' +
      d.channels.map(function (ch) {
        return '<a class="m-pill' + (state.view === "channel" && state.channel === ch.id ? " is-active" : "") +
          '" href="#/' + esc(ch.id) + '"><span class="nav-dot" style="background:' + esc(ch.accent) + '"></span>' +
          esc(ch.name) + '</a>';
      }).join("");
  }

  function parseHash() {
    var h = (location.hash || "#/overview").replace(/^#\/?/, "");
    if (!h || h === "overview") return { view: "overview", id: null };
    if (h === "radar") return { view: "radar", id: null };
    if (h === "board") return { view: "board", id: null };
    var found = state.data.channels.some(function (c) { return c.id === h; });
    return found ? { view: "channel", id: h } : { view: "overview", id: null };
  }

  function route() {
    var r = parseHash();
    state.view = r.view;
    state.channel = r.id;
    renderNav();
    if (r.view === "overview") renderOverview();
    else if (r.view === "radar") renderRadar();
    else if (r.view === "board") renderBoard();
    else renderChannel(state.data.channels.filter(function (c) { return c.id === r.id; })[0]);
    window.scrollTo(0, 0);
  }

  /* ---------------- charts ---------------- */
  function donut(segments, centerValue, centerLabel) {
    var size = 132, r = 50, c = 2 * Math.PI * r, gap = 2;
    var total = sum(segments.map(function (s) { return s.value; })) || 1;
    var offset = 0;
    var arcs = segments.map(function (s) {
      var len = (s.value / total) * c;
      var dash = Math.max(len - gap, 0.6) + " " + (c - Math.max(len - gap, 0.6));
      var el = '<circle cx="' + size / 2 + '" cy="' + size / 2 + '" r="' + r +
        '" fill="none" stroke="' + s.color + '" stroke-width="15" stroke-linecap="butt"' +
        ' stroke-dasharray="' + dash + '" stroke-dashoffset="' + (-offset) + '"' +
        ' transform="rotate(-90 ' + size / 2 + ' ' + size / 2 + ')"></circle>';
      offset += len;
      return el;
    }).join("");
    return '<div class="donut" style="width:' + size + 'px;height:' + size + 'px">' +
      '<svg viewBox="0 0 ' + size + ' ' + size + '" width="' + size + '" height="' + size + '">' +
      '<circle cx="' + size / 2 + '" cy="' + size / 2 + '" r="' + r + '" fill="none" stroke="#eff2f7" stroke-width="15"></circle>' +
      arcs + '</svg>' +
      '<div class="donut-center"><strong>' + esc(centerValue) + '</strong><span>' + esc(centerLabel) + '</span></div>' +
      '</div>';
  }

  function ring(pct, color) {
    var size = 84, r = 34, c = 2 * Math.PI * r;
    var dash = (pct / 100) * c;
    return '<div class="ring-wrap" style="width:' + size + 'px;height:' + size + 'px">' +
      '<svg viewBox="0 0 ' + size + ' ' + size + '" width="' + size + '" height="' + size + '">' +
      '<circle cx="42" cy="42" r="' + r + '" fill="none" stroke="#eef1f6" stroke-width="8"></circle>' +
      '<circle cx="42" cy="42" r="' + r + '" fill="none" stroke="' + color + '" stroke-width="8" stroke-linecap="round"' +
      ' stroke-dasharray="' + dash + ' ' + (c - dash) + '" transform="rotate(-90 42 42)"></circle></svg>' +
      '<div class="ring-center"><strong>' + pct + '%</strong><span>준비도</span></div></div>';
  }

  function funnelSvg(stages) {
    var W = 900, H = 300;
    var geo = [
      { top: [110, 790], bot: [150, 750], y: 8 },
      { top: [170, 730], bot: [205, 695], y: 104 },
      { top: [230, 670], bot: [265, 635], y: 200 }
    ];
    var paths = stages.map(function (s, i) {
      var g = geo[i];
      var pts = [g.top[0] + "," + g.y, g.top[1] + "," + g.y, g.bot[1] + "," + (g.y + 88), g.bot[0] + "," + (g.y + 88)].join(" ");
      return '<polygon points="' + pts + '" fill="' + esc(s.accent) + '" opacity="' + (0.14 + i * 0.08) + '"></polygon>' +
        '<polygon points="' + pts + '" fill="none" stroke="' + esc(s.accent) + '" stroke-width="1.4" opacity="0.45"></polygon>' +
        '<text x="' + W / 2 + '" y="' + (g.y + 30) + '" text-anchor="middle" font-size="11.5" font-weight="700" letter-spacing="1.4" fill="' + esc(s.accent) + '">' + esc(s.label.toUpperCase()) + '</text>' +
        '<text x="' + W / 2 + '" y="' + (g.y + 60) + '" text-anchor="middle" font-size="27" font-weight="750" fill="#0b1220" letter-spacing="-0.5">' + esc(s.headline) + '<tspan font-size="12" font-weight="600" fill="#6b7a90" dx="4">' + esc(s.unit) + '</tspan></text>' +
        '<text x="' + W / 2 + '" y="' + (g.y + 78) + '" text-anchor="middle" font-size="10" fill="#8c99ab">' + (i < 2 ? "▼" : "") + '</text>';
    }).join("");
    return '<svg class="funnel" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="수익화 퍼널">' + paths + '</svg>';
  }


  function revMini(d) {
    var rows = (d.overview_revenue || []).map(function (r) {
      return '<div class="rev-mini-row"><span class="rev-mini-label">' + esc(r.label) + '</span>' +
        '<b>' + esc(r.value) + '</b><span class="rev-mini-note">' + esc(r.note) + '</span></div>';
    }).join("");
    if (!rows) return "";
    return '<div class="rev-mini"><div class="rev-mini-head">수익 현황</div>' + rows + '</div>';
  }

  /* ---------------- live sales + blog charts ---------------- */
  function won(n) {
    var v = Number(n || 0);
    return v.toLocaleString("ko-KR");
  }

  function niceMax(v) {
    if (!(v > 0)) return 1;
    var pow = Math.pow(10, Math.floor(Math.log10(v)));
    var n = v / pow;
    var steps = [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10];
    for (var i = 0; i < steps.length; i++) { if (n <= steps[i]) return steps[i] * pow; }
    return 10 * pow;
  }

  var CH = { W: 700, H: 220 };

  /* 좁은 화면에서는 글자·점을 viewBox 단위로 키워 축소해도 읽히게 합니다. */
  function chartCfg() {
    var compact = window.innerWidth <= 720;
    return {
      W: CH.W, H: CH.H,
      L: compact ? 64 : 40, R: 14, T: 16, B: compact ? 44 : 28,
      fs: compact ? 19 : 11,
      stride: compact ? 3 : 2,
      dot: compact ? 5 : 3.1,
      stroke: compact ? 3.6 : 2.2
    };
  }

  function chartGrid(c, max) {
    var ih = c.H - c.T - c.B, out = "";
    [0, 0.25, 0.5, 0.75, 1].forEach(function (t) {
      var y = c.T + ih - ih * t;
      out += '<line x1="' + c.L + '" x2="' + (c.W - c.R) + '" y1="' + y + '" y2="' + y +
        '" stroke="' + (t === 0 ? "#dbe1ea" : "#eef1f6") + '" stroke-width="1"/>' +
        '<text x="' + (c.L - 8) + '" y="' + (y + c.fs * 0.36) + '" text-anchor="end" font-size="' + c.fs + '" fill="#9aa6b8">' +
        won(Math.round(max * t)) + '</text>';
    });
    return out;
  }

  function xLabels(c, labels, stride) {
    return labels.map(function (l, i) {
      if (i % stride) return "";
      return '<text x="' + (c._x(i)).toFixed(1) + '" y="' + (c.H - c.fs * 0.6) + '" text-anchor="middle" font-size="' + c.fs + '" fill="#8c99ab">' + esc(l) + '</text>';
    }).join("");
  }

  function lineChart(cfg) {
    var c = chartCfg();
    var vals = cfg.values.map(function (v) { return Number(v) || 0; });
    var max = niceMax(Math.max.apply(null, vals) * 1.12);
    var iw = c.W - c.L - c.R, ih = c.H - c.T - c.B;
    var step = vals.length > 1 ? iw / (vals.length - 1) : 0;
    c._x = function (i) { return c.L + step * i; };
    var pts = vals.map(function (v, i) {
      return [c.L + step * i, c.T + ih - (v / max) * ih];
    });
    var line = pts.map(function (p, i) { return (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1); }).join(" ");
    var area = line + " L" + (c.L + iw).toFixed(1) + " " + (c.T + ih) + " L" + c.L + " " + (c.T + ih) + " Z";
    var dots = pts.map(function (p, i) {
      return '<circle cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="' + c.dot + '" fill="#fff" stroke="' + esc(cfg.color) + '" stroke-width="' + (c.stroke * 0.75).toFixed(1) + '">' +
        '<title>' + esc(cfg.labels[i]) + " · " + won(vals[i]) + esc(cfg.unit || "") + '</title></circle>';
    }).join("");
    return '<div class="chart-wrap"><svg class="chart" viewBox="0 0 ' + c.W + ' ' + c.H + '" role="img" aria-label="' + esc(cfg.title || "추이 그래프") + '">' +
      chartGrid(c, max) +
      '<path d="' + area + '" fill="' + esc(cfg.color) + '" opacity="0.10"/>' +
      '<path d="' + line + '" fill="none" stroke="' + esc(cfg.color) + '" stroke-width="' + c.stroke + '" stroke-linejoin="round" stroke-linecap="round"/>' +
      dots + xLabels(c, cfg.labels, c.stride) + '</svg></div>';
  }

  function barChart(cfg) {
    var c = chartCfg();
    var series = cfg.series || [];
    var all = [];
    series.forEach(function (s) { s.values.forEach(function (v) { if (v != null) all.push(Number(v)); }); });
    var max = niceMax((all.length ? Math.max.apply(null, all) : 0) * 1.15);
    var iw = c.W - c.L - c.R, ih = c.H - c.T - c.B;
    var n = cfg.labels.length;
    var slot = iw / n;
    c._x = function (i) { return c.L + slot * i + slot / 2; };
    var bw = Math.max(4, (slot * 0.62) / series.length);
    var bars = [];
    series.forEach(function (s, si) {
      s.values.forEach(function (v, i) {
        if (v == null) return;
        var h = (Number(v) / max) * ih;
        var x = c.L + slot * i + slot * 0.19 + bw * si;
        if (Number(v) === 0) {
          bars.push('<rect x="' + x.toFixed(1) + '" y="' + (c.T + ih - 2.4).toFixed(1) + '" width="' + bw.toFixed(1) +
            '" height="2.4" rx="1" fill="' + esc(s.color) + '" opacity="0.28"><title>' + esc(cfg.labels[i]) + " · " + esc(s.label) + " 0" + esc(cfg.unit || "") + '</title></rect>');
          return;
        }
        bars.push('<rect x="' + x.toFixed(1) + '" y="' + (c.T + ih - h).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + h.toFixed(1) +
          '" rx="2" fill="' + esc(s.color) + '"><title>' + esc(cfg.labels[i]) + " · " + esc(s.label) + " " + won(v) + esc(cfg.unit || "") + '</title></rect>');
      });
    });
    return '<div class="chart-wrap"><svg class="chart" viewBox="0 0 ' + c.W + ' ' + c.H + '" role="img" aria-label="' + esc(cfg.title || "수익 그래프") + '">' +
      chartGrid(c, max) + bars.join("") + xLabels(c, cfg.labels, c.stride) + '</svg></div>';
  }

  function salesBadge(n) {
    return n > 0
      ? '<span class="sale-badge live"><span class="bdot"></span>신규 주문 ' + n + '건</span>'
      : '<span class="sale-badge idle"><span class="bdot"></span>신규 주문 0건</span>';
  }

  function salesCard(a) {
    var rows = a.products.map(function (p) {
      var on = p.status === "판매중";
      return '<tr><td class="p-name"><b>' + esc(p.name) + '</b>' + (p.badge ? '<span class="p-tag">' + esc(p.badge) + '</span>' : '') + '</td>' +
        '<td>' + esc(p.spec || "-") + '</td>' +
        '<td class="p-price">' + won(p.price) + '원' + (p.list_price ? '<small>' + won(p.list_price) + '</small>' : '') + '</td>' +
        '<td><span class="p-state ' + (on ? "on" : "off") + '">' + esc(p.status) + '</span></td>' +
        '<td class="p-stock">' + won(p.stock) + '</td></tr>';
    }).join("");
    return '<div class="acct" style="--c:' + esc(a.accent) + '">' +
      '<div class="acct-head">' +
      '<span class="acct-mark" style="background:' + esc(a.accent) + '">' + esc(a.name.slice(0, 1)) + '</span>' +
      '<div class="acct-id"><b>' + esc(a.name) + '</b><span>' + esc(a.platform) + ' · ' + esc(a.handle) + '</span></div>' +
      salesBadge(a.orders.new_today) + '</div>' +
      '<div class="acct-kpis">' +
      '<div><span>신규 주문</span><b>' + won(a.orders.new_today) + '<small>건</small></b></div>' +
      '<div><span>오늘 매출</span><b>' + won(a.revenue.today) + '<small>원</small></b></div>' +
      '<div><span>누적 매출</span><b>' + won(a.revenue.total) + '<small>원</small></b></div>' +
      '</div>' +
      '<div class="acct-flow">배송준비 ' + a.orders.prepare + ' · 배송중 ' + a.orders.shipping + ' · 배송완료 ' + a.orders.done +
      '<span class="acct-stamp">' + esc(a.synced_at) + ' 기준</span></div>' +
      '<div class="p-table-wrap"><table class="p-table"><thead><tr><th>상품</th><th>규격</th><th>판매가</th><th>상태</th><th>재고</th></tr></thead><tbody>' +
      rows + '</tbody></table></div>' +
      (a.notes && a.notes.length ? '<ul class="acct-notes">' + a.notes.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join("") + '</ul>' : "") +
      '</div>';
  }

  function salesSection(d) {
    var s = d.sales;
    if (!s) return "";
    var sync = d.sync || {};
    var live = s.new_orders_total > 0;
    return '<section class="panel panel-sales">' +
      '<div class="panel-head"><div><h2>판매계정 연동 · 판매 알림</h2><p>' + esc(s.caption) + '</p></div>' +
      '<div class="panel-tools"><span class="chip">마지막 동기화 ' + esc(sync.last_synced_label || "—") + '</span>' +
      '<span class="chip">' + esc(sync.schedule || "주기 동기화") + '</span></div></div>' +
      '<div class="sale-banner ' + (live ? "is-live" : "is-idle") + '">' +
      '<span class="sb-dot"></span><div class="sb-body"><b>' + esc(s.alert.badge) + '</b><p>' + esc(s.alert.detail) + '</p></div>' +
      '<span class="sb-total">오늘 합계 <b>' + won(s.new_orders_total) + '건</b></span></div>' +
      '<div class="acct-grid">' + s.accounts.map(salesCard).join("") + '</div>' +
      '<div class="sync-line">조회: ' + esc((sync.sources || []).join(" · ")) + '</div>' +
      '</section>';
  }

  function blogStatsSection(d, opts) {
    var bs = d.blog_stats;
    if (!bs) return "";
    var rev = bs.revenue;
    var revSeries = rev.sources.map(function (s) { return { label: s.label, color: s.color, values: s.values }; });
    var legend = rev.sources.map(function (s) {
      return '<span class="lg"><i style="background:' + esc(s.color) + '"></i>' + esc(s.label) + ' <b>' + won(s.total) + '원</b></span>';
    }).join("");
    var v = bs.visitors, w = bs.views;
    return '<div class="grid grid-2 chart-pair">' +
      '<section class="panel"><div class="panel-head"><div><h2>블로그 방문자 추이</h2>' +
      '<p>순방문자수 일별 · ' + esc(bs.period) + '</p></div>' +
      '<div class="panel-tools"><span class="chip">14일 ' + won(v.sum) + '명</span><span class="chip">일평균 ' + v.avg + '명</span><span class="chip">최근 ' + won(v.last) + '명</span></div></div>' +
      lineChart({ labels: bs.labels, values: v.values, color: v.color, unit: v.unit, title: "블로그 순방문자수 추이" }) +
      '<div class="chart-foot"><span>최고 ' + won(v.max) + '명</span><span>조회수 14일 ' + won(w.sum) + '회 · 최근 ' + won(w.last) + '회</span>' +
      '<span>오늘 실시간 조회 ' + won((bs.live || {}).realtime_views) + '회 (' + esc((bs.live || {}).at) + ')</span></div>' +
      '<p class="chart-note">' + esc(v.note) + '</p></section>' +
      '<section class="panel"><div class="panel-head"><div><h2>예상수익 추이</h2>' +
      '<p>애드포스트 · 쇼핑커넥트 일별 실측 · 합계 ' + won(rev.total) + '원</p></div></div>' +
      barChart({ labels: bs.labels, series: revSeries, unit: "원", title: "수익원별 일별 수입" }) +
      '<div class="chart-legend">' + legend + '</div>' +
      '<div class="chart-foot"><span>잔액 ' + won(rev.balance) + '원</span><span>' + esc(rev.sources[0].note) + '</span></div>' +
      '<p class="chart-note">' + esc(rev.period_note) + '</p></section>' +
      '</div>';
  }

  /* ---------------- 1년 제철 과일 족보 ---------------- */
  var SEASON_RANK = [
    { key: "now", tag: "지금 주력 판매", accent: "#16a34a", when: "지금" },
    { key: "next", tag: "소싱·등록 준비", accent: "#f59e0b", when: "다음 달" },
    { key: "watch", tag: "미리 체크", accent: "#3b82f6", when: "다다음 달" }
  ];

  /* 오늘 날짜의 월을 기준으로 '지금 / 다음 달 / 다다음 달'을 자동 계산합니다. */
  function seasonSection(d, opts) {
    var fc = d.fruit_calendar;
    if (!fc || !fc.months || !fc.months.length) return "";
    var compact = !!(opts && opts.compact);
    var nowMonth = new Date().getMonth() + 1;
    var byMonth = {};
    fc.months.forEach(function (m) { byMonth[m.month] = m; });
    function shift(off) { return ((nowMonth - 1 + off) % 12) + 1; }

    var cards = SEASON_RANK.map(function (r, off) {
      var mm = shift(off);
      var m = byMonth[mm] || { items: [] };
      var body = off === 0 ? m.todo : off === 1 ? m.prep : (m.watch || m.prep);
      return '<article class="season-card is-' + r.key + '" style="--c:' + r.accent + '">' +
        '<div class="sc-top"><span class="sc-when">' + mm + '월 · ' + r.when + '</span>' +
        '<span class="sc-tag">' + r.tag + '</span></div>' +
        '<h3>' + esc((m.items || []).join(" · ")) + '</h3>' +
        '<div class="sc-meta"><span>출하</span>' + esc(m.supply || "—") + '</div>' +
        '<div class="sc-meta"><span>검색 정점</span>' + esc(m.peak || "—") + '</div>' +
        '<p class="sc-act">' + esc(body || "") + '</p></article>';
    }).join("");

    if (compact) {
      return '<section class="panel panel-season panel-season-compact">' +
        '<div class="panel-head"><div><h2>이번 달 제철 과일 · 소싱 추천</h2>' +
        '<p>' + nowMonth + '월 기준 자동 계산 — 지금 주력 / 다음 달 준비 / 다다음 달 체크</p></div>' +
        '<div class="panel-tools"><a class="chip season-more" href="#/forest" data-nav="forest">1년 족보 전체 →</a></div></div>' +
        '<div class="season-cards">' + cards + '</div>' +
        '<p class="season-note">' + esc(fc.rule) + '</p></section>';
    }

    var cells = fc.months.map(function (m) {
      var off = (m.month - nowMonth + 12) % 12;
      var cls = off === 0 ? "is-now" : off === 1 ? "is-next" : off === 2 ? "is-watch" : "";
      var badge = off === 0 ? "지금" : off === 1 ? "준비" : off === 2 ? "체크" : "";
      var tip = (m.supply || "") + " · 검색 정점 " + (m.peak || "-") + " · " + (m.todo || "");
      return '<div class="sm-cell ' + cls + '" title="' + esc(tip) + '">' +
        '<div class="sm-top"><b>' + m.month + '월</b>' + (badge ? '<span class="sm-badge">' + badge + '</span>' : '') + '</div>' +
        '<span class="sm-items">' + esc((m.items || []).join(" · ")) + '</span>' +
        (cls ? '<span class="sm-todo">' + esc(m.todo || "") + '</span>' : '') + '</div>';
    }).join("");

    return '<section class="panel panel-season">' +
      '<div class="panel-head"><div><h2>1년 제철 과일 족보 · 시기별 소싱 추천</h2>' +
      '<p>' + esc(fc.caption) + '</p></div>' +
      '<div class="panel-tools"><span class="chip">기준 ' + nowMonth + '월</span>' +
      '<span class="chip">검색 정점 · 데이터랩 주간</span></div></div>' +
      '<div class="season-cards">' + cards + '</div>' +
      '<div class="season-months">' + cells + '</div>' +
      '<p class="season-note"><b>실행 규칙</b> ' + esc(fc.rule) + '</p>' +
      '<p class="season-note">' + esc(fc.supplier_note) + '</p>' +
      '<p class="season-note muted">' + esc(fc.basis) + '</p></section>';
  }

  /* ---------------- 수익화 레이더 · 진행 작업 보드 ---------------- */
  var TYPE_COLOR = { brand: "#0ea5e9", cpa: "#7c3aed", clip: "#6d5efc", fruit: "#16a34a", support: "#f59e0b" };
  var OWNER_CLS = { "파인": "me", "보현님": "user" };

  function todayStart() {
    var n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), n.getDate());
  }

  /* 마감일은 날짜만 저장하고 D-day는 화면을 연 날짜로 계산합니다. */
  function ddayOf(deadline) {
    if (!deadline) return null;
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(deadline));
    if (!m) return null;
    return Math.round((new Date(+m[1], +m[2] - 1, +m[3]) - todayStart()) / 86400000);
  }

  function ddayLabel(dd) {
    if (dd == null) return "상시";
    if (dd < 0) return "마감";
    if (dd === 0) return "D-DAY";
    return "D-" + dd;
  }

  function ddayClass(dd) {
    if (dd == null) return "dd-none";
    if (dd < 0) return "dd-past";
    if (dd <= 2) return "dd-urgent";
    if (dd <= 7) return "dd-soon";
    return "dd-ok";
  }

  function shortDate(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(s || ""));
    return m ? (+m[2]) + "/" + (+m[3]) : "";
  }

  function radarItems(d) {
    var r = d.radar;
    if (!r || !r.items || !r.items.length) return [];
    return r.items.slice().sort(function (a, b) {
      var da = ddayOf(a.deadline), db = ddayOf(b.deadline);
      var ka = da == null ? 9999 : (da < 0 ? 9000 : da);
      var kb = db == null ? 9999 : (db < 0 ? 9000 : db);
      if (ka !== kb) return ka - kb;
      return (a.priority || 9) - (b.priority || 9);
    });
  }

  function radarOpenCount(d) {
    return radarItems(d).filter(function (it) {
      var dd = ddayOf(it.deadline);
      return dd == null || dd >= 0;
    }).length;
  }

  function boardCount(d, key) {
    var b = d.board;
    if (!b || !b.tasks) return 0;
    return b.tasks.filter(function (t) { return t.status === key; }).length;
  }

  function radarCard(it) {
    var dd = ddayOf(it.deadline);
    var color = TYPE_COLOR[it.type] || "#64748b";
    var isPast = dd != null && dd < 0;
    var openState = { decide: "결정 필요", running: "진행 중", open: "검토", soon: "곧 시작", waiting: "대기" }[it.state] || "열림";
    var meta = [];
    meta.push('<div><span>마감</span><b>' + (it.deadline ? shortDate(it.deadline) + ' <i class="dd ' + ddayClass(dd) + '">' + ddayLabel(dd) + '</i>' : (it.window || "상시")) + '</b></div>');
    if (it.reward) meta.push('<div><span>리워드</span><b>' + esc(it.reward) + '</b></div>');
    if (it.window && it.deadline) meta.push('<div><span>기간</span><b>' + esc(it.window) + '</b></div>');
    meta.push('<div><span>상태</span><b>' + esc(it.status || openState) + '</b></div>');
    return '<article class="radar-card' + (isPast ? " is-past" : "") + '" style="--c:' + esc(color) + '">' +
      '<div class="rc-top"><span class="rc-type">' + esc(it.type_label || "기회") + '</span>' +
      (it.deadline ? '<span class="dd big ' + ddayClass(dd) + '">' + ddayLabel(dd) + '</span>' : '<span class="dd big dd-none">상시</span>') + '</div>' +
      '<h3>' + esc(it.title) + '</h3>' +
      '<p class="rc-org">' + esc(it.org || "") + '</p>' +
      '<div class="rc-meta">' + meta.join("") + '</div>' +
      (it.note ? '<p class="rc-note">' + esc(it.note) + '</p>' : "") +
      '<div class="rc-foot">' +
      '<div class="rc-action"><span>다음 액션</span>' + esc(it.action || "—") + '</div>' +
      '<span class="owner ' + (OWNER_CLS[it.owner] || "") + '">' + esc(it.owner || "") + '</span></div>' +
      (it.link ? '<a class="rc-link" href="' + esc(it.link) + '" target="_blank" rel="noopener">' + esc(it.link_label || "열기") + ' ↗</a>' : "") +
      '</article>';
  }

  /* 통합 화면에서는 마감이 가까운 4건만 요약해서 보여 줍니다. */
  function radarSection(d, opts) {
    var r = d.radar;
    var items = radarItems(d);
    if (!r || !items.length) return "";
    var compact = !!(opts && opts.compact);
    var soon = items.filter(function (it) { var dd = ddayOf(it.deadline); return dd != null && dd >= 0 && dd <= 3; }).length;
    var boardDoing = boardCount(d, "doing");
    var doing = r.caption ? '<p>' + esc(r.caption) + '</p>' : '<p>지금 열린 기회</p>';

    if (!compact) {
      return '<section class="panel panel-radar"><div class="panel-head"><div><h2>수익화 레이더</h2>' + doing + '</div>' +
        '<div class="panel-tools"><span class="chip">열린 기회 ' + radarOpenCount(d) + '</span>' +
        '<span class="chip">마감 3일 이내 ' + soon + '</span></div></div>' +
        '<div class="radar-grid">' + items.map(radarCard).join("") + '</div>' +
        '<p class="radar-note">' + esc(r.note || "") + '</p></section>';
    }

    var top = items.slice(0, 4);
    var rows = top.map(function (it) {
      var dd = ddayOf(it.deadline);
      return '<a class="radar-row" href="#/radar" style="--c:' + esc(TYPE_COLOR[it.type] || "#64748b") + '">' +
        '<span class="dd ' + ddayClass(dd) + '">' + (it.deadline ? ddayLabel(dd) : "상시") + '</span>' +
        '<span class="rr-body"><b>' + esc(it.title) + '</b><span>' + esc(it.org || "") + ' · ' + esc(it.status || "") + '</span></span>' +
        '<span class="rr-reward">' + esc(it.reward || "") + '</span></a>';
    }).join("");
    return '<section class="panel panel-radar panel-radar-compact">' +
      '<div class="panel-head"><div><h2>수익화 레이더 · 마감 임박</h2>' +
      '<p>브랜드커넥트·CPA·클립·제철 과일 마감을 D-day로 자동 정렬</p></div>' +
      '<div class="panel-tools"><span class="chip">열린 기회 ' + radarOpenCount(d) + '</span>' +
      '<a class="chip season-more" href="#/radar" data-nav="radar">레이더 전체 →</a>' +
      '<a class="chip season-more" href="#/board" data-nav="board">작업 ' + boardDoing + '건 →</a></div></div>' +
      '<div class="radar-rows">' + rows + '</div></section>';
  }

  function renderRadar() {
    var d = state.data;
    var r = d.radar;
    var items = radarItems(d);
    var soon = items.filter(function (it) { var dd = ddayOf(it.deadline); return dd != null && dd >= 0 && dd <= 3; }).length;
    var rewards = items.reduce(function (s, it) {
      var dd = ddayOf(it.deadline);
      if (dd != null && dd < 0) return s;
      return s + (Number(it.reward_value) || 0);
    }, 0);
    var decision = items.filter(function (it) { return it.state === "decide"; }).length;

    if (!r || !items.length) {
      main.innerHTML = '<div class="page-head"><h1>수익화 레이더</h1>' +
        '<p>아직 <code>data.json</code>에 <code>radar</code> 블록이 없습니다.</p></div>' + foot();
      return;
    }

    var filters = (r.filters || [{ key: "all", label: "전체" }]).map(function (f) {
      var n = f.key === "all" ? items.length : items.filter(function (it) { return it.type === f.key; }).length;
      return '<button class="rf-chip' + (state.radarFilter === f.key ? " is-active" : "") + '" type="button" data-filter="' + esc(f.key) + '">' +
        esc(f.label) + '<span>' + n + '</span></button>';
    }).join("");

    var list = items.filter(function (it) { return state.radarFilter === "all" || it.type === state.radarFilter; });

    main.innerHTML =
      '<div class="page-head">' +
      '<div class="page-eyebrow"><span class="live"></span>도구 · 수익화 레이더</div>' +
      '<h1>지금 열린 돈벌이 기회</h1>' +
      '<p>마감·리워드·다음 액션을 한 화면에 모았습니다. D-day는 화면을 연 날짜로 자동 계산됩니다.</p></div>' +
      '<div class="radar-stats">' +
      '<div class="rs-card" style="--c:#e11d48"><span>마감 3일 이내</span><b>' + soon + '<small>건</small></b></div>' +
      '<div class="rs-card" style="--c:#2563eb"><span>결정만 하면 되는 일</span><b>' + decision + '<small>건</small></b></div>' +
      '<div class="rs-card" style="--c:#0d9488"><span>확인된 리워드 합계</span><b>' + won(rewards) + '<small>원</small></b></div>' +
      '<div class="rs-card" style="--c:#7c3aed"><span>열린 기회</span><b>' + radarOpenCount(d) + '<small>건</small></b></div>' +
      '</div>' +
      '<div class="radar-filters" role="group" aria-label="기회 종류">' + filters + '</div>' +
      (list.length ? '<div class="radar-grid">' + list.map(radarCard).join("") + '</div>'
        : '<div class="radar-empty">이 종류에 열린 기회가 없습니다.</div>') +
      '<p class="radar-note">' + esc(r.note || "") + '</p>' +
      '<div class="tool-links">' +
      '<a class="tool-card" href="#/board" data-nav="board"><strong>진행 작업 보드</strong><span>진행중 ' + boardCount(d, "doing") + ' · 대기중 ' + boardCount(d, "waiting") + ' · 완료 ' + boardCount(d, "done") + '</span></a>' +
      '<a class="tool-card" href="./generator.html"><strong>과일 상세·마진 생성기 ↗</strong><span>공급가·판매가만 넣으면 마진표와 이미지 3장</span></a>' +
      '</div>' + foot();

    Array.prototype.forEach.call(main.querySelectorAll("[data-filter]"), function (b) {
      b.addEventListener("click", function () {
        state.radarFilter = b.getAttribute("data-filter");
        renderRadar();
      });
    });
    bindLinks();
  }

  function boardCard(t, d) {
    var ch = d.channels.filter(function (c) { return c.id === t.channel; })[0] || {};
    var cls = t.status === "doing" ? "doing" : t.status === "waiting" ? "waiting" : "done";
    return '<article class="task-card is-' + cls + '" style="--c:' + esc(ch.accent || "#94a3b8") + '">' +
      '<div class="tc-top"><span class="tc-ch">' + esc(ch.name || t.channel || "") + '</span>' +
      (t.due_label ? '<span class="tc-due">' + esc(t.due_label) + '</span>' : '') + '</div>' +
      '<h4>' + esc(t.title) + '</h4>' +
      (t.detail ? '<p>' + esc(t.detail) + '</p>' : "") +
      (typeof t.progress === "number" ? '<div class="tc-bar"><i style="width:' + Math.max(0, Math.min(100, t.progress)) + '%"></i><span>' + t.progress + '%</span></div>' : "") +
      '<div class="tc-foot"><span class="owner ' + (OWNER_CLS[t.owner] || "") + '">' + esc(t.owner || "") + '</span>' +
      (t.scheduled ? '<span class="tc-sched">🔁 ' + esc(t.scheduled) + '</span>' : '') + '</div></article>';
  }

  function renderBoard() {
    var d = state.data;
    var b = d.board;
    if (!b || !b.tasks) {
      main.innerHTML = '<div class="page-head"><h1>진행 작업 보드</h1>' +
        '<p>아직 <code>data.json</code>에 <code>board</code> 블록이 없습니다.</p></div>' + foot();
      return;
    }
    var cols = (b.columns || []).map(function (c) {
      var list = b.tasks.filter(function (t) { return t.status === c.key; });
      return '<section class="board-col" style="--c:' + esc(c.accent) + '">' +
        '<div class="bc-head"><span class="bc-dot"></span><h3>' + esc(c.label) + '</h3>' +
        '<span class="bc-count">' + list.length + '</span></div>' +
        '<div class="bc-body">' + (list.length ? list.map(function (t) { return boardCard(t, d); }).join("") : '<p class="bc-empty">비어 있습니다</p>') + '</div></section>';
    }).join("");

    main.innerHTML =
      '<div class="page-head">' +
      '<div class="page-eyebrow"><span class="live"></span>도구 · 진행 작업 보드</div>' +
      '<h1>진행중 · 대기중 · 완료</h1>' +
      '<p>' + esc(b.caption || "") + '</p></div>' +
      '<div class="board">' + cols + '</div>' +
      '<p class="radar-note">' + esc(b.note || "") + ' <a href="#/radar" data-nav="radar" style="color:#1d4ed8;font-weight:650">수익화 레이더로 →</a></p>' +
      foot();
    bindLinks();
  }

  function updatesSection(d) {
    var list = d.updates || [];
    if (!list.length) return "";
    var chip = { done: ['완료', 'done'], waiting: ['대기', 'waiting'], scheduled: ['예약', 'scheduled'] };
    return '<section class="panel" style="margin-bottom:18px"><div class="panel-head"><div><h2>최신 진행 현황</h2>' +
      '<p>어젯밤~오늘 완료·대기 중인 작업 (동기화 ' + esc((d.sync || {}).last_synced_label || "—") + ')</p></div>' +
      '<div class="panel-tools"><span class="chip">' + list.length + '건</span></div></div>' +
      '<div class="upd-list">' + list.map(function (u) {
        var c = chip[u.state] || ['완료', 'done'];
        var ch = d.channels.filter(function (x) { return x.id === u.channel; })[0] || {};
        return '<div class="upd-item" style="--c:' + esc(ch.accent || "#94a3b8") + '">' +
          '<div class="upd-time">' + esc(u.time) + '</div>' +
          '<div class="upd-body"><div class="upd-top"><h4>' + esc(u.title) + '</h4>' +
          '<span class="upd-state ' + c[1] + '">' + c[0] + '</span>' +
          '<span class="upd-ch">' + esc(ch.name || u.channel) + '</span></div>' +
          '<p>' + esc(u.detail) + '</p></div></div>';
      }).join("") + '</div></section>';
  }

  /* ---------------- overview ---------------- */
  function renderOverview() {
    var d = state.data;
    var counts = { operating: 0, preparing: 0, waiting: 0 };
    d.channels.forEach(function (c) { counts[c.status] = (counts[c.status] || 0) + 1; });
    var avg = Math.round(sum(d.channels.map(function (c) { return c.progress; })) / d.channels.length);
    var autoOn = (d.automation && d.automation.running) ||
      sum(d.channels.map(function (c) { return (c.automation || []).filter(function (a) { return a.state === "on"; }).length; }));

    var kpis = d.kpis.map(function (k) {
      return '<div class="kpi" style="--kpi-accent:' + esc(k.accent) + '">' +
        '<div class="kpi-label">' + esc(k.label) + '</div>' +
        '<div class="kpi-value">' + esc(k.value) + '<span class="unit">' + esc(k.unit) + '</span></div>' +
        '<div class="kpi-sub">' + esc(k.sub) + '</div></div>';
    }).join("");

    var rows = d.channels.map(function (ch) {
      var st = statusOf(ch.status);
      return '<a class="row-item" href="#/' + esc(ch.id) + '">' +
        '<div class="row-name"><span class="ch-dot" style="background:' + esc(ch.accent) + '"></span><span>' + esc(ch.name) + '</span></div>' +
        '<div class="bar" style="--c:' + esc(ch.accent) + '"><i style="width:' + ch.progress + '%"></i></div>' +
        '<div class="row-pct">' + ch.progress + '%</div>' +
        '<div><span class="chip ' + esc(ch.status) + '"><span class="d" style="background:' + st.color + '"></span>' + st.label + '</span></div>' +
        '</a>';
    }).join("");

    var donutSegs = [
      { value: counts.operating || 0, color: "#0f9d58" },
      { value: counts.preparing || 0, color: "#f59e0b" },
      { value: counts.waiting || 0, color: "#94a3b8" }
    ];
    var legend = donutSegs.map(function (s, i) {
      var labels = ["운영 중", "준비 중", "대기"];
      return '<div class="legend-item"><span class="sw" style="background:' + s.color + '"></span><span>' +
        labels[i] + '</span><b>' + s.value + '</b></div>';
    }).join("");

    var tl = d.timeline.items.map(function (it) {
      var ch = d.channels.filter(function (c) { return c.id === it.channel; })[0] || {};
      var cls = it.state === "on" ? "on" : it.state === "scheduled" ? "once" : "";
      var tag = it.state === "scheduled"
        ? '<span class="chip" style="background:#eff6ff;color:#1d4ed8;margin-top:7px">1회 예약</span>'
        : '<span class="chip" style="margin-top:7px">예정</span>';
      return '<div class="tl-item ' + cls + '" style="--c:' + esc(ch.accent || "#94a3b8") + '">' +
        '<div class="tl-time">' + esc(it.time) + '</div>' +
        '<div class="tl-node"></div>' +
        '<div class="tl-body"><div class="tl-title">' + esc(it.title) + '</div>' +
        '<div class="tl-detail">' + esc(it.detail) + '</div>' + tag + '</div></div>';
    }).join("");

    var alerts = d.alerts.map(function (a) {
      return '<div class="alert ' + esc(a.tone) + '">' +
        '<div class="alert-side"></div>' +
        '<div class="alert-body"><span class="alert-prio">' + esc(a.priority) + '</span>' +
        '<h3>' + esc(a.title) + '</h3><p>' + esc(a.detail) + '</p>' +
        '<a class="alert-link" href="#/' + esc(a.channel) + '">해당 채널 열기 →</a></div></div>';
    }).join("");

    var funnelLegend = d.funnel.stages.map(function (s) {
      return '<div><b><i style="background:' + esc(s.accent) + '"></i>' + esc(s.label) + '</b>' + esc(s.desc) + '</div>';
    }).join("");

    main.innerHTML =
      '<div class="page-head">' +
      '<div class="page-eyebrow"><span class="live"></span>통합 대시보드 · ' + esc(d.timeline.date) + '</div>' +
      '<h1>수익화 파이프라인 한눈에</h1>' +
      '<p>' + esc(d.meta.subtitle) + ' — 채널 8개의 진행 상황과 수익, 지금 해야 할 일을 한 화면에 모았습니다.</p>' +
      '</div>' +
      '<div class="kpi-grid">' + kpis + '</div>' +
      salesSection(d) +
      radarSection(d, { compact: true }) +
      seasonSection(d, { compact: true }) +
      '<div class="grid grid-3">' +
      '<section class="panel span-2"><div class="panel-head"><div><h2>채널별 파이프라인</h2>' +
      '<p>각 채널이 수익화까지 얼마나 준비됐는지 (막대를 누르면 세부 대시보드)</p></div></div>' +
      '<div class="rows">' + rows + '</div></section>' +
      '<section class="panel"><div class="panel-head"><div><h2>채널 상태</h2>' +
      '<p>운영 ' + counts.operating + ' · 준비 ' + counts.preparing + ' · 대기 ' + counts.waiting + '</p></div></div>' +
      '<div class="donut-wrap">' + donut(donutSegs, String(d.channels.length), "채널") +
      '<div class="legend">' + legend +
      '<div class="legend-item" style="border-top:1px solid #eef1f6;padding-top:9px;margin-top:2px">' +
      '<span>평균 준비도</span><b>' + avg + '%</b></div></div></div>' +
      revMini(d) + '</section>' +
      '</div>' +
      '<section class="panel" style="margin-bottom:18px"><div class="panel-head"><div><h2>수익화 퍼널</h2>' +
      '<p>' + esc(d.funnel.caption) + '</p></div></div>' +
      funnelSvg(d.funnel.stages) +
      '<div class="funnel-m">' + d.funnel.stages.map(function (s) {
        return '<div class="fm-row"><div class="fm-top"><span class="fm-label">' + esc(s.label) + '</span>' +
          '<span class="fm-value">' + esc(s.headline) + '<small>' + esc(s.unit) + '</small></span></div>' +
          '<div class="fm-bar"><i style="width:' + s.width + '%;background:' + esc(s.accent) + '"></i></div>' +
          '<p class="fm-desc">' + esc(s.desc) + '</p></div>';
      }).join("") + '</div>' +
      '<div class="funnel-legend">' + funnelLegend + '</div></section>' +
      blogStatsSection(d) +
      updatesSection(d) +
      '<section class="panel" style="margin-bottom:18px"><div class="panel-head"><div><h2>오늘의 자동화 타임라인</h2>' +
      '<p>' + esc(d.timeline.date) + ' · 자동 실행과 예약</p></div>' +
      '<div class="panel-tools"><span class="chip operating"><span class="d" style="background:#0f9d58"></span>자동 ' + autoOn + '개 가동</span></div></div>' +
      '<div class="timeline">' + tl + '</div></section>' +
      '<section class="panel"><div class="panel-head"><div><h2>지금 확인이 필요한 일</h2>' +
      '<p>보현님 결정이나 확인이 있어야 다음 단계로 넘어가는 항목</p></div>' +
      '<div class="panel-tools"><span class="chip">' + d.alerts.length + '건</span></div></div>' +
      '<div class="alert-grid">' + alerts + '</div></section>' +
      foot();
    bindLinks();
  }

  /* ---------------- channel detail ---------------- */
  function renderChannel(ch) {
    if (!ch) return renderOverview();
    var st = statusOf(ch.status);
    var d = state.data;

    var metrics = ch.metrics.map(function (m) {
      return '<div class="metric"><div class="metric-label">' + esc(m.label) + '</div>' +
        '<div class="metric-value">' + esc(m.value) + (m.unit ? '<small>' + esc(m.unit) + '</small>' : '') + '</div>' +
        '<div class="metric-note">' + esc(m.note) + '</div></div>';
    }).join("");

    var done = ch.done.map(function (x) {
      return '<div class="done-item"><div class="done-mark">' +
        '<svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 6.4 4.6 9 10 3.4"/></svg></div>' +
        '<div class="done-body"><div class="done-date">' + esc(x.date) + '</div>' +
        '<h4>' + esc(x.title) + '</h4><p>' + esc(x.detail) + '</p></div></div>';
    }).join("");

    var next = ch.next.map(function (x, i) {
      var ownerCls = x.owner === "파인" ? "me" : x.owner === "보현님" ? "user" : "";
      return '<div class="next-item"><div class="next-num">' + (i + 1) + '</div><div class="next-body">' +
        '<div class="next-top"><h4>' + esc(x.title) + '</h4>' +
        '<span class="owner ' + ownerCls + '">' + esc(x.owner) + '</span>' +
        (x.due ? '<span class="due">' + esc(x.due) + '</span>' : '') + '</div>' +
        '<p>' + esc(x.detail) + '</p></div></div>';
    }).join("");

    var auto = ch.automation.map(function (a) {
      var cls = a.state === "on" ? "on" : a.state === "once" ? "once" : "off";
      var label = a.state === "on" ? "가동" : a.state === "once" ? "예약" : "없음";
      return '<div class="auto-item"><div class="auto-time">' + esc(a.time) + '</div>' +
        '<div class="auto-label"><strong>' + esc(a.label) + '</strong><span>' + esc(a.note) + '</span></div>' +
        '<span class="state ' + cls + '"><span class="d"></span>' + label + '</span></div>';
    }).join("");

    var cols = ch.collections ? (
      '<section class="panel" style="margin-bottom:18px"><div class="panel-head"><div><h2>컬렉션</h2>' +
      '<p>' + esc(ch.collections_note || (ch.collections.length + '개')) + '</p></div></div>' +
      '<div class="col-list">' + ch.collections.map(function (c) {
        return '<a class="col-item" href="' + esc(c.url) + '" target="_blank" rel="noopener">' +
          '<span class="col-count">' + c.count + '</span>' +
          '<span class="col-name">' + esc(c.title) + '</span>' +
          '<span class="col-arrow">→</span></a>';
      }).join("") + '</div></section>'
    ) : "";

    var links = ch.links.map(function (l) {
      if (!l.url) {
        return '<span class="link-btn disabled" title="작업 폴더 파일입니다">' + esc(l.label) + '</span>';
      }
      return '<a class="link-btn" href="' + esc(l.url) + '" target="_blank" rel="noopener">' + esc(l.label) + ' ↗</a>';
    }).join("");

    var notes = ch.notes && ch.notes.length ? (
      '<section class="panel" style="margin-top:18px"><div class="panel-head"><div><h2>기준 · 메모</h2></div></div>' +
      '<ul class="note-list">' + ch.notes.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join("") + '</ul></section>'
    ) : "";

    main.innerHTML =
      '<div class="ch-head" style="--c:' + esc(ch.accent) + '">' +
      '<div class="ch-head-main">' +
      '<div class="ch-eyebrow"><a class="back" href="#/overview">← 통합 대시보드</a>' +
      '<span class="chip ' + esc(ch.status) + '"><span class="d" style="background:' + st.color + '"></span>' + st.label + '</span></div>' +
      '<h1>' + esc(ch.name) + '</h1>' +
      '<div class="ch-handle">' + esc(ch.handle) + '</div>' +
      '<p class="ch-role">' + esc(ch.role) + '</p>' +
      '</div>' +
      '<div class="ch-head-right">' + ring(ch.progress, ch.accent) +
      '<div class="ring-basis">' + esc(ch.progress_basis) + '</div></div></div>' +
      '<div class="metric-grid">' + metrics + '</div>' +
      '<div class="revenue">' +
      '<div class="rev-cell"><div class="rev-label">실현 수익</div><div class="rev-value">' + esc(ch.revenue.confirmed) + '</div></div>' +
      '<div class="rev-cell"><div class="rev-label">' + esc(ch.revenue.pending_label) + '</div><div class="rev-value pending-num">' + esc(ch.revenue.pending) + '</div></div>' +
      '<div class="rev-cell"><p class="rev-note">' + esc(ch.revenue.note) + '</p></div></div>' +
      (ch.id === "forest" ? salesSection(d) : "") +
      (ch.id === "forest" ? seasonSection(d) : "") +
      (ch.id === "blog" ? blogStatsSection(d) : "") +
      cols +
      '<div class="duo">' +
      '<section class="panel"><div class="panel-head"><div><h2>완료된 진행상황</h2>' +
      '<p>' + ch.done.length + '건 · 최근 순</p></div></div><div class="done-list">' + done + '</div></section>' +
      '<section class="panel"><div class="panel-head"><div><h2>앞으로 할 일</h2>' +
      '<p>위에서부터 순서대로</p></div></div><div class="next-list">' + next + '</div></section>' +
      '</div>' +
      '<div class="duo">' +
      '<section class="panel"><div class="panel-head"><div><h2>자동화 가동 현황</h2>' +
      '<p>파인이 자동으로 돌리는 루틴</p></div></div><div class="auto-list">' + auto + '</div></section>' +
      '<section class="panel"><div class="panel-head"><div><h2>바로가기</h2>' +
      '<p>실제 채널·상품 페이지</p></div></div><div class="link-row">' + links + '</div>' +
      (ch.notes && ch.notes.length ? '<div style="margin-top:16px"><div class="rev-label" style="margin-bottom:6px">메모</div>' +
        '<ul class="note-list">' + ch.notes.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join("") + '</ul></div>' : '') +
      '</section></div>' +
      foot();
    bindLinks();
  }

  function foot() {
    var d = state.data;
    return '<div class="foot"><span>데이터 <code>data.json</code> · 갱신 ' + esc(d.meta.updated_label) + ' · v' + esc(d.meta.data_version) + '</span>' +
      '<span>파인이 이 파일만 갱신하면 웹과 앱에 같은 내용이 반영됩니다</span></div>';
  }

  function bindLinks() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-nav]"), function (a) {
      a.addEventListener("click", function (e) {
        e.preventDefault();
        location.hash = "#/" + a.getAttribute("data-nav");
      });
    });
  }

  /* ---------------- boot ---------------- */
  function boot() {
    loadData(false).then(function (data) {
      state.data = data;
      $("#updatedAt").textContent = "업데이트 " + data.meta.updated_label;
      $("#brandTitle").textContent = "매장경영노트";
      route();
    }).catch(renderError);
  }

  window.addEventListener("hashchange", function () {
    if (state.data) route();
  });

  $("#refreshBtn").addEventListener("click", function () {
    var btn = this;
    btn.classList.add("spinning");
    loadData(true).then(function (data) {
      state.data = data;
      $("#updatedAt").textContent = "업데이트 " + data.meta.updated_label;
      route();
      toast("최신 데이터로 새로고침했습니다");
    }).catch(function () { toast("데이터를 새로고침하지 못했습니다"); })
      .then(function () { setTimeout(function () { btn.classList.remove("spinning"); }, 400); });
  });

  // PWA
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("./sw.js").catch(function () {});
    });
  }
  var deferredPrompt = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    var b = $("#installBtn");
    if (b) b.hidden = false;
  });
  var installBtn = $("#installBtn");
  if (installBtn) {
    installBtn.addEventListener("click", function () {
      if (!deferredPrompt) { toast("브라우저 메뉴에서 '홈 화면에 추가'를 눌러 주세요"); return; }
      deferredPrompt.prompt();
      deferredPrompt = null;
      installBtn.hidden = true;
    });
  }
  window.addEventListener("appinstalled", function () {
    var b = $("#installBtn");
    if (b) b.hidden = true;
  });

  boot();
})();
