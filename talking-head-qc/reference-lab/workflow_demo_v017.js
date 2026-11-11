/* Real current presenter, actual repo image and actual before/after video.
   A demo of this completed edit, not a fabricated app or generation result. */
/*MEDIA[{"id":"current","src":"assets/workflow-host.mp4","x":0,"y":0,"w":720,"h":1280,"start":0,"mstart":0,"dur":10},{"id":"before","src":"assets/workflow-before-extended.mp4","x":44,"y":342,"w":300,"h":533,"start":6.25,"mstart":0,"dur":3.7},{"id":"after","src":"assets/workflow-after-extended.mp4","x":376,"y":342,"w":300,"h":533,"start":6.25,"mstart":0,"dur":3.7}]MEDIA*/
window.RUN=(()=>{
 const E={},chips=[];const clamp=x=>Math.max(0,Math.min(1,x));
 const ease=(t,a,d)=>{let p=clamp((t-a)/d);return p*p*p*(10+p*(-15+6*p))};
 const mix=(a,b,p)=>a+(b-a)*p;
 function box(p,x,y,w,h,css,html=''){let e=C.abs(p,x,y,w,h,'',html);e.style.cssText+=';'+css;return e}
 function life(e,t,a,b,dy=18){let p=ease(t,a,.28),q=ease(t,b,.18);e.style.opacity=String(p*(1-q));e.style.transform=`translateY(${(1-p)*dy-q*12}px)`}
 function build(stage){
  document.querySelector('.bgl').style.background='#f1f0e9';document.querySelector('.vig').style.display='none';stage.style.fontFamily='KitVietnam';
  E.bg=box(stage,0,0,720,1280,'z-index:0;background:#f1f0e9');
  E.current=document.getElementById('vw_current');E.current.style.cssText+=';z-index:4;overflow:hidden;box-shadow:0 20px 45px #142b2430;';
  E.current.querySelector('video').style.cssText+=';width:100%;height:100%;object-fit:cover';
  E.community=box(stage,44,104,632,148,'z-index:8;border-radius:22px;background:#f4f3ed;box-shadow:0 12px 30px #142b2430;padding:20px 24px;color:#142b24','<div style="font:700 25px/1.3 KitVietnam;letter-spacing:1px">CỘNG ĐỒNG</div><div style="font:800 49px/1.35 KitVietnam">Việc làm Video AI</div>');
  E.title=box(stage,44,108,632,205,'z-index:7;font:900 75px/1.17 KitVietnam;letter-spacing:-2px;color:#142b24','5 REPO<br><span style="background:#d4f465;padding:0 8px">EDIT VIDEO</span>');
  const names=['FFmpeg Skill','Recordly','Remotion','fal','Runway'];
  for(let i=0;i<5;i++)chips.push(box(stage,315,351+i*86,360,70,`z-index:7;background:${i===0?'#d4f465':'#fff'};border:1px solid #c5cec3;border-radius:14px;padding:12px 16px;font:800 33px/1.35 KitVietnam;color:#142b24;box-shadow:0 7px 18px #142b2410`,names[i]));
  E.github=box(stage,44,804,632,174,'z-index:6;background:#101820;border-radius:16px;overflow:hidden;box-shadow:0 10px 25px #142b2425','<div style="height:37px;padding-left:16px;background:#d4f465;font:800 24px/37px KitVietnam;color:#142b24">GITHUB THẬT</div><img src="assets/workflow-github.png" style="width:100%;height:137px;object-fit:cover;object-position:top">');
  E.demoTitle=box(stage,44,113,632,154,'z-index:8;font:900 61px/1.22 KitVietnam;color:#142b24','DEMO<br><span style="background:#d4f465;padding:0 8px">BẢN DỰNG</span>');
  E.beforeTitle=box(stage,44,282,300,55,'z-index:8;text-align:center;font:800 35px/55px KitVietnam;color:#142b24','TRƯỚC');
  E.afterTitle=box(stage,376,282,300,55,'z-index:8;text-align:center;font:800 35px/55px KitVietnam;color:#142b24','SAU');
  for(const id of ['before','after']){E[id]=document.getElementById('vw_'+id);E[id].style.cssText+=';z-index:6;overflow:hidden;border:3px solid #d4f465;border-radius:20px;box-shadow:0 16px 30px #142b2425';E[id].querySelector('video').style.cssText+=';width:100%;height:100%;object-fit:cover';}
  E.note=box(stage,44,910,632,58,'z-index:8;border-radius:12px;background:#142b24;color:#d4f465;text-align:center;font:700 30px/58px KitVietnam','CÙNG MỘT ĐOẠN VLOG');
 }
 function render(t){
  const shrink=ease(t,2.22,.70),demo=ease(t,6.25,.30),back=ease(t,9.24,.76);
  E.bg.style.opacity=String(1-back);
  Object.assign(E.current.style,{left:mix(44*shrink,0,back)+'px',top:mix(351*shrink,0,back)+'px',width:mix(mix(720,240,shrink),720,back)+'px',height:mix(mix(1280,426,shrink),1280,back)+'px',borderRadius:24*shrink*(1-back)+'px',opacity:String((1-demo)*(1-back)+back)});
  life(E.community,t,.76,2.18,15);life(E.title,t,2.58,6.12,24);
  chips.forEach((e,i)=>{let p=ease(t,3.42+i*.10,.26),q=ease(t,6.05+i*.035,.18);e.style.opacity=String(p*(1-q));e.style.transform=`translateX(${(1-p)*50+q*25}px)`});
  life(E.github,t,5.0,6.18,18);
  life(E.demoTitle,t,6.22,9.85,20);life(E.beforeTitle,t,6.25,9.85,15);life(E.afterTitle,t,6.32,9.85,15);
  for(const id of ['before','after']){let p=ease(t,id==='before'?6.25:6.32,.28),q=ease(t,9.85,.15);E[id].style.opacity=String(p*(1-q));E[id].style.transform=`translateY(${(1-p)*30-q*12}px) scale(${.96+.04*p})`;}
  life(E.note,t,6.55,9.85,12);
  // Opaque left-to-right reveal: no white dip or moving/blurred face.
  if(t>=9.18){
    const reveal=ease(t,9.18,.67);
    Object.assign(E.current.style,{zIndex:'20',opacity:'1',left:'0px',top:'0px',width:'720px',height:'1280px',borderRadius:'0px',clipPath:`inset(0 ${100*(1-reveal)}% 0 0)`});
  }else{E.current.style.zIndex='4';E.current.style.clipPath='none';}

 }
 return {build,render};
})();
