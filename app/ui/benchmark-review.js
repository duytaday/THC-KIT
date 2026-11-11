"use strict";
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data, timers={};
const number=v=>v===''?null:Number(v);
function range(text){const t=text.trim().split(/\s*-\s*/);const seconds=s=>s.split(':').reduce((a,b)=>a*60+Number(b),0);if(t.length!==2||t.some(x=>!/^\d+(?::[0-5]?\d)*(?:\.\d+)?$/.test(x)))throw Error('Dùng timecode start-end, ví dụ 00:04.5-00:07.2');return t.map(seconds);}
function prepare(){
 const reviewer=$('reviewer').value.trim();if(!reviewer)throw Error('Điền người đã thực sự review.');
 const reviews=data.videos.map((v,i)=>{
  const box=$('case-'+i),get=id=>box.querySelector('[data-field="'+id+'"]'),player=box.querySelector('video'),canWatch=get('watch').checked,canListen=get('audio').checked;
  const gates={};for(const k of Object.keys(data.gates)){
   const status=get('gate-'+k).value,lines=get('notes-'+k).value.trim();
   const observations=lines?lines.split('\n').filter(Boolean).map(line=>{const pieces=line.split('|').map(s=>s.trim());if(pieces.length!==4)throw Error('Mỗi dòng: beat-id | start-end | visual/audio/both | điều thấy/nghe');return {beat_id:pieces[0],master_range:range(pieces[1]),modality:pieces[2],actual:pieces[3]};}):[];
   gates[k]={status,observations};
  }
  const flow={};for(const key of data.flow_dimensions){const rating=number(get('rating-'+key).value);flow[key]={rating,reference_id:get('ref-'+key).value||null,reference_range:rating?range(get('refrange-'+key).value):null,master_range:rating?range(get('range-'+key).value):null,note:get('flow-'+key).value};}
  const quiz_answers=(v.quiz||[]).map((q,j)=>({id:q.id,answer:q.modality==='audio'&&!canListen?null:get('answer-'+j).value||null,master_range:get('qrange-'+j).value?range(get('qrange-'+j).value):null}));
  const active=timers[i]||{seconds:0};if(active.start)throw Error('Dừng timer sửa trước khi tạo phiếu.');
  return {id:v.id,master_sha256:v.sha256,reviewer,can_watch:canWatch,can_listen:canListen,speed:player.playbackRate,width_px:Math.round(player.getBoundingClientRect().width),watched_ranges:get('fullwatch').checked?[[0,v.duration]]:[],listened_ranges:canListen&&get('fullhear').checked?[[0,v.duration]]:[],gates,flow,quiz_answers,first_pass_accepted:get('first').value===''?null:get('first').value==='yes',reviewed_segments:number(get('segments').value),unchanged_segments:number(get('kept').value),repair_sessions:active.seconds?[{active_seconds:active.seconds,editor:reviewer,evidence:get('repairnote').value}]:[],final_duration_seconds:v.duration,approved_correction_ids:get('corrections').value.split(',').map(s=>s.trim()).filter(Boolean)};
 });
 const result={protocol_sha256:data.protocol_sha256,reviews};$('json').value=JSON.stringify(result,null,2);return result;
}
async function init(){
 data=await (await fetch('review-data.json')).json();
 $('references').innerHTML='<details><summary>Reference và khoảng đã quan sát</summary>'+data.reference_cards.map(c=>`<p><strong>${esc(c.id)}</strong> · ${c.duration.toFixed(2)}s · SHA ${c.sha256.slice(0,12)}</p>${c.file?`<video controls preload="metadata" src="${esc(c.file)}"></video>`:''}<ul>${c.observed_intervals.map(o=>`<li>${o.source_range.join('–')}s: ${esc(o.observation)}</li>`).join('')}</ul>`).join('')+'<p>Scene-change candidates không chứng minh easing, SFX hoặc chất lượng. Chấm theo reference phù hợp với nội dung tập này.</p></details>';
 data.videos.forEach((v,i)=>{
  const field=(id,label,type='text')=>`<label>${esc(label)}<input type="${type}" data-field="${id}"></label>`;
  const text=(id,label)=>`<label>${esc(label)}<textarea data-field="${id}"></textarea></label>`;
  const select=(id,label,values)=>`<label>${esc(label)}<select data-field="${id}">${values.map(([value,name])=>`<option value="${esc(value)}">${esc(name)}</option>`).join('')}</select></label>`;
  const article=document.createElement('article');article.id='case-'+i;
  article.innerHTML=`<h2>${esc(v.label)}</h2><video controls playsinline preload="metadata" src="${esc(v.file)}"></video><small>SHA ${v.sha256} · ${v.duration.toFixed(3)}s</small>`+field('watch','Tôi có hình và có thể xem.','checkbox')+field('audio','Tôi có audio và có thể nghe.','checkbox')+field('fullwatch','Tôi đã xem trọn bản này ở 1×, khung điện thoại.','checkbox')+field('fullhear','Tôi đã nghe trọn bản này ở 1×.','checkbox')+`<p>Beats phải kiểm: ${v.required_beats.map(esc).join(', ')||'Theo brief hiện tại.'}</p>`+
   Object.entries(data.gates).map(([k,label])=>`<details><summary>${k} · ${esc(label)}</summary>`+select('gate-'+k,'Kết quả',[['UNVERIFIED','Chưa kiểm'],['FAIL','Cần sửa'],['PASS','Đạt']])+text('notes-'+k,'Mỗi dòng: beat-id | start-end | visual/audio/both | quan sát thực tế')+'</details>').join('')+
   `<details><summary>Flow so với reference · điểm 1–5</summary><p>1: lỗi rõ; 2: sửa nhiều; 3: sửa ít; 4: giữ ngay; 5: giữ ngay và người xem nhận đúng hành động/payoff. Ghi mốc reference lẫn master.</p>`+data.flow_dimensions.map(key=>'<fieldset><legend>'+esc(key)+'</legend>'+select('rating-'+key,'Điểm',[['','Chưa chấm'],...[1,2,3,4,5].map(n=>[n,n])])+select('ref-'+key,'Reference',[['','Chọn nguồn'],...data.reference_cards.map(c=>[c.id,c.id])])+field('refrange-'+key,'Reference start-end')+field('range-'+key,'Master start-end')+text('flow-'+key,'Vì sao giữ hoặc cần sửa?')+'</fieldset>').join('')+'</details>'+
   `<details><summary>Câu hỏi người xem · không lộ đáp án</summary>`+(v.quiz||[]).map((q,j)=>(q.options?.length?select('answer-'+j,q.text,[['','Chọn sau khi xem'],...q.options.map(s=>[s,s])]):field('answer-'+j,q.text))+field('qrange-'+j,'Timecode câu trả lời')).join('')+'</details>'+
   select('first','Có thể giữ nguyên bản đề xuất đầu tiên?',[['','Chưa quyết định'],['no','Không, cần sửa'],['yes','Có, giữ nguyên']])+field('segments','Số đoạn đã duyệt','number')+field('kept','Số đoạn giữ nguyên','number')+
   `<details><summary>Đo thời gian sửa thật</summary><p>Chỉ bật timer khi đang sửa; tạm dừng khi chờ render hoặc nghỉ.</p><button type="button" data-timer="${i}">Bắt đầu sửa</button><output id="timer-${i}">0s</output>`+text('repairnote','Đã sửa gì / phiên dựng hoặc log nào?')+'</details>'+field('corrections','Correction IDs đã xem trong bản này và duyệt để học · phân cách bằng dấu phẩy');
  $('videos').append(article);
  article.querySelector('video').addEventListener('ratechange',e=>{if(e.target.playbackRate!==1)$('message').textContent='Review benchmark yêu cầu 1×; hãy xem/nghe lại ở tốc độ thường.';});
 });
}
document.addEventListener('click',e=>{const b=e.target.closest('[data-timer]');if(!b)return;const i=b.dataset.timer,t=timers[i]||{seconds:0};if(t.start){t.seconds+=(performance.now()-t.start)/1000;delete t.start;b.textContent='Tiếp tục sửa';}else{t.start=performance.now();b.textContent='Tạm dừng';}timers[i]=t;$('timer-'+i).textContent=t.seconds.toFixed(1)+'s'+(t.start?' · đang đo':'');});
$('prepare').onclick=()=>{try{prepare();$('message').textContent='Đã tạo phiếu. Chưa cấp READY.';}catch(e){$('message').textContent=e.message;}};
$('save').onclick=async()=>{try{const review=prepare(),id=location.pathname.split('/').filter(Boolean).at(-2);if(!location.pathname.startsWith('/benchmarks/'))throw Error('Phiếu đã tạo. Lưu JSON trên D rồi chạy lệnh score trong kit.');const state=await(await fetch('/api/state')).json();const response=await fetch('/api/benchmarks/review',{method:'POST',headers:{'Content-Type':'application/json','X-Cutroom-Key':state.key},body:JSON.stringify({id,review})});const result=await response.json();if(!response.ok)throw Error(result.error);$('message').textContent='Đã lưu review '+result.version+'. Release vẫn đi qua QC hooks.';}catch(e){$('message').textContent=e.message;}};
init().catch(e=>{$('message').textContent=e.message+' · Mở qua HTTP local, không mở trực tiếp file://.';});
