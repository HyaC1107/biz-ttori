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
  const decide = (e, ok) => postEvent({
    type: ok ? "approval.granted" : "approval.rejected", actor: "PM", dept: "hq",
    summary: `${e.summary.slice(0, 90)} → ${ok ? "승인" : "반려"}`,
    ...(e.task_id ? { task_id: e.task_id } : {}),
    ...(e.project ? { project: e.project } : {}) });
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
  return { TYPE_ICON, esc, fmtTs, matches, pendingApprovals, postEvent, decide, fetchCost, fmtTok,
           getProjFilter, setProjFilter, matchesProject };
})();
