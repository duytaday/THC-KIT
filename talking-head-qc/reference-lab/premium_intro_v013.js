/* Full-canvas animation. Real presenter + real captured GitHub image.
   Timeline is explicitly an editorial illustration, never a fake software demo.
   Pure time functions; no particles, camera shake, flash or invented results. */
/*MEDIA[{"id":"host","src":"assets/intro-host.mp4","x":0,"y":0,"w":720,"h":1280,"start":0,"mstart":0,"dur":9.0666666667}]MEDIA*/
window.RUN=(()=>{
 const E={},bars=[];
 const clamp=x=>Math.max(0,Math.min(1,x));
 const ease=(t,a,d)=>{let p=clamp((t-a)/d);return p*p*p*(10+p*(-15+6*p))};
 const mix=(a,b,p)=>a+(b-a)*p;
 const T={edit:wt('ngồi'),insert:wt('chèn'),match:wt('khớp')};
 function box(parent,x,y,w,h,css,html=''){let e=C.abs(parent,x,y,w,h,'',html);e.style.cssText+=';'+css;return e}
 function life(e,t,a,b,dy=25){let p=ease(t,a,.30),q=ease(t,b,.18);e.style.opacity=String(p*(1-q));e.style.transform=`translateY(${(1-p)*dy-q*20}px)`}
 function build(stage){
  document.querySelector('.bgl').style.background='#f1f0e9';document.querySelector('.vig').style.display='none';stage.style.fontFamily='KitVietnam,sans-serif';
  E.bg=box(stage,0,0,720,1280,'z-index:0;background:radial-gradient(ellipse at 85% 20%,#d4f46588,transparent 48%),linear-gradient(#f5f4ed,#e7e8e2)');
  E.grid=box(stage,0,0,720,1020,'z-index:1;opacity:.25;background-image:linear-gradient(#adb6aa55 1px,transparent 1px),linear-gradient(90deg,#adb6aa55 1px,transparent 1px);background-size:48px 48px');
  E.video=document.getElementById('vw_host');E.video.style.cssText+=';z-index:4;overflow:hidden;box-shadow:0 26px 60px #0b1b1735;transform-origin:50% 50%';
  E.video.querySelector('video').style.cssText+=';width:100%;height:100%;object-fit:cover;object-position:50% 38%';
  E.kicker=box(stage,44,52,632,35,'z-index:10;font-size:24px;letter-spacing:2px;font-weight:800;color:#23372f','5 REPO GITHUB / AI EDIT VIDEO');
  E.head1=box(stage,42,122,638,213,'z-index:7;font:900 82px/1.16 KitVietnam;color:#142b24;letter-spacing:-2px','QUAY<br><span style="background:#d4f465;padding:0 8px">1 PHÚT.</span>');
  E.head2=box(stage,42,122,638,213,'z-index:7;font:900 82px/1.16 KitVietnam;color:#142b24;letter-spacing:-2px','DỰNG<br><span style="background:#d4f465;padding:0 8px">CẢ BUỔI?</span>');
  E.head3=box(stage,42,122,650,225,'z-index:7;font:900 74px/1.16 KitVietnam;color:#142b24;letter-spacing:-3px','HÌNH KHỚP<br><span style="background:#d4f465;padding:0 8px">ĐÚNG LỜI.</span>');
  E.clock=box(stage,451,354,208,208,'z-index:6;border-radius:50%;background:#142b24;color:#e9f4df;box-shadow:0 18px 35px #142b2425','<svg width="208" height="208" viewBox="0 0 208 208"><circle cx="104" cy="104" r="91" fill="none" stroke="#829477" stroke-width="2"/><circle id="time-ring" cx="104" cy="104" r="91" fill="none" stroke="#d4f465" stroke-width="9" stroke-linecap="round" transform="rotate(-90 104 104)" stroke-dasharray="572"/><text x="104" y="112" text-anchor="middle" fill="#fff" font-family="KitVietnam" font-size="42" font-weight="800">01:00</text><text x="104" y="142" text-anchor="middle" fill="#d4f465" font-family="KitVietnam" font-size="18">GIỌNG GỐC</text></svg>');
  E.sticker=box(stage,431,580,236,154,'z-index:7;border-radius:16px;background:#d4f465;padding:18px;box-shadow:0 14px 25px #172b2425;font:800 27px/1.24 KitVietnam;color:#142b24','QUAY XONG…<br>CHƯA DỰNG<br>XONG!');
  E.browser=box(stage,369,428,307,278,'z-index:6;border:7px solid white;border-radius:21px;background:white;box-shadow:0 20px 40px #142b2435;overflow:hidden;transform-origin:50% 50%','<div style="height:30px;background:#ecede7;padding-left:12px;font:700 17px/30px KitVietnam;color:#142b24">● ● ● &nbsp; GITHUB THẬT</div><img src="assets/github.png" style="width:100%;height:230px;object-fit:cover;object-position:50% 0">');
  E.timeline=box(stage,42,808,636,194,'z-index:7;background:#142b24;border:1px solid #354c3d;border-radius:22px;padding:16px;box-shadow:0 18px 35px #142b2425');
  box(E.timeline,17,12,590,26,'font:800 20px KitVietnam;letter-spacing:1px;color:#e9f4df','TIMELINE MINH HỌA / HÌNH + GIỌNG');
  const widths=[110,182,157,100],labels=['MẶT','MÀN HÌNH','KẾT QUẢ','MẶT'];let x=18;
  for(let i=0;i<4;i++){let b=box(E.timeline,x,54,widths[i],45,`border-radius:8px;background:${i%2?'#d4f465':'#ecede7'};color:#142b24;font:700 23px/1.15 KitVietnam;padding:9px 7px`,labels[i]);bars.push(b);x+=widths[i]+8}
  E.voice=box(E.timeline,18,114,600,37,'border-radius:8px;background:#d4f465;color:#142b24;font:700 25px/37px KitVietnam;text-align:center','GIỌNG NÓI LIỀN MẠCH');
  E.playhead=box(E.timeline,20,46,3,125,'z-index:9;background:white;box-shadow:0 0 7px #fff8');
  E.match=box(stage,436,732,232,44,'z-index:8;border-radius:22px;background:#142b24;color:#d4f465;text-align:center;font:800 22px/44px KitVietnam','✓ KHỚP LỜI');
 }
 function render(t){
  let shrink=ease(t,.12,1.02),edit=ease(t,T.edit-.12,.5),back=ease(t,8.05,1.0167);
  let x=mix(0,44,shrink),y=mix(0,373,shrink),w=mix(720,370,shrink),h=mix(1280,432,shrink);
  x=mix(x,43,edit);y=mix(y,390,edit);w=mix(w,318,edit);h=mix(h,388,edit);
  Object.assign(E.video.style,{opacity:'1',left:mix(x,0,back)+'px',top:mix(y,0,back)+'px',width:mix(w,720,back)+'px',height:mix(h,1280,back)+'px',borderRadius:(24*shrink*(1-back))+'px',transform:`perspective(1400px) rotateY(${(-2*shrink+1*edit)*(1-back)}deg) rotateZ(${(-1.2*shrink+.5*edit)*(1-back)}deg)`});
  E.bg.style.opacity=String(1-back);E.grid.style.opacity=String(.25*(1-back));
  life(E.kicker,t,.2,8.28,15);life(E.head1,t,.35,T.edit-.18,24);life(E.head2,t,T.edit-.02,T.match-.15,24);life(E.head3,t,T.match,8.28,24);
  life(E.clock,t,.65,T.edit-.15,40);document.getElementById('time-ring').style.strokeDashoffset=String(572*(1-clamp((t-.65)/3.7)));
  life(E.sticker,t,T.edit+.1,T.insert+.08,36);
  let browserIn=ease(t,T.insert+.08,.32),browserOut=ease(t,8.28,.22);E.browser.style.opacity=String(browserIn*(1-browserOut));E.browser.style.transform=`perspective(1200px) translateX(${(1-browserIn)*90}px) rotateY(${(1-browserIn)*-8-2}deg) rotateZ(${(1-browserIn)*3+1}deg)`;
  life(E.timeline,t,T.edit-.05,8.3,65);bars.forEach((b,i)=>{let p=ease(t,T.edit+.09+i*.07,.28);b.style.opacity=String(p);b.style.transform=`translateX(${(1-p)*85}px)`});
  E.playhead.style.left=(20+clamp((t-T.edit)/3.45)*585)+'px';life(E.match,t,T.match+.08,8.28,30);
 }
 return {build,render};
})();
