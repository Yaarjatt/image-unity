const express = require('express');
const path = require('path');
const fs = require('fs');
const http = require('http');
const crypto = require('crypto');

const CONFIG = {
  PORT: process.env.PORT || 3777,
  HOST: '0.0.0.0',
  UPLOAD_DIR: path.join(__dirname, '..', 'uploads'),
  SITES: {
    imagefree: 'https://imagefree.org',
    freegen: 'https://freegen.app',
    freeforai: 'https://draw.freeforai.com',
    aifreeforever: 'https://aifreeforever.com/image-generators',
    perchance: 'https://perchance.org/text-to-image'
  }
};

if (!fs.existsSync(CONFIG.UPLOAD_DIR)) fs.mkdirSync(CONFIG.UPLOAD_DIR, {recursive: true});

const app = express();
const server = http.createServer(app);

app.use(express.json({limit:'10mb'}));
app.use(express.urlencoded({extended:true, limit:'10mb'}));

app.use((req,res,next)=>{
  res.setHeader('Access-Control-Allow-Origin','*');
  res.setHeader('Access-Control-Allow-Methods','GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers','Content-Type,Authorization,X-Requested-With');
  res.setHeader('X-Frame-Options','SAMEORIGIN');
  if (req.method==='OPTIONS') return res.status(200).end();
  next();
});

// ===== PROXY: Forward requests to free websites =====
// This allows iframes to work even with X-Frame-Options
app.get('/api/proxy/:site', async (req, res) => {
  const { site } = req.params;
  const targetUrl = CONFIG.SITES[site];
  if (!targetUrl) return res.status(404).json({error:'Unknown site: '+site});

  try {
    const resp = await fetch(targetUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
      },
      signal: AbortSignal.timeout(15000)
    });
    let html = await resp.text();

    // Inject JS to allow iframe interaction and capture images
    const inject = `<script>
window.__IMAGE_UNITY_PARENT = "${req.headers.referer || window.location.origin}";
// Notify parent when an image appears
const observer = new MutationObserver(() => {
  const imgs = document.querySelectorAll('img');
  imgs.forEach(img => {
    if (img.src && img.src.startsWith('http') && img.naturalWidth > 100 && !img.dataset.unityTracked) {
      img.dataset.unityTracked = '1';
      window.parent.postMessage({
        type: 'IMAGE_DETECTED',
        site: "${site}",
        src: img.src,
        alt: img.alt,
        width: img.naturalWidth,
        height: img.naturalHeight
      }, '*');
    }
  });
});
observer.observe(document.body, { childList: true, subtree: true });
setTimeout(() => observer.disconnect(), 120000);
<\/script>`;
    html = html.replace('</head>', inject + '</head>');

    // Set headers to allow iframe embedding
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('X-Frame-Options', '');
    res.setHeader('Content-Security-Policy', "frame-ancestors 'self' *");
    res.send(html);
  } catch(e) {
    res.status(502).json({error:'Proxy failed: '+e.message});
  }
});

// ===== GENERATE via Puter.js (no API key needed) =====
// This endpoint generates a page that uses Puter.js client-side
// Each user's browser pays for compute (User-Pays model)
app.post('/api/generate', async (req, res) => {
  const { prompt, model, style } = req.body;
  if (!prompt) return res.status(400).json({error:'Prompt required'});

  // Generate a session ID
  const sessionId = crypto.randomBytes(8).toString('hex');
  const session = {
    id: sessionId,
    prompt,
    model: model || 'gpt-image-2',
    style: style || 'none',
    status: 'pending',
    created: Date.now()
  };

  // Store session
  if (!global.sessions) global.sessions = new Map();
  global.sessions.set(sessionId, session);

  // Return session info - the frontend will use Puter.js to actually generate
  res.json({
    success: true,
    sessionId,
    status: 'pending',
    message: 'Use the /api/session/'+sessionId+'/generate page to trigger generation',
    generateUrl: '/api/session/'+sessionId+'/generate'
  });
});

// ===== SESSION: Page that uses Puter.js to generate =====
app.get('/api/session/:id/generate', (req, res) => {
  const session = global.sessions?.get(req.params.id);
  if (!session) return res.status(404).json({error:'Session not found'});

  res.send(`<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<script src="https://js.puter.com/v2/"></script>
<style>body{background:#0b0d17;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;flex-direction:column;gap:20px}
.spinner{width:40px;height:40px;border:3px solid rgba(255,255,255,0.1);border-top-color:#6c63ff;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
#result{max-width:90vw;max-height:80vh;border-radius:12px;display:none}
#status{color:#8892b0;font-size:14px}
</style></head><body>
<div class="spinner"></div>
<div id="status">Generating "${session.prompt.slice(0,50)}..." using ${session.model}...</div>
<img id="result" />
<script>
(async function(){
  const prompt = ${JSON.stringify(session.prompt)};
  const model = ${JSON.stringify(session.model)};
  try {
    const img = await puter.ai.txt2img(prompt, { model: model });
    document.querySelector('.spinner').remove();
    document.getElementById('result').src = img.src;
    document.getElementById('result').style.display = 'block';
    document.getElementById('status').textContent = 'Done! Generated with ' + model;
    // Notify parent
    window.parent.postMessage({
      type: 'PUTER_IMAGE_READY',
      sessionId: ${JSON.stringify(req.params.id)},
      src: img.src
    }, '*');
  } catch(e) {
    document.getElementById('status').textContent = 'Error: ' + e.message;
  }
})();
<\/script>
</body></html>`);
});

// ===== GET image by ID =====
app.get('/api/image/:id', (req, res) => {
  const safeId = path.basename(req.params.id.replace(/\.\.\//g,''));
  const fp = path.join(CONFIG.UPLOAD_DIR, safeId);
  if (!fs.existsSync(fp)) return res.status(404).json({error:'Image not found'});
  const ext = path.extname(safeId).toLowerCase();
  const mm = {'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.svg':'image/svg+xml'};
  res.setHeader('Content-Type', mm[ext]||'image/png');
  res.setHeader('Cache-Control','public,max-age=86400');
  res.sendFile(fp);
});

// ===== SITES LIST =====
app.get('/api/sites', (req, res) => {
  res.json({
    sites: Object.entries(CONFIG.SITES).map(([k,v]) => ({
      id: k,
      name: k.charAt(0).toUpperCase() + k.slice(1),
      url: v,
      proxyUrl: '/api/proxy/'+k
    }))
  });
});

// ===== Health =====
app.get('/api/health', (req, res) => {
  res.json({
    status:'ok',
    mode:'bridge',
    description:'Bridging to free AI image generators - no API keys needed',
    sites: Object.keys(CONFIG.SITES),
    sessionsActive: global.sessions?.size || 0
  });
});

// Serve frontend
app.use(express.static(path.join(__dirname,'..','frontend')));
app.use((req, res, next) => {
  if (req.method === 'GET' && !req.path.startsWith('/api/')) {
    const fp = path.join(__dirname,'..','frontend','index.html');
    if (fs.existsSync(fp)) return res.sendFile(fp);
  }
  next();
});

server.listen(CONFIG.PORT, CONFIG.HOST, () => {
  console.log('\n  Image Unity Bridge v2');
  console.log('  Web UI: http://localhost:' + CONFIG.PORT);
  console.log('  Proxy:  http://localhost:' + CONFIG.PORT + '/api/proxy/{site}');
  console.log('  Sites:  ' + Object.keys(CONFIG.SITES).join(', '));
  console.log('  No API keys needed!\n');
});
process.on('SIGINT',()=>{console.log('Shutting down...');server.close(()=>process.exit(0));});