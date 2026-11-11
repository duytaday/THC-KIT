// Inspect only this project's rendered HTML in a separate headless browser.
const fs=require('fs');const path=require('path');const {pathToFileURL}=require('url');
const puppeteer=require('C:/Users/Acer/AppData/Local/npm-cache/_npx/53d5ac1d8acc5858/node_modules/puppeteer-core');
(async()=>{
 const root=process.argv[2],out=process.argv[3],html=process.argv[4]||'intro.html',time=Number(process.argv[5]||5.5);
 if(path.basename(html)!==html||!html.endsWith('.html')||!Number.isFinite(time))throw Error('Invalid local render audit arguments');
 const browser=await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--allow-file-access-from-files']});
 try{
 const page=await browser.newPage();await page.setViewport({width:720,height:1280});
 await page.goto(pathToFileURL(path.join(root,html)).href,{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.__timelines&&window.__timelines.root);
 await page.evaluate(async t=>{await document.fonts.ready;window.RUN.render(t)},time);
 const cdp=await page.createCDPSession();await cdp.send('DOM.enable');await cdp.send('CSS.enable');
 const {root:doc}=await cdp.send('DOM.getDocument',{depth:-1});
 const nodes=await cdp.send('DOM.querySelectorAll',{nodeId:doc.nodeId,selector:'#stage div,#stage span,svg text'});
 const result=[];
 for(const nodeId of nodes.nodeIds){
   const info=await cdp.send('CSS.getPlatformFontsForNode',{nodeId});
   if(info.fonts.length){const obj=await cdp.send('DOM.resolveNode',{nodeId});const text=await cdp.send('Runtime.callFunctionOn',{objectId:obj.object.objectId,functionDeclaration:'function(){return this.textContent}',returnByValue:true});result.push({text:text.result.value,fonts:info.fonts});}
 }
 const fontFaces=await page.evaluate(()=>[...document.fonts].map(f=>({family:f.family,weight:f.weight,status:f.status})));
 await page.screenshot({path:out+'.png'});fs.writeFileSync(out+'.json',JSON.stringify({fontFaces,nodes:result},null,2));
 console.log(JSON.stringify(result.filter(x=>/CẢ BUỔI|DỰNG|GIỌNG/.test(x.text))));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
