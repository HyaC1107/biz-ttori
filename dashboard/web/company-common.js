// company-common.js — board.html + dashboard3d.html 공용 로직 (전역 CC)
// 규칙: 미결 판정·결재 POST는 여기 한 벌만 수정한다 (2026-07-11 중복 2벌 추출).
// 매칭 기준은 briefing.py `_matches`와 동일하게 유지할 것.
window.CC = (() => {
  const TYPE_ICON = {
    "mail.in": "📥", "mail.out": "📤", "bot.spawned": "🚀", "bot.done": "✅",
    "bot.failed": "❌", "task.created": "📌", "task.assigned": "📌",
    "approval.requested": "📋", "approval.granted": "👤✅", "approval.rejected": "👤↩",
    "report.filed": "📄", "project.genesis": "🏢", "org.changed": "👥", "project.updated": "✏️",
    "debate.started": "🏛️", "debate.statement": "💬", "debate.concluded": "🤝",
  };
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  // 표시 전용 액터 별칭 — 이벤트 데이터의 actor는 원본 그대로 두고 화면 라벨만 치환한다.
  // "지시봇": PM 지시를 자동처리하는 헤드리스 워커의 합성 actor(상주 봇 아님 → 봇 현황판 명단엔 없다).
  // 태스크보드/피드에 이 워커가 뜰 때 조직 구성원처럼 보이지 않게 "자동 워커"로 표기 (2026-07-16 PM).
  const ACTOR_ALIAS = { "지시봇": "자동 워커" };
  const actorLabel = a => ACTOR_ALIAS[a] || a || "";
  const fmtTs = iso => {
    const d = new Date(iso);
    return `${String(d.getMonth()+1).padStart(2,"0")}/${String(d.getDate()).padStart(2,"0")} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
  };
  // 둘 다 task_id가 있으면 task_id만 신뢰(prefix 오탐 방지), 아니면 summary 앞 12자 폴백
  const matches = (req, later) => (req.task_id && later.task_id)
    ? later.task_id === req.task_id
    : (later.summary || "").includes((req.summary || "").slice(0, 12));
  const pendingApprovals = evs => {
    const decided = evs.filter(e => e.type === "approval.granted" || e.type === "approval.rejected");
    return evs.filter(e => e.type === "approval.requested"
      && !decided.some(d => d.ts >= e.ts && matches(e, d)));
  };
  const postEvent = async body => {
    const r = await fetch("/api/event", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    return r.json();
  };
  // 승인/반려는 원 요청의 project를 **승계**한다 — 안 하면 결재 결과 이벤트만
  // 프로젝트 필터에서 빠져 타임라인이 쪼개진다 (스프린트2, 2026-07-12)
  // 승인(approval.granted)은 서버가 실제 워커를 재기동하므로, 중복 클릭이 중복 실행으로
  // 이어지지 않게 처리 중인 task_id는 막는다 (board.html의 decide()와 동일 가드).
  const decidingTaskIds = new Set();
  const decide = async (e, ok) => {
    if (e.task_id) {
      if (decidingTaskIds.has(e.task_id)) return null;
      decidingTaskIds.add(e.task_id);
    }
    try {
      return await postEvent({
        type: ok ? "approval.granted" : "approval.rejected", actor: "PM", dept: "hq",
        summary: `${e.summary.slice(0, 90)} → ${ok ? "승인" : "반려"}`,
        ...(e.task_id ? { task_id: e.task_id } : {}),
        ...(e.project ? { project: e.project } : {}) });
    } finally {
      if (e.task_id) decidingTaskIds.delete(e.task_id);
    }
  };
  const fetchCost = async () => {
    try { const r = await fetch("/api/cost", { cache: "no-store" });
      return r.ok ? await r.json() : null; } catch { return null; }
  };
  const fmtTok = n => n >= 1e6 ? (n/1e6).toFixed(1) + "M"
    : n >= 1e3 ? (n/1e3).toFixed(1) + "K" : String(n || 0);
  /* ── 프로젝트 필터 (스프린트2) ──
     상태는 localStorage 한 키 — 현황판/3D가 같은 선택을 공유한다.
     "all"=전체, "?"=미지정(project 필드 없는 과거 이벤트), 그 외=projects.json id.
     판정은 이 한 벌만 쓴다 — 페이지별로 복제하면 기준이 어긋난다. */
  const PROJ_KEY = "bizttori.projFilter";
  const getProjFilter = () => localStorage.getItem(PROJ_KEY) || "all";
  const setProjFilter = v => localStorage.setItem(PROJ_KEY, v);
  const matchesProject = (item, sel) =>
    sel === "all" ? true : sel === "?" ? !item.project : item.project === sel;
  // PM지시 텍스트에 프로젝트 키워드(projects.json의 keywords[])가 있으면 그 프로젝트로 자동 분류.
  // 매칭 없으면 null(호출부가 현재 선택된 필터로 폴백). 대소문자 무시, 첫 매치 우선.
  const detectProjectFromText = (text, projects) => {
    const t = (text || "").toLowerCase();
    for (const p of projects || []) {
      for (const kw of p.keywords || []) {
        if (t.includes(String(kw).toLowerCase())) return p.id;
      }
    }
    return null;
  };
  return { TYPE_ICON, esc, fmtTs, actorLabel, matches, pendingApprovals, postEvent, decide, fetchCost, fmtTok,
           getProjFilter, setProjFilter, matchesProject, detectProjectFromText };
})();
