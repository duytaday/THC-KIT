'use strict';

async function openRetakes(exportId) {
  const entry = state.exports.find(e => e.id === exportId);
  const result = await req('/api/retakes', {operation:'list',id:entry.job,export:entry.id});
  const bound = {id:entry.job,export:entry.id,sha256:result.sha256,revision:result.revision};
  const choices = result.proposals.flatMap(p => p.choices);
  const stamp = ([a,b]) => `${a.toFixed(2)}–${b.toFixed(2)} s`;
  dialog('Kiểm take lặp · ' + cutVersion(entry), `
    ${result.proposals.map(p=>`<fieldset>
      <legend>Hai câu liền nhau</legend>
      ${p.takes.map((t,i)=>`<p>Take ${i+1} · nguồn ${stamp(t.source_range)} · ${esc(t.quote)}</p>`).join('')}
      <p>Chữ khớp và có khoảng nghỉ. Có thể là lặp để nhấn ý.</p>
      ${p.choices.map(c=>`<button class="soft" type="button" data-retake-preview="${c.id}">
        Nghe nối · giữ nguồn ${stamp(c.keep_take.source_range)} · bỏ MP4 ${stamp(c.master_cut)}
      </button>`).join('')}
    </fieldset>`).join('') || '<p>Giữ nguyên hoặc chỉnh tay. Cần hai câu liền nhau trùng chữ, timing từng từ và khoảng nghỉ đủ rõ.</p>'}
    <div id="retakeComparison"></div>
    ${result.undo?`<p><a href="/exports/${esc(result.undo.prior_export)}/mp4" target="_blank" rel="noopener">Mở bản trước khi bỏ take</a></p>
    <button class="soft" type="button" id="retakeUndo">Khôi phục và xuất bản mới</button>`:''}
  `);
  const area = el('retakeComparison');
  async function save(operation, detail, button) {
    button.disabled = true;
    try {
      const key = 'retake:' + result.sha256 + ':' + operation + ':' + (detail.choice || '');
      let requestId = sessionStorage.getItem(key);
      if (!requestId) {
        requestId = crypto.randomUUID();
        sessionStorage.setItem(key,requestId);
      }
      const saved = await req('/api/retakes',{...bound,...detail,operation,confirmed:true,request_id:requestId});
      await req('/api/queue',{ids:[saved.job],request_id:requestId+'-render'});
      sessionStorage.removeItem(key);
      el('modal').close();
      await refresh();
      notify('Revision '+saved.revision+' đã vào hàng đợi.');
    } finally { button.disabled = false; }
  }
  for (const button of all('[data-retake-preview]')) {
    button.addEventListener('click',guard(async () => {
      button.disabled = true;
      try {
        const choice=choices.find(c=>c.id===button.dataset.retakePreview);
        const preview=await req('/api/retakes',{...bound,operation:'preview',choice:choice.id});
        if (el('retakeComparison')!==area) return;
        const path='/retakes/'+entry.id+'/'+preview.id;
        area.innerHTML=`
          <div class="review-grid">
            <section><h3>Trước</h3><video controls playsinline src="${path}/before.mp4"></video></section>
            <section><h3>Sau</h3><video controls playsinline src="${path}/after.mp4"></video>
            <p>Điểm nối ở ${preview.splice.toFixed(2)} giây của preview.</p></section>
          </div>
          <label><input id="retakeConfirm" type="checkbox"> Tôi chọn bỏ đoạn nguồn ${stamp(choice.source_cut)}.</label>
          <button type="button" class="primary" id="retakeApply" disabled>Áp dụng và xuất bản mới</button>`;
        const apply=el('retakeApply');
        el('retakeConfirm').addEventListener('change',e=>{apply.disabled=!e.target.checked;});
        apply.addEventListener('click',guard(()=>save('apply',{choice:choice.id,preview:preview.id},apply)));
      } finally { button.disabled=false; }
    }));
  }
  el('retakeUndo')?.addEventListener('click',guard(event=>save('undo',{},event.currentTarget)));
}

document.addEventListener('click',guard(async event => {
  const button=event.target.closest('[data-retakes]');
  if (button) await openRetakes(button.dataset.retakes);
}));
