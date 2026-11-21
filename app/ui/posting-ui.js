'use strict';

async function postingDialog(id) {
  const {info, selection} = await req('/api/posting/info', {export:id});
  const entry = state.exports.find(e => e.id === id);
  const editable = state.jobs[entry.job].revision === info.revision &&
    latestFor(entry.job)?.id === id && !locked(state.jobs[entry.job]);
  const frameMax = Math.max(0, info.duration - .04);
  const options = [0, .3, .65].map(ratio => (frameMax * ratio).toFixed(2));
  dialog('Bộ đăng bài · ' + cutVersion(entry), `
    <p>Revision ${info.revision} · ${info.width}×${info.height} · MP4 ${info.duration.toFixed(2)} giây · ${esc(info.verdict)}</p>
    <div class="review-grid">
      <section>
        <video controls playsinline src="/exports/${esc(id)}/mp4"></video>
        <p>${info.cover?'Bìa 0–0,40 giây → hook → thân video.':'Hook → thân video.'} Timeline ${info.body_seconds.toFixed(2)} giây.</p>
      </section>
      <section id="postingForm">
        <label for="postingSuggestion">Gợi ý từ phụ đề trong bản xuất</label>
        <select id="postingSuggestion"><option value="">Chọn một gợi ý</option>${info.suggestions.map((_,i)=>`<option value="${i}">Gợi ý ${i+1}</option>`).join('')}</select>
        <label for="postingCaption">Caption đăng bài</label>
        <textarea id="postingCaption" rows="4" maxlength="2400">${esc(selection?.caption ?? info.suggestions[0] ?? '')}</textarea>
        <label for="postingFrame">Khung hình trong MP4 (giây)</label>
        <input id="postingFrame" type="number" min="0" max="${frameMax}" step="any" list="postingFrames" value="${selection?.source_seconds ?? options[1]}">
        <datalist id="postingFrames">${options.map(t=>`<option value="${t}"></option>`).join('')}</datalist>
        <label for="postingTitle">Chữ trên thumbnail · tối đa 2 dòng, 22 ký tự mỗi dòng</label>
        <textarea id="postingTitle" rows="2" maxlength="45">${esc(selection?.title ?? '')}</textarea>
        <label for="postingLayout">Vị trí chữ</label>
        <select id="postingLayout"><option value="top">Phía trên</option><option value="bottom">Phía dưới</option></select>
        <label for="postingCrop">Khung hình</label>
        <select id="postingCrop"><option value="full">Toàn khung</option><option value="close">Cận cảnh</option></select>
        <button type="button" class="primary" id="postingSave">Lưu và xem thumbnail</button>
        <button type="button" class="soft" id="postingCopy">Sao chép caption</button>
        <div id="postingFiles"></div>
      </section>
    </div>`);
  const form = el('postingForm');
  form.querySelector('#postingLayout').value = selection?.layout ?? 'top';
  form.querySelector('#postingCrop').value = selection?.crop ?? 'full';
  form.querySelector('#postingSuggestion').addEventListener('change', event => {
    if (event.target.value !== '') el('postingCaption').value = info.suggestions[Number(event.target.value)];
  });
  el('postingCopy').addEventListener('click', guard(async () => {
    await navigator.clipboard.writeText(el('postingCaption').value);
    notify('Đã sao chép caption.');
  }));
  let selected = selection;
  function showFiles() {
    if (!selected) return;
    const path = '/posting/' + encodeURIComponent(id) + '/' + selected.id;
    el('postingFiles').innerHTML = `
      <figure style="margin: .8rem 0"><img alt="Thumbnail đã lưu" src="${path}/thumbnail.png" width="150">
        <figcaption>Frame ${selected.source_frame} · ${selected.source_seconds.toFixed(2)} giây</figcaption></figure>
      <div class="dialogactions">
        <a class="primary" download href="${path}/posting.zip">Tải bộ đăng bài</a>
        <a class="link" download href="${path}/caption.txt?download=1">Caption TXT</a>
        <a class="link" download href="${path}/thumbnail.png?download=1">Thumbnail PNG</a>
      </div>
      ${editable&&selected.cover_sha256?`<details><summary>Xem thiết kế bìa trong video</summary><img alt="Thiết kế bìa" src="${path}/cover.png" width="150"></details><p>Dùng thẻ chữ 0,40 giây ở đầu video. Bản mới cần xem và nghe lại.</p>
      <button type="button" class="soft" id="postingCover">Đổi bìa trong video và xuất bản mới</button>`:''}`;
    el('postingCover')?.addEventListener('click', guard(async event => {
      event.currentTarget.disabled = true;
      try {
        await req('/api/posting/cover', {export:id, sha256:info.sha256, revision:info.revision, package:selected.id});
        el('modal').close();
        await refresh();
        notify('Đã xếp revision bìa mới vào hàng đợi.');
      } finally {
        if (el('postingCover')) el('postingCover').disabled = false;
      }
    }));
  }
  showFiles();
  el('postingSave').addEventListener('click', guard(async event => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      const at = el('postingFrame').valueAsNumber;
      if (!Number.isFinite(at)) throw Error('Chọn thời điểm của khung hình.');
      selected = await req('/api/posting/save', {export:id, sha256:info.sha256, at,
        caption:el('postingCaption').value, title:el('postingTitle').value,
        layout:el('postingLayout').value, crop:el('postingCrop').value});
      if (el('postingForm') === form) showFiles();
    } finally { button.disabled = false; }
  }));
}

document.addEventListener('click', guard(async event => {
  const button = event.target.closest('[data-posting]');
  if (button) await postingDialog(button.dataset.posting);
}));
