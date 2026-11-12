"use strict";
const el = (id) => document.getElementById(id),
  all = (selector) => [...document.querySelectorAll(selector)];
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const time = (s) =>
  Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0");
const stem = (name) =>
  name
    .normalize("NFC")
    .replace(/\.[^.]+$/, "")
    .toLowerCase();
const selected = new Set(),
  touched = new Set();
let state = {},
  inserts = [],
  activePanel = "script",
  timer,
  importing = false,
  versionKey = "",
  waiting = false;
let unresolvedScripts=[], inspectorOpen=true, manualEvents=[],pendingTakeParent='',editRevision=0;
let activeEditorTurn='',activeConversationId='';
const transferableStyle=['style','fit','caption_position','motion_profile','motion_intensity','music_mode','music_track','music_gain_db','brand_logo'];
async function sendFeedback(e,note,action){
 const payload={project:e.job,master:e.id,sha256:e.sha256,revision:state.jobs[e.job].revision,note,action};
 const key='cutroom-pending-feedback:'+e.job+':'+e.id,serialized=JSON.stringify(payload);
 let pending;try{pending=JSON.parse(sessionStorage.getItem(key));}catch{}
 if(!pending||pending.payload!==serialized){pending={payload:serialized,request_id:crypto.randomUUID()};sessionStorage.setItem(key,JSON.stringify(pending));}
 const result=await req('/api/feedback',{...payload,request_id:pending.request_id});sessionStorage.removeItem(key);return result;
}
const extraSettings=['motion_profile','motion_intensity','music_mode','music_track','music_gain_db','music_asset','planner_mode','brand_logo','brand_from','brand_to'];
const locked = (j) => ["Rendering", "Queued"].includes(j.status);
const notify = (s) => {
  const error=el('dialogError');if(el('modal')?.open&&error){error.textContent=s;error.classList.remove('hidden');}
  el("toast").textContent = s;
  el("toast").classList.remove("hidden");
  clearTimeout(timer);
  timer = setTimeout(() => el("toast").classList.add("hidden"), 5000);
};
const selectedIds = () => [...selected].filter((id) => state.jobs[id]);
function benchmarkQuizFields(exports){
 return `<details class="benchmark-quiz"><summary>Câu hỏi trắc nghiệm theo từng nguồn · tùy chọn</summary><p>Chuẩn bị đáp án từ footage trước khi so mù. Để trống lựa chọn thì chỉ thu câu trả lời mở, chưa tính độ chính xác.</p>${[...new Set(exports.map(e=>e.job))].map(job=>`<fieldset data-benchmark-quiz-job="${esc(job)}"><legend>${esc(sourceName(job))}</legend>${['Trong demo chính, người dẫn vừa bấm nút nào?','Sau khi bấm, điều gì thay đổi?'].map((text,i)=>`<label>Câu hỏi ${i+1}<input data-bq-text="${i}" value="${esc(text)}"></label><label>Lựa chọn · mỗi dòng một mục<textarea rows="4" data-bq-options="${i}"></textarea></label><label>Thứ tự đáp án đúng · từ 1<input type="number" min="1" max="6" data-bq-correct="${i}"></label>`).join('')}<label>Nguồn và timecode xác nhận đáp án<textarea rows="3" data-bq-evidence></textarea></label></fieldset>`).join('')}</details>`;
}
function readBenchmarkQuizzes(exportIds){
 const jobs=new Set(state.exports.filter(e=>exportIds.includes(e.id)).map(e=>e.job)),quizzes={};
 for(const box of all('[data-benchmark-quiz-job]')){
  const job=box.dataset.benchmarkQuizJob;if(!jobs.has(job))continue;
  const questions=[],evidence=box.querySelector('[data-bq-evidence]').value.trim();
  for(let i=0;i<2;i++){
   const options=box.querySelector(`[data-bq-options="${i}"]`).value.split(/\r?\n/).map(s=>s.trim()).filter(Boolean);if(!options.length)continue;
   const text=box.querySelector(`[data-bq-text="${i}"]`).value.trim(),correct=Number(box.querySelector(`[data-bq-correct="${i}"]`).value);
   if(!text||!evidence||!Number.isInteger(correct)||correct<1||correct>options.length)throw Error('Điền câu hỏi, đáp án và nguồn/timecode xác nhận trước khi tạo bài so mù.');
   questions.push({id:i?'result':'target',text,options,expected:options[correct-1],modality:'visual',answer_evidence:evidence});
  }
  if(questions.length)quizzes[job]=questions;
 }
 return quizzes;
}
const sourceName=id=>state.jobs[id]?.label||state.assets[id]?.name||'Recording';
function motionBackgroundControls(o,i){
 if(o.text===undefined)return '';
 return `<label>Text background<select data-motion-background="${i}"><option value="panel" ${(o.box_style||'panel')==='panel'?'selected':''}>One panel</option><option value="lines" ${o.box_style==='lines'?'selected':''}>Separate background per line</option></select></label>`;
}
function motionReplacementControls(o,i){
 let rect=o.rect;
 return (o.changes||[]).map((c,j)=>{rect=c.rect||rect;const id=i+'-'+j;return `<fieldset><legend>Replacement ${j+1} · source ${esc(c.anchor)}</legend><label>Visible text<textarea rows="2" data-motion-state-text="${id}">${esc(c.text)}</textarea></label><label><input type="checkbox" data-motion-state-custom="${id}" ${c.rect?'checked':''}> Change rectangle at this source anchor</label><small>Unchecked keeps the previous state’s rectangle. Font size and source time remain unchanged.</small><div class="roi-inputs">${['x','y','width','height'].map((name,k)=>`<label>${name} (0–1)<input type="number" min="0" max="1" step="0.01" data-motion-state-rect="${id}" data-coordinate="${k}" value="${rect[k]}" ${c.rect?'':'disabled'}></label>`).join('')}</div></fieldset>`;}).join('');
}
function readMotionReplacementControls(animation,o,i){
 (o.changes||[]).forEach((c,j)=>{const id=i+'-'+j;c.text=document.querySelector(`[data-motion-state-text="${id}"]`).value;
  if(!animation.context.texts.includes(c.text)){animation.context.texts.push(c.text);animation.context.voice_aligned=false;}
  if(document.querySelector(`[data-motion-state-custom="${id}"]`).checked)c.rect=all(`[data-motion-state-rect="${id}"]`).map(x=>Number(x.value));else delete c.rect;
 });
}
function retimeMotionKeys(keys,duration,tilt=null){
 if(!Number.isInteger(duration)||duration<keys.length-1||duration>60)throw Error('Entrance needs one frame per keyframe, up to60frames.');
 const last=keys.at(-1).frame,amplitude=Math.max(...keys.map(k=>Math.abs(k.rotation||0)));let previous=-1;
 const result=keys.map((k,i)=>{const frame=i===0?0:i===keys.length-1?duration:Math.max(previous+1,Math.min(duration-(keys.length-1-i),Math.round(k.frame*duration/last)));previous=frame;return {...k,frame};});
 if(tilt!==null&&tilt!==amplitude){if(!Number.isFinite(tilt)||tilt<0||tilt>45)throw Error('Entrance tilt must be0–45degrees.');result.forEach((k,i)=>k.rotation=amplitude?(k.rotation||0)*tilt/amplitude:i===0?tilt:0);}
 return result;
}
const versionsFor=id=>state.exports.filter(e=>e.job===id);
const cutVersion=e=>'v'+String(versionsFor(e.job).findIndex(x=>x.id===e.id)+1).padStart(3,'0');
const latestFor=id=>versionsFor(id).at(-1);
function visibleSources(){const query=(el('sourceSearch')?.value||'').toLocaleLowerCase('vi'),collection=el('sourceCollection')?.value||'',visibility=el('sourceVisibility')?.value||'active';return Object.values(state.jobs||{}).filter(j=>(!collection||(j.collection||'')===collection)&&(visibility==='all'||Boolean(j.archived)===(visibility==='archived'))&&(!query||[sourceName(j.id),state.assets[j.id].name,j.collection||'',j.id].join(' ').toLocaleLowerCase('vi').includes(query)));}
async function req(path, data, raw = false) {
  const opts =
    data === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "X-Cutroom-Key": state.key,
            ...(activeEditorTurn&&!path.startsWith('/api/conversations/')?{'X-Cutroom-Turn':activeEditorTurn}:{}),
            ...(raw ? {} : { "Content-Type": "application/json" }),
          },
          body: raw ? data : JSON.stringify(data),
        };
  const r = await fetch(path, opts);
  const body = await r.json();
  if (!r.ok) throw Error(body.error || "The request failed");
  return body;
}
const guard =
  (fn) =>
  async (...args) => {
    try {
      await fn(...args);
    } catch (e) {
      notify(e.message || String(e));
    }
  };
function thumb(a) {
  return a.thumb
    ? '<img class="thumb" alt="" src="/assets/' + a.id + '/thumb">'
    : '<span class="thumb"></span>';
}
function status(s) {
  const c = ["Queued", "Rendering"].includes(s)
    ? "live"
    : s === "For review"
      ? "warn"
      : ["Failed", "Interrupted"].includes(s)
        ? "fail"
        : "";
  return '<span class="pill ' + c + '">' + esc(s) + "</span>";
}
function dialog(title, html) {
  el("dialogTitle").textContent = title;
  el("dialogBody").innerHTML = '<p id="dialogError" role="alert" class="notice hidden"></p>'+html;
  if (!el("modal").open) el("modal").showModal();
}
function playsource(id) {
  const a = state.assets[id];
  dialog(
    a.name,
    '<video controls src="/assets/' +
      id +
      '/media"></video><small>Original recording · ' +
      time(a.duration) +
      "</small>",
  );
}
function review(id) {
  const e = state.exports.find((x) => x.id === id);
  dialog(
    sourceName(e.job)+' · '+cutVersion(e)+(latestFor(e.job)?.id===e.id?' · Latest cut':' · Previous cut'),
    '<div class="review-grid"><section class="review-picture"><video controls aria-label="Rendered export" src="/exports/' +
      id +
      '/mp4"></video><div class="dialogactions">' +
      ["mp4", "srt", "qc", "project"]
        .map(
          (k) =>
            '<a class="link" download href="/exports/' +
            id +
            "/" +
            k +
            '?download=1">' +
            {
              mp4: "Download MP4",
              srt: "Captions (.srt)",
              qc: "QC report",
              project: "Edit plan",
            }[k] +
            "</a>",
        )
        .join("") +
      "</div><small>" +
      esc(e.timing) +
      `.</small><details class="audio-audition"><summary>Listen to the mix · matched level</summary><label>Audio-only audition<select id="audioAudition" data-export="${id}"><option value="">Choose a mix…</option><option value="voice">Voice only</option><option value="voice_sfx">Voice + SFX</option><option value="full">Full mix</option></select></label><audio id="auditionPlayer" controls></audio><small>Audio auditions are leveled separately. Watch and approve the original master above.</small><div class="dialogactions">${['voice','sfx','music'].map(k=>`<a class="link" download href="/exports/${id}/${k}_stem?download=1">${k} WAV</a>`).join('')}<a class="link" download href="/exports/${id}/cues?download=1">Cue sheet</a></div></details></section><section class="review-inspection"><fieldset id="checklist"><legend>Final review</legend>` +
      [
        ["watched", "I watched the entire export at1× and phone size."],
        [
          "content",
          "The speaker, claims, proof and requested CTA are correct.",
        ],
        ["captions", "Captions are accurate, readable and on time."],
        [
          "audio",
          "I listened for clear speech, sync and unobtrusive sound effects.",
        ],
      ]
        .map(
          ([k, t]) =>
            '<label><input type="checkbox" data-gate="' +
            k +
            '"> ' +
            t +
            "</label>",
        )
        .join("") +
      '</fieldset>'+`<p class="source-lineage">Rendered cut ${cutVersion(e)} · original recording: ${esc(state.assets[e.job].name)} · source ${e.job.slice(0,8)}</p><button class="textbtn" data-reveal="export" data-local-id="${e.id}">Show MP4 in Explorer</button>`+technicalSummary(e)+`<button class="soft" data-hook-review="${id}">Review first 3 seconds before body</button>`+reviewEvidence(e)+'<label for="reviewNote">Timecode and correction (required for revisions)</label><input id="reviewNote" maxlength="2000" placeholder="e.g. 00:12 · Cutaway covers the result."><div class="dialogactions review-actions"><button class="soft" data-verdict="REVISE" data-eid="' +
      id +
      '">Request revision</button><button class="primary" data-verdict="READY" data-eid="' +
      id +
      '">Approve export</button><button class="soft" data-feedback-note="'+id+'">Save feedback only</button></div></section></div>',
  );
}
function technicalSummary(e){
  const t=e.technical, v=t?.verified, a=t?.output_audio;
  if(!v)return '<p class="notice">Measured QC unavailable for this older export. Download its QC report.</p>';
  return `<section class="technical"><h3>Technical checks · this master</h3><dl><div><dt>Picture</dt><dd>1080 × 1920 · 30 fps</dd></div><div><dt>Duration / frames</dt><dd>${Number(v.video_s).toFixed(2)}s · ${v.frames}</dd></div><div><dt>Voice loudness</dt><dd>${esc(a?.integrated_lufs ?? 'Not measured')} LUFS</dd></div><div><dt>True peak</dt><dd>${esc(a?.true_peak_dbtp ?? 'Not measured')} dBTP</dd></div></dl><small>Technical checks do not establish editorial approval. Review this exact export at normal speed. SHA256: <code>${esc(e.sha256)}</code></small>${Object.entries(t.kit_qc?.gates||{}).map(([k,g])=>`<p>${k} · ${esc(g.name)} <strong>${esc(g.status)}</strong></p>`).join('')}${(t.kit_qc?.issues||[]).map(i=>`<button class="textbtn" data-seek="${i.master_range[0]}">${time(i.master_range[0])} · ${esc(i.id)} · ${esc(String(i.actual))}</button>`).join('')}</section>`;
}
function reviewEvidence(e){
 const d=e.duration,samples=[Math.min(3,d/4),d/2,Math.max(0,d-2)],labels={A:'Opening, payoff and CTA',B:'Visible target, action and readable result',C:'Vietnamese names, numbers and caption timing',D:'Animation purpose and SFX alignment',E:'Intact speech, natural cuts and intelligible mix',F:'Export, captions and reproducible recipe'};
 return `<details class="evidence"><summary>Review observations · required for approval</summary><label>Your name<input id="reviewerName" autocomplete="name" placeholder="Person who watched and listened"></label><label><input id="explicitAttestation" type="checkbox"> I explicitly attest that I watched and listened to this entire exact MP4 at 1× and phone size. My name and decision apply only to this run and SHA256.</label>${Object.entries(labels).map(([k,label])=>`<label>${k} · ${label}<textarea data-qc-note="${k}" rows="2" placeholder="00:12 · What you saw or heard…"></textarea></label>`).join('')}<p>Check lip sync at these moments; enter the observed offset in output frames (0 if aligned).</p>${samples.map((t,i)=>`<label>${time(t)} · lip-sync offset<input type="number" step="any" data-sync-time="${t}" aria-label="Lip-sync offset ${i+1}"></label>`).join('')}${(e.technical?.kit_qc?.measurements?.cue_offsets||[]).map(c=>`<div class="cue-evidence"><strong>${esc(c.id)}</strong><audio controls src="/exports/${e.id}/sfx_stem"></audio><label><input type="checkbox" data-cue-reviewed="${esc(c.id)}"> I checked the isolated effect and final mix at this event.</label><label>Observed offset in frames<input type="number" step="any" data-cue-offset="${esc(c.id)}"></label></div>`).join('')}</details>`;
}
function tab(name) {
  el("work").classList.toggle("hidden", name !== "workspace");
  el("out").classList.toggle("hidden", name !== "exports");
  all("[data-tab]").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === name),
  );
}
function allowChange() {
  return (
    !touched.size || confirm("Discard the unsaved changes in Edit settings?")
  );
}
function changeSelection(ids) {
  if (!allowChange()) {
    drawList();
    return;
  }
  touched.clear();
  selected.clear();
  ids.forEach((x) => selected.add(x));
  versionKey = "";
  draw();
  localStorage.setItem('cutroom-selection:'+state.data_folder,JSON.stringify([...selected]));
}
function refs() {
  return Object.values(state.assets || {}).filter(
    (x) => x.kind === "reference",
  );
}
function options(id, none = true) {
  return (
    (none ? '<option value="">No pacing reference</option>' : "") +
    refs()
      .map(
        (a) =>
          '<option value="' +
          a.id +
          '" ' +
          (a.id === id ? "selected" : "") +
          ">" +
          esc(a.name) +
          "</option>",
      )
      .join("")
  );
}
function showPanel(name) {
  activePanel = name;
  all("[data-panel]").forEach((b) =>
    b.classList.toggle("active", b.dataset.panel === name),
  );
  all("[data-body]").forEach((p) =>
    p.classList.toggle("hidden", p.dataset.body !== name),
  );
}
function setDirty(k) {
  editRevision++;
  touched.add(k);
  el("dirty").textContent = "Unsaved changes";
  el("save").disabled = false;
  if(k==='script')el('generateArtifacts').disabled=!el('script').value.trim();
}
function drawList() {
  const focusRow=document.activeElement?.closest('[data-row]')?.dataset.row;
  const focusCheckbox=document.activeElement?.matches('input[type=checkbox]');
  const allJobs = Object.values(state.jobs || {}),oldCollection=el('sourceCollection').value;
  el('sourceCollection').innerHTML='<option value="">All projects</option>'+[...new Set(allJobs.map(j=>j.collection).filter(Boolean))].sort().map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');el('sourceCollection').value=oldCollection;
  const jobs=visibleSources();
  const ids = selectedIds();
  el("clipCount").textContent = allJobs.length;
  el('topImport').classList.toggle('hidden',!allJobs.length);
  el('topImport').textContent='＋ Add recordings';
  el("emptyDrop").classList.toggle("hidden", !!allJobs.length);
  el("selectAll").disabled = !jobs.length;
  el("selectAll").textContent =
    ids.length === jobs.length && jobs.length
      ? "Clear selection"
      : "Select all";
  el("selectionText").textContent = jobs.length
    ? `${ids.length} selected · ${jobs.length} of ${allJobs.length} sources shown`
    : allJobs.length?"No sources match this view":"No recordings yet";
  el("clips").innerHTML = jobs
    .map((j) => {
      const a = state.assets[j.id];
      return (
        '<div class="clip ' +
        (selected.has(j.id) ? "chosen" : "") +
        '" data-row="' +
        j.id +
        '"><input aria-label="Select ' +
        esc(sourceName(j.id)) +
        '" type="checkbox" ' +
        (selected.has(j.id) ? "checked" : "") +
        ">" +
        thumb(a) +
        '<div class="details"><button class="name clip-name" title="Edit '+esc(a.name)+'">' +
        esc(sourceName(j.id)) +
        '</button><div class="detail">' +
        `Original · Take ${j.take_number||1} · ${j.id.slice(0,8)} · ${versionsFor(j.id).length} cut${versionsFor(j.id).length===1?'':'s'}${j.collection?' · '+esc(j.collection):''}${j.archived?' · Archived':''}<br>`+time(a.duration) +
        " · " +
        (j.script_issue ? esc(j.script_issue) : j.settings.script.trim() ? "Script attached" : "Needs script") +
        (locked(j)||j.status==='Failed' ? " · " + esc(j.stage.slice(0,100)) : "") +
        "</div></div>" +
        status(j.status) + (!j.settings.script.trim()&&!locked(j)?`<button class="textbtn add-script" data-add-script="${j.id}">Add script</button>`:'') +`<button type="button" class="textbtn" data-manage-source="${j.id}">Manage</button>${latestFor(j.id)?`<button type="button" class="textbtn" data-source-cuts="${j.id}">View cuts</button>`:''}`+
        "</div>"
      );
    })
    .join("");
  if(!jobs.length&&allJobs.length)el('clips').innerHTML='<div class="simple-empty">No sources match this view. Try another project, search or archive filter.</div>';
  const downloadable = ids.filter((k) =>
    state.exports.some((e) => e.job === k),
  );
  el("selectedDownload").classList.toggle("hidden", !downloadable.length);
  el("selectedDownload").href =
    "/downloads/latest.zip?jobs=" + encodeURIComponent(downloadable.join(","));
  const ready=ids.filter(k=>!state.jobs[k].archived&&!locked(state.jobs[k])&&state.jobs[k].settings.script.trim()&&!state.jobs[k].script_issue).length;
  el("queue").disabled = !ready || !state.tools;
  el("queue").textContent = `Render ${ready} video${ready===1?'':'s'}`;
  el("queueHint").textContent = jobs.some(locked)
    ? jobs.filter((j) => j.status === "Rendering").length +
      " rendering · " +
      jobs.filter((j) => j.status === "Queued").length +
      " queued"
    : `${ids.length} selected · ${ready} ready · ${ids.length-ready} need input`;
  if(focusRow)document.querySelector(`[data-row="${focusRow}"] ${focusCheckbox?'input':'.clip-name'}`)?.focus({preventScroll:true});
}
function drawInserts() {
  el("insertRows").innerHTML =
    inserts
      .map(
        (r, i) =>
          '<div class="insert" data-insert="' +
          i +
          '"><label>Demo subject (optional)<input data-k="demonstrates" maxlength="140" placeholder="Remotion / Export invoice" value="'+esc(r.demonstrates||'')+'"></label><label>What must be visible<input data-k="visual_claim" maxlength="400" placeholder="Specific control, value or resulting state" value="'+esc(r.visual_claim||'')+'"></label><small>Assignment links this footage to a claim; it still needs review. An illustration cannot prove a software result.</small><select aria-label="Cutaway source" data-k="asset">' +
          options(r.asset, false) +
          `</select><img class="insert-thumb" alt="Cutaway source thumbnail" src="/assets/${r.asset}/thumb"><small>Show in video · presenter audio continues</small><label>Spoken cue (optional)<input data-k="cue" maxlength="240" placeholder="Exact words from this script" value="` +
          esc(r.cue || "") +
          `"></label><button type="button" class="textbtn" data-resolve="${i}">Find phrase in script</button><small>${r.occurrence!=null?'Chosen occurrence '+(r.occurrence+1)+' · ':''}${r.cue&&r.occurrence==null?'At spoken phrase · resolve to inspect timing':'Insertion at '+Number(r.at).toFixed(2)+'s'} · ${Number(r.duration).toFixed(2)}s long · ${esc(el('insert_sound')?.value||'none')} sound</small><div class="times">` +
          [
            ["at", "Starts at (s)"],
            ["offset", "Source in (s)"],
            ["duration", "Length (s)"],
          ]
            .map(
              ([k, l]) =>
                "<label>" +
                l +
                '<input data-k="' +
                k +
                '" type="number" min="0" step="any" value="' +
                Number(r[k]) +
                '"></label>',
            )
            .join("") +
          `</div><label>Layout<select data-k="layout"><option value="full_demo" ${(r.layout||'full_demo')==='full_demo'?'selected':''}>Full demo · original voice</option><option value="presenter_pip" ${r.layout==='presenter_pip'?'selected':''}>Presenter PiP · real recording</option></select></label><label>PiP corner<select data-k="pip_corner">${['auto','top_left','top_right','bottom_left','bottom_right'].map(k=>`<option value="${k}" ${(r.pip_corner||'auto')===k?'selected':''}>${k.replaceAll('_',' ')}</option>`).join('')}</select></label><label>PiP width (canvas fraction)<input data-k="pip_width" type="number" min="0.18" max="0.36" step="0.01" value="${r.pip_width??.25}"></label><small>Auto avoids observed control, result and captions; no safe corner uses full demo. The corner stays fixed for the cutaway.</small>${anchorControls(r)}<button type="button" data-remove="` +
          i +
          '" class="textbtn">Remove</button></div>',
      )
      .join("") || '<small class="simple-empty">No cutaways assigned.</small>';
}
function drawForm() {
  const ids = selectedIds();
  const single = ids.length === 1;
  const active = ids.some((id) => locked(state.jobs[id]));
  el('makeFirstCut').disabled=!ids.length||active;
  drawCreator(ids);
  if(ids.length===1&&state.jobs[ids[0]].creator&&!el('openingAuditions'))el('creatorPanel').insertAdjacentHTML('beforeend',`<div id="openingAuditions"><button class="soft" type="button" data-audition-openings="${ids[0]}">Compare 4-second openings</button><small>Host-first / assigned result-first. Same master audio; body stays fixed. Requires a rendered current cut and real result footage.</small></div>`);
  el("target").textContent = single
    ? 'Editing '+state.assets[ids[0]].name
    : ids.length
      ? 'Editing '+ids.length + " recordings"
      : "Select a recording to edit";
  el("blankInspect").classList.toggle("hidden", ids.length > 0 && !active);
  el("form").classList.toggle("hidden", !ids.length || active);
  el("blankInspect").querySelector("strong").textContent = active
    ? "Rendering in progress"
    : "Your edit controls";
  el("blankInspect").querySelector("p").textContent = active
    ? "You can edit these recordings again when the export finishes."
    : "Select one or more recordings to assign a script, set a style, or add a cutaway.";
  if (!ids.length || active) return;
  const key =
    ids.map((k) => k + ":" + state.jobs[k].revision).join("|") +
    ":" +
    refs().length;
  if (key === versionKey || touched.size) return;
  versionKey = key;
  const first = state.jobs[ids[0]].settings;
  ["script", "style", "fit", "insert_sound", "caption_position"].forEach(
    (k) => {
      el(k).value = first[k];
    },
  );
  el('music_asset').innerHTML='<option value="">Choose a cleared track…</option>'+Object.values(state.assets).filter(a=>a.kind==='music').map(a=>`<option value="${a.id}">${esc(a.name)}</option>`).join('');
  el('brand_logo').innerHTML='<option value="">No logo</option>'+Object.values(state.assets).filter(a=>a.kind==='graphic').map(a=>`<option value="${a.id}">${esc(a.name)}</option>`).join('');
  extraSettings.forEach(k=>{el(k).value=first[k]??({motion_profile:'baseline',motion_intensity:.5,music_mode:'off',music_track:'calm',music_gain_db:-20,music_asset:'',planner_mode:'built_in'}[k]);});
  const planner=state.jobs[ids[0]].planner_receipt;el('plannerStatus').textContent=planner?(planner.origin+' · '+planner.model_version+' · '+(planner.weights_loaded?'weights actually loaded':'no model weights loaded')+(planner.fallback?' · '+planner.fallback:'')):'Built-in rules · no model weights loaded. Pacing references do not automatically enter training.';
  const mixed = (k) =>
    ids.some(
      (id) =>
        JSON.stringify(state.jobs[id].settings[k]) !== JSON.stringify(first[k]),
    );
  if (mixed("script")) {
    el("script").value = "";
    el("script").placeholder =
      "Different scripts selected. Type to replace all selected scripts…";
  } else el("script").placeholder = "Paste what the presenter says…";
  el("style_ref").innerHTML = options(first.style_ref);
  ["style", "fit", "insert_sound", "caption_position", "style_ref",'motion_profile','music_mode','music_track','music_asset','planner_mode'].forEach(
    (k) => {
      const v = el(k);
      v.querySelector('option[value="__mixed"]')?.remove();
      if (mixed(k)) {
        const o = new Option("Mixed values", "__mixed", true, true);
        o.disabled = true;
        v.prepend(o);
        v.value = "__mixed";
      }
    },
  );
  inserts = mixed("inserts") ? [] : structuredClone(first.inserts);
  manualEvents=mixed('events')?[]:structuredClone(first.events||[]);
  drawEvents(mixed('events'));
  el('motion_intensity').setAttribute('aria-label',mixed('motion_intensity')?'Motion intensity · Mixed':'Motion intensity');
  drawInserts();
  el("scriptHelp").textContent =
    ids.length > 1
      ? "Only changed fields apply to all selected clips. Import TXT/SRT files named after each recording to match scripts."
      : "Plain text uses estimated timing. SRT uses your cue times.";
  el("sourceBox").classList.toggle("hidden", !single);
  el("sourceBox").innerHTML = single
    ? '<button type="button" data-play="' +
      ids[0] +
      '">▶ Preview source</button>'
    : "";
  el("save").disabled = true;
  el("dirty").textContent = mixed("inserts")
    ? "Different cutaways selected"
    : "Saved";
  showPanel(activePanel);
  drawFraming();
}
function drawCreator(ids){
 const panel=el('creatorPanel');if(!panel||panel.dataset.jobid===ids[0]&&panel.contains(document.activeElement))return;panel.dataset.jobid=ids[0]||'';
 if(ids.length!==1){panel.innerHTML='';return;}
 const id=ids[0],j=state.jobs[id],c=j.creator,files=refs().filter(a=>(a.owner_jobs||[]).includes(id));
 panel.innerHTML=`<details class="creator-files"><summary>Files for this recording</summary><p>Recording: ${esc(state.assets[id].name)}</p><p>Script: ${j.settings.script.trim()?'attached / editable below':'optional — local captions can read the recording'}</p><p>B-roll: ${files.filter(a=>a.source_role==='broll').map(a=>esc(a.name)).join(', ')||'none assigned'}</p><p>Style reference: ${esc(state.assets[j.settings.style_ref]?.name||'none')}</p><button type="button" id="attachCreatorScript" class="textbtn">Attach a prepared TXT / SRT</button></details>`;
 if(!c){panel.innerHTML+='<p class="notice">Make first cut creates a presenter-only candidate when no usable B-roll is assigned. Your original remains intact.</p>';return;}
 if(c.caption_timing_fallback_ranges?.length)panel.innerHTML+=`<p class="notice">${c.caption_timing_fallback_ranges.length} phrase windows use estimated timing because word timestamps were uncertain. Listen and retime those ranges before release.</p>`;
 const text=c.brief_text||[['Viewer',c.brief.viewer],['Takeaway',c.brief.takeaway],['Language',c.brief.spoken_language],['Opening quote',c.brief.hook?.quote],['Supporting shot',c.brief.supporting_moment],['Ending',c.brief.ending],['Story recipe',c.brief.format_label],['Missing proof',c.brief.format_status]].map(([k,v])=>k+': '+(v||'not assigned')).join('\n');
 panel.innerHTML+=`<details open><summary>Brief &amp; uncertain moments</summary><p>${esc(c.timing)} · ${esc(c.take_selection)}</p>${c.warning?`<p class="notice">${esc(c.warning)}</p>`:''}<label>Editable brief<textarea id="creatorBrief" rows="7">${esc(text)}</textarea></label><button type="button" class="soft" data-save-creator-brief="${id}">Save brief</button><p>Openings are editorial proposals. Recorded words and proof stay authoritative.</p>${c.hooks.map(h=>`<p><strong>${esc(h.kind.replaceAll('_',' '))}</strong>: ${esc(h.quote||'pickup required')} · ${esc(h.reason)}</p>`).join('')}<h3>Check these passages first</h3>${c.uncertain.map(m=>`<p>${time(m.source_range[0])}–${time(m.source_range[1])}: ${esc(m.reason)} <button type="button" class="textbtn" data-preview-passage="${id}" data-from="${m.source_range[0]}" data-to="${m.source_range[1]}">Play source passage</button></p>`).join('')||'<p>No low-confidence recognition flagged. This still needs actual listening.</p>'}<details><summary>Trim ends / restore original take</summary><p>Source time in seconds. Word-boundary guard applies; listen across the cut.</p><label>Keep from<input id="creatorKeepStart" type="number" min="0" step="any" value="${c.keep[0][0]}"></label><label>Keep through<input id="creatorKeepEnd" type="number" min="0" step="any" value="${c.keep.at(-1)[1]}"></label><button class="soft" type="button" data-creator-trim="${id}">Save source cut</button><button class="textbtn" type="button" data-restore-take="${id}">Restore entire take</button></details><h3>Suggested B-roll</h3>${(c.broll_suggestions||[]).map((q,i)=>`<p>${esc(state.assets[q.asset]?.name)} · ${time(q.at)} · ${esc(q.reason)} <button type="button" class="textbtn" data-accept-broll="${id}" data-suggestion="${i}">Assign after checking</button></p>`).join('')||'<p>No confident creator-label match. Presenter retained; label supplied B-roll or place it manually in Cutaways.</p>'}</details>`;
}
function anchorControls(r){
 const coords=(label,key,values,names)=>`<div class="roi-inputs">${names.map((name,j)=>`<label>${label} ${name}<input type="number" min="0" data-anchor-array="${key}" data-coordinate="${j}" value="${values?.[j]??''}"></label>`).join('')}</div>`;
 return `<details class="anchor-controls"><summary>Verified target, contact and result</summary><small>Use source seconds and pixels. Leave unobserved anchors blank.</small>${['target','contact','result'].map(k=>`<label>${k==='target'?'Control recognizable':k==='contact'?'Actual contact':'Success visible'} (source s)<input type="number" min="0" step="any" data-anchor="${k}" value="${r.anchors?.[k]??''}"></label>`).join('')}${coords('Control','roi_source',r.anchors?.roi_source,['x','y','width','height'])}${coords('Success','result_roi_source',r.anchors?.result_roi_source,['x','y','width','height'])}${coords('Contact point','contact_point_source',r.anchors?.contact_point_source,['x','y'])}<details><summary>Source crop · optional</summary><small>Original source pixels. Keep important details in view.</small>${coords('Crop','crop',r.crop,['width','height','x','y'])}</details></details>`;
}
function drawFraming(){
 const id=selectedIds()[0],a=state.assets?.[id];if(!a)return;
 const fit=el('fit').value,position=el('caption_position').value;
 el('framingPreview').innerHTML=`<video aria-label="Source framing preview · sample caption" muted autoplay loop playsinline src="/assets/${id}/media" style="object-fit:${fit==='cover'?'cover':'contain'}"></video><span class="mini-caption ${position}">Biến ý tưởng thành video</span>`;
 el('framingHelp').textContent=fit==='cover'?'Fill portrait frame: the sides of a horizontal recording will be cropped.':'Fit entire picture: keep the full source; unused portrait space is padded.';
 all('[data-style]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.style===el('style').value)));
}
function drawEvents(mixed=false){
 el('eventRows').innerHTML=mixed?'<p>Mixed manual cues. Changing profile, intensity or music preserves each recording’s cues.</p>':manualEvents.map((e,i)=>`<details class="cue-card" data-event="${i}"><summary>${esc(e.kind)} · ${Number(e.anchor?.timeline_source_pts??e.anchor?.source_pts??0).toFixed(2)}s · ${e.sound?.muted?'Silent':esc(e.sound?.id||'No sound')}</summary><label>Effect<select data-event-field="kind">${['speaker','keyword','ui_focus','contact','result','comparison','reframe','chapter'].map(k=>`<option ${k===e.kind?'selected':''}>${k}</option>`).join('')}</select></label><label>Presenter timeline anchor (s)<input type="number" step="any" data-event-field="at" value="${e.anchor?.timeline_source_pts??e.anchor?.source_pts??0}"></label><label>Readable hold (frames)<input type="number" min="1" data-event-field="hold_frames" value="${e.hold_frames||18}"></label><label>Text (optional)<input data-event-field="text" value="${esc(e.text||'')}"></label><label>Sound<select data-sound-field="id"><option value="">Intentional silence</option>${['click','tap','slide','chime_fast','chime','chapter'].map(k=>`<option value="${k}" ${e.sound?.id===k?'selected':''}>${k}</option>`).join('')}</select></label><label><input type="checkbox" data-sound-field="muted" ${e.sound?.muted?'checked':''}> Mute this cue</label><label>Gain (dB)<input type="number" step="1" min="-60" max="6" data-sound-field="gain_db" value="${e.sound?.gain_db??-14}"></label><label>Timing offset (frames)<input type="number" step="any" data-sound-field="offset_frames" value="${e.sound?.offset_frames||0}"></label><label>Reason for intentional offset<input data-sound-field="offset_reason" value="${esc(e.sound?.offset_reason||'')}"></label><details><summary>Advanced target / marker</summary>${['x','y','width','height'].map((k,j)=>`<label>Output ${k}<input type="number" data-event-roi="${j}" value="${e.roi?.[j]??''}"></label>`).join('')}<label>Perceptual marker sample (48 kHz)<input type="number" min="0" data-sound-field="marker_sample" value="${e.sound?.marker_sample??''}"></label><label>Trim audio from sample<input type="number" min="0" data-sound-field="trim_in_samples" value="${e.sound?.trim_in_samples??0}"></label></details>${(e.reference_evidence||[]).map(r=>`<small>Reference ${esc(r.reference_id?.slice(0,10))} · ${r.source_range.map(t=>Number(t).toFixed(2)).join('–')}s · ${esc(r.observation)} (${esc(r.status)})</small>`).join('')}<button type="button" class="textbtn" data-remove-event="${i}">Remove cue</button></details>`).join('')||'<small>No manual cues. Verified cutaway anchors can suggest focus, click and result cues.</small>';
}
function showReferenceAnalysis(id,result){
 state.assets[id].analysis=result;
 dialog('Reference profile · measured candidates',`<p>${esc(state.assets[id].name)} · ${esc(result.analysis)} · ${result.sample_seconds.toFixed(1)}s sampled</p><p>${esc(result.profile.id)} · ${esc(result.profile.origin)} · no trained model</p><p>Music and SFX: ${esc(result.audio.status)} · ${esc(result.audio.reason)}</p>${result.observations.map((o,i)=>`<div class="observation"><strong>${o.source_range.map(t=>Number(t).toFixed(2)).join('–')}s</strong><p>${esc(o.observation)}</p><small>${esc(o.status)} · confidence ${o.confidence} · ${esc(o.limitations||'')}</small><button class="textbtn" data-edit-observation="${i}" data-ref-id="${id}">Correct observation</button></div>`).join('')}<button class="soft" data-full-analysis="${id}">Analyze entire reference</button><small>Style references contribute timing rules and observations; their pictures, voice and music are not copied.</small>`);
}
function draw() {
  const speech=state.speech_setup||{};el('speechBanner').classList.toggle('hidden',speech.status==='READY'||!speech.status);
  el('speechBanner').innerHTML=`<span>${esc(speech.stage||'')}<br><small>${esc(speech.download||'')} · ${esc(speech.destination||'')}</small></span>${speech.status!=='INSTALLING'?'<button type="button" id="setupLocalCaptions" class="soft">Set up local captions</button>':''}`;
  el('graphicCount').textContent=Object.values(state.assets||{}).filter(a=>a.kind==='graphic').length+' local images available for original scenes';
  drawList();
  drawForm();
  drawArtifacts();
  drawGenerative();
  el("refCount").textContent = refs().length;
  el("refs").innerHTML =
    refs()
      .map(
        (a) =>
          '<div class="asset">' +
          thumb(a) +
          '<div class="details"><div class="name">' +
          esc(a.name) +
          '</div><div class="detail">' +
          time(a.duration) +
          " · " +
          a.width +
          " × " +
          a.height +
          '</div></div><button class="textbtn" data-play="' +
          a.id +
          `">Preview</button><div class="ref-actions"><small>${esc(a.source_role==='style_reference'?'Style only · not inserted automatically':a.source_role==='broll'?'Usable B-roll':'Library footage · explicit assignment required')}</small><button class="textbtn" data-describe-footage="${a.id}">Label / assign to recording</button><button class="textbtn" data-analyze="${a.id}">Reference profile</button><button class="textbtn" data-pacing="${a.id}">Use for pacing</button><button class="textbtn" data-show-reference="${a.id}">Show in video</button><button class="textbtn" data-training-intake="${a.id}">Include in training</button></div></div>`,
      )
      .join("") ||
    '<div class="simple-empty">Added footage will be available to every recording in this batch.</div>';
  el("matchRow").classList.toggle("hidden", !refs().length);
  el("matchRefs").disabled = !selectedIds().some(
    (id) => !locked(state.jobs[id]) && state.jobs[id].settings.script.trim(),
  );
  el("exportCount").textContent = state.exports.length;
  el("batchDownload").classList.toggle("hidden", !state.exports.length);
  drawExports();
  el("setupBanner").classList.toggle("hidden", !!state.tools);
  if (!state.tools)
    el("setupBanner").innerHTML =
      "<span>" +
      esc(
        state.setup ||
          "Install the video encoder once to import and render footage.",
      ) +
      '</span><button class="soft" data-setup>Encoder setup</button>';
}
function drawExports(){
 const prior=el('exportSource').value;
 el('exportSource').innerHTML='<option value="">All source recordings</option>'+Object.values(state.jobs||{}).map(j=>`<option value="${j.id}">${esc(sourceName(j.id))} · Take ${j.take_number||1} · ${j.id.slice(0,6)}</option>`).join('');el('exportSource').value=prior;
 const filtered=state.exports.filter(e=>!prior||e.job===prior),allHistory=el('exportHistory').value==='all',shown=filtered.filter(e=>allHistory||latestFor(e.job)?.id===e.id).reverse();
 el('exportSummary').textContent=`${shown.length} ${allHistory?'versions':'latest cuts'} shown · ${filtered.length} versions kept`;
 el('batchDownload').href='/downloads/latest.zip?jobs='+encodeURIComponent([...new Set(shown.map(e=>e.job))].join(','));
 el('outputs').innerHTML=shown.map(e=>`<div class="exportrow"><div class="cut-badge">${cutVersion(e)}<small>${latestFor(e.job)?.id===e.id?'Latest':'Previous'}</small></div>${thumb(state.assets[e.job])}<div class="details"><div class="name">${esc(sourceName(e.job))} · Take ${state.jobs[e.job].take_number||1}</div><div class="detail">Rendered MP4 · ${time(e.duration)} · ${new Date(e.created*1000).toLocaleString()}<br>From ${esc(state.assets[e.job].name)} · source ${e.job.slice(0,8)} · SHA ${e.sha256.slice(0,10)}${state.jobs[e.job].collection?' · '+esc(state.jobs[e.job].collection):''}</div></div><div class="actions">${status({READY:'Approved',REVISE:'Needs revision'}[e.verdict]||'For review')}<button type="button" class="soft" data-hook-review="${e.id}">Hook 0–3s</button><button type="button" class="soft" data-review="${e.id}">Review ${cutVersion(e)}</button><button type="button" class="textbtn" data-locate-source="${e.job}">Go to source</button>${!allHistory&&versionsFor(e.job).length>1?`<button type="button" class="textbtn" data-cut-history="${e.job}">${versionsFor(e.job).length} versions</button>`:''}</div></div>`).join('')||'<div class="outempty"><h2>No exports in this view</h2><p>Choose another source or render a new cut. Previous versions are kept.</p></div>';
}
async function manageSource(id){
 const info=await req('/api/source-info',{id}),j=state.jobs[id],latest=latestFor(id),family=j.source_family||id;
 dialog('Manage original · Take '+(j.take_number||1),`<div class="source-manager"><video controls src="/assets/${id}/media"></video><section><strong>Original recording</strong><p>${esc(info.original_name)}</p><small>Source ${id.slice(0,8)} · family ${family.slice(0,8)}<br>SHA256 ${esc(info.sha256)}</small><label>Display name<input id="sourceLabel" maxlength="100" value="${esc(j.label||'')}" placeholder="${esc(info.original_name)}"></label><label>Project / folder<input id="sourceProject" maxlength="80" value="${esc(j.collection||'')}" placeholder="e.g. 5 repo GitHub"></label><p class="local-path">Local original: ${esc(info.local_copy)}</p><button type="button" class="textbtn" data-reveal="source" data-local-id="${id}">Show original in Explorer</button><div class="dialogactions"><button type="button" class="primary" data-save-source="${id}">Save organization</button><button type="button" class="soft" data-new-take="${id}">Add new take</button><button type="button" class="textbtn" data-archive-source="${id}">${j.archived?'Restore source':'Archive source'}</button></div><small>Archive hides the source; it keeps the original, scenes and every export. A new take keeps style, starts with its own script/timing, and does not replace this recording.</small>${latest?`<p>Newest rendered cut: ${cutVersion(latest)} · ${esc(latest.verdict)} <button type="button" class="soft" data-source-cuts="${id}">View cuts</button></p>`:'<p>No rendered cut yet.</p>'}</section></div>${j.reference_script?`<details><summary>Previous take’s script · reference only</summary><textarea readonly rows="7">${esc(j.reference_script)}</textarea><small>Not applied. Compare with the new voice and realign captions before rendering.</small></details>`:''}`);
}
function drawArtifacts(){
 const ids=selectedIds();el('generateArtifacts').disabled=!ids.length||ids.some(id=>locked(state.jobs[id])||(state.scene_generating||[]).includes(id))||!ids.every(id=>state.jobs[id].settings.script.trim());
 el('transcribeRecording').disabled=ids.length!==1||ids.some(id=>locked(state.jobs[id]));
 el('animationModelStatus').textContent=state.animation_model?`Experimental spec adapter · ${state.animation_model.actual_optimizer_steps} optimizer steps · SHA ${state.animation_model.checkpoint_sha256.slice(0,12)} · choose per generation; not production-approved${state.animation_model.training_style_counts?` · training labels: ${Object.entries(state.animation_model.training_style_counts).map(([name,count])=>`${name} ${count}`).join(', ')}`:''}${state.animation_model.provenance_warnings?.length?' · Style metadata differs from the training labels; fidelity unverified.':''}`:'No animation-spec adapter installed. Native rules and existing scenes remain available.';
 const records=Object.values(state.artifacts||{}).filter(r=>ids.includes(r.job));
 el('storyboard').innerHTML=ids.length===1?(state.storyboards?.[ids[0]]?.passages||[]).map(p=>`<details class="passage"><summary>${time(p.start)} · Passage ${esc(p.id.slice(-6))} · occurrence ${p.occurrence+1}</summary><p>${esc(p.quote)}</p><small>${esc(p.timing)} · ${p.start.toFixed(2)}–${p.end.toFixed(2)}s</small></details>`).join(''):'';
 el('artifactCards').innerHTML=records.map(r=>`<article class="artifact-card"><div class="artifact-heading"><img src="/artifacts/${r.id}/thumb?v=${r.version}" alt="${esc(r.plan.type)} thumbnail"><div><small>${r.plan.type==='introduction'?'Introduction':'Demo'} · v${String(r.version).padStart(3,'0')}</small><strong>${esc(r.plan.title)}</strong><span>${r.plan.duration.toFixed(1)}s · ${r.plan.enabled?'':'Disabled · '}${esc(r.status)}</span></div></div><blockquote>${esc(r.plan.source_quote)}</blockquote><small>${esc(r.plan.intended_visual)} · ${esc(r.plan.timing)}</small><div class="artifact-actions"><button type="button" class="soft" data-artifact-preview="${r.id}">Preview</button><button type="button" class="textbtn" data-artifact-edit="${r.id}">Edit</button><button type="button" class="textbtn" data-artifact-regenerate="${r.id}">Regenerate this scene</button><button type="button" class="textbtn" data-artifact-toggle="${r.id}">${r.plan.enabled?'Disable':'Enable'}</button><button type="button" class="textbtn" data-artifact-insert="${r.id}">${r.inserted?'Remove from episode':'Insert in episode'}</button><a class="link" download href="/artifacts/${r.id}/preview?download=1">Export MP4</a></div></article>`).join('');
 drawAnimationLibrary();
}
function drawAnimationLibrary(){
 el('animationLibrary').innerHTML=Object.values(state.animation_library||{}).map(r=>`<article class="cue-card"><strong>${esc(r.title)}</strong><small>${esc(r.kind||'native_spec')} · ${esc(r.status)} · silent preview</small><button type="button" class="soft" data-animation-preview="${r.id}">Preview / inspect</button>${r.kind==='reference_excerpt'?`<button type="button" class="textbtn" data-animation-import="${r.id}">Add as illustration</button>`:`<button type="button" class="textbtn" data-animation-adapt="${r.id}">Adapt to a current scene</button>`}<button type="button" class="textbtn" data-reveal="animation" data-local-id="${r.id}">Show in animations folder</button></article>`).join('')||'<small>No saved animations yet. Native templates keep editable specs; reference clips retain baked pixels. New episodes need their own narration and proof.</small>';
 all('[data-artifact-edit]').forEach(b=>{const r=state.artifacts[b.dataset.artifactEdit];if(r?.plan.kind==='animation_spec'){const button=document.createElement('button');button.type='button';button.className='textbtn';button.dataset.animationSaveScene=r.id;button.textContent='Save to animations';b.parentElement.appendChild(button);}});
}
function drawGenerative(){
 const runs=Object.values(state.generative_runs||{}),trained=runs.filter(r=>r.receipt.task==='video_diffusion_lora');el('generateIllustration').disabled=!trained.length;
 el('generativeRuns').innerHTML=runs.map(r=>`<article class="cue-card"><strong>${esc(r.receipt.base_model||'CogVideoX candidate')}</strong><small>${r.receipt.task==='video_diffusion_lora'?r.receipt.actual_optimizer_steps+' actual optimizer steps':'Kaggle generation · adapter loaded: '+Boolean(r.receipt.weights_loaded)} · ${esc(r.status)}<br>Run ${r.id.slice(0,8)} · source ${esc(r.source_kernel||'Imported receipt')}</small>${(r.receipt.outputs||[]).map((v,i)=>`<div class="dialogactions"><button type="button" class="textbtn" data-generated-preview="${r.id}" data-generated-index="${i}">${esc(v.label)} · Preview ${i+1}</button>${v.label==='candidate'?`<button type="button" class="soft" data-generated-scene="${r.id}" data-generated-index="${i}">Create illustration scene</button>`:''}</div>`).join('')}</article>`).join('')||'<small>No generative model result imported. Built-in animations remain available.</small>';
 el('generativeJobs').innerHTML=Object.values(state.generative_jobs||{}).map(j=>`<article class="cue-card"><strong>${esc(j.status)}</strong><p>${esc(j.prompt)}</p><small>Private Kaggle · prompt only · seed ${j.seed}</small><button type="button" class="soft" data-generative-check="${j.id}">Refresh generation</button></article>`).join('');
}
function artifactEditor(id){
 const r=state.artifacts[id],p=r.plan,parts=state.storyboards?.[r.job]?.passages||[];
 if(p.kind==='animation_spec'){
  dialog('Edit animation spec',`<p>${esc(p.source_quote)}</p><small>${esc(p.status)} · ${esc(p.animation.model.mode)} · ${esc(p.animation.model.checkpoint_sha256||'rules; no weights')}</small>${p.animation.spec.objects.map((o,i)=>`<details open><summary>${esc(o.id)} · source ${esc(o.anchor)}</summary>${motionBackgroundControls(o,i)}${o.text!==undefined?`<label>Visible text<textarea rows="2" data-motion-text="${i}">${esc(o.text)}</textarea></label><label>Font size<input type="number" data-motion-font="${i}" min="38" max="92" value="${o.font_size}"></label>`:''}<div class="roi-inputs">${['x','y','width','height'].map((k,j)=>`<label>${k} (0–1)<input type="number" min="0" max="1" step="0.01" data-motion-rect="${i}" data-coordinate="${j}" value="${o.rect[j]}"></label>`).join('')}</div><label>Entrance (frames)<input type="number" min="${Math.max(1,o.keyframes.length-1)}" max="60" data-motion-entrance="${i}" value="${o.keyframes.at(-1).frame}"></label>${o.text!==undefined?`<label>Entrance tilt (°)<input type="number" min="0" max="45" step="0.5" data-motion-tilt="${i}" value="${Math.max(...o.keyframes.map(k=>Math.abs(k.rotation||0)))}"></label>`:''}<label>Readable hold (frames)<input type="number" min="12" max="180" data-motion-hold="${i}" value="${o.hold_frames}"></label>${motionReplacementControls(o,i)}</details>`).join('')}${(p.animation.spec.sfx||[]).map((s,i)=>`<div class="scene-controls"><label><input type="checkbox" data-motion-sound="${i}" checked> ${esc(s.id)} · ${esc(s.anchor)}</label><label>Gain dB<input type="number" min="-60" max="-6" data-motion-gain="${i}" value="${s.gain_db??-26}"></label></div>`).join('')}<label>Save edits from<select id="motionEditMode"><option value="controls">Controls above</option><option value="json">Advanced JSON below</option></select></label><details><summary>Advanced · source anchors, replacement states and keyframes</summary><textarea id="motionSpecEditor" rows="18">${esc(JSON.stringify(p.animation,null,2))}</textarea></details><p>Music remains independent in Style. Manual specifications survive preview regeneration.</p><button type="button" class="primary" data-save-motion="${id}" ${r.locked?'disabled':''}>Save new scene version</button><button type="button" class="soft" data-motion-lock="${id}">${r.locked?'Unlock scene':'Lock scene'}</button>`);return;
 }
 dialog('Edit '+(p.type==='introduction'?'introduction':'demo'),`<label>Wording<input id="sceneTitle" value="${esc(p.title)}"></label><label>Spoken passage<select id="scenePassage">${parts.map(s=>`<option value="${s.id}" ${p.passage_ids.includes(s.id)?'selected':''}>${esc(s.quote)} · occurrence ${s.occurrence+1}</option>`).join('')}</select></label><small>${esc(p.timing)}. This is not a claim of successful speech alignment.</small><div class="scene-controls"><label>Duration (s)<input type="number" id="sceneDuration" min="0.5" max="30" step="any" value="${p.duration}"></label><label>Insert at (s)<input type="number" id="sceneAt" min="0" step="any" value="${p.at}"></label></div><label>Position<select id="scenePosition">${['top','center','bottom'].map(k=>`<option ${k===p.position?'selected':''}>${k}</option>`).join('')}</select></label><label>Motion intensity<input id="sceneIntensity" type="range" min="0" max="1" step="0.05" value="${p.intensity}"></label><label>Sound<select id="sceneSound"><option value="none" ${p.sound==='none'?'selected':''}>Off · intentional silence</option><option value="click+chime" ${p.sound!=='none'?'selected':''}>Click on contact · chime on result</option></select></label>${['contact','result'].map(key=>`<details><summary>${key==='contact'?'Contact click':'Success chime'} overrides</summary><label><input id="sceneMute-${key}" type="checkbox" ${p.sounds?.[key]?.muted?'checked':''}> Mute</label><label>Gain (dB)<input id="sceneGain-${key}" type="number" min="-60" max="6" value="${p.sounds?.[key]?.gain_db??-14}"></label><label>Offset (frames)<input id="sceneOffset-${key}" type="number" value="${p.sounds?.[key]?.offset_frames??0}"></label></details>`).join('')}${designFields(p.design)}${evidenceFields(p.evidence)}<button type="button" class="primary" data-save-scene="${id}">Save new scene version</button><p>Other scenes, their versions and manual edits remain unchanged.</p>`);
}
function evidenceFields(e){
 const choices=refs().map(a=>`<option value="${a.id}" ${e?.asset===a.id?'selected':''}>${esc(a.name)}</option>`).join('');
 const arrayField=(key,label,names)=>`<div class="roi-inputs">${names.map((name,i)=>`<label>${label} ${name}<input data-scene-evidence-array="${key}" data-coordinate="${i}" type="number" min="0" value="${e?.[key]?.[i]??''}"></label>`).join('')}</div>`;
 const scope=`<label>Repository for this proof · multi-repo episode only<select id="sceneEvidenceRepo"><option value="">Single demo / no multi-repo assignment</option>${['FFmpeg Skill','Recordly','Remotion','fal','Runway'].map(repo=>`<option ${e?.for_repo===repo?'selected':''}>${repo}</option>`).join('')}</select></label>`;
 return `<details class="scene-evidence"><summary>Actual proof and source anchors · optional</summary><label>On-screen proof (not pacing)<select id="sceneEvidence"><option value="">No proof · keep capture placeholder</option>${choices}</select></label>${scope}<small>Enter only observed source times. Export completion and opening the file are separate events.</small>${['target','contact','result','opened','crop_start','crop_end'].map(k=>`<label>${({target:'Control recognizable',contact:'Actual contact',result:'Export completed',opened:'Exported file opened',crop_start:'Start close-up',crop_end:'End close-up'})[k]} (source s)<input data-scene-evidence="${k}" type="number" min="0" step="any" value="${e?.[k]??''}"></label>`).join('')}${arrayField('target_roi','Control',['x','y','width','height'])}${arrayField('result_roi','Success',['x','y','width','height'])}${arrayField('contact_point','Contact',['x','y'])}${arrayField('crop','Close-up crop',['width','height','x','y'])}${arrayField('result_crop','Opened-file crop',['width','height','x','y'])}</details>`;
}
function readSceneEvidence(){
 const asset=el('sceneEvidence')?.value;if(!asset)return null;
 const result={asset};all('[data-scene-evidence]').filter(x=>x.value!=='').forEach(x=>result[x.dataset.sceneEvidence]=Number(x.value));
 if(el('sceneEvidenceRepo')?.value)result.for_repo=el('sceneEvidenceRepo').value;
 for(const key of new Set(all('[data-scene-evidence-array]').map(x=>x.dataset.sceneEvidenceArray))){const inputs=all(`[data-scene-evidence-array="${key}"]`);if(inputs.every(x=>x.value!==''))result[key]=inputs.map(x=>Number(x.value));}
 return result;
}
function sourceObservationFields(){
 const ids=selectedIds();if(ids.length!==1)return '<p>Review source observations on each recording separately. Saved regions remain specific to their own take.</p>';
 const id=ids[0],j=state.jobs[id],a=state.assets[id],saved=state.presenter_observations?.[id],ref=state.assets[j.settings.style_ref],reviewed=ref?state.reference_observations?.[ref.id]:null,rect=saved?.rect||[.1,.15,.8,.4];
 const range=(key,values)=>`<div class="roi-inputs">${['From','To'].map((label,i)=>`<label>${label} · source seconds<input type="number" min="0" step="any" data-observation-range="${key}" data-coordinate="${i}" value="${values[i]}"></label>`).join('')}</div>`;
 return `<details><summary>Checked source observations · optional</summary><p>A source region belongs to this take and framing. Inspect the face throughout the stated interval; this does not approve an exported master or verify audio.</p><label>Observer<input id="sourceObserver" maxlength="100" value="${esc(saved?.reviewer||reviewed?.reviewer||'')}"></label><label>Observation basis<select id="sourceObservationBasis"><option value="operator_observation">Operator observation</option><option value="agent_experimental" ${(saved?.basis||reviewed?.basis)==='agent_experimental'?'selected':''}>Agent experiment · visual frames</option></select></label><label><input id="observePresenter" type="checkbox"> Use/update a checked presenter face region for this intro</label><small>${saved?'Saved region is available for this take.':'Without a checked observation, a conservative assumed region is used.'} Source ${esc(a.source_sha256?.slice(0,12)||'')} · ${esc(j.settings.fit)}. The region is for static framing; punch-ins require a separate check.</small>${range('presenter',saved?.source_range||[0,Math.min(3,a.duration)])}<div class="source-region-preview"><video controls muted playsinline src="/assets/${id}/media#t=${(saved?.source_range||[0])[0]}" style="object-fit:${j.settings.fit==='cover'?'cover':'contain'}"></video><svg viewBox="0 0 1 1" preserveAspectRatio="none" aria-hidden="true"><rect id="observedFaceBox" x="${rect[0]}" y="${rect[1]}" width="${rect[2]}" height="${rect[3]}"/></svg></div><div class="roi-inputs">${['x','y','width','height'].map((label,i)=>`<label>${label} (0–1)<input type="number" min="0" max="1" step="0.005" data-observed-face="${i}" value="${rect[i]}"></label>`).join('')}</div><label>Observed frames and scope<textarea id="presenterObservationNotes" maxlength="900" rows="3">${esc(saved?.notes||'')}</textarea></label>${ref?`<label><input id="observeReference" type="checkbox"> Add/update checked visual observations of ${esc(ref.name)}</label><small>Measured cut candidates remain candidates. Describe visible treatment; do not infer music/SFX from a silent frame. Source ${esc(ref.source_sha256?.slice(0,12)||'')}.</small>${range('reference',reviewed?.source_range||[0,Math.min(8,ref.duration)])}<video class="reference-observation-preview" controls muted playsinline src="/assets/${ref.id}/media#t=${(reviewed?.source_range||[0])[0]}"></video><label>Reference visual observations<textarea id="referenceObservationNotes" maxlength="900" rows="3">${esc(reviewed?.notes||'')}</textarea></label>`:'<p>Assign this recording’s style reference to record reference observations.</p>'}</details>`;
}
function readSourceObservations(){
 const ids=selectedIds();if(ids.length!==1)return null;
 const id=ids[0],j=state.jobs[id],result={};
 function observation(key,asset,notes){return {asset:asset.id,source_sha256:asset.source_sha256,source_range:all(`[data-observation-range="${key}"]`).map(x=>Number(x.value)),reviewer:el('sourceObserver').value,basis:el('sourceObservationBasis').value,notes};}
 if(el('observePresenter')?.checked)result.presenter={...observation('presenter',state.assets[id],el('presenterObservationNotes').value),rect:all('[data-observed-face]').map(x=>Number(x.value)),fit:j.settings.fit};
 if(el('observeReference')?.checked)result.reference=observation('reference',state.assets[j.settings.style_ref],el('referenceObservationNotes').value);
 return Object.keys(result).length?result:null;
}
function designFields(d={}){const choices=(key)=>Object.values(state.assets||{}).filter(a=>a.kind==='graphic').map(a=>`<option value="${a.id}" ${d[key]===a.id?'selected':''}>${esc(a.name)}</option>`).join('');return `<details><summary>Branding / supplied comparison images · optional</summary><label>Brand accent<input id="sceneBrandColor" type="color" value="${esc(d.color||'#173a2c')}"></label>${['logo','before','after'].map(k=>`<label>${k}<select id="sceneDesign-${k}"><option value="">None</option>${choices(k)}</select></label>`).join('')}<small>A before/after pair stays labeled and uses the same fit. Images are local; no third-party assets are downloaded.</small></details>`;}
function readSceneDesign(){const result={color:el('sceneBrandColor')?.value||'#173a2c'};for(const k of ['logo','before','after'])if(el('sceneDesign-'+k)?.value)result[k]=el('sceneDesign-'+k).value;return result;}
async function refresh() {
  const initial=!state.jobs;
  state = await req("/api/state");
  if(initial){try{JSON.parse(localStorage.getItem('cutroom-selection:'+state.data_folder)||'[]').filter(id=>state.jobs[id]).forEach(id=>selected.add(id));}catch{}}
  unresolvedScripts=state.script_inbox||[];
  if(unresolvedScripts.length){el('scriptResults').classList.remove('hidden');el('scriptResults').innerHTML=`<span>${unresolvedScripts.length} scripts need assignment</span><button class="textbtn" id="resolveScripts">Resolve assignments</button>`;}
  if(initial){try{const saved=JSON.parse(sessionStorage.getItem('cutroom-active-turn:'+state.data_folder)||'null');if(saved){const t=state.editing_conversations?.[saved.conversation]?.turns.find(t=>t.id===saved.turn&&t.status==='OPEN');if(t){activeConversationId=saved.conversation;activeEditorTurn=saved.turn;}}}catch{}}
  draw();
  el('editingTurnStatus').textContent=activeEditorTurn?'Editing request active · '+activeEditorTurn.slice(0,8):'Request history records your tools and changes; it does not approve a master.';
}
async function save() {
  if (!touched.size) return;
  const savingRevision=editRevision;
  const changes = {};
  for (const k of touched) changes[k] = k === "inserts" ? inserts : k==='events'?manualEvents:['motion_intensity','music_gain_db','brand_from','brand_to'].includes(k)?Number(el(k).value):el(k).value;
  await req("/api/update", { ids: selectedIds(), changes });
  if(editRevision!==savingRevision){notify('Earlier settings saved. Newer edits are still unsaved.');return;}
  touched.clear();
  versionKey = "";
  await refresh();
  notify("Edit settings saved");
}
async function upload(files, kind, parentSource='',role='') {
  if (!files.length) return;
  if (importing) throw Error("Wait for the current import to finish.");
  if (!allowChange()) return;
  importing = true;
  const ids = [],
    errors = [];
  el("importState").classList.remove("hidden");
  try {
    for (const [i, f] of [...files].entries()) {
      el("importState").textContent =
        "Importing " + (i + 1) + " of " + files.length + " · " + f.name;
      try {
        const res = await req(
          "/api/import?kind=" + kind + "&name=" + encodeURIComponent(f.name)+(kind==='host'?'&collection='+encodeURIComponent(el('sourceCollection').value)+(parentSource?'&parent_source='+encodeURIComponent(parentSource):''):'')+(role?'&role='+encodeURIComponent(role)+'&owners='+encodeURIComponent(selectedIds().join(',')):''),
          f,
          true,
        );
        ids.push(res.id);
      } catch (e) {
        errors.push(f.name + ": " + e.message);
      }
    }
    touched.clear();
    if (kind === "host" && ids.length) {
      el('sourceSearch').value='';el('sourceVisibility').value='active';
      selected.clear();
      ids.forEach((id) => selected.add(id));
      localStorage.setItem('cutroom-selection:'+state.data_folder,JSON.stringify([...selected]));
    }
    versionKey = "";
    await refresh();
    if(kind==='reference'&&role==='style_reference'&&ids.length&&selectedIds().length){await req('/api/update',{ids:selectedIds(),changes:{style_ref:ids[0]}});versionKey='';await refresh();}
    if(kind==='music'&&ids.length){el('modal').close();el('music_asset').value=ids[0];el('music_mode').value='my_track';setDirty('music_asset');setDirty('music_mode');showPanel('look');}
    if (errors.length)
      dialog("Import results", "<p>" + esc(errors.join(" · ")) + "</p>");
    else
      notify(
        "Imported " + ids.length + " file" + (ids.length === 1 ? "" : "s"),
      );
  } finally {
    importing = false;
    el("importState").classList.add("hidden");
  }
}
async function importScripts(files) {
  if (!files.length || !selectedIds().length) return;
  if (!allowChange()) return;
  const result=await req('/api/scripts',{ids:selectedIds(),scripts:await Promise.all([...files].map(async f=>({name:f.name,text:await f.text()})))});
  unresolvedScripts=result.unresolved;
  touched.clear();
  versionKey = "";
  await refresh();
  const summary=`${result.matched} scripts matched · ${unresolvedScripts.length} need assignment`;
  el('scriptResults').classList.remove('hidden');el('scriptResults').innerHTML=`<span>${summary}</span>${unresolvedScripts.length?'<button class="textbtn" id="resolveScripts">Resolve assignments</button>':''}`;
  notify(summary);
}
function setup() {
  dialog(
    "Workspace settings",
    "<h3>Video encoder</h3><p>" +
      esc(
        state.tools
          ? "FFmpeg and FFprobe are available."
          : state.setup ||
              "Install FFmpeg and FFprobe once to process your videos locally.",
      ) +
      '</p><div class="dialogactions">' +
      (!state.tools && state.platform === "nt"
        ? '<button id="install" class="primary">Download local FFmpeg (~104MB)</button>'
        : "") +
      '<button id="recheck" class="soft">Check again</button></div><h3>Local files</h3><p>Recordings, scripts and exports are stored on this computer. Closing the tab leaves active renders running.</p><div class="dialogactions"><button id="quit" class="soft">Quit Talking Head Cutroom</button></div>',
  );
}
document.addEventListener(
  "click",
  guard(async (e) => {
    const b = e.target.closest("button,input,[data-row],a");
    if (!b) return;
    if(b.id==='componentInventory'){const c=await req('/api/components');dialog('Component inventory',`<p>${c.specified} specified · ${c.render_tested} render-tested · ${c.editorially_approved} editorially approved for delivery.</p><p>Render tests do not replace reviewing this episode’s exact master.</p>${c.components.map(r=>`<p><strong>${r.id} · ${esc(r.name)}</strong><br><small>v${esc(r.version)} · ${r.render_tested?'Render-tested variant':'Specified / separate validation needed'} · ${esc(r.limitation)}</small></p>`).join('')}`);return;}
    if(b.id==='importGenerative'){dialog('Import generative run',`<p>Compact ZIP: one completed provenance receipt, adapter and matching MP4 previews. This does not activate an edit-selector adapter or approve the video.</p><label>Private Kaggle kernel · optional, required for new prompts<input id="generativeKernel" placeholder="owner/kernel-slug/version"></label><button type="button" id="chooseGenerativeZip" class="primary">Choose result ZIP</button>`);return;}
    if(b.id==='chooseGenerativeZip'){el('generativePackageInput').click();return;}
    if(b.dataset.generatedPreview){const r=state.generative_runs[b.dataset.generatedPreview],i=Number(b.dataset.generatedIndex),v=r.receipt.outputs[i];dialog('AI illustration · '+v.label,`<video controls src="/generated/${r.id}/${i}"></video><p>${esc(v.prompt)}</p><small>Generated illustration; not proof of a real software action. Seed ${v.seed} · SHA ${esc(v.sha256)}</small>`);return;}
    if(b.dataset.generatedScene){if(selectedIds().length!==1)throw Error('Select one recording and its own script first.');await save();const job=selectedIds()[0],r=state.generative_runs[b.dataset.generatedScene],v=r.receipt.outputs[Number(b.dataset.generatedIndex)],data=await req('/api/generative-passages',{id:job});dialog('Attach illustration to spoken passage',`<p>Keep your recorded voice. Generated imagery cannot replace a promised software demo.</p><label>Source passage<select id="generatedPassage">${data.passages.map(p=>`<option value="${p.id}" data-start="${p.start}">${esc(p.quote)} · occurrence ${p.occurrence+1}</option>`).join('')}</select></label><small>${esc(data.timing)} · spoken synchronization remains unverified.</small><label>Title<input id="generatedTitle" value="Minh họa ý tưởng"></label><label>Insert at (s)<input id="generatedAt" type="number" min="0" step="any" value="${data.passages[0].start}"></label><button type="button" class="primary" data-create-generated="${r.id}" data-video="${esc(v.file)}" data-job="${job}">Create editable scene</button>`);return;}
    if(b.dataset.createGenerated){b.disabled=true;try{await req('/api/generative-scene',{run:b.dataset.createGenerated,video:b.dataset.video,job:b.dataset.job,passage:el('generatedPassage').value,at:Number(el('generatedAt').value),title:el('generatedTitle').value});el('modal').close();await refresh();notify('Illustration scene created. Preview and insert it explicitly; narration/music stay on the episode buses.');}finally{b.disabled=false;}return;}
    if(b.id==='generateIllustration'){const runs=Object.values(state.generative_runs||{}).filter(r=>r.receipt.task==='video_diffusion_lora');dialog('Generate illustration on Kaggle',`<p>Sends only the prompt below and seed to your private Kaggle GPU. No recording or narration is uploaded. Requires your configured Kaggle account/quota; generation may take several minutes. Output remains experimental.</p><label>Generative adapter<select id="generativeModel">${runs.map(r=>`<option value="${r.id}">${esc(r.receipt.base_model)} · ${r.id.slice(0,8)} · ${r.receipt.actual_optimizer_steps} steps</option>`).join('')}</select></label><label>Exact prompt<textarea id="generativePrompt" rows="5">THCUTROOM explainer animation, three rounded floating cards align on an ivory background, ultramarine and lime accents, smooth motion, no words or people.</textarea></label><label>Seed<input id="generativeSeed" type="number" min="0" value="3407"></label><button type="button" id="submitGenerative" class="primary">Generate private illustration</button>`);return;}
    if(b.id==='submitGenerative'){b.disabled=true;try{await req('/api/generative-submit',{run:el('generativeModel').value,prompt:el('generativePrompt').value,seed:Number(el('generativeSeed').value)});el('modal').close();await refresh();notify('Private Kaggle job submitted. Use Refresh generation to retrieve its actual status and result.');}finally{b.disabled=false;}return;}
    if(b.dataset.generativeCheck){b.disabled=true;try{await req('/api/generative-check',{id:b.dataset.generativeCheck});await refresh();}finally{b.disabled=false;}return;}
    if(b.dataset.manageSource){await manageSource(b.dataset.manageSource);return;}
    if(b.dataset.saveSource){await req('/api/source-organize',{id:b.dataset.saveSource,label:el('sourceLabel').value,collection:el('sourceProject').value});el('modal').close();versionKey='';await refresh();return;}
    if(b.dataset.archiveSource){const id=b.dataset.archiveSource,restore=state.jobs[id].archived;await req('/api/source-organize',{id,archived:!restore});selected.delete(id);el('modal').close();if(restore)el('sourceVisibility').value='active';await refresh();notify(restore?'Source restored.':'Source archived. Original files and exports were kept.');return;}
    if(b.dataset.sourceCuts||b.dataset.cutHistory){const id=b.dataset.sourceCuts||b.dataset.cutHistory;el('modal').close();el('exportSource').value=id;el('exportHistory').value=b.dataset.cutHistory?'all':'latest';tab('exports');drawExports();return;}
    if(b.dataset.locateSource){el('sourceSearch').value='';el('sourceCollection').value='';el('sourceVisibility').value=state.jobs[b.dataset.locateSource].archived?'archived':'active';tab('workspace');changeSelection([b.dataset.locateSource]);return;}
    if(b.dataset.newTake){pendingTakeParent=b.dataset.newTake;el('hostInput').multiple=false;el('hostInput').click();el('modal').close();notify('New take keeps the original and prior cuts. Add this take’s own script and timing.');return;}
    if(b.dataset.reveal){await req('/api/reveal',{kind:b.dataset.reveal,id:b.dataset.localId});return;}
    if(b.id==='makeFirstCut'){
      await save();const j=state.jobs[selectedIds()[0]],mixedNiche=selectedIds().some(id=>state.jobs[id].settings.niche!==j.settings.niche),mixedFormat=selectedIds().some(id=>state.jobs[id].settings.story_format!==j.settings.story_format),niche=mixedNiche?'':j.settings.niche||'',format=mixedFormat?'':j.settings.story_format||'auto';
      dialog('Make first cut',`<p>Use the real recorded voice. Prepared scripts, B-roll and style references are optional. Ambiguous takes remain for review. Unchanged fields keep each recording’s own choices.</p><label>Your niche · optional<input id="creatorNiche" maxlength="500" data-original="${esc(niche)}" value="${esc(niche)}" placeholder="e.g. retail, hospitality, WordPress tutorials…"></label><label>Story recipe<select id="creatorFormat" data-original="${esc(format)}">${[...(mixedFormat?[['','Keep each recording’s recipe']]:[]),['auto','Choose from available evidence'],['result-first','Result first'],['mistake-fix','Mistake → fix'],['before-after','Before / after'],['a-b','Two options'],['myth-check','Check a belief'],['checklist','Checklist'],['viewer-question','Answer a viewer'],['challenge','Challenge'],['teardown','Teardown'],['mini-case','Mini case']].map(([id,label])=>`<option value="${id}" ${format===id?'selected':''}>${label}</option>`).join('')}</select></label><p>A recipe requiring missing proof keeps the presenter and names the pickup. Visual style stays independent.</p><button id="startFirstCut" class="primary" type="button">Make reviewable cut</button>`);return;
    }
    if(b.id==='startFirstCut'){
      b.disabled=true;try{const r=await req('/api/creator/first-cut',{ids:selectedIds(),niche:el('creatorNiche').value===el('creatorNiche').dataset.original?undefined:el('creatorNiche').value,story_format:el('creatorFormat').value===el('creatorFormat').dataset.original?undefined:el('creatorFormat').value});
       if(r.setup_required){dialog('Local captions · first use',`<p>${esc(r.speech_setup.download)}</p><p>Destination: ${esc(r.speech_setup.destination)}</p><p>Only model/dependency files are downloaded. Your recording stays local. Future runs use the cache offline.</p><button type="button" id="setupLocalCaptions" class="primary">Download local captions</button><button type="button" id="attachCreatorScript" class="soft">Use a prepared TXT / SRT instead</button>`);}
       else{el('modal').close();versionKey='';await refresh();notify(`First cut queued: ${r.queued}. Uncertain words and proof stay pending.`);}
      }finally{b.disabled=false;}return;
    }
    if(b.id==='setupLocalCaptions'){await req('/api/creator/setup',{});el('modal').close();await refresh();notify('Local captions setup started. Progress appears above the recordings.');return;}
    if(b.id==='attachCreatorScript'){if(selectedIds().length!==1)throw Error('Select one recording to attach its prepared script.');el('creatorScriptInput').click();return;}
    if(b.dataset.saveCreatorBrief){const id=b.dataset.saveCreatorBrief;await req('/api/creator/brief',{id,revision:state.jobs[id].revision,text:el('creatorBrief').value});versionKey='';await refresh();notify('Brief saved; render a new cut for review.');return;}
    if(b.dataset.auditionOpenings){b.disabled=true;try{const r=await req('/api/creator/openings',{id:b.dataset.auditionOpenings});dialog('Opening audition · same audio',`<p>Only ${r.duration}s rendered. Original narration and body are fixed. Editorial choice; audience performance is not established.</p><div class="review-grid">${[['host','Host first','host_first'],['proof','Assigned result first','proof_first']].map(([key,label,mode])=>`<section><h3>${label}</h3><video controls width="360" src="/openings/${r.id}/${key}"></video><button class="soft" data-opening-choice="${mode}" data-audition="${r.id}">Choose ${label.toLowerCase()}</button></section>`).join('')}</div><a href="/openings/${r.id}/receipt" download>Source timecodes &amp; hashes</a><p>Check whether this actual result supports the spoken promise and is readable. These previews do not approve the full master.</p>`);}finally{b.disabled=false;}return;}
    if(b.dataset.openingChoice){await req('/api/creator/opening-choice',{audition:b.dataset.audition,mode:b.dataset.openingChoice});el('modal').close();versionKey='';await refresh();notify('Opening saved. Render a new version; original narration and old cuts are kept.');return;}
    if(b.dataset.previewPassage){const id=b.dataset.previewPassage;playsource(id);const video=el('dialogBody').querySelector('video'),start=Number(b.dataset.from),end=Number(b.dataset.to);video.addEventListener('loadedmetadata',()=>{video.currentTime=start;},{once:true});video.addEventListener('timeupdate',()=>{if(video.currentTime>end)video.pause();});return;}
    if(b.dataset.creatorTrim||b.dataset.restoreTake){const id=b.dataset.creatorTrim||b.dataset.restoreTake;await req('/api/creator/trim',{id,revision:state.jobs[id].revision,start:b.dataset.restoreTake?0:Number(el('creatorKeepStart').value),end:b.dataset.restoreTake?state.assets[id].duration:Number(el('creatorKeepEnd').value)});versionKey='';await refresh();notify('Source cut saved. Prior cuts remain; check meaning and joins on the next export.');return;}
    if(b.dataset.acceptBroll){const id=b.dataset.acceptBroll,q=state.jobs[id].creator.broll_suggestions[Number(b.dataset.suggestion)];await req('/api/update',{ids:[id],changes:{inserts:[...state.jobs[id].settings.inserts,{id:crypto.randomUUID(),asset:q.asset,at:q.at,offset:q.offset,duration:q.duration,cue:'',reason:q.reason}]}});versionKey='';await refresh();return;}
    if(b.id==='addBroll'){el('brollInput').click();return;}
    if(b.id==='addStyleReference'){el('styleReferenceInput').click();return;}
    if(b.dataset.describeFootage){const id=b.dataset.describeFootage,a=state.assets[id];dialog('Describe usable footage',`<p>${esc(a.name)} · tags help match ordinary filenames; no action/result is inferred from a filename alone.</p><textarea id="footageDescription" rows="4">${esc(a.description||'')}</textarea><fieldset><legend>Belongs to these recordings</legend>${Object.keys(state.jobs).map(k=>`<label><input type="checkbox" data-footage-owner="${k}" ${(a.owner_jobs?.includes(k)||!a.owner_jobs?.length&&selectedIds().includes(k))?'checked':''}>${esc(sourceName(k))}</label>`).join('')}</fieldset><button type="button" class="primary" data-save-footage-label="${id}">Save label & assignment</button>`);return;}
    if(b.dataset.saveFootageLabel){await req('/api/creator/asset-label',{id:b.dataset.saveFootageLabel,description:el('footageDescription').value,owners:all('[data-footage-owner]:checked').map(x=>x.dataset.footageOwner)});el('modal').close();await refresh();return;}
    if(b.id==='addGraphic'){el('graphicInput').click();return;}
    if(b.id==='generateArtifacts'){await save();dialog('Generate intro & demos',`<p>Use each recording’s own script. A script alone does not prove these words were recorded.</p><label>Animation planner<select id="animationMode"><option value="">Current native rules</option><option value="rules">Editable scene specs · rules baseline</option><option value="base_rag">Base model + frozen train-only RAG · local runtime required</option><option value="fine_tuned">Fine-tuned spec adapter + same RAG · experimental</option></select></label><label>Intro layout<select id="introLayout" disabled><option value="full">Full screen · existing default</option><option value="host">Keep presenter · headline above face</option></select></label><small>Choose an editable scene planner to set the intro layout. Existing scenes stay unchanged until you replace them.</small><label>Animation style<select id="animationStyle"><option value="balanced">Balanced · clear explanation</option><option value="maverick_fast">Maverick · fast emphasis</option></select></label><label><input type="checkbox" id="useReferenceObservations" checked> Guide new proposals with observations from the selected reference</label><label><input type="checkbox" id="sceneSpokenConfirmed"> I have checked that the script matches the recorded words.</label>${sourceObservationFields()}${designFields()}${selectedIds().length===1?evidenceFields(null):'<p>For a batch, proof remains unassigned until you attach it to the intended scene. Shared pacing is preserved.</p>'}<button type="button" class="primary" id="confirmGenerateArtifacts">Generate storyboard & previews</button>`);return;}
    if(b.id==='confirmGenerateArtifacts'){b.disabled=true;b.textContent='Generating original scenes…';try{await req('/api/artifacts/generate',{ids:selectedIds(),evidence:readSceneEvidence(),spoken_confirmed:el('sceneSpokenConfirmed').checked,design:readSceneDesign(),animation_mode:el('animationMode').value||null,animation_style:el('animationStyle').value,intro_layout:el('introLayout').value,observations:readSourceObservations(),reference_guidance:el('useReferenceObservations').checked});el('modal').close();versionKey='';await refresh();showPanel('script');notify('Storyboard and independent scene previews created. Review the original quote and any pickups.');}finally{b.disabled=false;}return;}
    if(b.id==='benchmarkExports'){
      const source=el('exportSource').value,available=state.exports.filter(e=>!source||e.job===source);
      dialog('Benchmark full edited videos',`<p>Choose complete exports from the same episode for controlled comparisons. This does not approve delivery. Every master is decoded and measured; human viewing/listening remains pending.</p><fieldset><legend>Exports · previous cuts remain intact</legend>${available.slice(-12).map(e=>`<label><input type="checkbox" data-benchmark-export="${e.id}" ${e.id===available.at(-1)?.id?'checked':''}>${esc(sourceName(e.job))} · ${cutVersion(e)} · ${time(e.duration)}</label>`).join('')}</fieldset><fieldset><legend>Style references · optional</legend>${refs().map(a=>`<label><input type="checkbox" data-benchmark-ref="${a.id}">${esc(a.name)}</label>`).join('')||'<p>No style references imported.</p>'}</fieldset>${benchmarkQuizFields(available.slice(-12))}<button id="createBenchmark" type="button" class="primary">Measure full videos & create blind review</button>`);return;
    }
    if(b.id==='createBenchmark'){
      const ids=all('[data-benchmark-export]:checked').map(x=>x.dataset.benchmarkExport),references=all('[data-benchmark-ref]:checked').map(x=>x.dataset.benchmarkRef);
      b.disabled=true;b.textContent='Decoding complete exports…';try{const r=await req('/api/benchmarks/create',{ids,references,quiz_by_job:readBenchmarkQuizzes(ids)});dialog('Full-video benchmark ready',`<p>Measured ${r.technical.length} complete exports. Review, first-pass decisions and repair time are pending.</p><a class="link" href="${esc(r.url)}" target="_blank" rel="noopener">Open blind phone-size review</a><p>${r.technical.map(v=>`${esc(v.id.slice(0,8))}: ${esc(v.status)}`).join(' · ')}</p><small>Results saved locally. Confirmed corrections from development episodes can be exported for learning. Frozen test corrections stay quarantined.</small>`);await refresh();}finally{b.disabled=false;}return;
    }
    if(b.id==='importMotionModel'){el('motionPackageInput').click();return;}
    if(b.dataset.animationSaveScene){await req('/api/animations/save',{id:b.dataset.animationSaveScene});await refresh();notify('Saved an editable template and silent preview in animations.');return;}
    if(b.id==='extractReferenceAnimation'){dialog('Save reference animation',`<label>Reference<select id="animationSource">${refs().map(a=>`<option value="${a.id}">${esc(a.name)}</option>`).join('')}</select></label><label>Name<input id="animationTitle" maxlength="120"></label><label>Source in (s)<input id="animationIn" type="number" min="0" step="any" value="0"></label><label>Source out (s)<input id="animationOut" type="number" min="0" step="any" value="2"></label><label>Optional crop [width,height,x,y]<input id="animationCrop" placeholder="Leave blank for the original frame"></label><label>Permission for reuse<textarea id="animationPermission" placeholder="Owner declaration or source permission"></textarea></label><small>Original text, faces and logos stay baked into the clip. Audio is removed. Inspect the excerpt before using it.</small><button type="button" id="saveAnimationExcerpt" class="primary">Save silent clip</button>`);return;}
    if(b.id==='saveAnimationExcerpt'){b.disabled=true;try{await req('/api/animations/excerpt',{asset:el('animationSource').value,title:el('animationTitle').value,start:Number(el('animationIn').value),end:Number(el('animationOut').value),crop:el('animationCrop').value.trim()?JSON.parse(el('animationCrop').value):null,permission:el('animationPermission').value});el('modal').close();await refresh();}finally{b.disabled=false;}return;}
    if(b.dataset.animationPreview){const r=state.animation_library[b.dataset.animationPreview];dialog(r.title,`<video controls src="/animations/${r.id}/preview"></video><p>${esc(r.status)}</p><small>${esc(r.baked_content||r.origin)}</small>${r.kind==='reference_excerpt'?`<label>Reviewer<input id="animationReviewer"></label><label>Observed watermark / baked-content evidence<textarea id="animationEvidence"></textarea></label><label><input id="animationClear" type="checkbox"> I inspected this exact clip; no unwanted watermark is present.</label><label><input id="animationLayoutClear" type="checkbox"> The crop and baked content are usable as an illustration.</label><label>Confirmed defects, if any<textarea id="animationDefects"></textarea></label><button type="button" class="primary" data-animation-review="${r.id}">Save inspection</button>`:''}`);return;}
    if(b.dataset.animationReview){const r=state.animation_library[b.dataset.animationReview];await req('/api/animations/review',{id:r.id,sha256:r.preview_sha256,reviewer:el('animationReviewer').value,evidence:el('animationEvidence').value,clear:el('animationClear').checked,layout_clear:el('animationLayoutClear').checked,defects:el('animationDefects').value});el('modal').close();await refresh();return;}
    if(b.dataset.animationImport){await req('/api/animations/import',{id:b.dataset.animationImport});await refresh();notify('Illustration added to footage. Assign it explicitly in Cutaways; it is not proof of a new product run.');return;}
    if(b.dataset.animationAdapt){const library=state.animation_library[b.dataset.animationAdapt],choices=Object.values(state.artifacts||{}).filter(r=>selectedIds().includes(r.job)&&r.plan.kind==='animation_spec'&&r.plan.type===library.type);dialog('Adapt template to this take',`<label>Current scene<select id="adaptAnimationScene">${choices.map(r=>`<option value="${r.id}">${esc(r.plan.title)} · v${r.version}</option>`).join('')}</select></label><p>Current text and source anchors replace the template’s content. Other scenes stay unchanged; unlock the selected scene first.</p><button type="button" class="primary" data-confirm-animation-adapt="${library.id}" ${choices.length?'':'disabled'}>Create a new scene version</button>`);return;}
    if(b.dataset.confirmAnimationAdapt){const r=state.artifacts[el('adaptAnimationScene').value];await req('/api/animations/reuse',{id:r.id,library:b.dataset.confirmAnimationAdapt,version:r.version});el('modal').close();await refresh();return;}
    if(b.id==='transcribeRecording'){const ids=selectedIds();if(ids.length!==1)throw Error('Select one take');b.disabled=true;try{const t=await req('/api/transcribe',{id:ids[0]});dialog('Vietnamese transcript · review required',`<p>${esc(t.device)} · ${esc(t.compute_type)} · source SHA ${t.source_sha256.slice(0,12)}</p><textarea rows="16" id="asrTranscript">${esc(t.srt)}</textarea><small>Check names, Vietnamese meaning and CTA against the recording. This does not certify listening.</small><button type="button" class="primary" id="useAsrTranscript" data-job="${ids[0]}">Use as this take’s script</button>`);}finally{b.disabled=false;}return;}
    if(b.id==='useAsrTranscript'){await req('/api/update',{ids:[b.dataset.job],changes:{script:el('asrTranscript').value}});el('modal').close();versionKey='';await refresh();return;}
    if(b.dataset.saveMotion){const r=state.artifacts[b.dataset.saveMotion],animation=el('motionEditMode').value==='json'?JSON.parse(el('motionSpecEditor').value):JSON.parse(JSON.stringify(r.plan.animation));if(el('motionEditMode').value==='controls'){animation.spec.objects.forEach((o,i)=>{const text=document.querySelector(`[data-motion-text="${i}"]`);if(text){o.text=text.value;o.font_size=Number(document.querySelector(`[data-motion-font="${i}"]`).value);o.box_style=document.querySelector(`[data-motion-background="${i}"]`).value;if(!animation.context.texts.includes(o.text)){animation.context.texts.push(o.text);animation.context.voice_aligned=false;}}o.rect=all(`[data-motion-rect="${i}"]`).map(x=>Number(x.value));const tilt=document.querySelector(`[data-motion-tilt="${i}"]`);o.keyframes=retimeMotionKeys(o.keyframes,Number(document.querySelector(`[data-motion-entrance="${i}"]`).value),tilt?Number(tilt.value):null);o.hold_frames=Number(document.querySelector(`[data-motion-hold="${i}"]`).value);readMotionReplacementControls(animation,o,i);});animation.spec.sfx=(animation.spec.sfx||[]).filter((s,i)=>{s.gain_db=Number(document.querySelector(`[data-motion-gain="${i}"]`).value);return document.querySelector(`[data-motion-sound="${i}"]`).checked;});}b.disabled=true;try{await req('/api/artifacts/edit',{id:r.id,version:r.version,changes:{animation}});el('modal').close();await refresh();}finally{b.disabled=false;}return;}
    if(b.dataset.motionLock){const r=state.artifacts[b.dataset.motionLock];await req('/api/artifacts/edit',{id:r.id,version:r.version,changes:{locked:!r.locked}});el('modal').close();await refresh();return;}
    if(b.dataset.artifactPreview){const r=state.artifacts[b.dataset.artifactPreview];dialog(r.plan.title,`<video controls src="/artifacts/${r.id}/preview?v=${r.version}"></video><p>${esc(r.status)} · ${esc(r.plan.narration_status)}</p><blockquote>${esc(r.plan.source_quote)}</blockquote><p>${esc(r.plan.intended_visual)}</p><div class="dialogactions"><a class="link" download href="/artifacts/${r.id}/preview?download=1">Export MP4</a><a class="link" download href="/artifacts/${r.id}/source?download=1">Editable scene JSON</a><a class="link" download href="/artifacts/${r.id}/timeline?download=1">Timeline</a></div>`);return;}
    if(b.dataset.artifactEdit){artifactEditor(b.dataset.artifactEdit);return;}
    if(b.dataset.artifactRegenerate){const id=b.dataset.artifactRegenerate;b.disabled=true;try{await req('/api/artifacts/edit',{id,version:state.artifacts[id].version,changes:{}});await refresh();notify('Only this scene regenerated; prior version retained.');}finally{b.disabled=false;}return;}
    if(b.dataset.artifactToggle){const id=b.dataset.artifactToggle;await req('/api/artifacts/toggle',{id,enabled:!state.artifacts[id].plan.enabled});await refresh();return;}
    if(b.dataset.artifactInsert){const id=b.dataset.artifactInsert;await req('/api/artifacts/insert',{id,enabled:!state.artifacts[id].inserted});await refresh();notify('Episode insertion updated. Narration and episode music remain continuous.');return;}
    if(b.dataset.saveScene){const id=b.dataset.saveScene,r=state.artifacts[id],passage=state.storyboards[r.job].passages.find(p=>p.id===el('scenePassage').value),sounds={};for(const key of ['contact','result'])sounds[key]={id:key==='contact'?'click':'chime',muted:el('sceneMute-'+key).checked,gain_db:Number(el('sceneGain-'+key).value),offset_frames:Number(el('sceneOffset-'+key).value)};b.disabled=true;try{await req('/api/artifacts/edit',{id,version:r.version,changes:{title:el('sceneTitle').value,source_quote:passage.quote,passage_ids:[passage.id],occurrence:passage.occurrence,duration:Number(el('sceneDuration').value),at:Number(el('sceneAt').value),position:el('scenePosition').value,intensity:Number(el('sceneIntensity').value),sound:el('sceneSound').value,sounds,design:readSceneDesign(),evidence:r.plan.kind==='generated_video'?r.plan.evidence:readSceneEvidence()}});el('modal').close();await refresh();}finally{b.disabled=false;}return;}
    if(b.dataset.analyze){dialog('Reference observations','<p>Analyzing opening, middle and ending on this computer…</p>');const id=b.dataset.analyze,result=await req('/api/analyze-reference',{id});showReferenceAnalysis(id,result);return;}
    if(b.id==='trainingReport'||b.id==='exportTrainingDataset'){const r=await req(b.id==='trainingReport'?'/api/training-report':'/api/training-export',{}),report=r.report||r;dialog('Training readiness',`<p>${report.accessible} references · ${report.distinct_recordings} distinct files · ${report.eligible_references} eligible · ${report.usable_labels} usable labels</p><p>${esc(report.status)} · no weight update started</p><ul>${report.blockers.map(s=>`<li>${esc(s)}</li>`).join('')}</ul><small>Unknown decisions remain UNLABELED. A deliberate presenter hold needs an explicit label. Groups are connected by creator, series, family, excerpts and hashes before splitting. Held-out transcripts and corrections stay outside retrieval.</small>${r.folder?`<p>Saved locally: ${esc(r.folder)}</p>`:'<button type="button" id="exportTrainingDataset" class="soft">Prepare versioned dataset</button>'}`);return;}
    if(b.dataset.trainingIntake){const id=b.dataset.trainingIntake,t=state.assets[id].training||{};dialog('Include in training · deliberate intake',`<p>Style analysis and visible demonstration are separate uses. This action records eligibility; it does not start training.</p><label>Creator group<input id="trainingCreator" value="${esc(t.creator||'')}"></label><label>Series group<input id="trainingSeries" value="${esc(t.series||'')}"></label><label>Original recording family<input id="trainingFamily" value="${esc(t.family||'')}"></label><label>Excerpt / repost parent group, if any<input id="trainingParent" value="${esc(t.parent_group||'')}"></label><label>Permission evidence<input id="trainingPermission" value="${esc(t.permission||'')}" placeholder="Owner declaration / recorded permission for model training"></label><label>Reviewer<input id="trainingReviewer" value="${esc(t.reviewer||'')}"></label><label>Presenter evidence / source timecode<input id="trainingContentEvidence" value="${esc(t.content_evidence||'')}"></label><label><input id="trainingPresenter" type="checkbox" ${t.presenter_verified?'checked':''}> Presenter-led reference confirmed.</label><label><input id="trainingGrouped" type="checkbox" ${t.group_reviewed?'checked':''}> I checked creator, series, duplicates, excerpts and reposts.</label><button type="button" class="primary" data-save-training="${id}">Include / update eligibility</button><button type="button" class="textbtn" data-exclude-training="${id}">Exclude from future training</button>${(t.moments||[]).map(m=>`<p>${m.master_range.map(x=>Number(x).toFixed(2)).join('–')}s · ${esc(m.decision)} <button type="button" class="textbtn" data-label-moment="${m.id}" data-label-asset="${id}">Annotate</button></p>`).join('')}`);return;}
    if(b.dataset.saveTraining){const id=b.dataset.saveTraining;await req('/api/training-intake',{id,metadata:{include:true,creator:el('trainingCreator').value,series:el('trainingSeries').value,family:el('trainingFamily').value,parent_group:el('trainingParent').value,permission:el('trainingPermission').value,reviewer:el('trainingReviewer').value,group_reviewed:el('trainingGrouped').checked,presenter_verified:el('trainingPresenter').checked,content_evidence:el('trainingContentEvidence').value}});el('modal').close();await refresh();notify('Recorded for eligibility. Add independently reviewed moments before training.');return;}
    if(b.dataset.excludeTraining){await req('/api/training-intake',{id:b.dataset.excludeTraining,metadata:{include:false}});el('modal').close();await refresh();return;}
    if(b.dataset.labelMoment){const id=b.dataset.labelAsset,m=state.assets[id].training.moments.find(m=>m.id===b.dataset.labelMoment),label={id:m.id,master_range:m.master_range,raw_source_range:null,passage:'',decision:'REVIEW',visible_evidence:'',audible_evidence:null,can_listen:false,reviewer:'',label_kind:'agent_experiment',input_independently_reviewed:false,input_evidence:'',input:{passage:'',speech_timing:m.master_range,available_media:[],reference_observations:[],choices:['STAY_PRESENTER','SHOW_CONTROL','CONTACT','HOLD_RESULT','OPEN_FILE','ILLUSTRATE','CTA','NO_EFFECT','REVIEW']},target:{choice:'REVIEW',reason:''}};dialog('Review an editorial moment',`<video controls src="/assets/${id}/media#t=${m.master_range[0]},${m.master_range[1]}"></video><p>Keep inference inputs separate from final-editor targets. A finished video cannot explain discarded raw takes. Audio claims require actual listening.</p><label>Structured moment annotation<textarea id="momentAnnotation" rows="20">${esc(JSON.stringify(label,null,2))}</textarea></label><button type="button" class="primary" data-save-moment="${id}">Save reviewed annotation</button>`);return;}
    if(b.dataset.saveMoment){await req('/api/training-label',{asset:b.dataset.saveMoment,label:JSON.parse(el('momentAnnotation').value)});el('modal').close();await refresh();notify('Versioned annotation saved. It enters a dataset only after eligibility and split checks.');return;}
    if(b.id==='reviewCorrections'){const rows=(state.corrections||[]).filter(c=>selectedIds().includes(c.job));dialog('Source-anchored editorial corrections',rows.map(c=>`<details><summary>${esc(c.id.slice(0,8))} · ${c.editor_confirmed?'editor confirmed':'unconfirmed'}</summary><small>${esc(c.alignment)} · source ${esc(c.source_sha256?.slice(0,12))}</small><pre>${esc(JSON.stringify({before:c.before,after:c.after},null,2))}</pre><label>Editor<input data-correction-reviewer="${c.id}" value="${esc(c.reviewer||'')}"></label><label>Reason · optional<textarea data-correction-reason="${c.id}">${esc(c.reason||'')}</textarea></label><button type="button" class="soft" data-confirm-correction="${c.id}">Confirm correction</button></details>`).join('')||'<p>No cutaway or sound-cue corrections saved for these recordings.</p>');return;}
    if(b.dataset.confirmCorrection){const id=b.dataset.confirmCorrection;await req('/api/correction-review',{id,reviewer:document.querySelector(`[data-correction-reviewer="${id}"]`).value,reason:document.querySelector(`[data-correction-reason="${id}"]`).value,confirmed:true});notify('Editor confirmation recorded. Dataset eligibility and holdout exclusion still apply.');return;}
    if(b.dataset.fullAnalysis){const id=b.dataset.fullAnalysis;dialog('Reference observations','<p>Analyzing the complete reference…</p>');showReferenceAnalysis(id,await req('/api/analyze-reference',{id,full:true}));return;}
    if(b.dataset.correctObservation!=null){await req('/api/reference-observation',{id:b.dataset.refId,index:Number(b.dataset.correctObservation),observation:el('observationText').value,start:el('observationStart').value,end:el('observationEnd').value,reviewer:el('observationReviewer').value});notify('Observation saved with reviewer and source time.');return;}
    if(b.dataset.editObservation!=null){const id=b.dataset.refId,index=Number(b.dataset.editObservation),r=state.assets[id]?.analysis?.observations[index];if(!r)throw Error('Reload the reference profile to inspect its current observations.');dialog('Correct reference observation',`<label>Source start (s)<input id="observationStart" type="number" value="${r.source_range[0]}"></label><label>Source end (s)<input id="observationEnd" type="number" value="${r.source_range[1]}"></label><label>Observed behavior<textarea id="observationText">${esc(r.observation)}</textarea></label><label>Reviewer<input id="observationReviewer"></label><button class="primary" data-correct-observation="${index}" data-ref-id="${id}">Save correction</button>`);return;}
    if(b.id==='addMusic'){dialog('Import your music','<p>Choose audio you may use in this export. Reference permission does not automatically grant permission to reuse its soundtrack.</p><label><input id="musicRights" type="checkbox"> I have permission to use this track in my exported videos.</label><button id="chooseMusic" class="primary">Choose audio file</button>');return;}
    if(b.id==='chooseMusic'){if(!el('musicRights').checked)throw Error('Confirm permission for this audio before importing it.');el('musicInput').click();return;}
    if(b.id==='addEvent'){if(selectedIds().length!==1)throw Error('Select one recording to add its manual cues.');manualEvents.push({id:crypto.randomUUID(),kind:'keyword',anchor:{asset:selectedIds()[0],source_pts:0,type:'manual_source_pts'},hold_frames:30,text:'',origin:'manual',confidence:1,sound:{id:null,muted:true,gain_db:-14,offset_frames:0}});setDirty('events');drawEvents();return;}
    if(b.dataset.removeEvent!=null){manualEvents.splice(Number(b.dataset.removeEvent),1);setDirty('events');drawEvents();return;}
    if(b.id==='previewCues'){if(selectedIds().length!==1)throw Error('Select one recording to inspect its exact cue plan.');await save();const result=await req('/api/preview-cues',{id:selectedIds()[0]});manualEvents=result.events.filter(e=>e.origin!=='legacy_insert_sound_v1');setDirty('events');drawEvents();notify('Cue proposal loaded. Save to accept it; existing overrides were preserved.');return;}
    if(b.dataset.seek!=null){el('dialogBody').querySelector('video').currentTime=Number(b.dataset.seek);return;}
    if(b.dataset.addScript){changeSelection([b.dataset.addScript]);showPanel('script');el('script').focus();return;}
    if(b.dataset.style){el('style').value=b.dataset.style;setDirty('style');drawFraming();return;}
    if(b.id==='toggleInspector'){inspectorOpen=!inspectorOpen;el('form').classList.toggle('collapsed',!inspectorOpen);b.setAttribute('aria-expanded',String(inspectorOpen));b.textContent=inspectorOpen?'Hide settings':'Show settings';return;}
    if(b.dataset.pacing){if(!selectedIds().length)throw Error('Select recordings to apply pacing.');await save();await req('/api/update',{ids:selectedIds(),changes:{style_ref:b.dataset.pacing}});versionKey='';await refresh();showPanel('look');notify('Pacing reference applied. It stays off screen.');return;}
    if(b.dataset.showReference){if(selectedIds().length!==1)throw Error('Select one recording to add its on-screen demonstration.');inserts.push({asset:b.dataset.showReference,at:0,offset:0,duration:Math.min(2,state.assets[b.dataset.showReference].duration,state.assets[selectedIds()[0]].duration)});setDirty('inserts');showPanel('inserts');drawInserts();return;}
    if(b.id==='resolveScripts'){
      dialog('Assign unmatched scripts',unresolvedScripts.map((f,i)=>`<div class="assignment"><strong>${esc(f.name)}</strong><small>${esc(f.reason)}</small><label>Recording<select data-assignment="${i}"><option value="">Choose recording…</option>${Object.values(state.jobs).map(j=>`<option value="${j.id}">${esc(state.assets[j.id].name)}</option>`).join('')}</select></label><button class="soft" data-assign="${i}">Assign script</button></div>`).join(''));return;
    }
    if(b.dataset.assign!=null){const i=Number(b.dataset.assign),id=all('[data-assignment]').find(x=>Number(x.dataset.assignment)===i).value;if(!id)throw Error('Choose the intended recording.');await req('/api/assign-script',{script_id:unresolvedScripts[i].id,job_id:id});el('modal').close();versionKey='';await refresh();return;}
    if(b.dataset.resolve!=null){if(selectedIds().length!==1)throw Error('Choose one recording to resolve its spoken phrase.');const i=Number(b.dataset.resolve),r=inserts[i];if(!r.cue?.trim())throw Error('Enter the exact spoken phrase first.');await save();const result=await req('/api/phrases',{id:selectedIds()[0],phrase:r.cue});dialog('Choose the spoken occurrence',`<p>${esc(result.timing)} · review timing against speech.</p>`+(result.matches.map(m=>`<button class="occurrence soft" data-occurrence="${m.occurrence}" data-index="${i}" data-at="${m.at}">${time(m.at)} · ${esc(m.context)}</button>`).join('')||'<p>No match. Leave it unassigned or use an explicit timestamp.</p>'));return;}
    if(b.dataset.occurrence!=null){const i=Number(b.dataset.index);inserts[i].occurrence=Number(b.dataset.occurrence);inserts[i].at=Number(b.dataset.at);setDirty('inserts');drawInserts();el('modal').close();return;}
    if (b.classList.contains("importAction")) {
      pendingTakeParent='';el('hostInput').multiple=true;
      e.stopPropagation();
      el("hostInput").click();
      return;
    }
    if(b.id==='beginEditingTurn'){if(selectedIds().length!==1)throw Error('Choose one recording for this request.');if(activeEditorTurn)throw Error('Finish the active request first.');dialog('Current public editing request','<label>What should change?<textarea id="publicEditingRequest" rows="4"></textarea></label><p>This records the request before you or your agent use the controls. Missing footage remains a pickup.</p><button class="primary" id="savePublicEditingRequest">Start this request</button>');return;}
    if(b.id==='savePublicEditingRequest'){activeConversationId=activeConversationId||crypto.randomUUID().replaceAll('-','');const t=await req('/api/conversations/begin',{conversation:activeConversationId,project:selectedIds()[0],request_id:crypto.randomUUID(),message:el('publicEditingRequest').value});activeEditorTurn=t.id;sessionStorage.setItem('cutroom-active-turn:'+state.data_folder,JSON.stringify({conversation:activeConversationId,turn:t.id}));el('modal').close();await refresh();notify('Public request recorded. Subsequent tool changes belong to this turn.');return;}
    if(b.id==='completeEditingTurn'){if(!activeEditorTurn)throw Error('No editing request is active.');await req('/api/conversations/complete',{turn:activeEditorTurn});activeEditorTurn='';sessionStorage.removeItem('cutroom-active-turn:'+state.data_folder);await refresh();notify('Request history saved. Editorial review remains separate.');return;}
    if(b.dataset.hookReview){const e=state.exports.find(x=>x.id===b.dataset.hookReview);dialog('Hook · first exported 3 seconds',`<video id="hookPlayer" controls playsinline style="width:360px;max-width:100%" src="/exports/${e.id}/hook"></video><p>Watch once at 1×. Titles and silence count. What do you expect this episode to show?</p><label>Actual viewer<input id="hookReviewer"></label><label>Your expectation<textarea id="hookAnswer"></textarea></label><label><input id="hookFirst" type="checkbox"> I have not watched the body in this review and am answering now.</label><button class="primary" data-save-hook="${e.id}">Record answer, then watch body</button>`);return;}
    if(b.dataset.saveHook){const e=state.exports.find(x=>x.id===b.dataset.saveHook),v=el('hookPlayer');const r=await req('/api/hook-response',{id:e.id,sha256:e.sha256,reviewer:el('hookReviewer').value,answer:el('hookAnswer').value,speed:v.playbackRate,width_px:Math.round(v.getBoundingClientRect().width),before_body_attested:el('hookFirst').checked});dialog('Find the payoff',`<p>Recorded expectation: ${esc(r.response.answer)}</p><video controls playsinline style="width:360px;max-width:100%" src="${r.body_url}"></video><label>Payoff time (seconds)<input id="hookPayoff" type="number" min="0" step="any"></label><label>What visibly delivers the promise?<textarea id="hookPayoffEvidence"></textarea></label><button class="primary" data-save-payoff="${r.response.id}">Save payoff observation</button>`);return;}
    if(b.dataset.savePayoff){await req('/api/hook-payoff',{response:b.dataset.savePayoff,time:Number(el('hookPayoff').value),evidence:el('hookPayoffEvidence').value});el('modal').close();await refresh();notify('Hook and payoff observations saved; full QC remains separate.');return;}
    if(b.dataset.feedbackNote){const e=state.exports.find(x=>x.id===b.dataset.feedbackNote);b.disabled=true;try{const r=await sendFeedback(e,el('reviewNote').value,{kind:'note'});el('modal').close();await refresh();notify('Feedback saved · '+r.note_id.slice(0,8));}finally{b.disabled=false;}return;}
    if(b.id==='editStyleLocks'){
      if(selectedIds().length!==1)throw Error('Choose one recording whose style you want to lock.');await save();const j=state.jobs[selectedIds()[0]],locks=j.style_locks||{};
      dialog('Select style fields',`<p>Locks preserve these values. Scripts, cues, footage, scenes and approval remain episode-specific.</p>${transferableStyle.map(k=>`<label><input type="checkbox" data-style-lock="${k}" ${k in locks?'checked':''}> ${esc(k.replaceAll('_',' '))} · ${esc(j.settings[k])}</label>`).join('')}<button class="primary" data-save-style-locks="${j.id}">Save selected locks</button><p>Optional targets; existing manual style overrides remain.</p>${Object.values(state.jobs).filter(t=>t.id!==j.id).map(t=>`<label><input type="checkbox" data-style-target="${t.id}"> ${esc(state.assets[t.id].name)}</label>`).join('')}<button class="soft" data-transfer-style="${j.id}">Transfer saved locks</button>`);return;
    }
    if(b.dataset.saveStyleLocks){const id=b.dataset.saveStyleLocks;await req('/api/style-locks',{job:id,revision:state.jobs[id].revision,fields:all('[data-style-lock]:checked').map(x=>x.dataset.styleLock)});await refresh();notify('Selected style fields locked.');return;}
    if(b.dataset.transferStyle){const targets=all('[data-style-target]:checked').map(x=>x.dataset.styleTarget);if(!targets.length)throw Error('Choose target recordings.');const r=await req('/api/style-transfer',{source:b.dataset.transferStyle,targets});el('modal').close();await refresh();notify('Style transferred; '+r.reduce((n,x)=>n+x.manual_overrides_preserved.length,0)+' manual overrides preserved.');return;}
    if (b.dataset.verdict) {
      const e = state.exports.find((x) => x.id === b.dataset.eid);
      const checks = Object.fromEntries(
        all("[data-gate]").map((x) => [x.dataset.gate, x.checked]),
      );
      await req("/api/review", {
        id: e.id,
        sha256: e.sha256,
        verdict: b.dataset.verdict,
        checks,
        note: el("reviewNote").value,
        reviewer:el('reviewerName')?.value,
        gate_notes:Object.fromEntries(all('[data-qc-note]').map(x=>[x.dataset.qcNote,x.value])),
        sync_observations:all('[data-sync-time]').filter(x=>x.value!=='').map(x=>({time:Number(x.dataset.syncTime),offset_frames:Number(x.value)})),
        cue_observations:all('[data-cue-offset]').filter(x=>x.value!==''&&all('[data-cue-reviewed]').find(c=>c.dataset.cueReviewed===x.dataset.cueOffset)?.checked).map(x=>({id:x.dataset.cueOffset,offset_frames:Number(x.value),stem_checked:true,final_mix_checked:true})),
        attestation:el('explicitAttestation')?.checked?{run_id:e.id,sha256:e.sha256,reviewer:el('reviewerName').value,decision:b.dataset.verdict,full_watch:checks.watched===true,full_listen:checks.audio===true,speed:1,width_px:360,watched_ranges:[[0,e.duration]],listened_ranges:[[0,e.duration]]}:null,
      });
      el("modal").close();
      await refresh();
      notify("Review saved");
      return;
    }
    if (b.dataset.tab) {
      tab(b.dataset.tab);
      return;
    }
    if (b.dataset.panel) {
      showPanel(b.dataset.panel);
      return;
    }
    if (b.dataset.play) {
      playsource(b.dataset.play);
      return;
    }
    if (b.dataset.review) {
      review(b.dataset.review);
      return;
    }
    if (b.dataset.remove != null) {
      inserts.splice(Number(b.dataset.remove), 1);
      setDirty("inserts");
      drawInserts();
      return;
    }
    if (b.hasAttribute("data-setup") || b.id === "settings") {
      setup();
      return;
    }
    const row = b.closest("[data-row]");
    if (row) {
      const id = row.dataset.row;
      if (b.tagName === "INPUT") {
        const a = new Set(selected);
        a.has(id) ? a.delete(id) : a.add(id);
        changeSelection([...a]);
      } else changeSelection([id]);
      return;
    }
    switch (b.id) {
      case "close":
        el("modal").close();
        break;
      case "selectAll":
        changeSelection(
          visibleSources().every(j=>selected.has(j.id))
            ? []
            : visibleSources().map(j=>j.id),
        );
        break;
      case "addRef":
        el("refInput").click();
        break;
      case "importScript":
        el("scriptInput").click();
        break;
      case "addInsert": {
        const r = refs()[0];
        if (!r) throw Error("Add reference footage first.");
        const at = inserts.length
          ? inserts.at(-1).at + inserts.at(-1).duration
          : 0;
        const len = Math.min(
          2,
          r.duration,
          ...selectedIds().map((k) => state.assets[k].duration - at),
        );
        if (len < 1 / 30) throw Error("No time remains for another cutaway.");
        inserts.push({
          asset: r.id,
          at: +at.toFixed(3),
          offset: 0,
          duration: Math.floor(len * 1000) / 1000,
        });
        setDirty("inserts");
        drawInserts();
        break;
      }
      case "matchRefs":
        b.disabled = true;
        try {
          await save();
          const r = await req("/api/match", { ids: selectedIds() });
          await refresh();
          notify(
            r.matches
              ? r.matches + " cutaway(s) matched. Review them under Cutaways."
              : "No new matches. Use a unique filename phrase or assign Cutaways manually.",
          );
        } finally {
          draw();
        }
        break;
      case "queue":
        if (waiting) return;
        waiting = true;
        try {
          await save();
          const r = await req("/api/queue", { ids: selectedIds(),request_id:crypto.randomUUID() });
          await refresh();
          notify(
            "Queued " +
              r.queued +
              " recording(s)" +
              (r.skipped.length
                ? " · Needs input: " + r.skipped.join(", ")
                : ""),
          );
        } finally {
          waiting = false;
        }
        break;
      case "recheck":
        await req("/api/check", {});
        await refresh();
        setup();
        break;
      case "install":
        await req("/api/setup", {});
        await refresh();
        el("modal").close();
        break;
      case "quit":
        await req("/api/quit", {});
        clearInterval(poll);
        dialog(
          "Workspace closed",
          "<p>Your projects are saved. You can close this tab.</p>",
        );
        break;
    }
  }),
);
el("form").addEventListener(
  "submit",
  guard(async (e) => {
    e.preventDefault();
    await save();
  }),
);
el("form").addEventListener("input", (e) => {
  if(e.target.dataset.anchorArray){const i=Number(e.target.closest('[data-insert]').dataset.insert),key=e.target.dataset.anchorArray,index=Number(e.target.dataset.coordinate);inserts[i].anchors??={};if(key==='crop'){inserts[i].crop??=[1280,800,0,0];inserts[i].crop[index]=Number(e.target.value);}else{inserts[i].anchors[key]??=key==='contact_point_source'?[0,0]:[0,0,100,60];inserts[i].anchors[key][index]=Number(e.target.value);}setDirty('inserts');return;}
  if(e.target.dataset.eventField||e.target.dataset.soundField||e.target.dataset.eventRoi!=null){const index=Number(e.target.closest('[data-event]').dataset.event),event=manualEvents[index],field=e.target.dataset.eventField,sound=e.target.dataset.soundField;
    if(field==='at'){event.anchor.timeline_source_pts=Number(e.target.value);}else if(field)event[field]=field==='hold_frames'?Number(e.target.value):e.target.value;
    if(sound){event.sound??={};if(sound==='muted')event.sound.muted=e.target.checked;else if(['id','offset_reason'].includes(sound))event.sound[sound]=e.target.value||null;else if(e.target.value==='')delete event.sound[sound];else event.sound[sound]=Number(e.target.value);}
    if(e.target.dataset.eventRoi!=null){event.roi??=[0,0,100,60];event.roi[Number(e.target.dataset.eventRoi)]=Number(e.target.value);}
    event.origin='manual';event.manual_override=true;setDirty('events');return;
  }
  if(e.target.dataset.anchor||e.target.dataset.roi!=null){const i=Number(e.target.closest('[data-insert]').dataset.insert);inserts[i].anchors??={};if(e.target.dataset.anchor){const k=e.target.dataset.anchor;if(e.target.value==='')delete inserts[i].anchors[k];else inserts[i].anchors[k]=Number(e.target.value);}else{inserts[i].anchors.roi_source??=[0,0,100,60];inserts[i].anchors.roi_source[Number(e.target.dataset.roi)]=Number(e.target.value);}setDirty('inserts');return;}
  const k = e.target.dataset.k;
  if (k) {
    const i = Number(e.target.closest("[data-insert]").dataset.insert);
    inserts[i][k] = ["asset", "cue", "layout", "pip_corner", "demonstrates", "visual_claim"].includes(k)
      ? e.target.value
      : Number(e.target.value);
    if(k==='cue')delete inserts[i].occurrence;
    setDirty("inserts");
  } else if (
    [
      "script",
      "style",
      "fit",
      "insert_sound",
      "caption_position",
      "style_ref",
    ].concat(extraSettings).includes(e.target.id)
  )
    setDirty(e.target.id);
  if(['style','fit','caption_position'].includes(e.target.id))drawFraming();
});
for (const [id, kind] of [
  ["hostInput", "host"],
  ["refInput", "reference"], ["graphicInput", "graphic"],
  ["scriptInput", "script"],
  ['musicInput','music'],
])
  el(id).addEventListener(
    "change",
    guard(async (e) => {
      const list = [...e.target.files];
      e.target.value = "";
      if (kind === "script") await importScripts(list);
      else if(kind==='host'){const parent=pendingTakeParent;pendingTakeParent='';el('hostInput').multiple=true;await upload(list,kind,parent);}
      else await upload(list, kind);
    }),
  );
el("emptyDrop").addEventListener("click", (e) => {
  if (!e.target.closest("button")) el("hostInput").click();
});
el("emptyDrop").addEventListener("keydown", (e) => {
  if (e.target === el("emptyDrop") && ["Enter", " "].includes(e.key)) {
    e.preventDefault();
    el("hostInput").click();
  }
});
el("emptyDrop").addEventListener("dragover", (e) => {
  e.preventDefault();
  el("emptyDrop").classList.add("drag");
});
el("emptyDrop").addEventListener("dragleave", () =>
  el("emptyDrop").classList.remove("drag"),
);
el("emptyDrop").addEventListener(
  "drop",
  guard(async (e) => {
    e.preventDefault();
    el("emptyDrop").classList.remove("drag");
    await upload([...e.dataTransfer.files], "host");
  }),
);
let polling = false;
const poll = setInterval(async () => {
  if (
    !state.jobs ||
    importing ||
    polling ||
    waiting ||
    (!Object.values(state.jobs).some(locked) &&
      !state.installing &&
      state.speech_setup?.status!=='INSTALLING' &&
      !el("setupBanner").offsetHeight)
  )
    return;
  polling = true;
  try {
    await refresh();
  } catch (e) {
    notify(e.message);
  } finally {
    polling = false;
  }
}, 1600);
guard(refresh)();
document.addEventListener('change',e=>{if(e.target.id==='audioAudition'&&e.target.value){el('dialogBody').querySelector('video')?.pause();el('auditionPlayer').src=`/exports/${e.target.dataset.export}/audition-${e.target.value}`;}});
const libraryValues={sourceSearch:'',sourceCollection:'',sourceVisibility:'active'};
for(const id of Object.keys(libraryValues))el(id).addEventListener(id==='sourceSearch'?'input':'change',()=>{if(!allowChange()){el(id).value=libraryValues[id];return;}libraryValues[id]=el(id).value;touched.clear();selected.clear();versionKey='';draw();});
for(const id of ['exportSource','exportHistory'])el(id).addEventListener('change',drawExports);
for(const [id,role] of [['brollInput','broll'],['styleReferenceInput','style_reference']])el(id).addEventListener('change',guard(async e=>{const files=[...e.target.files];e.target.value='';await upload(files,'reference','',role);}));
el('creatorScriptInput').addEventListener('change',guard(async e=>{const f=e.target.files[0];e.target.value='';if(!f)return;if(selectedIds().length!==1)throw Error('Choose one recording for this script.');const bytes=new Uint8Array(await f.arrayBuffer()),encoding=bytes[0]===255&&bytes[1]===254?'utf-16le':'utf-8',text=new TextDecoder(encoding).decode(bytes).replace(/^\uFEFF/,'');await req('/api/update',{ids:selectedIds(),changes:{script:text}});el('modal').close();versionKey='';await refresh();notify('Prepared script attached to this recording. Actual speech remains authoritative.');}));
el('generativePackageInput').addEventListener('change',guard(async e=>{const file=e.target.files[0];e.target.value='';if(!file)return;const kernel=el('generativeKernel')?.value||'';await req('/api/generative-package?kernel='+encodeURIComponent(kernel),file,true);el('modal').close();await refresh();notify('Generative result imported; no production approval or planner activation implied.');}));
el('motionPackageInput').addEventListener('change',guard(async e=>{const file=e.target.files[0];e.target.value='';if(!file)return;await req('/api/motion-package',file,true);await refresh();notify('Spec adapter imported. Existing scenes and planner modes were preserved.');}));
document.addEventListener('change',e=>{if(e.target.id==='generatedPassage')el('generatedAt').value=e.target.selectedOptions[0].dataset.start;});

document.addEventListener('change',e=>{if(e.target.id==='animationMode'){const select=el('introLayout');select.disabled=!e.target.value;if(select.disabled)select.value='full';}});
document.addEventListener('change',e=>{const id=e.target.dataset.motionStateCustom;if(id!==undefined)all(`[data-motion-state-rect="${id}"]`).forEach(x=>x.disabled=!e.target.checked);});

document.addEventListener('input',e=>{if(e.target.dataset.observedFace!==undefined){const values=all('[data-observed-face]').map(x=>Number(x.value));if(values.every(Number.isFinite))['x','y','width','height'].forEach((k,i)=>el('observedFaceBox').setAttribute(k,values[i]));}});
