/* 매장경영노트 수익화 대시보드
   UI는 이 파일에, 데이터는 data.json에 있습니다.
   data.json만 갱신해서 배포하면 웹·앱이 같은 내용을 표시합니다. */
(function () {
  "use strict";

  var state = { data: null, view: "overview", channel: null };
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
    nav.innerHTML = '<div class="nav-label">통합</div>' + overview +
      '<div class="nav-label">채널</div>' + items;

    mobileNav.innerHTML =
      '<a class="m-pill' + (state.view === "overview" ? " is-active" : "") + '" href="#/overview">통합</a>' +
      d.channels.map(function (ch) {
        return '<a class="m-pill' + (state.view === "channel" && state.channel === ch.id ? " is-active" : "") +
          '" href="#/' + esc(ch.id) + '"><span class="nav-dot" style="background:' + esc(ch.accent) + '"></span>' +
          esc(ch.name) + '</a>';
      }).join("");
  }

  function parseHash() {
    var h = (location.hash || "#/overview").replace(/^#\/?/, "");
    if (!h || h === "overview") return { view: "overview", id: null };
    var found = state.data.channels.some(function (c) { return c.id === h; });
    return found ? { view: "channel", id: h } : { view: "overview", id: null };
  }

  function route() {
    var r = parseHash();
    state.view = r.view;
    state.channel = r.id;
    renderNav();
    if (r.view === "overview") renderOverview();
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

  /* ---------------- overview ---------------- */
  function renderOverview() {
    var d = state.data;
    var counts = { operating: 0, preparing: 0, waiting: 0 };
    d.channels.forEach(function (c) { counts[c.status] = (counts[c.status] || 0) + 1; });
    var avg = Math.round(sum(d.channels.map(function (c) { return c.progress; })) / d.channels.length);

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
      '<section class="panel" style="margin-bottom:18px"><div class="panel-head"><div><h2>오늘의 자동화 타임라인</h2>' +
      '<p>' + esc(d.timeline.date) + ' · 자동 실행과 예약</p></div>' +
      '<div class="panel-tools"><span class="chip operating"><span class="d" style="background:#0f9d58"></span>자동 3개 가동</span></div></div>' +
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
