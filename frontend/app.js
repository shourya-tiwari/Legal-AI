// Config
const baseURL = window.LEGALAI_CONFIG.baseURL;
const endpoints = {
  upload: "/upload",
  rewrite: "/rewrite",
  map: "/map",
  risk: "/risk/scan",
  ask: "/ask",
  contextualize: "/contextualize/scan"
};

// Helpers
const $ = (q)=>document.querySelector(q);
const $$ = (q)=>document.querySelectorAll(q);

function setText(el, text=""){ if(el) el.textContent = text ?? ""; }
function setHTMLSafe(el, text=""){ if(el) el.textContent = text ?? ""; }

function setLoading(btn, isLoading, textIdle, textBusy){
  btn.disabled = !!isLoading;
  btn.classList.toggle("loading", !!isLoading);
  btn.querySelector(".btn-label").textContent = isLoading ? textBusy : textIdle;
}

async function apiPost(endpoint, data, isForm=false){
  const opts = isForm ? { method:"POST", body:data } : {
    method:"POST",
    headers:{ "Content-Type":"application/json" },
    body: JSON.stringify(data)
  };
  const res = await fetch(baseURL + endpoint, opts);
  if(!res.ok){
    const msg = await res.text();
    throw new Error(msg || res.statusText);
  }
  return res.json();
}

// Navigation
const navToggle = $("#navToggle");
const navLinks = $("#navLinks");
navToggle?.addEventListener("click", ()=> navLinks.classList.toggle("open"));
navLinks?.addEventListener("click", (e)=>{
  if(e.target.matches("a")) navLinks.classList.remove("open");
});

$$(".nav-link").forEach(a=>{
  a.addEventListener("click", (e)=>{
    e.preventDefault();
    const href = a.getAttribute("href");
    if(href?.startsWith("#")){
      document.querySelector(href)?.scrollIntoView({behavior:"smooth"});
    }
  });
});

// Tabs
$$(".tab-btn").forEach(btn=>{
  btn.addEventListener("click", ()=>{
    $$(".tab-btn").forEach(b=>b.classList.remove("active"));
    $$(".tab-content").forEach(c=>c.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
  });
});

// Global State
let LAST_TEXT = "";
let LAST_RESULTS = { simple:"", advanced:"", timeline:[], risks:[] };

// Upload + Analyze Flow
const uploadBtn = $("#uploadBtn");
const fileInput = $("#fileInput");
const uploadStatus = $("#uploadStatus");
const fileBadge = $("#fileBadge");

uploadBtn?.addEventListener("click", async ()=>{
  if(!fileInput.files[0]){
    setText(uploadStatus, "Please select a file first.");
    return;
  }

  setLoading(uploadBtn, true, "Upload & Analyze", "Analyzing…");
  setText(uploadStatus, "Uploading…");

  try{
    // Step 1: Upload file
    const fd = new FormData();
    fd.append("file", fileInput.files[0]);
    const uploadRes = await apiPost(endpoints.upload, fd, true);

    LAST_TEXT = uploadRes.full_text;
    fileBadge.hidden = false;
    setText(fileBadge, uploadRes.filename);
    setText(uploadStatus, "File uploaded. Running analysis…");

    // Step 2: Rewrite simplified
    const simple = await apiPost(endpoints.rewrite, { text: LAST_TEXT, mode:"layman" });

    // Show simplified + original
    LAST_RESULTS.simple = simple.rewritten_text;
    LAST_RESULTS.advanced = LAST_TEXT;

    $("#resultsEmpty").style.display="none";
    setHTMLSafe($("#simple"), LAST_RESULTS.simple);
    setHTMLSafe($("#advanced"), LAST_RESULTS.advanced);

    // Step 3: Timeline
    const mapRes = await apiPost(endpoints.map, { contract_text: LAST_TEXT });
    LAST_RESULTS.timeline = mapRes.timeline || [];
    if(LAST_RESULTS.timeline.length){
      $("#timelineEmpty").style.display="none";
      const tl = $("#timelineList");
      tl.innerHTML = "";
      LAST_RESULTS.timeline.forEach(ev=>{
        const li = document.createElement("li");
        li.textContent = `${ev.date_description}: ${ev.event}`;
        tl.appendChild(li);
      });
    }

    // Step 4: Risk scan
    const riskRes = await apiPost(endpoints.risk, { text: LAST_TEXT });

    // Extract risks from backend response
    LAST_RESULTS.risks = [];
    if (riskRes.flagged_clauses && riskRes.flagged_clauses.length) {
      riskRes.flagged_clauses.forEach(fc => {
        if (fc.keyword_flags?.length) {
          fc.keyword_flags.forEach(f => LAST_RESULTS.risks.push(f.term));
        }
        if (fc.contextual_flags?.length) {
          fc.contextual_flags.forEach(f => LAST_RESULTS.risks.push(f.term));
        }
      });
    }

    if (LAST_RESULTS.risks.length) {
      $("#risksEmpty").style.display = "none";
      const rl = $("#riskList");
      rl.innerHTML = "";
      LAST_RESULTS.risks.forEach(r => {
        const li = document.createElement("li");
        li.textContent = r;
        rl.appendChild(li);
      });
    }

    setText(uploadStatus, "Analysis complete!");
  }catch(err){
    console.error(err);
    setText(uploadStatus, "Error: " + err.message);
  }finally{
    setLoading(uploadBtn, false, "Upload & Analyze", "Analyzing…");
  }
});

// Quick Question
const quickQ = $("#quickQuestion");
const askBtn = $("#askBtn");

askBtn?.addEventListener("click", async ()=>{
  const q = quickQ.value.trim();
  if(!q) return;

  askBtn.disabled = true;
  try{
    const res = await apiPost(endpoints.ask, { contract_text: LAST_TEXT, question: q });
    alert("Answer: " + res.answer);
  }catch(err){
    alert("Error: " + err.message);
  }finally{
    askBtn.disabled = false;
  }
});

// Chatbot Panel
const chatToggle = $("#chatToggle");
const chatPanel = $("#chatPanel");
const chatClose = $("#chatClose");
const chatForm = $("#chatForm");
const chatText = $("#chatText");
const chatMessages = $("#chatMessages");

function addMsg(text, who="bot"){
  const div = document.createElement("div");
  div.className = "msg " + who;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

chatToggle?.addEventListener("click", ()=> chatPanel.classList.add("open"));
chatClose?.addEventListener("click", ()=> chatPanel.classList.remove("open"));

chatForm?.addEventListener("submit", async (e)=>{
  e.preventDefault();
  const q = chatText.value.trim();
  if(!q) return;
  addMsg(q, "user");
  chatText.value = "";

  const thinking = document.createElement("div");
  thinking.className="msg bot thinking";
  thinking.textContent="Thinking…";
  chatMessages.appendChild(thinking);

  try{
    const res = await apiPost(endpoints.ask, { contract_text: LAST_TEXT, question:q });
    thinking.remove();
    addMsg(res.answer, "bot");
  }catch(err){
    thinking.remove();
    addMsg("Error: " + err.message, "bot");
  }
});

// CONTEXTUALIZER HANDLER
const explainBtn = $("#explainBtn");
const selectedText = $("#selectedText");
const userRole = $("#userRole");
const userLocation = $("#userLocation");
const contractType = $("#contractType");
const explanationTone = $("#explanationTone");
const contextualizerEmpty = $("#contextualizerEmpty");
const contextualizerResult = $("#contextualizerResult");
const explanationText = $("#explanationText");
const usedHints = $("#usedHints");
const hintsList = $("#hintsList");

explainBtn?.addEventListener("click", async () => {
  const text = selectedText.value.trim();
  if (!text) {
    alert("Please enter contract text to explain.");
    return;
  }

  setLoading(explainBtn, true, "Explain This Clause", "Explaining...");

  try {
    const context = {
      role: userRole.value,
      location: userLocation.value.trim() || null,
      contract_type: contractType.value || null,
      interests: null, // Could be expanded later
      tone: explanationTone.value
    };

    const response = await apiPost(endpoints.contextualize, {
      text: text,
      context: context
    });

    // Show results
    contextualizerEmpty.style.display = "none";
    contextualizerResult.style.display = "block";
    
    setHTMLSafe(explanationText, response.explanation);
    
    // Show hints if available
    if (response.used_hints && response.used_hints.length > 0) {
      usedHints.style.display = "block";
      hintsList.innerHTML = "";
      response.used_hints.forEach(hint => {
        const li = document.createElement("li");
        li.textContent = hint;
        hintsList.appendChild(li);
      });
    } else {
      usedHints.style.display = "none";
    }

  } catch (err) {
    console.error("Contextualizer error:", err);
    alert("Error explaining clause: " + err.message);
  } finally {
    setLoading(explainBtn, false, "Explain This Clause", "Explaining...");
  }
});

// Add text selection helper
function selectTextFromContract() {
  const contractText = $("#advanced").textContent || $("#simple").textContent;
  if (contractText && contractText.trim()) {
    selectedText.value = contractText.substring(0, 1000) + "...";
    selectedText.focus();
  }
}

// Add button to copy contract text for contextualization
const copyTextBtn = document.createElement("button");
copyTextBtn.className = "btn ghost";
copyTextBtn.innerHTML = '<span class="btn-label">Use Contract Text</span>';
copyTextBtn.addEventListener("click", selectTextFromContract);

// Insert the button after the explain button
if (explainBtn && explainBtn.parentNode) {
  explainBtn.parentNode.insertBefore(copyTextBtn, explainBtn.nextSibling);
}
