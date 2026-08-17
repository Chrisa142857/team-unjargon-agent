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
  return `<article class="task ${review ? "review-task" : "aligned-task"}"><p class="eyebrow">${review ? "Needs team review" : "Automatically aligned"}</p><h3>${task.term}</h3><p>${task.reason}</p><small>${task.sightings} sighting${task.sightings === 1 ? "" : "s"} · ${task.source}</small>${review ? `<button data-term="${task.term}" class="review-button">Review this term</button>` : ""}</article>`;
}
async function loadInbox() {
  const {tasks} = await request("/api/inbox");
  const review = tasks.filter((task) => task.status === "needs_review");
  const aligned = tasks.length - review.length;
  $("counts").textContent = `${review.length} need review · ${aligned} aligned automatically`;
  $("inbox").innerHTML = tasks.length ? tasks.map(card).join("") : `<p class="empty">Waiting for a connected detector. The agent will build this inbox automatically.</p>`;
  document.querySelectorAll(".review-button").forEach((button) => button.onclick = () => openReview(tasks.find((task) => task.term === button.dataset.term)));
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
