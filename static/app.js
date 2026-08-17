const $ = (id) => document.getElementById(id);
let currentTask;
async function request(path, body) {
  const response = await fetch(path, {method: body ? "POST" : "GET", headers: body ? {"Content-Type": "application/json"} : {}, body: body ? JSON.stringify(body) : undefined});
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Request failed.");
  return data;
}
function card(task) {
  const review = task.status === "needs_review";
  const term = escape(task.term);
  const reference = task.team_definition
    ? `<p class="definition"><strong>Team definition</strong> · ${escape(task.team_definition)}</p>`
    : `<p class="reference" data-reference="${term}">Loading public reference…</p><p class="links"><a href="https://www.google.com/search?q=${encodeURIComponent(task.term)}" target="_blank" rel="noreferrer">Search Google ↗</a> <a href="https://en.wikipedia.org/wiki/${encodeURIComponent(task.term)}" target="_blank" rel="noreferrer">Open Wikipedia ↗</a></p>`;
  return `<article class="task ${review ? "review-task" : "aligned-task"}"><p class="eyebrow">${review ? "Needs team review" : "Automatically aligned"}</p><h3>${term}</h3>${reference}<p>${escape(task.reason)}</p><small>${task.sightings} sighting${task.sightings === 1 ? "" : "s"} · ${escape(task.source)}</small>${review ? `<button data-term="${term}" class="review-button">Review this term</button>` : ""}</article>`;
}
function escape(value) { return value.replace(/[&<>'"]/g, (character) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"})[character]); }
async function loadPublicReferences() {
  for (const target of document.querySelectorAll("[data-reference]")) {
    const term = target.dataset.reference;
    try {
      const response = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(term)}`);
      const data = await response.json();
      target.textContent = data.extract ? `Public reference · zero AI — ${data.extract}` : "Public reference unavailable; use the links below.";
    } catch { target.textContent = "Public reference unavailable; use the links below."; }
  }
}
async function loadInbox() {
  const {tasks} = await request("/api/inbox");
  const review = tasks.filter((task) => task.status === "needs_review");
  const aligned = tasks.length - review.length;
  $("counts").textContent = `${review.length} need review · ${aligned} aligned automatically`;
  $("inbox").innerHTML = tasks.length ? tasks.map(card).join("") : `<p class="empty">Waiting for a connected detector. The agent will build this inbox automatically.</p>`;
  document.querySelectorAll(".review-button").forEach((button) => button.onclick = () => openReview(tasks.find((task) => task.term === button.dataset.term)));
  loadPublicReferences();
}
function openReview(task) {
  currentTask = task;
  $("review-term").textContent = task.term;
  $("review-reason").textContent = task.reason;
  $("result").classList.add("hidden"); $("error").textContent = ""; $("feedback-status").textContent = "";
  $("review").classList.remove("hidden");
  $("review").scrollIntoView({behavior:"smooth", block:"start"});
}
$("simulate").onclick = async () => {
  $("run-status").textContent = "Processing detector events…";
  try {
    const run = await request("/api/detection-events", {source:"Codex", candidates:["ADR", "RAG", "SLO", "runbook", "vector database", "RAG"]});
    $("run-status").textContent = `${run.received} candidates received · ${run.aligned} aligned · ${run.needs_review} added for team review.`;
    await loadInbox();
  } catch (error) { $("run-status").textContent = error.message; }
};
$("draft").onclick = async () => {
  $("error").textContent = "";
  try {
    const answer = await request("/api/explain", {member: $("member").value, term: currentTask.term});
    $("source").textContent = `Draft source: ${answer.source}`; $("definition").textContent = answer.definition; $("why").textContent = answer.why_it_matters; $("next").textContent = answer.next_action; $("clarification").textContent = answer.clarification ? `Clarification: ${answer.clarification}` : "";
    $("correction").value = answer.definition; $("result").classList.remove("hidden");
  } catch (error) { $("error").textContent = error.message; }
};
$("save-correction").onclick = async () => {
  try {
    await request("/api/feedback", {member: $("member").value, term: currentTask.term, correction: $("correction").value});
    $("feedback-status").textContent = "Approved. Future detections will align automatically.";
    await loadInbox();
  } catch (error) { $("feedback-status").textContent = error.message; }
};
loadInbox();
