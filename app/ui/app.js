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
let formRevisions = {};
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
async function firstCut(ids,niche,story_format){
 const key='cutroom-first-cut-pending:'+state.data_folder+':'+ids.slice().sort().join(','), intent={ids,niche,story_format};
 let pending;try{pending=JSON.parse(sessionStorage.getItem(key)||'null');}catch{}
 if(pending&&JSON.stringify(pending.intent)!==JSON.stringify(intent))throw Error('A previous cut request has an uncertain result. Retry with the same options before starting another cut.');
 const body=pending?.body||{...intent,request_id:crypto.randomUUID(),revisions:Object.fromEntries(ids.map(id=>[id,state.jobs[id].revision]))};
 sessionStorage.setItem(key,JSON.stringify({intent,body}));
 try{const result=await req('/api/creator/first-cut',body);sessionStorage.removeItem(key);return result;}
 catch(error){if(error.status&&error.status<500)sessionStorage.removeItem(key);throw error;}
}
async function req(path, data, raw = false) {
  if(path==='/api/update' && data && !raw && data.revisions===undefined)
    data={...data,revisions:Object.fromEntries(data.ids.map(id=>[id,state.jobs[id].revision]))};
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
  if (!r.ok) {const error=Error(body.error || "The request failed");error.status=r.status;throw error;}
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
      '/media"></video><small>'+(a.kind==='host'?'Original recording':'Source footage · not the edited cut')+' · ' +
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
function draftKey(){return 'cutroom-settings-draft:'+state.data_folder+':'+selectedIds().slice().sort().join(',');}
function draftChanges(){return Object.fromEntries([...touched].map(k=>[k,k==='inserts'?inserts:k==='events'?manualEvents:['motion_intensity','music_gain_db','brand_from','brand_to'].includes(k)?Number(el(k).value):el(k).value]));}
function persistDraft(){try{sessionStorage.setItem(draftKey(),JSON.stringify({ids:selectedIds(),revisions:formRevisions,changes:draftChanges()}));}catch{notify('Draft storage unavailable. Keep this page open or copy your changes before reloading.');}}
function showSavedDraft(){
 let draft;try{draft=JSON.parse(sessionStorage.getItem(draftKey())||'null');}catch{}
 if(!draft)return;
 dialog('Unsaved draft',`<p>This draft keeps its original revision. Compare it with the current settings; it will never overwrite a newer revision automatically.</p><textarea id="savedDraftText" rows="14" readonly>${esc(JSON.stringify(draft,null,2))}</textarea><button type="button" class="soft" id="downloadSettingsDraft">Download draft JSON</button><button type="button" class="textbtn" id="discardSettingsDraft">Discard saved draft</button>`);
 el('downloadSettingsDraft').onclick=()=>{const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(draft,null,2)],{type:'application/json'}));a.href=url;a.download='cutroom-unsaved-settings.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
 el('discardSettingsDraft').onclick=()=>{sessionStorage.removeItem(draftKey());el('modal').close();};
}
const draftButton=document.createElement('button');draftButton.type='button';draftButton.className='textbtn';draftButton.id='savedSettingsDraft';draftButton.textContent='Review saved draft';draftButton.onclick=showSavedDraft;el('save').after(draftButton);
function setDirty(k) {
  editRevision++;
  touched.add(k);
  persistDraft();
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
  const ready=ids.filter(k=>!state.jobs[k].archived&&!locked(state.jobs[k])&&state.jobs[k].status!=='Failed'&&state.jobs[k].settings.script.trim()&&!state.jobs[k].script_issue).length;
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
          refs().filter(a=>a.source_role!=='style_reference'||a.id===r.asset).map(a=>`<option value="${esc(a.id)}" ${a.id===r.asset?'selected':''}>${esc(a.name)}</option>`).join('') +
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
          `</div><label>Layout<select data-k="layout"><option value="full_demo" ${(r.layout||'full_demo')==='full_demo'?'selected':''}>Full demo · original voice</option><option value="presenter_pip" ${r.layout==='presenter_pip'?'selected':''}>Presenter PiP · real recording</option></select></label><label>Presenter shape<select data-k="pip_shape"><option value="rectangle" ${(r.pip_shape||'rectangle')==='rectangle'?'selected':''}>Rectangle</option><option value="circle" ${r.pip_shape==='circle'?'selected':''}>Circle</option></select></label><label>PiP corner<select data-k="pip_corner">${['auto','top_left','top_right','bottom_left','bottom_right'].map(k=>`<option value="${k}" ${(r.pip_corner||(r.pip_shape==='circle'?'bottom_right':'auto'))===k?'selected':''}>${k.replaceAll('_',' ')}</option>`).join('')}</select></label><label>PiP width (canvas fraction)<input data-k="pip_width" type="number" min="0.18" max="0.36" step="0.01" value="${r.pip_width??.25}"></label>${['Center X','Center Y','Zoom'].map((label,index)=>`<label>Presenter crop · ${label}<input type="number" data-pip-crop="${index}" min="${index===2?1:0}" max="${index===2?3:1}" step=".01" value="${r.pip_crop?.[index]??[.5,.38,1][index]}"></label>`).join('')}<small>Auto avoids observed control, result and captions; no safe corner uses full demo. The corner stays fixed for the cutaway.</small>${anchorControls(r)}<button type="button" data-remove="` +
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
  if(ids.length===1&&state.jobs[ids[0]].creator&&!el('openingAuditions'))el('creatorPanel').insertAdjacentHTML('beforeend',`<div id="openingAuditions"><button class="soft" type="button" data-audition-openings="${ids[0]}">Compare 3-second openings</button><small>Host-first / assigned result-first. Same master audio; body stays fixed. Requires a rendered current cut and real result footage.</small></div>`);
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
  formRevisions=Object.fromEntries(ids.map(id=>[id,state.jobs[id].revision]));
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
          `">Preview</button><div class="ref-actions"><small>${esc(a.source_role==='style_reference'?'Style only · not inserted automatically':a.source_role==='broll'?'Usable B-roll':'Library footage · explicit assignment required')}</small><button class="textbtn" data-describe-footage="${a.id}">Label / assign to recording</button><button class="textbtn" data-analyze="${a.id}">Reference profile</button><button class="textbtn" data-pacing="${a.id}">Use for pacing</button>${a.source_role==='style_reference'?'':`<button class="textbtn" data-show-reference="${a.id}">Show in video</button>`}<button class="textbtn" data-training-intake="${a.id}">Include in training</button></div></div>`,
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
function artifactVisual(p){
 if(p.kind!=='animation_spec')return p.intended_visual;
 const c=p.animation.context;
 if(c.proof)return c.proof.data_class==='real_screen'?'Assigned screen capture: control, contact and result; inspect readability on the export.':'Declared visual illustration; it is not proof of a software result.';
 if(c.request==='intro')return c.layout_requirement==='host'?'Headline with presenter preserved; verify the declared promise and placement.':'Full-screen introduction from this episode’s declared text.';
 return 'Declared explanatory graphic; it is not a recording of a software result.';
}
function drawArtifacts(){
 const ids=selectedIds();el('generateArtifacts').disabled=!ids.length||ids.some(id=>locked(state.jobs[id])||(state.scene_generating||[]).includes(id))||!ids.every(id=>state.jobs[id].settings.script.trim());
 el('transcribeRecording').disabled=ids.length!==1||ids.some(id=>locked(state.jobs[id]));
 el('animationModelStatus').textContent=state.animation_model?`Experimental spec adapter · ${state.animation_model.actual_optimizer_steps} optimizer steps · SHA ${state.animation_model.checkpoint_sha256.slice(0,12)} · choose per generation; not production-approved${state.animation_model.training_style_counts?` · training labels: ${Object.entries(state.animation_model.training_style_counts).map(([name,count])=>`${name} ${count}`).join(', ')}`:''}${state.animation_model.provenance_warnings?.length?' · Style metadata differs from the training labels; fidelity unverified.':''}`:'No animation-spec adapter installed. Native rules and existing scenes remain available.';
 const records=Object.values(state.artifacts||{}).filter(r=>ids.includes(r.job));
 el('storyboard').innerHTML=ids.length===1?(state.storyboards?.[ids[0]]?.passages||[]).map(p=>`<details class="passage"><summary>${time(p.start)} · Passage ${esc(p.id.slice(-6))} · occurrence ${p.occurrence+1}</summary><p>${esc(p.quote)}</p><small>${esc(p.timing)} · ${p.start.toFixed(2)}–${p.end.toFixed(2)}s</small></details>`).join(''):'';
 el('artifactCards').innerHTML=records.map(r=>`<article class="artifact-card"><div class="artifact-heading"><img src="/artifacts/${r.id}/thumb?v=${r.version}" alt="${esc(r.plan.type)} thumbnail"><div><small>${r.plan.type==='introduction'?'Introduction':'Demo'} · v${String(r.version).padStart(3,'0')}</small><strong>${esc(r.plan.title)}</strong><span>${r.plan.duration.toFixed(1)}s · ${r.plan.enabled?'':'Disabled · '}${esc(r.status)}</span></div></div><blockquote>${esc(r.plan.source_quote)}</blockquote><small>${esc(artifactVisual(r.plan))} · ${esc(r.plan.timing)}</small><div class="artifact-actions"><button type="button" class="soft" data-artifact-preview="${r.id}">Preview</button><button type="button" class="textbtn" data-artifact-edit="${r.id}">Edit</button><button type="button" class="textbtn" data-artifact-regenerate="${r.id}">Regenerate this scene</button><button type="button" class="textbtn" data-artifact-toggle="${r.id}">${r.plan.enabled?'Disable':'Enable'}</button><button type="button" class="textbtn" data-artifact-insert="${r.id}">${r.inserted?'Remove from episode':'Insert in episode'}</button><a class="link" download href="/artifacts/${r.id}/preview?download=1">Export MP4</a></div></article>`).join('');
 drawAnimationLibrary();
}
function drawAnimationLibrary(){
 el('animationLibrary').innerHTML=Object.values(state.animation_library||{}).map(r=>`<article class="cue-card"><strong>${esc(r.title)}</strong><small>${esc(r.kind||'native_spec')}${r.kind==='native_spec'?' · template v'+(r.template_version||1)+' / source scene v'+r.source_version:''} · ${esc(r.status)} · silent preview</small><button type="button" class="soft" data-animation-preview="${r.id}">Preview / inspect</button>${r.kind==='reference_excerpt'?`<button type="button" class="textbtn" data-animation-import="${r.id}">Add as illustration</button>`:`<button type="button" class="textbtn" data-animation-adapt="${r.id}">Adapt to a current scene</button>`}<button type="button" class="textbtn" data-reveal="animation" data-local-id="${r.id}">Show in animations folder</button></article>`).join('')||'<small>No saved animations yet. Native templates keep editable specs; reference clips retain baked pixels. New episodes need their own narration and proof.</small>';
 all('[data-artifact-edit]').forEach(b=>{const r=state.artifacts[b.dataset.artifactEdit];if(r?.plan.kind==='animation_spec'){const button=document.createElement('button');button.type='button';button.className='textbtn';button.dataset.animationSaveScene=r.id;button.textContent='Save to animations';b.parentElement.appendChild(button);}});
}
function drawGenerative(){
 const runs=Object.values(state.generative_runs||{}),trained=runs.filter(r=>r.receipt.task==='video_diffusion_lora');el('generateIllustration').disabled=!trained.length;
 el('generativeRuns').innerHTML=runs.map(r=>`<article class="cue-card"><strong>${esc(r.receipt.base_model||'CogVideoX candidate')}</strong><small>${r.receipt.task==='video_diffusion_lora'?r.receipt.actual_optimizer_steps+' actual optimizer steps':'Kaggle generation · adapter loaded: '+Boolean(r.receipt.weights_loaded)} · ${esc(r.status)}<br>Run ${r.id.slice(0,8)} · source ${esc(r.source_kernel||'Imported receipt')}</small>${(r.receipt.outputs||[]).map((v,i)=>`<div class="dialogactions"><button type="button" class="textbtn" data-generated-preview="${r.id}" data-generated-index="${i}">${esc(v.label)} · Preview ${i+1}</button>${v.label==='candidate'?`<button type="button" class="soft" data-generated-scene="${r.id}" data-generated-index="${i}">Create illustration scene</button>`:''}</div>`).join('')}</article>`).join('')||'<small>No generative model result imported. Built-in animations remain available.</small>';
 el('generativeJobs').innerHTML=Object.values(state.generative_jobs||{}).map(j=>`<article class="cue-card"><strong>${esc(j.status)}</strong><p>${esc(j.prompt)}</p><small>Private Kaggle · prompt only · seed ${j.seed}</small><button type="button" class="soft" data-generative-check="${j.id}">Refresh generation</button></article>`).join('');
}
function compositionFields(p){const c=p.composition||{};return `<details open><summary>Presenter composition</summary><label>Layout<select id="scenePresenterLayout"><option value="full_demo" ${c.layout!=='presenter_pip'?'selected':''}>Current scene</option><option value="presenter_pip" ${c.layout==='presenter_pip'?'selected':''}>Presenter inset</option></select></label><label>Shape<select id="scenePresenterShape"><option value="circle" ${c.pip_shape!=='rectangle'?'selected':''}>Circle</option><option value="rectangle" ${c.pip_shape==='rectangle'?'selected':''}>Rectangle</option></select></label><label>Position<select id="scenePresenterCorner">${['bottom_right','bottom_left','top_right','top_left','auto'].map(k=>`<option value="${k}" ${(c.pip_corner||'bottom_right')===k?'selected':''}>${k.replaceAll('_',' ')}</option>`).join('')}</select></label><label>Diameter / canvas width<input id="scenePresenterSize" type="number" min=".18" max=".36" step=".01" value="${c.pip_width??.25}"></label>${['Center X','Center Y','Zoom'].map((label,i)=>`<label>${label}<input type="number" data-scene-presenter-crop="${i}" min="${i===2?1:0}" max="${i===2?3:1}" step=".01" value="${c.pip_crop?.[i]??[.5,.38,1][i]}"></label>`).join('')}<small>Crop centers use the fitted presenter canvas (0–1), zoom 1–3. Caption/result conflicts require moving or resizing. Voice and SFX stay unchanged.</small></details>`;}
function readComposition(){return {layout:el('scenePresenterLayout').value,pip_shape:el('scenePresenterShape').value,pip_corner:el('scenePresenterCorner').value,pip_width:Number(el('scenePresenterSize').value),pip_crop:all('[data-scene-presenter-crop]').map(x=>Number(x.value))};}
function artifactEditor(id){
 const r=state.artifacts[id],p=r.plan,parts=state.storyboards?.[r.job]?.passages||[];
 if(p.kind==='animation_spec'){
  dialog('Edit animation spec',`${compositionFields(p)}<button type="button" class="soft" data-save-composition="${id}" data-scene-version="${r.version}" ${r.locked?'disabled':''}>Save presenter layout only</button><p>${esc(p.source_quote)}</p><small>${esc(p.status)} · ${esc(p.animation.model.mode)} · ${esc(p.animation.model.checkpoint_sha256||'rules; no weights')}</small>${p.animation.spec.objects.map((o,i)=>`<details open><summary>${esc(o.id)} · source ${esc(o.anchor)}</summary>${motionBackgroundControls(o,i)}${o.text!==undefined?`<label>Visible text<textarea rows="2" data-motion-text="${i}">${esc(o.text)}</textarea></label><label>Font size<input type="number" data-motion-font="${i}" min="38" max="92" value="${o.font_size}"></label>`:''}<div class="roi-inputs">${['x','y','width','height'].map((k,j)=>`<label>${k} (0–1)<input type="number" min="0" max="1" step="0.01" data-motion-rect="${i}" data-coordinate="${j}" value="${o.rect[j]}"></label>`).join('')}</div><label>Entrance (frames)<input type="number" min="${Math.max(1,o.keyframes.length-1)}" max="60" data-motion-entrance="${i}" value="${o.keyframes.at(-1).frame}"></label>${o.text!==undefined?`<label>Entrance tilt (°)<input type="number" min="0" max="45" step="0.5" data-motion-tilt="${i}" value="${Math.max(...o.keyframes.map(k=>Math.abs(k.rotation||0)))}"></label>`:''}<label>Readable hold (frames)<input type="number" min="12" max="180" data-motion-hold="${i}" value="${o.hold_frames}"></label>${motionReplacementControls(o,i)}</details>`).join('')}${(p.animation.spec.sfx||[]).map((s,i)=>`<div class="scene-controls"><label><input type="checkbox" data-motion-sound="${i}" checked> ${esc(s.id)} · ${esc(s.anchor)}</label><label>Gain dB<input type="number" min="-60" max="-6" data-motion-gain="${i}" value="${s.gain_db??-26}"></label></div>`).join('')}<label>Save edits from<select id="motionEditMode"><option value="controls">Controls above</option><option value="json">Advanced JSON below</option></select></label><details><summary>Advanced · source anchors, replacement states and keyframes</summary><textarea id="motionSpecEditor" rows="18">${esc(JSON.stringify(p.animation,null,2))}</textarea></details><p>Music remains independent in Style. Manual specifications survive preview regeneration.</p><button type="button" class="primary" data-save-motion="${id}" data-scene-version="${r.version}" ${r.locked?'disabled':''}>Save new scene version</button><button type="button" class="soft" data-motion-lock="${id}">${r.locked?'Unlock scene':'Lock scene'}</button>`);return;
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
  persistDraft();
  let saved;
  try{saved=await req("/api/update", { ids: selectedIds(), revisions:formRevisions, changes });}
  catch(error){if(error.status===409)showSavedDraft();throw error;}
  formRevisions=saved.revisions;
  if(editRevision===savingRevision)sessionStorage.removeItem(draftKey());else persistDraft();
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
    if(b.id==='componentInventory'){const c=await req('/api/components');dialog('Component inventory',`<p>${c.specified} specified · ${c.render_tested} render-tested · ${c.editorially_approved} editorially approved for delivery.</p><p>Render tests do not replace reviewing this episode’s exact master.</p>${c.components.map(r=>`<p><strong>${r.id} · ${esc(r.name)}</strong><br><small>v${esc(r.version)} · ${r.render_tested?'Render-tested variant':'Specified / separate validation needed'} · ${esc(r.limitation)}<br>Renderer: ${esc(r.renderer||'Unavailable')} · ${esc(r.kind)}<br>Parameters: ${esc(r.parameters.join(', ')||'None declared')}<br>Requires: ${esc(r.requirements.join('; '))}<br>${esc(r.validation)}</small></p>`).join('')}`);return;}
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
      b.disabled=true;try{const r=await firstCut(selectedIds(),el('creatorNiche').value===el('creatorNiche').dataset.original?undefined:el('creatorNiche').value,el('creatorFormat').value===el('creatorFormat').dataset.original?undefined:el('creatorFormat').value);
       if(r.setup_required){dialog('Local captions · first use',`<p>${esc(r.speech_setup.download)}</p><p>Destination: ${esc(r.speech_setup.destination)}</p><p>Only model/dependency files are downloaded. Your recording stays local. Future runs use the cache offline.</p><button type="button" id="setupLocalCaptions" class="primary">Download local captions</button><button type="button" id="attachCreatorScript" class="soft">Use a prepared TXT / SRT instead</button>`);}
       else{el('modal').close();versionKey='';await refresh();notify(`First cut queued: ${r.queued}. Uncertain words and proof stay pending.`);}
      }finally{b.disabled=false;}return;
    }
    if(b.id==='setupLocalCaptions'){await req('/api/creator/setup',{});el('modal').close();await refresh();notify('Local captions setup started. Progress appears above the recordings.');return;}
    if(b.id==='attachCreatorScript'){if(selectedIds().length!==1)throw Error('Select one recording to attach its prepared script.');el('creatorScriptInput').click();return;}
    if(b.dataset.saveCreatorBrief){const id=b.dataset.saveCreatorBrief;await req('/api/creator/brief',{id,revision:state.jobs[id].revision,text:el('creatorBrief').value});versionKey='';await refresh();notify('Brief saved; render a new cut for review.');return;}
    if(b.dataset.auditionOpenings){
      const job=b.dataset.auditionOpenings;b.disabled=true;
      try{
        const r=await req('/api/creator/openings',{id:job});
        const shot=state.assets[r.proof.asset]?.name||'assigned result footage';
        const candidates=[['host','Presenter first','host_first','Opens on the recorded presenter.'],['proof','Result first','proof_first',`Opens on ${shot} at source ${time(r.proof.source_range[0])}.`]];
        dialog('Compare openings',`<p>Both options use the same recorded line: “${esc(r.quote)}”. These are editorial choices, not proven winners.</p><div class="opening-grid">${candidates.map(([key,label,mode,reason])=>`<section><h3>${label}</h3><video controls playsinline preload="metadata" id="opening-${key}" aria-label="${label} preview" src="/openings/${r.id}/${key}"></video><p>${esc(reason)}</p><button type="button" class="soft" data-play-opening="${key}">Play into the body</button><button type="button" class="textbtn" data-opening-choice="${mode}" data-audition="${r.id}">Choose ${label.toLowerCase()}</button></section>`).join('')}</div><section class="opening-body"><h3>Same body for both</h3><video controls playsinline id="openingBody" aria-label="Shared edited body" src="/exports/${r.baseline_export}/mp4"></video><p id="openingPlaybackStatus" role="status">The preview switches to the shared body after ${r.duration} seconds. Playback may pause briefly at the switch.</p></section><p><small>Check whether the result supports the line. Choosing an opening requires a new cut and review.</small></p>`);
        for(const [key] of candidates){const preview=el('opening-'+key);preview.addEventListener('ended',()=>{const body=el('openingBody');if(!body)return;body.currentTime=r.duration;body.play().then(()=>{el('openingPlaybackStatus').textContent='Playing the shared body.';}).catch(()=>{el('openingPlaybackStatus').textContent='Press play on the shared body to continue.';});});}
      }finally{b.disabled=false;}return;
    }
    if(b.dataset.playOpening){const body=el('openingBody');body.pause();for(const v of all('[id^="opening-"]'))v.pause();const preview=el('opening-'+b.dataset.playOpening);preview.currentTime=0;await preview.play();el('openingPlaybackStatus').textContent='Playing the opening; the shared body follows.';return;}
    if(b.dataset.openingChoice){await req('/api/creator/opening-choice',{audition:b.dataset.audition,mode:b.dataset.openingChoice});el('modal').close();versionKey='';await refresh();notify('Opening saved. Render a new version; original narration and old cuts are kept.');return;}
    if(b.dataset.previewPassage){const id=b.dataset.previewPassage;playsource(id);const video=el('dialogBody').querySelector('video'),start=Number(b.dataset.from),end=Number(b.dataset.to);video.addEventListener('loadedmetadata',()=>{video.currentTime=start;},{once:true});video.addEventListener('timeupdate',()=>{if(video.currentTime>end)video.pause();});return;}
    if(b.dataset.creatorTrim||b.dataset.restoreTake){const id=b.dataset.creatorTrim||b.dataset.restoreTake;await req('/api/creator/trim',{id,revision:state.jobs[id].revision,start:b.dataset.restoreTake?0:Number(el('creatorKeepStart').value),end:b.dataset.restoreTake?state.assets[id].duration:Number(el('creatorKeepEnd').value)});versionKey='';await refresh();notify('Source cut saved. Prior cuts remain; check meaning and joins on the next export.');return;}
    if(b.dataset.acceptBroll){const id=b.dataset.acceptBroll,q=state.jobs[id].creator.broll_suggestions[Number(b.dataset.suggestion)];await req('/api/update',{ids:[id],changes:{inserts:[...state.jobs[id].settings.inserts,{id:crypto.randomUUID(),asset:q.asset,at:q.at,offset:q.offset,duration:q.duration,cue:'',reason:q.reason}]}});versionKey='';await refresh();return;}
    if(b.id==='addBroll'){el('brollInput').click();return;}
    if(b.id==='addStyleReference'){el('styleReferenceInput').click();return;}
    if(b.dataset.describeFootage){const id=b.dataset.describeFootage,a=state.assets[id];dialog('Describe usable footage',`<p>${esc(a.name)} · tags help match ordinary filenames; no action/result is inferred from a filename alone.</p><textarea id="footageDescription" rows="4">${esc(a.description||'')}</textarea><fieldset><legend>Belongs to these recordings</legend>${Object.keys(state.jobs).map(k=>`<label><input type="checkbox" data-footage-owner="${k}" ${(a.owner_jobs?.includes(k)||!a.owner_jobs?.length&&selectedIds().includes(k))?'checked':''}>${esc(sourceName(k))}</label>`).join('')}</fieldset><button type="button" class="primary" data-save-footage-label="${id}">Save label & assignment</button>`);return;}
    if(b.dataset.saveFootageLabel){await req('/api/creator/asset-label',{id:b.dataset.saveFootageLabel,description:el('footageDescription').value,owners:all('[data-footage-owner]:checked').map(x=>x.dataset.footageOwner)});el('modal').close();await refresh();return;}
    if(b.id==='addGraphic'){el('graphicInput').click();return;}
    if(b.id==='generateArtifacts'){await save();dialog('Generate intro & demos',`<p>Use each recording’s own script. A script alone does not prove these words were recorded.</p><label>Animation planner<select id="animationMode"><option value="">Current native rules</option><option value="rules">Editable scene specs · rules baseline</option><option value="base_rag">Base model + frozen train-only RAG · local runtime required</option><option value="fine_tuned">Fine-tuned spec adapter + same RAG · experimental</option></select></label>${selectedIds().length===1?'<label>Intro promise · optional<input id="introHeadline" maxlength="140" placeholder="What will this episode help the viewer do?"></label><small>Visual headline for this recording only. Keep it supported by the script/brief; recorded voice and captions stay unchanged.</small>':'<p>Set an intro promise on each recording separately.</p>'}<label>Intro layout<select id="introLayout" disabled><option value="full">Full screen · existing default</option><option value="host">Keep presenter · headline above face</option></select></label><small>Choose an editable scene planner to set the intro layout. Existing scenes stay unchanged until you replace them.</small><label>Animation style<select id="animationStyle"><option value="balanced">Balanced · clear explanation</option><option value="maverick_fast">Maverick · fast emphasis</option></select></label><label><input type="checkbox" id="useReferenceObservations" checked> Guide new proposals with observations from the selected reference</label><label><input type="checkbox" id="sceneSpokenConfirmed"> I have checked that the script matches the recorded words.</label>${sourceObservationFields()}${designFields()}${selectedIds().length===1?evidenceFields(null):'<p>For a batch, proof remains unassigned until you attach it to the intended scene. Shared pacing is preserved.</p>'}<button type="button" class="primary" id="confirmGenerateArtifacts">Generate storyboard & previews</button>`);return;}
    if(b.id==='confirmGenerateArtifacts'){b.disabled=true;b.textContent='Generating original scenes…';try{await req('/api/artifacts/generate',{ids:selectedIds(),evidence:readSceneEvidence(),spoken_confirmed:el('sceneSpokenConfirmed').checked,design:readSceneDesign(),animation_mode:el('animationMode').value||null,animation_style:el('animationStyle').value,intro_layout:el('introLayout').value,observations:readSourceObservations(),reference_guidance:el('useReferenceObservations').checked,intro_headline:el('introHeadline')?.value||null});el('modal').close();versionKey='';await refresh();showPanel('script');notify('Storyboard and independent scene previews created. Review the original quote and any pickups.');}finally{b.disabled=false;}return;}
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
    if(b.dataset.saveComposition){const r=state.artifacts[b.dataset.saveComposition];b.disabled=true;try{await req('/api/artifacts/edit',{id:r.id,version:Number(b.dataset.sceneVersion),changes:{composition:readComposition()}});el('modal').close();await refresh();notify('Presenter layout saved as a new scene version. Voice and sound cues retained.');}finally{b.disabled=false;}return;}
    if(b.dataset.saveMotion){const r=state.artifacts[b.dataset.saveMotion],animation=el('motionEditMode').value==='json'?JSON.parse(el('motionSpecEditor').value):JSON.parse(JSON.stringify(r.plan.animation));if(el('motionEditMode').value==='controls'){animation.spec.objects.forEach((o,i)=>{const text=document.querySelector(`[data-motion-text="${i}"]`);if(text){o.text=text.value;o.font_size=Number(document.querySelector(`[data-motion-font="${i}"]`).value);o.box_style=document.querySelector(`[data-motion-background="${i}"]`).value;if(!animation.context.texts.includes(o.text)){animation.context.texts.push(o.text);animation.context.voice_aligned=false;}}o.rect=all(`[data-motion-rect="${i}"]`).map(x=>Number(x.value));const tilt=document.querySelector(`[data-motion-tilt="${i}"]`);o.keyframes=retimeMotionKeys(o.keyframes,Number(document.querySelector(`[data-motion-entrance="${i}"]`).value),tilt?Number(tilt.value):null);o.hold_frames=Number(document.querySelector(`[data-motion-hold="${i}"]`).value);readMotionReplacementControls(animation,o,i);});if('sfx' in animation.spec)animation.spec.sfx=animation.spec.sfx.filter((s,i)=>{s.gain_db=Number(document.querySelector(`[data-motion-gain="${i}"]`).value);return document.querySelector(`[data-motion-sound="${i}"]`).checked;});}b.disabled=true;try{await req('/api/artifacts/edit',{id:r.id,version:Number(b.dataset.sceneVersion),changes:{animation}});el('modal').close();await refresh();}finally{b.disabled=false;}return;}
    if(b.dataset.motionLock){const r=state.artifacts[b.dataset.motionLock];await req('/api/artifacts/edit',{id:r.id,version:r.version,changes:{locked:!r.locked}});el('modal').close();await refresh();return;}
    if(b.dataset.artifactPreview){const r=state.artifacts[b.dataset.artifactPreview];dialog(r.plan.title,`<video controls src="/artifacts/${r.id}/preview?v=${r.version}"></video><p>${esc(r.status)} · ${esc(r.plan.narration_status)}</p><blockquote>${esc(r.plan.source_quote)}</blockquote><p>${esc(artifactVisual(r.plan))}</p><div class="dialogactions"><a class="link" download href="/artifacts/${r.id}/preview?download=1">Export MP4</a><a class="link" download href="/artifacts/${r.id}/source?download=1">Editable scene JSON</a><a class="link" download href="/artifacts/${r.id}/timeline?download=1">Timeline</a></div>`);return;}
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
    if(b.dataset.showReference){if(state.assets[b.dataset.showReference]?.source_role==='style_reference')throw Error('Add this file as footage to include before placing it in the video.');if(selectedIds().length!==1)throw Error('Select one recording to add its on-screen demonstration.');inserts.push({asset:b.dataset.showReference,at:0,offset:0,duration:Math.min(2,state.assets[b.dataset.showReference].duration,state.assets[selectedIds()[0]].duration)});setDirty('inserts');showPanel('inserts');drawInserts();return;}
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
        const r = refs().find(a=>a.source_role!=='style_reference');
        if (!r) throw Error("Add footage to include first.");
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
          const readyIds=selectedIds().filter(k=>!state.jobs[k].archived&&!locked(state.jobs[k])&&state.jobs[k].status!=="Failed"&&state.jobs[k].settings.script.trim()&&!state.jobs[k].script_issue);
          const r = await req("/api/queue", { ids: readyIds,request_id:crypto.randomUUID() });
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
  if(e.target.dataset.pipCrop!==undefined){const i=Number(e.target.closest('[data-insert]').dataset.insert);inserts[i].pip_crop??=[.5,.38,1];inserts[i].pip_crop[Number(e.target.dataset.pipCrop)]=Number(e.target.value);setDirty('inserts');return;}
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
    inserts[i][k] = ["asset", "cue", "layout", "pip_corner", "pip_shape", "demonstrates", "visual_claim"].includes(k)
      ? e.target.value
      : Number(e.target.value);
    if(k==='cue')delete inserts[i].occurrence;
    if(k==='pip_shape'){inserts[i].pip_corner??=inserts[i].pip_shape==='circle'?'bottom_right':'auto';drawInserts();}
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
// Creator workspace: presentation over the existing, versioned Cutroom handlers.
(() => {
  const root = document.createElement('section'); root.id = 'creatorRoom';
  const layout = document.querySelector('#work .layout');
  const advanced = document.createElement('details'); advanced.className='creator-advanced';
  advanced.innerHTML='<summary>Batch workflow & advanced editing</summary>';
  layout.before(root, advanced); advanced.append(layout);
  document.querySelector('#work .sectionhead h1').textContent='Your cut';
  document.querySelector('#work .sectionhead p').textContent='Bring your recording. Make a first cut, then make it yours.';
  const cutForPassage=id=>Boolean(latestFor(id)&&state.jobs[id]?.passage_revision===state.jobs[id]?.revision);
  const originalDraw=draw; let signature='', chosenBeat=-1, captionDraft=null, shotDraft=null; const roomProjects=new Map(), nicheDrafts=new Map();
  draw=function(){originalDraw(); renderRoom();};
  const format=t=>time(Math.max(0,Number(t)||0));
  function editTime(t, keep){let offset=0; for(const [a,b] of keep||[]){if(t>=a&&t<b)return offset+t-a; offset+=b-a;} return null;}
  function selectedBeat(job,index){
    const cut=latestFor(job.id),project=cut&&roomProjects.get(cut.id);
    return project?.beats?.[index];
  }
  function selectBeat(index){
    chosenBeat=index;
    root.querySelectorAll('.room-beat.selected').forEach(x=>{x.classList.remove('selected');x.querySelector('.beat-actions')?.remove();});
    const button=root.querySelector(`[data-room-beat="${index}"]`), row=button?.closest('.room-beat');
    if(!row)return;
    row.classList.add('selected');
    root.querySelectorAll('.timeline-clip').forEach(x=>x.classList.toggle('selected',x.dataset.roomBeat===String(index)));
    row.insertAdjacentHTML('beforeend','<div class="beat-actions"><button type="button" class="soft" data-room-correct="'+index+'">Correct caption</button><button type="button" class="textbtn" data-room-shot="'+index+'">Replace shot</button><button type="button" class="textbtn" data-room-restore>Restore entire take</button><button type="button" class="textbtn" data-room-scenes>Scene plan & style board</button></div>');
  }
  function renderRoom(force=false){
    if(!state.jobs)return;
    const ids=selectedIds(), id=ids.length===1?ids[0]:null, j=id&&state.jobs[id], a=id&&state.assets[id], cut=id&&latestFor(id);
    const key=JSON.stringify([ids,Object.values(state.jobs).map(x=>[x.id,x.revision,x.status,x.stage,x.latest]),Object.values(state.assets).map(x=>[x.id,x.source_role,x.owner_jobs]),state.speech_setup?.status]);
    if(!force&&key===signature)return; signature=key;
    const names=Object.values(state.jobs).filter(x=>!x.archived).map(x=>`<option value="${esc(x.id)}" ${id===x.id?'selected':''}>${esc(sourceName(x.id))} · ${esc(x.status)}</option>`).join('');
    const own=id?refs().filter(x=>(x.owner_jobs||[]).includes(id)):[];
    const roleList=role=>own.filter(x=>x.source_role===role).map(x=>`<li class="room-media-item">${thumb(x)}<span><strong>${esc(x.name)}</strong><small>${role==='broll'?'Can be placed in cut':'Style only · stays off screen'}</small></span>${role==='broll'?`<button type="button" class="textbtn" data-room-assign="${esc(x.id)}">Assign</button>`:''}</li>`).join('')||'<li class="room-media-empty">None added</li>';
    if(cut&&!roomProjects.has(cut.id)){
      roomProjects.set(cut.id,null);
      fetch(`/api/creator/editor?id=${encodeURIComponent(id)}&export=${encodeURIComponent(cut.id)}`).then(r=>{if(!r.ok)throw Error('Project unavailable');return r.json();}).then(project=>{roomProjects.set(cut.id,project);signature='';renderRoom();}).catch(()=>{roomProjects.set(cut.id,false);signature='';renderRoom();});
    }
    const project=cut&&roomProjects.get(cut.id), plan=project?.plan;
    const stale=cut&&cut.revision!==j.revision, beats=project?.beats||[], canMap=Boolean(cut&&!stale&&project?.editable&&!locked(j));

    const proof=(j?.settings?.inserts||[]).find(q=>state.assets[q.asset]?.source_role==='broll' && q.anchors?.result!=null && Number(q.offset||0)+Number(q.duration||0)-Number(q.anchors.result)>=2);
    const stage=j?.stage && j.status!=='Draft'?`<p class="room-stage" role="status"><strong>${esc(j.status)}</strong> · ${esc(j.stage)}${j.status==='Failed'?' · Check the recording or script, correct the problem, then make the cut again.':''}</p>`:'';
    let review='';
    if(cut){
      const issues=j.creator?.uncertain||[];
      const rows=beats.map((b,i)=>{const t=b.segments?.[0]?.edit_start??null, shot=(project?.settings?.inserts||j.settings.inserts||[]).find(q=>q.at<=b.source_start&&q.at+q.duration>b.source_start), picture=shot?state.assets[shot.asset]?.name:'Presenter';
        const caption=(plan?.captions||[]).flat().filter(w=>w[0]>=b.source_start-.05&&w[1]<=b.source_end+.05).map(w=>w[2]).join(' ');
        return `<div class="room-beat ${i===chosenBeat?'selected':''}"><button type="button" data-room-beat="${i}" ${!canMap||t===null?'disabled':''}><span class="room-time">${t===null?'Removed':format(t)}</span><span><strong>${esc(b.quote)}</strong><small>${caption?`Caption in ${cutVersion(cut)}: ${esc(caption)}<br>`:''}Planned picture: ${esc(picture||'Assigned footage')} · check the player · source ${format(b.source_start)}</small></span></button>${i===0&&proof&&canMap?`<button type="button" class="soft" data-audition-openings="${id}">Compare openings</button>`:''}${i===chosenBeat&&canMap?`<div class="beat-actions"><button type="button" class="soft" data-room-correct="${i}">Correct caption</button><button type="button" class="textbtn" data-room-shot="${i}">Replace shot</button><button type="button" class="textbtn" data-room-restore>Restore entire take</button><button type="button" class="textbtn" data-room-scenes>Scene plan & style board</button></div>`:''}</div>`;}).join('');
      review=`<div class="room-review"><section class="room-player"><div class="room-player-head"><div><span class="eyebrow">${stale?'Previous edited cut':'Edited cut'} · ${cutVersion(cut)}</span><h2>${esc(sourceName(id))}</h2></div><button type="button" class="textbtn" data-room-original>Watch original</button></div><video id="roomVideo" controls playsinline aria-label="Edited cut ${cutVersion(cut)}" src="/exports/${cut.id}/mp4"></video><p>${stale?'Your edits have changed since this cut. Make a new cut and review that version.':`This is ${cutVersion(cut)} of your edited video.`}</p><div class="room-buttons"><button type="button" class="primary" data-room-review="${cut.id}">Review & export ${cutVersion(cut)}</button><a class="soft" href="/exports/${cut.id}/mp4?download=1" download>Download video</a></div></section><section class="room-story"><div class="room-story-head"><div><span class="eyebrow">STORYBOARD</span><h2>Listen through the words</h2></div>${issues.length===3&&canMap?'<button class="soft" type="button" data-room-issues>Check 3 moments</button>':''}</div>${stale?'<p class="room-note">These spoken phrases are from the earlier cut. Make a new cut before seeking.</p>':''}${project===false?'<p class="room-note" role="alert">Saved cut could not be loaded. Editing is disabled.</p><button type="button" class="soft" data-room-retry>Retry loading cut</button>':rows||'<p class="room-note">Loading saved passages, or no timed captions available. Use advanced editing for untimed scripts.</p>'}</section></div>`;
    }
    root.innerHTML=`<div class="room-top"><div><span class="eyebrow">CUTROOM / ${cut?'REVIEW':'IMPORT'}</span><h2>${cut?(stale?'Your previous cut':'Your cut is ready to watch'):'Start with your recording'}</h2><p>${cut?'Watch the edited cut beside the words. Choose a phrase to hear it in context.':'Add a recording, then add any helpful material before making your first cut.'}</p></div>${names?`<label class="room-select">Recording<select id="roomRecording"><option value="">Choose a recording</option>${names}</select></label>`:''}</div>
    ${!names?'<div class="room-drop" aria-label="Add recording"><strong>Drop your recording here</strong><span>or choose one or more video files</span><button type="button" class="primary" data-room-add>Add recording</button></div>':!id?'<p class="room-note">Choose one recording above, or open Batch workflow to select several.</p>':`<div class="room-recording">${thumb(a)}<div><strong>${esc(a.name)}</strong><small>Original recording · ${format(a.duration)} · ${esc(j.status)}</small></div><button type="button" class="textbtn" data-room-original>Watch original</button></div>${stage}<div class="room-inputs"><div><span class="eyebrow">OPTIONAL INPUTS · ${esc(sourceName(id))}</span><p>Footage to include is available for this recording; choose where to place it. A style reference guides pacing and style and will not appear by itself.</p></div><div class="room-input-grid"><section><h3>Script</h3><p>${j.settings.script.trim()?'Attached to this recording':'Optional · captions can be made locally'}</p><button type="button" class="soft" data-room-script>Add script</button></section><section><h3>Footage to include</h3><ul>${roleList('broll')}</ul><button type="button" class="soft" data-room-broll>Add footage</button></section><section><h3>Style reference</h3><ul>${roleList('style_reference')}</ul><button type="button" class="soft" data-room-style>Add reference</button></section><section><h3>Niche</h3><label for="roomNiche">Who is this for?</label><input id="roomNiche" maxlength="500" value="${esc(nicheDrafts.has(id)?nicheDrafts.get(id):j.settings.niche||'')}" placeholder="e.g. fitness creators"></section></div></div><div class="room-start"><span>${cut?(stale?'Changes need a new cut before review.':'You are viewing the latest cut.'):'Your original stays intact.'}</span><button type="button" class="primary" data-room-start ${locked(j)?'disabled':''}>${cut?'Make updated cut':'Make first cut'}</button></div>${review}`}`;
    if(id)root.insertAdjacentHTML('beforeend','<button type="button" class="soft" data-room-scenes>Scene plan & style board</button>');
    if(cut){
      root.classList.add('room-has-cut');
      const editor=document.createElement('div');editor.className='room-editor';
      const rail=document.createElement('aside');rail.className='room-media-rail';rail.setAttribute('aria-label','Media for this recording');
      rail.innerHTML='<div class="room-rail-heading"><span class="eyebrow">PROJECT MEDIA</span><strong>Media</strong><small>Files for this recording</small></div>';
      for(const selector of ['.room-recording','.room-inputs','.room-start']){const node=root.querySelector(selector);if(node)rail.append(node);}
      editor.append(rail,root.querySelector('.room-review'));root.append(editor);
      const duration=Math.max(.001,Number(cut.duration)||a.duration), keep=plan?.keep||j.creator?.keep||[[0,a.duration]];
      const timeline=document.createElement('section');timeline.className='room-timeline';timeline.setAttribute('aria-label','Edited cut timeline');
      const ticks=[0,.25,.5,.75,1].map(p=>`<span>${format(duration*p)}</span>`).join('');
      const clips=beats.map((beat,i)=>{return (beat.segments||[]).map(segment=>{const begin=segment.edit_start,finish=segment.edit_end;const left=Math.max(0,Math.min(100,begin/duration*100)),width=Math.max(.5,Math.min(100-left,(finish-begin)/duration*100));return `<button type="button" class="timeline-clip" data-room-beat="${i}" style="left:${left}%;width:${width}%" aria-label="Play passage at ${format(begin)}: ${esc(beat.quote)}" ${!canMap?'disabled':''}><span>${esc(beat.quote)}</span></button>`;}).join('');}).join('');
      const pictures=(plan?.proof||[]).map(q=>{const begin=editTime(q.start,keep),end=editTime(Math.max(q.start,q.end-.001),keep);if(begin===null||end===null)return '';const left=Math.max(0,Math.min(100,begin/duration*100)),width=Math.max(.5,Math.min(100-left,(end-begin+.001)/duration*100)),asset=state.assets[q.asset_id];return `<span class="timeline-picture" style="left:${left}%;width:${width}%" title="${esc(q.source_name||'Assigned footage')}">${asset?thumb(asset):''}<span>${esc(q.source_name||'Assigned footage')}</span></span>`;}).join('');
      timeline.innerHTML=`<div class="timeline-head"><div><span class="eyebrow">EDITED CUT · ${esc(cutVersion(cut))}</span><h2>Timeline</h2></div><span class="timeline-duration">${format(duration)}</span></div><div class="timeline-grid"><div class="timeline-label">Time</div><div class="timeline-ruler">${ticks}</div><div class="timeline-label">Picture</div><div class="timeline-source">${thumb(a)}<span>${esc(a.name)} · presenter</span>${pictures}</div><div class="timeline-label">Speech</div><div class="timeline-track">${clips||'<small>Timed passages will appear when available.</small>'}</div></div><small class="timeline-help">Select a speech segment to play it in context. Picture segments reflect the saved edit plan; check the player.</small>`;
      root.append(timeline);
    }else root.classList.remove('room-has-cut');
  }
  root.addEventListener('input',e=>{if(e.target.id==='roomNiche'&&selectedIds().length===1)nicheDrafts.set(selectedIds()[0],e.target.value);});
  root.addEventListener('change',e=>{if(e.target.id==='roomRecording'&&e.target.value){chosenBeat=-1;changeSelection([e.target.value]);}});
  root.addEventListener('dragover',e=>{if(e.target.closest('.room-drop')){e.preventDefault();e.target.closest('.room-drop').classList.add('drag');}});
  root.addEventListener('dragleave',e=>e.target.closest('.room-drop')?.classList.remove('drag'));
  root.addEventListener('drop',guard(async e=>{if(!e.target.closest('.room-drop'))return;e.preventDefault();await upload([...e.dataTransfer.files],'host');}));
  root.addEventListener('keydown',e=>{if(e.target.classList.contains('room-drop')&&['Enter',' '].includes(e.key)){e.preventDefault();el('hostInput').click();}});
  root.addEventListener('click',guard(async e=>{
    const b=e.target.closest('button'); if(!b){if(e.target.closest('.room-drop'))el('hostInput').click();return;} const id=selectedIds()[0],j=state.jobs[id];
    if(b.hasAttribute('data-room-scenes')){await openScenePlan(id);return;}
    if(b.hasAttribute('data-room-retry')){roomProjects.delete(latestFor(id).id);signature='';renderRoom();return;}
    if(b.hasAttribute('data-room-add')){el('hostInput').click();return;}
    if(b.hasAttribute('data-room-script')){el('creatorScriptInput').click();return;}
    if(b.hasAttribute('data-room-broll')){el('brollInput').click();return;}
    if(b.hasAttribute('data-room-style')){el('styleReferenceInput').click();return;}
    if(b.dataset.roomAssign){document.querySelector(`[data-describe-footage="${b.dataset.roomAssign}"]`)?.click();return;}
    if(b.hasAttribute('data-room-original')){playsource(id);return;}
    if(b.dataset.roomReview){review(b.dataset.roomReview);return;}
    if(b.hasAttribute('data-room-start')){b.disabled=true;try{if(cutForPassage(id)){
        await req('/api/queue',{ids:[id],request_id:crypto.randomUUID()});
        versionKey='';await refresh();notify('Updated cut queued for '+sourceName(id)+'.');return;
      }await save();const result=await firstCut([id],el('roomNiche').value);versionKey='';await refresh();if(result.setup_required)dialog('Captions need setup',`<p>Your recording is safe. To make captions from this recording, set up local captions once, or attach a prepared script.</p><p>${esc(result.speech_setup.download)}</p><button type="button" id="setupLocalCaptions" class="primary">Set up local captions</button><button type="button" id="attachCreatorScript" class="soft">Use a prepared TXT / SRT</button>`);else notify('First cut queued for '+sourceName(id)+'.');}finally{b.disabled=false;}return;}
    if(b.dataset.roomBeat!==undefined){const i=Number(b.dataset.roomBeat), beat=selectedBeat(j,i),cut=latestFor(id),project=cut&&roomProjects.get(cut.id),t=beat.segments[0].edit_start,player=el('roomVideo');selectBeat(i);player.currentTime=Math.max(0,t-1);player.play().catch(()=>{});return;}
    if(b.dataset.roomCorrect!==undefined){
      const beat=selectedBeat(j,Number(b.dataset.roomCorrect)), view=roomProjects.get(latestFor(id).id), parsed=beat.cues.length?{cues:beat.cues.map(c=>({...c,i:c.index}))}:null;
      if(!parsed)throw Error('Use advanced editing for untimed or boundary-crossing captions.');
      captionDraft={id,revision:j.revision,script:j.settings.script,beat:beat.id,export:view.export,sha256:view.sha256};
      const fields=parsed.cues.map((c,n)=>`<label for="roomCue-${n}">Caption · source ${format(c.start)}–${format(c.end)}</label><textarea id="roomCue-${n}" data-room-cue="${c.i}" rows="2">${esc(c.text)}</textarea>`).join('');
      const choices=refs().filter(a=>a.source_role==='broll'&&(a.owner_jobs||[]).includes(id))
        .map(a=>`<option value="${esc(a.id)}">${esc(a.name)}</option>`).join('');
      dialog('Edit this passage',`<p>Spoken phrase: “${esc(beat.quote)}”</p><p>Edit only the captions in this passage. Their timing stays the same. Save, then make a new cut to check the result.</p>${fields}<label for="roomCaptionShot">Picture for this passage</label><select id="roomCaptionShot"><option value="keep">Keep current picture</option><option value="">Presenter only</option>${choices}</select><button type="button" class="primary" data-room-save-caption="${id}">Save passage</button>`);return;
    }
    if(b.dataset.roomShot!==undefined){
      const beat=selectedBeat(j,Number(b.dataset.roomShot)),available=refs().filter(a=>a.source_role==='broll'&&(a.owner_jobs||[]).includes(id));
      const existing=(j.settings.inserts||[]).findIndex(q=>q.at<beat.source_end&&q.at+q.duration>beat.source_start);
      const view=roomProjects.get(latestFor(id).id);shotDraft={id,revision:j.revision,beat:beat.id,export:view.export,sha256:view.sha256};
      const choices=available.map(a=>`<option value="${esc(a.id)}" ${existing>=0&&j.settings.inserts[existing].asset===a.id?'selected':''}>${esc(a.name)} · ${format(a.duration)}</option>`).join('');
      dialog(existing>=0?'Replace this shot':'Show a shot here',`<p>At source ${format(beat.source_start)} · “${esc(beat.quote)}”</p><p>Choose footage assigned to this recording. The recorded voice continues.</p><label for="roomShotChoice">Picture for this passage</label><select id="roomShotChoice"><option value="">Presenter only</option>${choices}</select>${available.length?'':'<p class="room-note">No footage has been assigned to this recording yet. Add footage to include first.</p>'}<button type="button" class="primary" data-room-save-shot="${id}">Save shot choice</button><p><small>Replacing a shot clears its old proof markers. Check the new shot before treating it as evidence.</small></p>`);return;
    }
    if(b.hasAttribute('data-room-restore')){await req('/api/creator/trim',{id,revision:j.revision,start:0,end:state.assets[id].duration});versionKey='';await refresh();notify('Entire take restored. Make a new cut to review it.');return;}
    if(b.hasAttribute('data-room-issues')){const m=j.creator.uncertain[0];const v=el('roomVideo'),t=editTime(m.source_range[0],j.creator.keep);if(t!==null){v.currentTime=Math.max(0,t-1);v.play().catch(()=>{});}dialog('Check these moments',j.creator.uncertain.map((x,i)=>`<p><strong>Source ${format(x.source_range[0])}</strong> · ${esc(x.reason)}<br>${esc(x.action)}<br><button type="button" class="soft" data-room-moment="${i}">Play this moment</button></p>`).join(''));return;}
  }));
  document.addEventListener('click',guard(async e=>{const moment=e.target.closest('[data-room-moment]');if(moment){const id=selectedIds()[0],j=state.jobs[id],issue=j.creator.uncertain[Number(moment.dataset.roomMoment)],index=j.creator.beats.findIndex(b=>b.source_end>issue.source_range[0]&&b.source_start<issue.source_range[1]);el('modal').close();if(index>=0){chosenBeat=index;renderRoom(true);const v=el('roomVideo'),t=editTime(issue.source_range[0],j.creator.keep);if(t!==null){v.currentTime=Math.max(0,t-1);v.play().catch(()=>{});}notify('Choose a passage action below the selected phrase.');}return;}const b=e.target.closest('[data-room-save-caption]');if(!b)return;const id=b.dataset.roomSaveCaption;b.disabled=true;try{
      if(!captionDraft||captionDraft.id!==id||state.jobs[id].revision!==captionDraft.revision||state.jobs[id].settings.script!==captionDraft.script)throw Error('This recording changed while the editor was open. Reopen the caption and try again.');
      const cues=all('[data-room-cue]').map(field=>({index:Number(field.dataset.roomCue),text:field.value}));
      const asset=el('roomCaptionShot').value;
      await req('/api/creator/passage',{id,revision:captionDraft.revision,export:captionDraft.export,sha256:captionDraft.sha256,beat:captionDraft.beat,cues,...(asset==='keep'?{}:{asset})});captionDraft=null;el('modal').close();versionKey='';await refresh();notify('Caption correction saved. Make an updated cut to review it.');
    }finally{b.disabled=false;}}));
  document.addEventListener('click',guard(async e=>{
    const b=e.target.closest('[data-room-save-shot]');if(!b)return;const id=b.dataset.roomSaveShot;
    if(!shotDraft||shotDraft.id!==id||state.jobs[id].revision!==shotDraft.revision)throw Error('This recording changed while the editor was open. Reopen the shot and try again.');
    const asset=el('roomShotChoice').value;
    b.disabled=true;try{await req('/api/creator/shot',{id,revision:shotDraft.revision,export:shotDraft.export,sha256:shotDraft.sha256,beat:shotDraft.beat,asset});shotDraft=null;el('modal').close();versionKey='';await refresh();notify('Shot choice saved. Make an updated cut to review it.');}finally{b.disabled=false;}
  }));
  renderRoom();
})();

// Vietnamese/English interface. Creator text, filenames and caption fields are never translated.
(() => {
  const words = {
    'Workspace':'Không gian làm việc','Exports':'Bản xuất','Local workspace':'Làm việc trên máy',
    'Workspace settings':'Cài đặt không gian làm việc','Your cut':'Bản dựng của bạn','Bring your recording. Make a first cut, then make it yours.':'Thêm bản quay, tạo bản dựng đầu tiên rồi chỉnh theo ý bạn.',
    '＋ Add recordings':'＋ Thêm bản quay','CUTROOM / REVIEW':'CUTROOM / XEM LẠI','CUTROOM / IMPORT':'CUTROOM / NHẬP TỆP',
    'Your cut is ready to watch':'Bản dựng đã sẵn sàng để xem','Your previous cut':'Bản dựng trước đó','Start with your recording':'Bắt đầu với bản quay của bạn',
    'Watch the edited cut beside the words. Choose a phrase to hear it in context.':'Xem bản dựng bên cạnh lời thoại. Chọn một câu để nghe trong ngữ cảnh.',
    'Add a recording, then add any helpful material before making your first cut.':'Thêm bản quay và các tư liệu cần thiết trước khi tạo bản dựng đầu tiên.',
    'Drop your recording here':'Thả bản quay vào đây','or choose one or more video files':'hoặc chọn một hay nhiều tệp video','Add recording':'Thêm bản quay','Recording':'Bản quay','Choose a recording':'Chọn bản quay',
    'Choose one recording above, or open Batch workflow to select several.':'Chọn một bản quay ở trên, hoặc mở quy trình hàng loạt để chọn nhiều bản.',
    'PROJECT MEDIA':'TƯ LIỆU DỰ ÁN','Media':'Tư liệu','Files for this recording':'Tệp của bản quay này','Watch original':'Xem bản gốc',
    'OPTIONAL INPUTS':'TƯ LIỆU TÙY CHỌN','Script':'Kịch bản','Attached to this recording':'Đã gắn với bản quay này','Optional · captions can be made locally':'Tùy chọn · có thể tạo phụ đề trên máy',
    'Add script':'Thêm kịch bản','Footage to include':'Cảnh có thể đưa vào','Can be placed in cut':'Có thể đưa vào bản dựng','Style only · stays off screen':'Chỉ tham khảo phong cách · không xuất hiện trong video','None added':'Chưa thêm','Assign':'Gán','Add footage':'Thêm cảnh',
    'Style reference':'Video tham khảo phong cách','Add reference':'Thêm video tham khảo','Niche':'Chủ đề','Who is this for?':'Video dành cho ai?','e.g. fitness creators':'Ví dụ: người làm nội dung thể hình',
    'Footage to include is available for this recording; choose where to place it. A style reference guides pacing and style and will not appear by itself.':'Cảnh được thêm có thể đặt vào bản dựng của bản quay này. Video tham khảo chỉ định hướng nhịp và phong cách, không tự xuất hiện trong video.',
    'Your original stays intact.':'Bản gốc của bạn được giữ nguyên.','You are viewing the latest cut.':'Bạn đang xem bản dựng mới nhất.','Changes need a new cut before review.':'Cần tạo bản dựng mới để xem lại các thay đổi.',
    'Make first cut':'Tạo bản dựng đầu tiên','Make updated cut':'Tạo bản dựng mới','Edited cut':'Bản dựng đã chỉnh','Previous edited cut':'Bản dựng trước đó',
    'Your edits have changed since this cut. Make a new cut and review that version.':'Bạn đã chỉnh sửa sau bản dựng này. Hãy tạo bản mới và xem lại đúng phiên bản đó.',
    'Download video':'Tải video','STORYBOARD':'LỜI THOẠI','Listen through the words':'Nghe theo lời thoại','Check 3 moments':'Kiểm tra 3 đoạn',
    'These spoken phrases are from the earlier cut. Make a new cut before seeking.':'Đây là lời thoại của bản trước. Hãy tạo bản mới trước khi chuyển tới từng đoạn.',
    'No timed spoken phrases are available for this cut. Open advanced editing to inspect the script.':'Bản dựng này chưa có lời thoại kèm thời gian. Mở chỉnh sửa nâng cao để xem kịch bản.',
    'Correct caption':'Sửa phụ đề','Replace shot':'Thay cảnh','Restore take':'Khôi phục bản quay','Compare openings':'So sánh đoạn mở đầu',
    'EDITED CUT':'BẢN DỰNG ĐÃ CHỈNH','Timeline':'Dòng thời gian','Time':'Thời gian','Picture':'Hình ảnh','Speech':'Lời thoại',
    'Timed passages will appear when available.':'Các đoạn có thời gian sẽ xuất hiện khi sẵn sàng.',
    'Select a speech segment to play it in context. Picture segments reflect the saved edit plan; check the player.':'Chọn một đoạn lời thoại để nghe trong ngữ cảnh. Các đoạn hình ảnh theo kế hoạch đã lưu; hãy kiểm tra trên trình phát.',
    'Batch workflow & advanced editing':'Xử lý hàng loạt và chỉnh sửa nâng cao','Source recordings':'Bản quay gốc','No recordings yet':'Chưa có bản quay','Select all':'Chọn tất cả','Clear selection':'Bỏ chọn tất cả',
    'Find a source recording':'Tìm bản quay gốc','Project':'Dự án','All projects':'Tất cả dự án','Source visibility':'Hiển thị bản quay','Active sources':'Bản quay đang dùng','Archived':'Đã lưu trữ','All sources':'Tất cả bản quay',
    'B-roll & style library':'Thư viện cảnh và phong cách','＋ Usable B-roll':'＋ Cảnh có thể dùng','＋ Style reference':'＋ Video tham khảo','Other footage':'Tư liệu khác','Show in video':'Đưa vào video','Use for pacing':'Dùng làm nhịp tham khảo','Preview':'Xem trước','Manage':'Quản lý','View cuts':'Xem bản dựng','Edit settings':'Cài đặt chỉnh sửa','Hide settings':'Ẩn cài đặt','Show settings':'Hiện cài đặt','Style':'Phong cách','Cutaways':'Cảnh chèn','Save changes':'Lưu thay đổi','Saved':'Đã lưu','Unsaved changes':'Chưa lưu thay đổi',
    'Draft':'Bản nháp','Queued':'Đang chờ','Rendering':'Đang dựng','For review':'Chờ xem lại','Failed':'Thất bại','Needs input':'Cần bổ sung','Needs revision':'Cần chỉnh sửa','Approved':'Đã duyệt','Interrupted':'Bị gián đoạn',
    'Add a TXT/SRT, or set up local captions once.':'Thêm tệp TXT/SRT hoặc thiết lập phụ đề trên máy một lần.',
    'Multilingual small model ~486MB, plus Python dependencies':'Mô hình đa ngôn ngữ khoảng 486 MB cùng các thành phần Python',
    'Captions need setup':'Cần thiết lập phụ đề','Your recording is safe. To make captions from this recording, set up local captions once, or attach a prepared script.':'Bản quay của bạn vẫn an toàn. Để tạo phụ đề, hãy thiết lập phụ đề trên máy một lần hoặc thêm kịch bản đã chuẩn bị.','Set up local captions':'Thiết lập phụ đề trên máy','Use a prepared TXT / SRT':'Dùng tệp TXT / SRT đã chuẩn bị','Close':'Đóng',
    'Correct caption':'Sửa phụ đề','Script / captions':'Kịch bản / phụ đề','Save caption correction':'Lưu chỉnh sửa phụ đề','Review the words against the recording.':'Đối chiếu lời với bản quay.','Edit only the captions in this passage. Their timing stays the same.':'Chỉ sửa phụ đề trong đoạn này. Thời gian sẽ được giữ nguyên.',
    'The script has no matching timed cues. Edit the full script here and keep any timing information intact.':'Kịch bản không có đoạn phụ đề khớp thời gian. Hãy sửa toàn bộ kịch bản và giữ nguyên thông tin thời gian.',
    'Replace this shot':'Thay cảnh này','Show a shot here':'Đưa cảnh vào đoạn này','Choose footage assigned to this recording. The recorded voice continues.':'Chọn cảnh đã gán cho bản quay này. Giọng nói gốc vẫn tiếp tục.','Picture for this passage':'Hình ảnh cho đoạn này','Presenter only':'Chỉ người nói','Save shot choice':'Lưu lựa chọn cảnh',
    'No footage has been assigned to this recording yet. Add footage to include first.':'Chưa có cảnh nào được gán cho bản quay này. Hãy thêm cảnh trước.','Replacing a shot clears its old proof markers. Check the new shot before treating it as evidence.':'Thay cảnh sẽ xóa các dấu xác minh của cảnh cũ. Hãy kiểm tra cảnh mới trước khi xem là bằng chứng.',
    'Check these moments':'Kiểm tra các đoạn này','Play this moment':'Phát đoạn này','Compare openings':'So sánh đoạn mở đầu','Presenter first':'Người nói trước','Result first':'Kết quả trước','Play into the body':'Phát tiếp vào phần chính','Same body for both':'Cùng một phần chính',
    'Final review':'Xem lại lần cuối','I watched the entire export at1× and phone size.':'Tôi đã xem toàn bộ bản xuất ở tốc độ 1× và kích thước điện thoại.','The speaker, claims, proof and requested CTA are correct.':'Người nói, nội dung, bằng chứng và lời kêu gọi hành động đều chính xác.','Captions are accurate, readable and on time.':'Phụ đề chính xác, dễ đọc và đúng thời điểm.','I listened for clear speech, sync and unobtrusive sound effects.':'Tôi đã nghe để kiểm tra giọng nói, đồng bộ và hiệu ứng âm thanh.','Download MP4':'Tải MP4','Captions (.srt)':'Phụ đề (.srt)','Request revision':'Yêu cầu chỉnh sửa','Approve export':'Duyệt bản xuất','Save feedback only':'Chỉ lưu góp ý','Show MP4 in Explorer':'Mở vị trí MP4','Timecode and correction (required for revisions)':'Thời điểm và nội dung cần sửa (bắt buộc khi yêu cầu chỉnh sửa)',
    'Your name':'Tên của bạn','Person who watched and listened':'Người đã xem và nghe','I explicitly attest that I watched and listened to this entire exact MP4 at 1× and phone size. My name and decision apply only to this run and SHA256.':'Tôi xác nhận đã xem và nghe toàn bộ đúng tệp MP4 này ở tốc độ 1× và kích thước điện thoại. Tên và quyết định của tôi chỉ áp dụng cho bản xuất và mã SHA256 này.',
    'A · Opening, payoff and CTA':'A · Mở đầu, kết quả và lời kêu gọi hành động','B · Visible target, action and readable result':'B · Đối tượng, thao tác và kết quả dễ đọc','C · Vietnamese names, numbers and caption timing':'C · Tên tiếng Việt, số liệu và thời gian phụ đề','D · Animation purpose and SFX alignment':'D · Mục đích chuyển động và đồng bộ hiệu ứng âm thanh','E · Intact speech, natural cuts and intelligible mix':'E · Lời nói đầy đủ, điểm cắt tự nhiên và âm thanh rõ','F · Export, captions and reproducible recipe':'F · Bản xuất, phụ đề và thiết lập có thể lặp lại',
    'Check lip sync at these moments; enter the observed offset in output frames (0 if aligned).':'Kiểm tra đồng bộ khẩu hình tại các thời điểm này; nhập độ lệch theo khung hình đầu ra (0 nếu khớp).','e.g. 00:12 · Cutaway covers the result.':'Ví dụ: 00:12 · Cảnh chèn che khuất kết quả.','00:12 · What you saw or heard…':'00:12 · Điều bạn nhìn thấy hoặc nghe được…',
    'A · Opening and payoff':'A · Mở đầu và kết quả','B · Visual proof':'B · Bằng chứng hình ảnh',
    'Download selected edits':'Tải các bản dựng đã chọn','Share a style guide or cutaway across your recordings.':'Dùng chung video tham khảo hoặc cảnh chèn cho các bản quay.','Usable B-roll':'Cảnh có thể sử dụng','Style only · not inserted automatically':'Chỉ tham khảo phong cách · không tự đưa vào video','Library footage · explicit assignment required':'Tư liệu thư viện · cần gán trước khi sử dụng',
    'Label / assign to recording':'Đặt nhãn / gán cho bản quay','Reference profile':'Thông tin video tham khảo','Include in training':'Đưa vào dữ liệu huấn luyện','＋ Add screenshot / logo':'＋ Thêm ảnh màn hình / logo','Match to scripts':'Ghép với kịch bản',
    'Use a filename like “save the result.mp4” to match a spoken phrase.':'Dùng tên tệp như “save the result.mp4” để ghép với câu nói.','▶ Preview source':'▶ Xem bản gốc','Brief & uncertain moments':'Tóm tắt và các đoạn cần kiểm tra','Editable brief':'Tóm tắt có thể chỉnh sửa','Save brief':'Lưu tóm tắt',
    'Openings are editorial proposals. Recorded words and proof stay authoritative.':'Đoạn mở đầu chỉ là đề xuất. Lời đã quay và bằng chứng thực tế là nguồn xác nhận.','Check these passages first':'Kiểm tra các đoạn này trước','Play source passage':'Phát đoạn gốc','Trim ends / restore original take':'Cắt hai đầu / khôi phục bản quay gốc','Suggested B-roll':'Cảnh chèn được đề xuất',
    'No confident creator-label match. Presenter retained; label supplied B-roll or place it manually in Cutaways.':'Chưa tìm được cảnh khớp chắc chắn. Giữ hình người nói; hãy gắn nhãn hoặc đặt cảnh thủ công trong mục Cảnh chèn.','Compare 3-second openings':'So sánh đoạn mở đầu 3 giây',
    'Host-first / assigned result-first. Same master audio; body stays fixed. Requires a rendered current cut and real result footage.':'Người nói trước / kết quả đã gán trước. Cùng âm thanh và phần chính. Cần bản dựng hiện tại và cảnh kết quả thực tế.',
    'Plain text uses estimated timing. SRT uses your cue times.':'Văn bản thường dùng thời gian ước tính. Tệp SRT dùng thời gian trong tệp.','Paste what the presenter says…':'Dán lời người nói vào đây…','Generate intro & demos':'Tạo phần mở đầu và minh họa','Transcribe this take · Vietnamese':'Tạo lời thoại tiếng Việt cho bản quay này','Import animation-spec adapter':'Nhập bộ điều hợp thông số chuyển động',
    'No animation-spec adapter installed. Native rules and existing scenes remain available.':'Chưa cài bộ điều hợp chuyển động. Quy tắc có sẵn và các cảnh hiện có vẫn dùng được.','Built-in storyboard and original animation. No API key. Recorded words still need verification.':'Có bảng phân cảnh và chuyển động gốc tích hợp. Không cần khóa API. Lời đã quay vẫn cần được kiểm tra.',
    'Animation library · reusable templates and clips':'Thư viện chuyển động · mẫu và đoạn dùng lại','Component inventory · specification / render / QC':'Danh sách thành phần · thông số / dựng / kiểm tra','Optional lab · AI illustrations · outside V1':'Thử nghiệm tùy chọn · hình minh họa AI · ngoài V1',
    'Media for this recording':'Tư liệu của bản quay này','Edited cut timeline':'Dòng thời gian bản dựng','Rendered export':'Bản xuất đã dựng','QC report':'Báo cáo kiểm tra','Edit plan':'Kế hoạch dựng','Imported SRT phrase timings.':'Thời gian được lấy từ phụ đề SRT đã nhập.',
    'Listen to the mix · matched level':'Nghe bản phối · cùng mức âm lượng','Choose a mix…':'Chọn bản phối…','Voice only':'Chỉ giọng nói','Voice + SFX':'Giọng nói + hiệu ứng','Full mix':'Bản phối đầy đủ','Technical checks · this master':'Kiểm tra kỹ thuật · bản xuất này','Duration / frames':'Thời lượng / số khung hình','Voice loudness':'Độ lớn giọng nói','True peak':'Đỉnh âm thanh',
    'Technical checks do not establish editorial approval. Review this exact export at normal speed. SHA256:':'Kiểm tra kỹ thuật không thay thế việc duyệt nội dung. Hãy xem đúng bản xuất này ở tốc độ bình thường. SHA256:',
    'Review first 3 seconds before body':'Xem 3 giây đầu trước phần chính','Review observations · required for approval':'Nhận xét khi xem lại · cần có để duyệt','UNVERIFIED':'CHƯA XÁC MINH',
    'A · Opening and payoff':'A · Mở đầu và kết quả','B · Visual proof':'B · Bằng chứng hình ảnh','C · Vietnamese captions':'C · Phụ đề tiếng Việt','D · Animation and SFX':'D · Chuyển động và hiệu ứng âm thanh','E · Voice and mix':'E · Giọng nói và bản phối','F · Final export':'F · Bản xuất cuối',
    'Edit only the captions in this passage. Their timing stays the same. Save, then make a new cut to check the result.':'Chỉ sửa phụ đề trong đoạn này; thời gian sẽ được giữ nguyên. Lưu rồi tạo bản dựng mới để kiểm tra kết quả.',
    'Review the words against the recording. Save, then make a new cut to check the result.':'Đối chiếu lời với bản quay. Lưu rồi tạo bản dựng mới để kiểm tra kết quả.',
    'Choose a passage action below the selected phrase.':'Chọn thao tác bên dưới câu đã chọn.','The preview switches to the shared body after 3 seconds. Playback may pause briefly at the switch.':'Bản xem trước chuyển sang phần chính sau 3 giây. Video có thể dừng ngắn khi chuyển.',
    'Technical checks passed · editorial review needed':'Đã kiểm tra kỹ thuật · cần xem lại nội dung','Transcribing locally; your recording stays on this computer':'Đang tạo lời thoại trên máy; bản quay không rời khỏi máy này','Analyzing speech':'Đang phân tích lời nói','Encoding and checking playback':'Đang dựng video và kiểm tra phát lại','Running six-gate QC':'Đang kiểm tra bản dựng',
    'Set up local captions or attach this recording’s TXT/SRT':'Thiết lập phụ đề trên máy hoặc thêm tệp TXT/SRT cho bản quay này','SRT cues must be ordered and fit within the recording.':'Các đoạn SRT phải đúng thứ tự và nằm trong thời lượng bản quay.','Check the recording or script, correct the problem, then make the cut again.':'Kiểm tra bản quay hoặc kịch bản, sửa lỗi rồi tạo lại bản dựng.',
    'Edit settings':'Cài đặt chỉnh sửa','Spoken script':'Kịch bản lời nói','Import TXT / SRT':'Nhập TXT / SRT','On-screen cutaways':'Cảnh chèn trên màn hình','＋ Add insert':'＋ Thêm cảnh chèn','Place footage at a spoken phrase or a time in seconds. The presenter’s voice continues.':'Đặt cảnh vào một câu nói hoặc thời điểm cụ thể. Giọng người nói vẫn tiếp tục.','Cutaway source':'Nguồn cảnh chèn','Remove':'Xóa','Cutaway sound':'Âm thanh cảnh chèn','Off · voice only':'Tắt · chỉ giọng nói',
    'No footage has been assigned to this recording yet.':'Chưa có cảnh nào được gán cho bản quay này.','Picture segments reflect the saved edit plan; check the player.':'Các đoạn hình ảnh theo kế hoạch đã lưu; hãy kiểm tra trên trình phát.'
  };
  Object.assign(words, {
  "Review the final picture, captions, and voice before publishing.": "Xem lại hình ảnh, phụ đề và giọng nói trước khi xuất bản.",
  "Download all latest exports (.zip)": "Tải tất cả bản xuất mới nhất (.zip)",
  "All source recordings": "Tất cả bản quay gốc",
  "Versions": "Phiên bản",
  "Latest cut per source": "Bản mới nhất của mỗi bản quay",
  "All versions / history": "Tất cả phiên bản / lịch sử",
  "Benchmark full videos": "Đánh giá toàn bộ video",
  "Latest": "Mới nhất",
  "Previous": "Trước đó",
  "Go to source": "Đến bản quay gốc",
  "No exports in this view": "Không có bản xuất trong chế độ xem này",
  "Choose another source or render a new cut. Previous versions are kept.": "Chọn bản quay khác hoặc dựng bản mới. Các phiên bản trước vẫn được giữ lại.",
  "Hook 0–3s": "Mở đầu 0–3 giây",
  "Branding": "Nhận diện thương hiệu",
  "Logo on presenter shots": "Logo trên cảnh người nói",
  "No logo": "Không có logo",
  "From source seconds": "Bắt đầu tại giây nguồn",
  "Through source seconds · 0 = entire take": "Kết thúc tại giây nguồn · 0 = toàn bộ bản quay",
  "Original image, top-left; hidden during cutaways and native scenes so it cannot cover their proof. Review the frame on a phone.": "Ảnh gốc ở góc trên trái; ẩn trong cảnh chèn và cảnh tạo sẵn để không che nội dung. Hãy kiểm tra trên điện thoại.",
  "Built-in caption presets": "Kiểu phụ đề có sẵn",
  "Clean": "Đơn giản",
  "Focus": "Nhấn mạnh",
  "Built-in · phrase captions": "Có sẵn · phụ đề theo cụm",
  "Built-in · word emphasis": "Có sẵn · nhấn từng từ",
  "Caption treatment": "Kiểu phụ đề",
  "Clean · phrase captions": "Đơn giản · phụ đề theo cụm",
  "Focus · highlighted words": "Nhấn mạnh · tô sáng từng từ",
  "Portrait framing": "Khung hình dọc",
  "Fit entire picture": "Hiển thị toàn bộ hình",
  "Fill frame · center crop": "Lấp đầy khung · cắt giữa",
  "Portrait framing preview": "Xem trước khung hình dọc",
  "Caption placement": "Vị trí phụ đề",
  "Lower third": "Phần dưới",
  "Upper third": "Phần trên",
  "Pacing reference": "Video tham khảo nhịp dựng",
  "Cut frequency guides caption length. This footage stays off screen.": "Tần suất cắt giúp xác định độ dài phụ đề. Video tham khảo không xuất hiện trên màn hình.",
  "Record editing request": "Ghi yêu cầu chỉnh sửa",
  "Finish current request": "Hoàn tất yêu cầu hiện tại",
  "Request history records your tools and changes; it does not approve a master.": "Lịch sử ghi lại công cụ và thay đổi; việc này không duyệt bản xuất.",
  "Select style locks / transfer": "Chọn khóa phong cách / chuyển sang bản khác",
  "Locks copy only selected style fields; speech, proof and approval stay with each recording.": "Chỉ sao chép các thiết lập phong cách đã chọn; lời nói, bằng chứng và phê duyệt thuộc từng bản quay.",
  "Decision planner": "Bộ lập kế hoạch",
  "Preset source": "Nguồn thiết lập",
  "Built-in rules / assigned reference": "Quy tắc có sẵn / video tham khảo đã gán",
  "Base planner · local weights required": "Bộ cơ sở · cần trọng số trên máy",
  "Base + frozen training-only retrieval": "Bộ cơ sở + dữ liệu huấn luyện cố định",
  "Fine-tuned candidate · experimental": "Mô hình tinh chỉnh · thử nghiệm",
  "No model weights loaded. References can guide rules immediately.": "Chưa tải trọng số mô hình. Có thể dùng video tham khảo để hướng dẫn quy tắc ngay.",
  "Training readiness": "Mức sẵn sàng huấn luyện",
  "Motion": "Chuyển động",
  "Motion profile": "Kiểu chuyển động",
  "Current preset · original behavior": "Thiết lập hiện tại · hành vi ban đầu",
  "Reference guided · built-in rules": "Theo video tham khảo · quy tắc có sẵn",
  "Reference badges · original motion preset": "Nhãn tham khảo · chuyển động gốc",
  "Calm · reduced motion": "Nhẹ nhàng · ít chuyển động",
  "Focus · restrained emphasis": "Tập trung · nhấn vừa phải",
  "Motion intensity": "Cường độ chuyển động",
  "Motion strength changes visual emphasis. Individual sound cues and music remain independent.": "Cường độ thay đổi mức nhấn hình ảnh. Hiệu ứng âm thanh và nhạc vẫn độc lập.",
  "Preview cue plan": "Xem trước kế hoạch hiệu ứng",
  "Review saved corrections": "Xem các chỉnh sửa đã lưu",
  "Sound effects": "Hiệu ứng âm thanh",
  "Each contact and result can have its own sound, offset or intentional silence.": "Mỗi thao tác và kết quả có thể có âm thanh, độ lệch hoặc khoảng im lặng riêng.",
  "＋ Add manual cue": "＋ Thêm hiệu ứng thủ công",
  "Music": "Nhạc",
  "Music bed": "Nhạc nền",
  "Off · voice and chosen effects only": "Tắt · chỉ giọng nói và hiệu ứng đã chọn",
  "Choose automatically · original instrumental": "Tự chọn · nhạc không lời gốc",
  "My track · cleared audio": "Nhạc của tôi · đã có quyền sử dụng",
  "Texture": "Sắc thái",
  "Calm explanation · sparse / quiet": "Giải thích nhẹ nhàng · thưa / nhỏ",
  "Tutorial pulse · restrained / moderate": "Nhịp hướng dẫn · vừa phải",
  "Music level before voice ducking (dB)": "Mức nhạc trước khi giảm theo giọng nói (dB)",
  "My imported track": "Nhạc đã nhập",
  "Choose a cleared track…": "Chọn bản nhạc có quyền sử dụng…",
  "Import my music": "Nhập nhạc của tôi",
  "The original narration controls ducking. No paid service, model weights or reference music is used.": "Giọng nói gốc điều khiển mức giảm nhạc. Không dùng dịch vụ trả phí, trọng số mô hình hoặc nhạc tham khảo.",
  "Effect": "Hiệu ứng",
  "Presenter timeline anchor (s)": "Điểm neo trên dòng thời gian người nói (giây)",
  "Readable hold (frames)": "Thời gian giữ để đọc (khung hình)",
  "Text (optional)": "Văn bản (tùy chọn)",
  "Sound": "Âm thanh",
  "Intentional silence": "Chủ ý im lặng",
  "Mute this cue": "Tắt âm hiệu ứng này",
  "Gain (dB)": "Mức âm (dB)",
  "Timing offset (frames)": "Độ lệch thời gian (khung hình)",
  "Reason for intentional offset": "Lý do chủ ý đặt độ lệch",
  "Advanced target / marker": "Đối tượng / dấu mốc nâng cao",
  "Perceptual marker sample (48 kHz)": "Mẫu dấu mốc cảm nhận (48 kHz)",
  "Trim audio from sample": "Cắt âm thanh từ mẫu",
  "Remove cue": "Xóa hiệu ứng",
  "No manual cues. Verified cutaway anchors can suggest focus, click and result cues.": "Chưa có hiệu ứng thủ công. Các điểm neo cảnh chèn đã xác minh có thể gợi ý hiệu ứng.",
  "Soft click": "Tiếng nhấp nhẹ",
  "Slide": "Trượt",
  "Chime": "Âm báo",
  "Save an animation from reference footage": "Lưu chuyển động từ video tham khảo",
  "Private Kaggle LoRA outputs are experimental illustrations. The core editor uses your real recording and voice. These outputs cannot replace real software proof.": "Hình minh họa Kaggle LoRA riêng tư đang thử nghiệm. Trình dựng sử dụng bản quay và giọng nói thật; hình minh họa không thay thế bằng chứng thao tác phần mềm.",
  "Import trained run / previews": "Nhập kết quả huấn luyện / bản xem trước",
  "Generate illustration on Kaggle": "Tạo hình minh họa trên Kaggle",
  "Select a recording to edit": "Chọn bản quay để chỉnh sửa",
  "Your edit controls": "Công cụ chỉnh sửa",
  "Select one or more recordings to assign a script, set a style, or add a cutaway.": "Chọn một hoặc nhiều bản quay để gán kịch bản, chọn phong cách hoặc thêm cảnh chèn.",
  "Wait for the current import to finish.": "Hãy đợi quá trình nhập hiện tại hoàn tất.",
  "The request failed": "Yêu cầu không thành công",
  "Import results": "Kết quả nhập tệp",
  "Choose B-roll or style reference": "Chọn cảnh B-roll hoặc video tham khảo phong cách.",
  "Choose an existing source recording for a new take.": "Chọn bản quay gốc hiện có để thêm lần quay mới.",
  "Install FFmpeg and FFprobe using the setup panel first.": "Hãy cài FFmpeg và FFprobe trong phần cài đặt trước.",
  "Choose a decodable PNG or JPEG image.": "Chọn ảnh PNG hoặc JPEG có thể đọc được.",
  "Choose a decodable audio track.": "Chọn tệp âm thanh có thể đọc được.",
  "This file has no video track.": "Tệp này không có hình ảnh video.",
  "A talking-head recording needs an audio track.": "Bản quay người nói cần có âm thanh.",
  "Choose an editorial recipe": "Chọn cách kể chuyện.",
  "Choose an available opening": "Chọn đoạn mở đầu có sẵn.",
  "Choose an imported logo image": "Chọn ảnh logo đã nhập.",
  "Logo times must be nonnegative seconds": "Thời gian logo phải là số giây không âm.",
  "Logo end must follow its start": "Thời điểm kết thúc logo phải sau thời điểm bắt đầu.",
  "Choose an available decision planner.": "Chọn bộ lập kế hoạch có sẵn.",
  "Unknown project setting.": "Thiết lập dự án không hợp lệ.",
  "Choose an available built-in motion profile.": "Chọn kiểu chuyển động tích hợp có sẵn.",
  "Choose Music Off, Choose automatically, or My track.": "Chọn Tắt nhạc, Tự chọn hoặc Nhạc của tôi.",
  "Choose an available instrumental bed.": "Chọn nhạc không lời có sẵn.",
  "Choose an available cutaway sound.": "Chọn âm thanh cảnh chèn có sẵn.",
  "Invalid visual settings.": "Thiết lập hình ảnh không hợp lệ.",
  "Use a script of up to 200,000 characters.": "Kịch bản tối đa 200.000 ký tự.",
  "Choose an imported reference.": "Chọn video tham khảo đã nhập.",
  "Use up to 32 cutaways per video.": "Mỗi video có tối đa 32 cảnh chèn.",
  "Cutaway times must be numbers.": "Thời gian cảnh chèn phải là số.",
  "Use a short phrase for the spoken cue.": "Hãy dùng một cụm ngắn làm điểm chèn theo lời nói.",
  "The cutaway must fit its source footage.": "Cảnh chèn phải nằm trong thời lượng của tư liệu nguồn.",
  "Cutaways must fit the recording without overlapping.": "Các cảnh chèn phải nằm trong bản quay và không chồng lên nhau.",
  "A queued or rendering clip is locked until it finishes.": "Bản quay đang chờ hoặc đang dựng sẽ bị khóa đến khi hoàn tất.",
  "Unlock the selected style field before changing it": "Mở khóa thiết lập phong cách đã chọn trước khi thay đổi.",
  "Wait for these recordings to finish rendering before importing scripts.": "Đợi các bản quay dựng xong trước khi nhập kịch bản.",
  "Choose reference footage to analyze.": "Chọn video tham khảo để phân tích.",
  "Add reviewer, observation and an in-range source interval.": "Thêm người kiểm tra, nhận xét và khoảng thời gian hợp lệ trong video nguồn.",
  "FFmpeg and FFprobe must be installed before rendering.": "Cần cài FFmpeg và FFprobe trước khi dựng.",
  "Add a script to render this recording.": "Thêm kịch bản để dựng bản quay này.",
  "The original source file changed. Import it as a new take; prior timings were preserved.": "Tệp nguồn đã thay đổi. Hãy nhập thành lần quay mới; thời gian cũ vẫn được giữ.",
  "Style reference changed. Import the replacement; prior analysis and edits were preserved.": "Video tham khảo đã thay đổi. Hãy nhập tệp thay thế; phân tích và chỉnh sửa cũ vẫn được giữ.",
  "Add and select a recording first": "Hãy thêm và chọn một bản quay trước.",
  "This master has changed. Reopen the correct export.": "Bản xuất đã thay đổi. Hãy mở lại đúng phiên bản.",
  "Choose a review result.": "Chọn kết quả xem lại.",
  "Complete all four viewing and listening checks before approving.": "Hoàn tất cả bốn bước kiểm tra hình và tiếng trước khi duyệt.",
  "A confirmed defect remains on this master; render and review a new version": "Bản xuất này còn lỗi đã xác nhận; hãy dựng và xem lại phiên bản mới.",
  "The project changed after this export. Render the current revision before release; the prior cut is preserved.": "Dự án đã thay đổi sau bản xuất này. Hãy dựng phiên bản hiện tại trước khi phát hành; bản trước vẫn được giữ.",
  "Describe the defect with a timecode.": "Mô tả lỗi kèm thời điểm.",
  "Render a recording first.": "Hãy dựng một bản quay trước.",
  "Upload interrupted.": "Quá trình tải lên bị gián đoạn.",
  "Upload was interrupted.": "Quá trình tải lên bị gián đoạn.",
  "Select a video smaller than 8 GB.": "Chọn video nhỏ hơn 8 GB.",
  "Use MP4, MOV, M4V, MKV or WebM.": "Sử dụng MP4, MOV, M4V, MKV hoặc WebM.",
  "Request is too large.": "Yêu cầu có dung lượng quá lớn.",
  "This cut may clip a word. Move it into the adjacent pause.": "Điểm cắt có thể cắt mất một phần từ. Hãy chuyển vào khoảng nghỉ gần đó.",
  "Choose existing recordings for this footage": "Chọn bản quay hiện có để gán tư liệu này.",
  "The selected local file is missing.": "Không tìm thấy tệp đã chọn trên máy.",
  "Set up local captions, or use the supplied script timing.": "Thiết lập phụ đề trên máy hoặc sử dụng thời gian trong kịch bản đã cung cấp.",
  "This recording changed while the editor was open. Reopen the caption and try again.": "Bản quay đã thay đổi trong khi mở trình chỉnh sửa. Hãy mở lại phụ đề và thử lại.",
  "Add footage to include first.": "Hãy thêm cảnh có thể đưa vào trước.",
  "No time remains for another cutaway.": "Không còn thời gian để thêm cảnh chèn.",
  "Select one recording to add its manual cues.": "Chọn một bản quay để thêm hiệu ứng thủ công.",
  "Select one recording to inspect its exact cue plan.": "Chọn một bản quay để xem kế hoạch hiệu ứng.",
  "Select recordings to apply pacing.": "Chọn bản quay để áp dụng nhịp dựng.",
  "Add this file as footage to include before placing it in the video.": "Hãy thêm tệp này vào cảnh có thể đưa vào trước khi đặt vào video.",
  "Select one recording to add its on-screen demonstration.": "Chọn một bản quay để thêm cảnh minh họa.",
  "Choose the intended recording.": "Chọn bản quay cần dùng.",
  "Choose one recording to resolve its spoken phrase.": "Chọn một bản quay để tìm câu nói.",
  "Enter the exact spoken phrase first.": "Nhập chính xác câu nói trước.",
  "Confirm permission for this audio before importing it.": "Xác nhận quyền sử dụng âm thanh trước khi nhập.",
  "Choose one recording for this script.": "Chọn một bản quay cho kịch bản này.",
  "honest question": "Câu hỏi tự nhiên",
  "host first": "Người nói trước",
  "proof first": "Kết quả trước",
  ": Recorded question; a later quote is a proposal, not silently moved speech.": ": Câu hỏi đã quay; câu nói phía sau chỉ là đề xuất, chưa tự động chuyển vị trí.",
  ": Available recorded voice; no unverified result inserted.": ": Dùng giọng đã quay; không chèn kết quả chưa xác minh.",
  ": No assigned verified result; retain presenter.": ": Chưa có kết quả đã gán và xác minh; giữ hình người nói."
});
  Object.assign(words, {'Workspace account information':'Thông tin tài khoản không gian làm việc','Workspace information':'Thông tin không gian làm việc','Your projects are stored on this computer.':'Các dự án được lưu trên máy tính này.'});
  Object.assign(words, {'Video encoder':'Bộ mã hóa video','FFmpeg and FFprobe are available.':'FFmpeg và FFprobe đã sẵn sàng.','Check again':'Kiểm tra lại','Local files':'Tệp trên máy','Recordings, scripts and exports are stored on this computer. Closing the tab leaves active renders running.':'Bản quay, kịch bản và bản xuất được lưu trên máy này. Đóng thẻ trình duyệt không dừng quá trình dựng đang chạy.','Quit Talking Head Cutroom':'Thoát Talking Head Cutroom','No pacing reference':'Không có video tham khảo nhịp dựng','Source framing preview · sample caption':'Xem trước khung hình nguồn · phụ đề mẫu','Fit entire picture: keep the full source; unused portrait space is padded.':'Hiển thị toàn bộ hình gốc; phần trống của khung dọc được lấp nền.','Fill frame: the centered source is cropped to fill the portrait frame.':'Lấp đầy khung: hình gốc được cắt ở giữa theo khung dọc.','built-in rules · rules-v2 · no model weights loaded':'Quy tắc có sẵn · rules-v2 · chưa tải trọng số mô hình','Output':'Bản xuất'});
  Object.assign(words, {'Import your music':'Nhập nhạc của bạn','Choose audio you may use in this export. Reference permission does not automatically grant permission to reuse its soundtrack.':'Chọn âm thanh bạn có quyền dùng trong bản xuất này. Quyền dùng video tham khảo không tự động bao gồm quyền dùng nhạc của video đó.','I have permission to use this track in my exported videos.':'Tôi có quyền dùng bản nhạc này trong video xuất ra.','Choose audio file':'Chọn tệp âm thanh'});
  Object.assign(words, {'Display language':'Ngôn ngữ hiển thị'});
  Object.assign(words, {'About local profiles':'Thông tin hồ sơ trên máy','Local profiles':'Hồ sơ trên máy','Review saved draft':'Xem nháp đã lưu','Unsaved draft':'Nháp chưa lưu','Download draft JSON':'Tải nháp JSON','Discard saved draft':'Bỏ nháp đã lưu','Restore entire take':'Khôi phục toàn bộ take','Scene plan & style board':'Kế hoạch cảnh & bảng tham chiếu','Presenter composition':'Bố cục người dẫn','Save presenter layout only':'Chỉ lưu bố cục người dẫn','Create scene preview':'Tạo preview cảnh','Save observation':'Lưu quan sát','Current passage → scene instance':'Câu nói hiện tại → cảnh dựng','Source-linked style board':'Bảng style liên kết nguồn','Scene preview · review before insertion':'Preview cảnh · kiểm tra trước khi chèn','Insert in episode':'Chèn vào tập','Edit instance':'Sửa cảnh của tập','Spoken passage':'Câu nói','Visible title':'Chữ hiển thị','Editable component':'Component chỉnh được','Style observation':'Quan sát tham chiếu','Reference source':'Nguồn tham chiếu','Scene family':'Nhóm cảnh','Observed layout / motion':'Bố cục / chuyển động đã quan sát','Visual confidence':'Độ tin cậy hình ảnh','Observer':'Người quan sát','What was heard':'Âm thanh đã nghe','I can hear this reference and inspected its audio':'Tôi nghe được và đã kiểm tra âm thanh tham chiếu'});
  Object.assign(words, {'Edit profile':'Chỉnh sửa hồ sơ','Edit profile and picture':'Chỉnh sửa hồ sơ và ảnh','Display name':'Tên hiển thị','Email (optional)':'Email (không bắt buộc)','Profile picture':'Ảnh hồ sơ','Choose an image':'Chọn ảnh','Remove current picture':'Xóa ảnh hiện tại','Save profile':'Lưu hồ sơ','Profile details and picture are stored in this browser on this computer.':'Thông tin và ảnh hồ sơ được lưu trong trình duyệt trên máy tính này.','Local profile':'Hồ sơ trên máy','Profile saved':'Đã lưu hồ sơ','Enter a valid email address.':'Nhập địa chỉ email hợp lệ.','Choose an image smaller than 10 MB.':'Chọn ảnh nhỏ hơn 10 MB.','Could not save the profile. Check the picture and browser storage.':'Không thể lưu hồ sơ. Hãy kiểm tra ảnh và bộ nhớ trình duyệt.'});
  Object.assign(words, {'Sign in':'Đăng nhập','Switch account':'Chuyển tài khoản','Switch local profile':'Chuyển hồ sơ trên máy','Online sign-in is not available in this local workspace yet.':'Đăng nhập trực tuyến chưa khả dụng trong không gian làm việc trên máy.','Local profiles are stored in this browser and do not sign you in to an online account.':'Hồ sơ được lưu trong trình duyệt này và không đăng nhập vào tài khoản trực tuyến.','Add local profile':'Thêm hồ sơ trên máy','Current':'Đang dùng','A profile could not be saved in this browser.':'Không thể lưu hồ sơ trong trình duyệt này.'});
  const states={'Draft':'Bản nháp','Queued':'Đang chờ','Rendering':'Đang dựng','For review':'Chờ xem lại','Failed':'Thất bại','Needs input':'Cần bổ sung','Needs revision':'Cần chỉnh sửa','Approved':'Đã duyệt','Interrupted':'Bị gián đoạn'};
  const records=new WeakMap();
  let language=localStorage.getItem('cutroom-language')||'vi';
  const switcher=document.createElement('button');switcher.id='languageSwitch';switcher.type='button';switcher.className='language-switch';
  document.querySelector('header .right').prepend(switcher);
  // Local workspace information is intentionally separate from online account authentication.
  const account=document.createElement('details'); account.className='account-menu';
  const menuIcon=(path)=>`<svg class="account-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`;
  account.innerHTML=`<summary aria-label="Workspace account information" title="Workspace account information"><span class="account-avatar" aria-hidden="true">C</span><span class="account-chevron" aria-hidden="true">⌄</span></summary><div class="account-panel"><div class="account-profile"><span class="account-avatar account-avatar-large" aria-hidden="true">C</span><div class="account-identity"><strong class="account-profile-name"></strong><small class="account-profile-email"></small><button type="button" class="account-edit-link" data-account-edit>Edit profile</button></div></div><p class="account-description">Profile details and picture are stored in this browser on this computer.</p><div class="account-group"><button type="button" class="account-row" data-account-login>${menuIcon('<path d="M14 3h5v18h-5M10 8l4 4-4 4M14 12H3"/>')}<span>About local profiles</span></button><button type="button" class="account-row" data-account-switch>${menuIcon('<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M5 17c.3-2 1.5-3 4-3s3.7 1 4 3M16 9h3m-1.5-1.5L19 9l-1.5 1.5"/>')}<span>Switch local profile</span><span class="account-row-arrow" aria-hidden="true">›</span></button><button type="button" class="account-row" data-account-edit>${menuIcon('<circle cx="12" cy="8" r="3.5"/><path d="M5 20c.5-4 3-6 7-6s6.5 2 7 6"/>')}<span>Edit profile and picture</span></button><button type="button" class="account-row" data-account-workspace>${menuIcon('<path d="M3 10 12 3l9 7v10H3z"/><path d="M9 20v-6h6v6"/>')}<span>Workspace</span></button><button type="button" class="account-row" data-account-exports>${menuIcon('<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M10 8.5 15 12l-5 3.5z"/>')}<span>Exports</span></button></div><div class="account-group"><button type="button" class="account-row" data-account-language>${menuIcon('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>')}<span>Display language</span><span id="accountLanguage" class="account-row-value"></span><span class="account-row-arrow" aria-hidden="true">›</span></button><button type="button" class="account-row" data-account-settings>${menuIcon('<circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/><circle cx="12" cy="12" r="7"/>')}<span>Workspace settings</span></button></div></div>`;
  document.querySelector('header .right').append(account);
  document.addEventListener('click',event=>{if(account.open&&!account.contains(event.target))account.open=false;const target=event.target.closest('[data-account-settings],[data-account-language],[data-account-workspace],[data-account-exports],[data-account-edit],[data-account-login],[data-account-switch]');if(!target)return;account.open=false;if(target.hasAttribute('data-account-login'))dialog('Local profiles','<p>Online sign-in is not available in this local workspace yet.</p><p>Local profiles are stored in this browser and do not sign you in to an online account.</p>');else if(target.hasAttribute('data-account-switch'))openProfileSwitcher();else if(target.hasAttribute('data-account-edit'))openProfileEditor();else if(target.hasAttribute('data-account-settings'))document.getElementById('settings').click();else if(target.hasAttribute('data-account-language'))switcher.click();else document.querySelector(target.hasAttribute('data-account-exports')?'[data-tab=exports]':'[data-tab=workspace]').click();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&account.open){account.open=false;account.querySelector('summary').focus();}});

  const profileKey='cutroom-local-profile', profilesKey='cutroom-local-profiles-v1';
  const cleanProfile=stored=>({name:typeof stored?.name==='string'?stored.name:'',email:typeof stored?.email==='string'?stored.email:'',picture:typeof stored?.picture==='string'&&/^data:image\/(png|jpeg|webp);base64,/.test(stored.picture)?stored.picture:''});
  let profiles=[],activeProfile='local-default',profile={name:'',email:'',picture:''};
  try {const list=JSON.parse(localStorage.getItem(profilesKey)||'null');if(list&&Array.isArray(list.profiles)&&list.profiles.length){profiles=list.profiles.filter(x=>x&&typeof x.id==='string').map(x=>({id:x.id,...cleanProfile(x)}));activeProfile=profiles.some(x=>x.id===list.active)?list.active:profiles[0].id;}else{profiles=[{id:activeProfile,...cleanProfile(JSON.parse(localStorage.getItem(profileKey)||'{}'))}];}profile=cleanProfile(profiles.find(x=>x.id===activeProfile));} catch (_) {profiles=[{id:activeProfile,...profile}];}
  function storeProfiles(next,active){localStorage.setItem(profilesKey,JSON.stringify({active,profiles:next}));profiles=next;activeProfile=active;profile=cleanProfile(next.find(x=>x.id===active));drawProfile();}
  function openProfileSwitcher(){dialog('Switch local profile',`<p>Local profiles are stored in this browser and do not sign you in to an online account.</p><div class="profile-switch-list">${profiles.map(x=>`<button type="button" class="profile-switch-row" data-switch-profile="${esc(x.id)}"><span class="account-avatar" aria-hidden="true">${esc((x.name.trim().charAt(0)||'C').toLocaleUpperCase())}</span><span class="profile-switch-name">${esc(x.name|| (language==='vi'?'Hồ sơ trên máy':'Local profile'))}</span>${x.id===activeProfile?'<small>Current</small>':''}</button>`).join('')}</div><button type="button" class="soft" data-new-profile>Add local profile</button>`);}
  document.addEventListener('click',event=>{const selection=event.target.closest('[data-switch-profile],[data-new-profile]');if(!selection)return;try{if(selection.hasAttribute('data-new-profile')){const id=crypto.randomUUID(),next=[...profiles,{id,name:'',email:'',picture:''}];storeProfiles(next,id);openProfileEditor();}else{const id=selection.dataset.switchProfile;if(!profiles.some(x=>x.id===id))return;storeProfiles(profiles,id);el('modal').close();}}catch(_){notify(language==='vi'?'Không thể lưu hồ sơ trong trình duyệt này.':'A profile could not be saved in this browser.');}});
  function drawProfile(){
    const name=profile.name|| (language==='vi'?'Làm việc trên máy':'Local workspace');
    account.querySelector('.account-profile-name').textContent=name;
    account.querySelector('.account-profile-email').textContent=profile.email|| (language==='vi'?'Hồ sơ trên máy':'Local profile');
    const initial=(profile.name.trim().charAt(0)||'C').toLocaleUpperCase();
    account.querySelectorAll('.account-avatar').forEach(avatar=>{avatar.replaceChildren();if(profile.picture){const img=document.createElement('img');img.src=profile.picture;img.alt='';avatar.append(img);}else avatar.textContent=initial;});
  }
  function openProfileEditor(){
    dialog('Edit profile',`<p>Profile details and picture are stored in this browser on this computer.</p><div class="profile-edit-head"><span class="account-avatar account-avatar-large profile-preview" aria-hidden="true"></span><div><strong>Profile picture</strong><label class="profile-file-label" for="profilePicture">Choose an image</label><input id="profilePicture" type="file" accept="image/png,image/jpeg,image/webp"/><label class="profile-remove"><input id="profileRemove" type="checkbox"> Remove current picture</label></div></div><label for="profileName">Display name</label><input id="profileName" maxlength="80" value="${esc(profile.name)}"><label for="profileEmail">Email (optional)</label><input id="profileEmail" type="email" maxlength="254" value="${esc(profile.email)}"><div class="profile-actions"><button type="button" class="primary" data-save-profile>Save profile</button></div>`);
    const preview=document.querySelector('.profile-preview');if(profile.picture){const img=document.createElement('img');img.src=profile.picture;img.alt='';preview.append(img);}else preview.textContent=(profile.name.trim().charAt(0)||'C').toLocaleUpperCase();
  }
  async function prepareProfileImage(file){
    if(!file.type.startsWith('image/')||file.size>10*1024*1024)throw new Error(language==='vi'?'Chọn ảnh nhỏ hơn 10 MB.':'Choose an image smaller than 10 MB.');
    const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(new Error(language==='vi'?'Không thể đọc ảnh.':'Could not read the image.'));reader.readAsDataURL(file);});
    try {const img=new Image();img.src=data;await img.decode();const side=Math.min(img.naturalWidth,img.naturalHeight);if(!side)throw new Error('Invalid image');const canvas=document.createElement('canvas');canvas.width=256;canvas.height=256;const ctx=canvas.getContext('2d');if(!ctx)throw new Error('Canvas unavailable');ctx.drawImage(img,(img.naturalWidth-side)/2,(img.naturalHeight-side)/2,side,side,0,0,256,256);return canvas.toDataURL('image/jpeg',.86);}catch(_){throw new Error(language==='vi'?'Không thể đọc ảnh. Hãy chọn ảnh khác.':'Could not read the image. Choose another picture.');}
  }
  document.addEventListener('click',async event=>{const button=event.target.closest('[data-save-profile]');if(!button)return;const name=document.getElementById('profileName'),email=document.getElementById('profileEmail'),file=document.getElementById('profilePicture'),remove=document.getElementById('profileRemove');if(!email.checkValidity()){notify(language==='vi'?'Nhập địa chỉ email hợp lệ.':'Enter a valid email address.');return;}button.disabled=true;try{const picture=file.files[0]?await prepareProfileImage(file.files[0]):remove.checked?'':profile.picture;const next={name:name.value.trim(),email:email.value.trim(),picture};storeProfiles(profiles.map(x=>x.id===activeProfile?{id:x.id,...next}:x),activeProfile);el('modal').close();notify(language==='vi'?'Đã lưu hồ sơ':'Profile saved');}catch(error){notify(error.message|| (language==='vi'?'Không thể lưu hồ sơ. Hãy kiểm tra ảnh và bộ nhớ trình duyệt.':'Could not save the profile. Check the picture and browser storage.'));}finally{button.disabled=false;}});

  function translate(raw){
    const trimmed=raw.trim();if(!trimmed)return raw;
    let out=words[trimmed] || words[trimmed.replace(/\s+/g, " ")];
    if(!out){
      out=trimmed
        .replace(/^(\d+) latest cuts? shown · (\d+) versions? kept$/,'Hiển thị $1 bản mới nhất · đã giữ $2 phiên bản')
        .replace(/^Rendered MP4 · /,'MP4 đã dựng · ').replace(/^From (.+) · source ([a-f0-9]+) · SHA /,'Từ $1 · nguồn $2 · SHA ')
        .replace(/ · Take (\d+)(?= · [a-f0-9]+$)/,' · lần quay $1')
        .replace(/^Review (v\d+)$/,'Xem lại $1').replace(/^(\d+) versions?$/,'$1 phiên bản')
        .replace(/^(\d+) local images available for original scenes$/,'Có $1 hình ảnh trên máy cho cảnh gốc')
        .replace(/^Original recording · /,'Bản quay gốc · ').replace(/^Source footage · not the edited cut · /,'Tư liệu gốc · không phải bản dựng · ')
        .replace(/^Previous edited cut · /,'Bản dựng trước · ').replace(/^Edited cut · /,'Bản dựng đã chỉnh · ')
        .replace(/^EDITED CUT · /,'BẢN DỰNG ĐÃ CHỈNH · ').replace(/^OPTIONAL INPUTS · /,'TƯ LIỆU TÙY CHỌN · ')
        .replace(/^Caption in (v\d+): /,'Phụ đề trong $1: ').replace(/^Planned picture: /,'Hình ảnh dự kiến: ').replace(/^Hình ảnh dự kiến: Presenter(?= ·)/,'Hình ảnh dự kiến: Người nói').replace(/ · check the player · source /,' · kiểm tra trình phát · nguồn ')
        .replace(/^This is (v\d+) of your edited video\.$/,'Đây là bản $1 của video đã chỉnh.')
        .replace(/^Review & export (v\d+)$/,'Xem lại và xuất $1').replace(/^Play passage at (\d+:\d+): /,'Phát đoạn lúc $1: ')
        .replace(/^Select (.+)$/,'Chọn $1').replace(/^Editing (.+)$/,'Đang chỉnh sửa $1')
        .replace(/^(\d+) selected · (\d+) of (\d+) sources shown$/,'Đã chọn $1 · đang hiển thị $2 trên $3 bản quay')
        .replace(/^(\d+) selected · (\d+) ready · (\d+) need input$/,'Đã chọn $1 · $2 sẵn sàng · $3 cần bổ sung')
        .replace(/^Render (\d+) videos?$/,'Dựng $1 video').replace(/^Original · Take (\d+) · (.+) · (\d+) cuts?$/,'Bản gốc · lần quay $1 · $2 · $3 bản dựng')
        .replace(/ · Script attached/,' · Đã thêm kịch bản').replace(/ · Needs script/,' · Cần kịch bản')
        .replace(/^(\d+:\d+–\d+:\d+: )Low recognition confidence:/,'$1Độ tin cậy nhận dạng thấp:').replace(/^(\d+:\d+–\d+:\d+: )Possible repeated take; natural delivery not inferred from ASR\./,'$1Có thể là lần quay lặp; chưa thể xác định cách nói tự nhiên từ nhận dạng tự động.')
        .replace(/ASR word timings · not human listening approval/,'Thời gian từ nhận dạng giọng nói · chưa được người nghe xác nhận').replace(/Conservative: uncertain retakes and meaningful pauses retained/,'Giữ lại các lần quay chưa chắc chắn và khoảng nghỉ có ý nghĩa')
        .replace(/^Rendered cut (v\d+) · original recording: (.+) · source (.+)$/,'Bản dựng $1 · bản quay gốc: $2 · nguồn $3')
        .replace(/^Lip-sync offset (\d+)$/,'Độ lệch khẩu hình $1')
        .replace(/^Edited cut (v\d+)$/,'Bản dựng đã chỉnh $1').replace(/ · presenter$/,' · người nói')
        .replace(/ · Latest cut$/,' · Bản dựng mới nhất').replace(/ · Previous cut$/,' · Bản dựng trước')
        .replace(/Technical checks passed · editorial review needed/,'Đã kiểm tra kỹ thuật · cần xem lại nội dung')
        .replace(/Set up local captions or attach this recording’s TXT\/SRT/,'Thiết lập phụ đề trên máy hoặc thêm tệp TXT/SRT cho bản quay này')
        .replace(/Multilingual small model ~486MB, plus Python dependencies/,'Mô hình đa ngôn ngữ khoảng 486 MB cùng các thành phần Python')
        .replace(/Transcribing locally; your recording stays on this computer/,'Đang tạo lời thoại trên máy; bản quay không rời khỏi máy này')
        .replace(/Analyzing speech/,'Đang phân tích lời nói').replace(/Encoding and checking playback/,'Đang dựng video và kiểm tra phát lại').replace(/Running six-gate QC/,'Đang kiểm tra bản dựng')
        .replace(/SRT cues must be ordered and fit within the recording\./,'Các đoạn SRT phải đúng thứ tự và nằm trong thời lượng bản quay.')
        .replace(/Check the recording or script, correct the problem, then make the cut again\./,'Kiểm tra bản quay hoặc kịch bản, sửa lỗi rồi tạo lại bản dựng.')
        .replace(/^Caption · source /,'Phụ đề · nguồn ').replace(/^Spoken phrase: /,'Lời thoại: ').replace(/^At source /,'Tại thời điểm nguồn ')
        .replace(/^First cut queued for (.+)\.$/,'Đã đưa bản dựng đầu tiên của $1 vào hàng chờ.')
        .replace(/^Imported (\d+) file(s?)$/,'Đã nhập $1 tệp')
        .replace(/^Caption correction saved\. Make an updated cut to review it\.$/,'Đã lưu phụ đề. Hãy tạo bản dựng mới để xem lại.')
        .replace(/^Shot choice saved\. Make an updated cut to review it\.$/,'Đã lưu cảnh. Hãy tạo bản dựng mới để xem lại.')
        .replace(/^Entire take restored\. Make a new cut to review it\.$/,'Đã khôi phục toàn bộ bản quay. Hãy tạo bản dựng mới để xem lại.')
        .replace(/ · (Draft|Queued|Rendering|For review|Failed|Needs input|Needs revision|Approved|Interrupted)$/,(m,s)=>' · '+states[s]);
      if(states[out])out=states[out];
    }
    return raw.replace(trimmed,out);
  }
  function translateFor(el,raw){
    if(el.closest('.room-beat small'))return raw.replace(/^Caption in (v\d+): /,'Phụ đề trong $1: ').replace(/^Planned picture: Presenter(?= ·)/,'Hình ảnh dự kiến: Người nói').replace(/^Planned picture: /,'Hình ảnh dự kiến: ').replace(/ · check the player · source /,' · kiểm tra trình phát · nguồn ');
    return translate(raw);
  }
  function excluded(el){return !!el.closest('textarea,script,style,.room-beat strong,.timeline-clip span,.room-media-item strong,.room-recording strong,.clip-name,.refs .name,.exportrow .name,.passage p,.artifact-card blockquote,.occurrence,.account-profile-name,.account-profile-email,.profile-switch-name');}
  function apply(root){
    if(!root)return; const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let node;
    while(node=walker.nextNode()){
      if(!node.parentElement||excluded(node.parentElement)||node.parentElement===switcher)continue;
      let rec=records.get(node);if(!rec||node.nodeValue!==rec.last){rec={original:node.nodeValue,last:node.nodeValue};records.set(node,rec);}
      const next=language==='vi'?translateFor(node.parentElement,rec.original):rec.original;if(node.nodeValue!==next)node.nodeValue=next;rec.last=next;
    }
    const elements=root.nodeType===1?[root,...root.querySelectorAll('[placeholder],[aria-label],[title]')]:[...document.querySelectorAll('[placeholder],[aria-label],[title]')];
    for(const el of elements){if(el===switcher||(excluded(el)&&el.tagName!=='TEXTAREA'))continue;for(const attr of ['placeholder','aria-label','title']){if(!el.hasAttribute(attr))continue;let map=records.get(el);if(!map||!map.attrs){map={attrs:{}};records.set(el,map);}const value=el.getAttribute(attr),previous=map.attrs[attr];if(!previous||value!==previous.last)map.attrs[attr]={original:value,last:value};const entry=map.attrs[attr],next=language==='vi'?translate(entry.original):entry.original;if(value!==next)el.setAttribute(attr,next);entry.last=next;}}
  }
  function update(){document.documentElement.lang=language==='vi'?'vi':'en';switcher.textContent=language==='vi'?'English':'Tiếng Việt';switcher.setAttribute('aria-label',language==='vi'?'Chuyển giao diện sang tiếng Anh':'Chuyển giao diện sang tiếng Việt');switcher.title=switcher.getAttribute('aria-label');document.getElementById('accountLanguage').textContent=language==='vi'?'Tiếng Việt':'English';drawProfile();apply(document.body);}
  switcher.addEventListener('click',()=>{language=language==='vi'?'en':'vi';localStorage.setItem('cutroom-language',language);update();});
  let scheduled=false;new MutationObserver(()=>{if(scheduled)return;scheduled=true;queueMicrotask(()=>{scheduled=false;apply(document.body);});}).observe(document.body,{childList:true,subtree:true});
  update();
})();
let scenePlanDraft=null;
async function openScenePlan(id){
 const [view,catalog]=await Promise.all([req('/api/scene-plan?id='+encodeURIComponent(id)),req('/api/components')]);
 scenePlanDraft={view,request_id:crypto.randomUUID()};
 const observations=view.reference.observations;
 const references=refs();
 dialog('Scene plan & style board',`<p>Current recording · revision ${view.revision}. Words and source clocks stay with this episode. New scenes are previews until explicitly inserted.</p>
 <div class="sceneplan-grid"><section><h3>Current passage → scene instance</h3>
 <label>Spoken passage<select id="scenePlanPassage">${view.passages.map(p=>`<option value="${p.id}">${time(p.start)}–${time(p.end)} · ${esc(p.quote)}</option>`).join('')}</select></label>
 <video id="scenePlanSource" controls playsinline src="/assets/${id}/media"></video><small id="scenePlanTiming"></small>
 <label>Visible title<input id="scenePlanTitle" maxlength="140" value="${esc(view.passages[0]?.quote||'')}"></label>
 <label>Editable component<select id="scenePlanComponent">${catalog.components.filter(c=>c.selectable_in_scene_plan).map(c=>`<option value="${c.id}">${c.id} · ${esc(c.name)} · native editable</option>`).join('')}${view.library.filter(x=>x.editable).map(x=>`<option value="library:${x.id}">${esc(x.title)} · template v${x.version}</option>`).join('')}</select></label>
 <label>Motion treatment<select id="sceneMotionEasing"><option value="">Current native easing</option><option value="motion_ease_out" ${!catalog.motion_library.providers.find(p=>p.id==='motion').runtime.available?'disabled':''}>Motion · ease out</option><option value="motion_ease_in_out" ${!catalog.motion_library.providers.find(p=>p.id==='motion').runtime.available?'disabled':''}>Motion · ease in/out</option><option value="motion_spring" ${!catalog.motion_library.providers.find(p=>p.id==='motion').runtime.available?'disabled':''}>Motion · spring</option></select></label><label>Style observation<select id="scenePlanObservation"><option value="">No reference treatment selected</option>${observations.map(o=>`<option value="${o.id}" ${!o.available?'disabled':''}>${esc(o.family)} · ${o.source_range.map(x=>Number(x).toFixed(3)+'s').join('–')} · ${esc(o.visual.slice(0,70))}${o.available?'':' · relink source'}</option>`).join('')}</select></label>
 <video id="scenePlanReference" controls playsinline hidden></video><small id="scenePlanReferenceNote"></small>
 <details><summary>Find a suitable motion treatment</summary><label>Scene purpose<select id="motionLibraryFamily">${view.reference.families.map(f=>`<option value="${f}">${f}</option>`).join('')}</select></label><label>Reference treatment<select id="motionLibraryMood"><option value="">Use the default treatment</option><option value="calm,minimal">Calm / minimal</option><option value="marketing,business">Emphasis / marketing</option><option value="education,tutorial">Educational / tutorial</option></select></label><button type="button" class="soft" id="recommendMotion">Suggest available treatments</button><div id="motionLibraryChoices"></div><small>Suggestions use purpose, inputs, readable hold and runtime availability. Review the rendered scene before inserting it.</small></details><details><summary>Reviewed animation sources</summary>${catalog.motion_library.providers.map(p=>`<p><strong>${esc(p.id)}</strong> · ${esc(p.runtime.status)}<br><small>${esc(p.purpose)}</small></p>`).join('')}</details>
 ${compositionFields({})}<button type="button" class="primary" id="createPassageScene"  ${!view.passages.length?'disabled':''}>Create scene preview</button>
 <div id="scenePlanInstances">${view.passages.flatMap(p=>(p.scenes||[]).map(s=>`<p>${esc(p.quote)} · scene v${s.version} · ${s.locked?'Locked':esc(s.status)} <button type="button" class="soft" data-artifact-preview="${s.id}">Preview</button><button type="button" class="textbtn" data-artifact-edit="${s.id}">Edit instance</button></p>`)).join('')}</div>
 </section><section><h3>Source-linked style board</h3><p>Observations describe reference treatment. They do not become this episode’s software proof.</p>
 ${observations.map(o=>`<p>${esc(o.family)} · ${o.source_range.map(x=>Number(x).toFixed(3)+'s').join('–')} · ${esc(o.visual)}<br><small>Visual confidence ${o.visual_confidence} · Audio ${esc(o.audio_status)} · ${esc(o.state)}</small></p>`).join('')||'<p>No saved observations yet.</p>'}
 <label>Reference source<select id="styleBoardAsset">${references.map(a=>`<option value="${a.id}">${esc(a.name)}</option>`).join('')}</select></label>
 <video id="styleBoardSource" controls playsinline ${references.length?'':'hidden'}></video>
 <div class="scene-controls"><label>Source in (s)<input type="number" id="styleBoardIn" min="0" step="any" value="0"></label><label>Source out (s)<input type="number" id="styleBoardOut" min="0" step="any" value="${Math.min(3,references[0]?.duration||3)}"></label></div>
 <label>Scene family<select id="styleBoardFamily">${view.reference.families.map(f=>`<option>${f}</option>`).join('')}</select></label>
 <label>Observed layout / motion<textarea id="styleBoardVisual" rows="3" maxlength="1500"></textarea></label><label>Visual confidence<input id="styleBoardConfidence" type="number" min="0" max="1" step=".1" value=".5"></label>
 <label>Observer<input id="styleBoardReviewer" maxlength="120"></label><label><input type="checkbox" id="styleBoardCanListen"> I can hear this reference and inspected its audio</label><label>What was heard<textarea id="styleBoardAudio" rows="2" maxlength="1500" disabled></textarea></label>
 <button type="button" class="soft" id="saveStyleObservation" ${!references.length?'disabled':''}>Save observation</button></section></div>`);
 const selectPassage=()=>{scenePlanDraft.recipe_id=null;const p=view.passages.find(p=>p.id===el('scenePlanPassage').value);if(!p)return;el('scenePlanSource').currentTime=p.start;el('scenePlanTiming').textContent=`Source ${p.start.toFixed(3)}–${p.end.toFixed(3)}s · ${p.timing}`;el('scenePlanTitle').value=state.artifacts[p.choice?.scene]?.plan.title||p.quote;el('scenePlanComponent').value=p.choice?.component||'05';const previousMotion=state.artifacts[p.choice?.scene]?.plan.animation?.spec.objects?.flatMap(o=>o.keyframes).find(k=>k.ease?.startsWith('motion_'))?.ease;el('sceneMotionEasing').value=previousMotion||'';el('scenePlanObservation').value=p.choice?.observation||'';el('scenePlanObservation').dispatchEvent(new Event('change'));const composition=state.artifacts[p.choice?.scene]?.plan.composition||{};el('scenePresenterLayout').value=composition.layout||'full_demo';el('scenePresenterShape').value=composition.pip_shape||'circle';el('scenePresenterCorner').value=composition.pip_corner||'bottom_right';el('scenePresenterSize').value=composition.pip_width??.25;all('[data-scene-presenter-crop]').forEach((field,i)=>field.value=composition.pip_crop?.[i]??[.5,.38,1][i]);};
 el('scenePlanPassage').onchange=selectPassage;el('scenePlanSource').onloadedmetadata=()=>{const passage=view.passages.find(p=>p.id===el('scenePlanPassage').value);if(passage)el('scenePlanSource').currentTime=passage.start;};
 el('scenePlanObservation').onchange=()=>{const o=observations.find(o=>o.id===el('scenePlanObservation').value),v=el('scenePlanReference');v.hidden=!o?.available;if(o?.available){v.src=`/assets/${o.seek_asset}/media#t=${o.source_range.join(',')}`;el('scenePlanReferenceNote').textContent=`${o.visual} · Audio ${o.audio_status}`;}else el('scenePlanReferenceNote').textContent='';};
 const setReference=()=>{const a=state.assets[el('styleBoardAsset').value];if(a)el('styleBoardSource').src=`/assets/${a.id}/media`;};el('styleBoardAsset').onchange=setReference;setReference();selectPassage();
 el('styleBoardCanListen').onchange=()=>el('styleBoardAudio').disabled=!el('styleBoardCanListen').checked;
 el('saveStyleObservation').onclick=guard(async()=>{const a=state.assets[el('styleBoardAsset').value];await req('/api/style-board/save',{asset:a.id,source_sha256:a.source_sha256,source_range:[Number(el('styleBoardIn').value),Number(el('styleBoardOut').value)],family:el('styleBoardFamily').value,visual:el('styleBoardVisual').value,visual_confidence:Number(el('styleBoardConfidence').value),reviewer:el('styleBoardReviewer').value,can_listen:el('styleBoardCanListen').checked,audio:el('styleBoardAudio').value});await openScenePlan(id);});
 el('scenePlanComponent').onchange=()=>scenePlanDraft.recipe_id=null;
 el('sceneMotionEasing').onchange=()=>scenePlanDraft.recipe_id=null;
 el('recommendMotion').onclick=guard(async()=>{
  const passage=view.passages.find(p=>p.id===el('scenePlanPassage').value);if(!passage)return;
  const observed=observations.find(o=>o.id===el('scenePlanObservation').value&&o.available);
  const ranked=await req('/api/motion-library/recommend',{family:el('motionLibraryFamily').value,duration:passage.end-passage.start,niche:state.jobs[id].settings.niche||'',available_inputs:['recording','text',...(observed?['reference']:[])],reference_tags:el('motionLibraryMood').value.split(',').filter(Boolean)});
  el('motionLibraryChoices').innerHTML=ranked.candidates.map(r=>`<p><button type="button" class="soft" data-motion-choice="${esc(r.id)}">${esc(r.id)}</button> · ${esc(r.why.join(' · '))}</p>`).join('')||'<p>No available treatment fits these inputs. Select an inspected reference for a CTA or adjust the passage duration.</p>';
  all('[data-motion-choice]').forEach(button=>button.onclick=()=>{const r=ranked.candidates.find(r=>r.id===button.dataset.motionChoice);if(!r)return;scenePlanDraft.recipe_id=r.id;el('scenePlanComponent').value=r.component;el('sceneMotionEasing').value=r.easing;button.textContent='Selected · '+r.id;});
 });
 el('createPassageScene').onclick=guard(async()=>{const button=el('createPassageScene');button.disabled=true;try{const r=await req('/api/scene-plan/create',{id,revision:view.revision,passage:el('scenePlanPassage').value,component:el('scenePlanComponent').value,title:el('scenePlanTitle').value,observation:el('scenePlanObservation').value||null,composition:readComposition(),motion_easing:el('sceneMotionEasing').value||null,recipe_id:scenePlanDraft.recipe_id||null,request_id:scenePlanDraft.request_id});await refresh();dialog('Scene preview · review before insertion',`<video controls playsinline src="/artifacts/${r.scene}/preview"></video><p>Scene v${r.version}. Current source voice retained. No delivery sign-off or proof approval.</p><button type="button" class="soft" data-artifact-edit="${r.scene}">Edit instance</button><button type="button" class="primary" data-artifact-insert="${r.scene}">Insert in episode</button>`);}finally{if(button.isConnected)button.disabled=false;}});
}
