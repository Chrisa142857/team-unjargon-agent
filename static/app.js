const $ = (id) => document.getElementById(id);
let currentTerm = "";
async function request(path, body) {
  const response = await fetch(path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Request failed.");
  return data;
}
$("explain").onclick = async () => {
  $("error").textContent = "";
  currentTerm = $("term").value.trim();
  try {
    const answer = await request("/api/explain", {member: $("member").value, term: currentTerm, context: $("context").value});
    $("source").textContent = `Source: ${answer.source}`;
    $("definition").textContent = answer.definition;
    $("why").textContent = answer.why_it_matters;
    $("next").textContent = answer.next_action;
    $("clarification").textContent = answer.clarification ? `Clarification: ${answer.clarification}` : "";
    $("result").classList.remove("hidden");
  } catch (error) { $("error").textContent = error.message; }
};
$("useful").onclick = async () => {
  try { const data = await request("/api/feedback", {member: $("member").value, term: currentTerm, useful: true}); $("feedback-status").textContent = `Shared learning confirmed (${data.record.helpful_count} useful).`; }
  catch (error) { $("feedback-status").textContent = error.message; }
};
$("show-correction").onclick = () => $("correction-box").classList.toggle("hidden");
$("save-correction").onclick = async () => {
  try { await request("/api/feedback", {member: $("member").value, term: currentTerm, correction: $("correction").value}); $("feedback-status").textContent = "Saved. Switch members and ask again to see the team memory."; }
  catch (error) { $("feedback-status").textContent = error.message; }
};
