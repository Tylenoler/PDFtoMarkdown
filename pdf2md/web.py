"""Flask Web UI for pdf2md — modern drag-drop interface with SSE progress."""

import json
import os
import queue
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template_string, request, send_file

from pdf2md.converter import Converter
from pdf2md.utils.helpers import collect_pdf_files

# ── In-memory progress store ─────────────────────────────────────────
_jobs: dict[str, Any] = {}
_job_queues: dict[str, "queue.Queue"] = {}


def _emit(job_id: str, event: str, data: dict) -> None:
    if job_id in _job_queues:
        _job_queues[job_id].put((event, data))


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PDF → Markdown</title>
<style>
/* ── CSS Variables / Theme ──────────────────────────────────── */
:root { --bg: #0f0f13; --surface: #1a1a22; --surface2: #23232e;
  --border: #2d2d3d; --text: #e4e4ec; --text2: #9090a8;
  --accent: #6c5ce7; --accent-hover: #7f6ff0; --accent-glow: rgba(108,92,231,.25);
  --green: #00d2a0; --red: #ff6b6b; --orange: #ffa94d;
  --radius: 12px; --font: 'Inter', -apple-system, system-ui, sans-serif; }
:root[data-theme="light"] { --bg: #f5f5fa; --surface: #ffffff;
  --surface2: #eeeef4; --border: #dcdce6; --text: #1a1a2e;
  --text2: #6c6c82; --accent: #6c5ce7; --accent-hover: #5b4bd6;
  --accent-glow: rgba(108,92,231,.15); --green: #00a87a; --red: #e74c3c;
  --orange: #d97a00; }

/* ── Reset & Base ───────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }
body { font-family: var(--font); background: var(--bg); color: var(--text);
  display: flex; flex-direction: column; transition: background .3s, color .3s;
  -webkit-font-smoothing: antialiased; }

/* ── Scrollbar ──────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* ── Header ─────────────────────────────────────────────────── */
header { display: flex; align-items: center; justify-content: space-between;
  padding: 20px 32px; border-bottom: 1px solid var(--border);
  flex-shrink: 0; }
header h1 { font-size: 18px; font-weight: 600; letter-spacing: -.3px;
  display: flex; align-items: center; gap: 10px; }
header h1 span.icon { font-size: 22px; }
.header-actions { display: flex; align-items: center; gap: 12px; }
.theme-toggle { background: var(--surface2); border: 1px solid var(--border);
  color: var(--text2); width: 34px; height: 34px; border-radius: 8px;
  cursor: pointer; font-size: 16px; display: flex; align-items: center;
  justify-content: center; transition: .2s; }
.theme-toggle:hover { background: var(--border); color: var(--text); }

/* ── Main Layout ────────────────────────────────────────────── */
main { flex: 1; display: flex; flex-direction: column; padding: 24px 32px;
  gap: 20px; overflow-y: auto; }

/* ── Drop Zone ──────────────────────────────────────────────── */
.drop-zone { position: relative; border: 2px dashed var(--border);
  border-radius: var(--radius); padding: 48px 24px;
  text-align: center; cursor: pointer; transition: all .25s ease;
  background: var(--surface); }
.drop-zone:hover, .drop-zone.dragover { border-color: var(--accent);
  background: var(--accent-glow); }
.drop-zone .icon { font-size: 40px; margin-bottom: 12px; opacity: .6; }
.drop-zone h2 { font-size: 16px; font-weight: 500; margin-bottom: 6px; }
.drop-zone p { font-size: 13px; color: var(--text2); }
.drop-zone input[type="file"] { display: none; }

/* ── File Queue ─────────────────────────────────────────────── */
.queue { display: flex; flex-direction: column; gap: 8px;
  max-height: 360px; overflow-y: auto; }
.queue-item { display: flex; align-items: center; gap: 12px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 12px 16px;
  transition: border-color .2s; }
.queue-item .name { flex: 1; font-size: 14px; font-weight: 500;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.queue-item .status { font-size: 12px; color: var(--text2);
  min-width: 60px; text-align: right; }
.queue-item .bar { width: 80px; height: 4px; background: var(--surface2);
  border-radius: 2px; overflow: hidden; flex-shrink: 0; }
.queue-item .bar .fill { height: 100%; width: 0%; border-radius: 2px;
  background: var(--accent); transition: width .4s ease; }
.queue-item .bar .fill.done { background: var(--green); }
.queue-item .bar .fill.error { background: var(--red); }
.queue-item .remove-btn { background: none; border: none; color: var(--text2);
  cursor: pointer; font-size: 16px; padding: 2px; border-radius: 4px; }
.queue-item .remove-btn:hover { color: var(--red); background: rgba(255,107,107,.1); }
.queue-empty { text-align: center; padding: 24px; color: var(--text2);
  font-size: 13px; }

/* ── Controls Bar ───────────────────────────────────────────── */
.controls { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.controls button { display: inline-flex; align-items: center; gap: 6px;
  padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 500;
  border: none; cursor: pointer; transition: .2s;
  font-family: var(--font); }
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover:not(:disabled) { background: var(--accent-hover);
  box-shadow: 0 4px 16px var(--accent-glow); }
.btn-primary:disabled { opacity: .4; cursor: not-allowed; }
.btn-secondary { background: var(--surface2); color: var(--text);
  border: 1px solid var(--border) !important; }
.btn-secondary:hover { background: var(--border); }
.btn-danger { background: rgba(255,107,107,.1); color: var(--red); }
.btn-danger:hover { background: rgba(255,107,107,.2); }
.btn-success { background: rgba(0,210,160,.1); color: var(--green); }
.btn-success:hover { background: rgba(0,210,160,.2); }

/* ── Summary / Result ───────────────────────────────────────── */
.summary { display: none; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 20px 24px; margin-top: 8px; }
.summary.show { display: block; }
.summary h3 { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
.summary .stats { display: flex; gap: 24px; font-size: 13px; color: var(--text2); }
.summary .stats span { display: flex; align-items: center; gap: 4px; }
.summary .stats strong { color: var(--text); }

/* ── Toast ──────────────────────────────────────────────────── */
.toast { position: fixed; bottom: 24px; right: 24px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 12px 20px;
  font-size: 13px; box-shadow: 0 8px 32px rgba(0,0,0,.4);
  transform: translateY(100px); opacity: 0; transition: .35s ease;
  pointer-events: none; z-index: 999; }
.toast.show { transform: translateY(0); opacity: 1; }
.toast.error { border-color: var(--red); }
.toast.done { border-color: var(--green); }

/* ── Responsive ─────────────────────────────────────────────── */
@media (max-width: 640px) {
  header { padding: 16px; }
  main { padding: 16px; }
  .drop-zone { padding: 32px 16px; }
}

/* ── Animations ─────────────────────────────────────────────── */
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); } }
.queue-item { animation: fadeIn .3s ease; }
</style>
</head>
<body>

<header>
  <h1><span class="icon">📄</span> PDF → Markdown</h1>
  <div class="header-actions">
    <button class="theme-toggle" onclick="toggleTheme()" title="切换主题" id="themeBtn">🌙</button>
  </div>
</header>

<main>
  <!-- Drop Zone -->
  <div class="drop-zone" id="dropZone">
    <div class="icon">📂</div>
    <h2>拖拽 PDF 文件到这里</h2>
    <p>或者点击选择文件 · 支持批量</p>
    <input type="file" id="fileInput" accept=".pdf" multiple>
  </div>

  <!-- Controls -->
  <div class="controls">
    <button class="btn-primary" id="convertBtn" disabled onclick="startConvert()">
      ⚡ 开始转换
    </button>
    <button class="btn-secondary" onclick="clearQueue()">🗑 清空列表</button>
    <button class="btn-secondary" onclick="openOutput()" id="openOutputBtn" disabled>
      📂 打开输出目录
    </button>
  </div>

  <!-- Queue -->
  <div class="queue" id="queue">
    <div class="queue-empty" id="queueEmpty">还没有添加文件</div>
  </div>

  <!-- Summary -->
  <div class="summary" id="summary"></div>
</main>

<!-- Toast -->
<div class="toast" id="toast"></div>

<script>
(function() {
  /* ── State ──────────────────────────────────────────────── */
  const queue = [];
  let convertId = 0;
  let currentJobId = null;

  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const queueEl = document.getElementById('queue');
  const queueEmpty = document.getElementById('queueEmpty');
  const convertBtn = document.getElementById('convertBtn');
  const summaryEl = document.getElementById('summary');
  const toastEl = document.getElementById('toast');
  const openOutputBtn = document.getElementById('openOutputBtn');

  let lastOutputDirs = [];

  /* ── Drop / Select ──────────────────────────────────────── */
  dropZone.addEventListener('click', () => fileInput.click());
  dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', (e) => { e.preventDefault(); dropZone.classList.remove('dragover');
    addFiles(Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.pdf'))); });
  fileInput.addEventListener('change', () => { addFiles(Array.from(fileInput.files)); fileInput.value = ''; });

  function addFiles(files) {
    files.forEach(f => { if (!queue.find(q => q.name === f.name && q.size === f.size)) queue.push(f); });
    renderQueue();
    if (queue.length > 0) convertBtn.disabled = false;
  }

  function removeFile(idx) {
    queue.splice(idx, 1);
    renderQueue();
    if (queue.length === 0) convertBtn.disabled = true;
  }

  function clearQueue() { queue.length = 0; renderQueue(); convertBtn.disabled = true; }

  function renderQueue() {
    if (queue.length === 0) { queueEl.innerHTML = '<div class="queue-empty" id="queueEmpty">还没有添加文件</div>'; return; }
    let html = '';
    queue.forEach((f, i) => {
      const s = f._status || 'pending';
      const label = { pending: '待转换', converting: '转换中…', done: '完成', error: '失败' }[s] || s;
      const fillClass = s === 'done' ? 'done' : s === 'error' ? 'error' : '';
      const pct = f._pct || 0;
      html += `<div class="queue-item" data-idx="${i}">
        <span class="name" title="${f.name}">📄 ${f.name}</span>
        <div class="bar"><div class="fill ${fillClass}" style="width:${pct}%"></div></div>
        <span class="status">${label}</span>
        <button class="remove-btn" onclick="removeFile(${i})" ${s === 'converting' ? 'disabled' : ''}>✕</button>
      </div>`;
    });
    queueEl.innerHTML = html;
  }

  /* ── SSE progress ───────────────────────────────────────── */
  function listenProgress(jobId) {
    const evtSource = new EventSource(`/progress/${jobId}`);
    evtSource.onmessage = (e) => {
      const data = JSON.parse(e.data);
      const idx = data.idx;
      if (idx !== undefined && queue[idx]) {
        queue[idx]._status = data.status;
        queue[idx]._pct = data.pct || 0;
        renderQueue();
      }
      if (data.type === 'done' || data.type === 'error') {
        if (queue.every(q => q._status === 'done' || q._status === 'error')) {
          convertBtn.disabled = false;
        }
      }
    };
    evtSource.addEventListener('done', (e) => {
      evtSource.close();
      const data = JSON.parse(e.data);
      lastOutputDirs = data.dirs || [];
      if (lastOutputDirs.length > 0) openOutputBtn.disabled = false;
      showSummary(data);
      showToast(`转换完成！共 ${data.success}/${data.total} 个文件`, 'done');
    });
    evtSource.addEventListener('error', (e) => {
      evtSource.close();
      convertBtn.disabled = false;
      showToast(e.data || '转换出错', 'error');
    });
  }

  /* ── Convert ─────────────────────────────────────────────── */
  function startConvert() {
    if (queue.length === 0) return;
    convertBtn.disabled = true;
    openOutputBtn.disabled = true;
    summaryEl.classList.remove('show');
    summaryEl.innerHTML = '';
    convertId++;

    const files = queue.map((f, i) => ({ name: f.name, idx: i }));
    files.forEach(f => { queue[f.idx]._status = 'converting'; queue[f.idx]._pct = 0; });
    renderQueue();

    // Step 1: Upload files
    const formData = new FormData();
    queue.forEach((f, i) => {
      formData.append('files', f, `${i}|${f.name}`);
    });

    fetch(`/upload?convertId=${convertId}`, { method: 'POST', body: formData })
      .then(r => r.json())
      .then(() => {
        // Step 2: Start conversion
        return fetch('/start-convert', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ files: files.map(f => f.name), convertId }),
        });
      })
      .then(r => r.json())
      .then(data => {
        currentJobId = data.job_id;
        listenProgress(data.job_id);
      })
      .catch(e => { showToast('上传失败: ' + e.message, 'error'); convertBtn.disabled = false; });
  }

  /* ── Summary ─────────────────────────────────────────────── */
  function showSummary(data) {
    const ok = data.success, total = data.total, err = total - ok;
    const time = data.elapsed ? (data.elapsed / 1000).toFixed(1) : '?';
    summaryEl.innerHTML = `<h3>📊 转换报告</h3>
      <div class="stats">
        <span>✅ 成功 <strong>${ok}</strong></span>
        ${err > 0 ? `<span>❌ 失败 <strong>${err}</strong></span>` : ''}
        <span>📄 总计 <strong>${total}</strong></span>
        <span>⏱ 耗时 <strong>${time}s</strong></span>
      </div>`;
    summaryEl.classList.add('show');
  }

  /* ── Open output ─────────────────────────────────────────── */
  function openOutput() {
    if (lastOutputDirs.length > 0) {
      fetch('/open-dir', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dirs: lastOutputDirs }),
      });
    }
  }

  /* ── Toast ───────────────────────────────────────────────── */
  let toastTimer = null;
  function showToast(msg, type) {
    toastEl.textContent = msg;
    toastEl.className = 'toast ' + (type || '');
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove('show'), 3000);
  }

  /* ── Theme ───────────────────────────────────────────────── */
  function toggleTheme() {
    const html = document.documentElement;
    const cur = html.getAttribute('data-theme');
    const next = cur === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('pdf2md-theme', next);
    document.getElementById('themeBtn').textContent = next === 'dark' ? '🌙' : '☀️';
  }
  const saved = localStorage.getItem('pdf2md-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  document.getElementById('themeBtn').textContent = saved === 'dark' ? '🌙' : '☀️';

  window.toggleTheme = toggleTheme;
  window.removeFile = removeFile;
  window.clearQueue = clearQueue;
  window.startConvert = startConvert;
  window.openOutput = openOutput;
})();
</script>
</body>
</html>
"""


# ── Flask app factory ─────────────────────────────────────────────────
def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

    # Serve HTML
    @app.route("/")
    def index():
        return render_template_string(HTML_PAGE)

    # Start conversion job
    @app.route("/start-convert", methods=["POST"])
    def start_convert():
        data = request.get_json()
        filenames: list[str] = data.get("files", [])
        convert_id = data.get("convertId", 0)

        job_id = f"job_{convert_id}_{int(time.time())}"
        _job_queues[job_id] = queue.Queue()
        _jobs[job_id] = {"filenames": filenames, "done": False}

        # Run in background thread
        def _run():
            out_root = Path(tempfile.mkdtemp(prefix="pdf2md_"))
            results = []
            success = 0
            t0 = time.time()

            for idx, fname in enumerate(filenames):
                try:
                    _emit(job_id, "progress", {
                        "idx": idx, "status": "converting", "pct": 10,
                    })
                    src = Path(tempfile.gettempdir()) / f"pdf2md_upload_{convert_id}_{idx}_{fname}"
                    out_dir = out_root / Path(fname).stem

                    converter = Converter(output_dir=out_dir)
                    report = converter.convert(src)
                    results.append(report)

                    _emit(job_id, "progress", {
                        "idx": idx, "status": "done", "pct": 100,
                    })
                    success += 1
                except Exception as e:
                    _emit(job_id, "progress", {
                        "idx": idx, "status": "error", "pct": 0,
                    })
                    results.append({"error": str(e)})
                finally:
                    # Cleanup uploaded temp file
                    try:
                        src_path = Path(tempfile.gettempdir()) / f"pdf2md_upload_{convert_id}_{idx}_{fname}"
                        if src_path.exists():
                            src_path.unlink()
                    except Exception:
                        pass

            elapsed = int((time.time() - t0) * 1000)
            dirs = [str(r.get("output_dir", "")) for r in results if "output_dir" in r]
            _emit(job_id, "done", {
                "type": "done",
                "success": success,
                "total": len(filenames),
                "elapsed": elapsed,
                "dirs": dirs,
            })
            _jobs[job_id]["done"] = True

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        return jsonify({"job_id": job_id})

    # SSE progress stream
    @app.route("/progress/<job_id>")
    def progress_stream(job_id: str):
        def generate():
            q = _job_queues.get(job_id)
            if q is None:
                yield f"event: error\ndata: Job not found\n\n"
                return
            while True:
                try:
                    event, data = q.get(timeout=30)
                    if event == "done":
                        yield f"event: done\ndata: {json.dumps(data)}\n\n"
                        break
                    elif event == "error":
                        yield f"event: error\ndata: {json.dumps(data)}\n\n"
                        break
                    else:
                        yield f"data: {json.dumps(data)}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

        return Response(generate(), mimetype="text/event-stream")

    # Upload files before starting convert
    @app.route("/upload", methods=["POST"])
    def upload_files():
        convert_id = request.args.get("convertId", "0")
        uploaded = []
        for f in request.files.getlist("files"):
            idx = f.filename.split("|")[0]
            name = "|".join(f.filename.split("|")[1:])
            dst = Path(tempfile.gettempdir()) / f"pdf2md_upload_{convert_id}_{idx}_{name}"
            dst.parent.mkdir(parents=True, exist_ok=True)
            f.save(str(dst))
            uploaded.append(name)
        return jsonify({"uploaded": len(uploaded)})

    # Open output directories in file explorer
    @app.route("/open-dir", methods=["POST"])
    def open_dir():
        data = request.get_json()
        for d in data.get("dirs", []):
            if os.path.isdir(d):
                os.startfile(d)  # Windows only
        return jsonify({"ok": True})

    # Serve result files
    @app.route("/view/<dir_name>")
    def view_result(dir_name: str):
        base = Path(tempfile.gettempdir())
        result_dir = base / dir_name
        if not result_dir.exists():
            return "Result not found", 404
        files = sorted(result_dir.rglob("*"))
        items = []
        for f in files:
            if f.is_file():
                rel = f.relative_to(result_dir).as_posix()
                items.append(
                    f'<li><a href="/file/{dir_name}/{rel}">{f.name}</a></li>'
                )
        return f"<html><body><h3>转换结果</h3><ul>{''.join(items)}</ul></body></html>"

    @app.route("/file/<dir_name>/<path:file_path>")
    def serve_file(dir_name: str, file_path: str):
        import mimetypes

        base = Path(tempfile.gettempdir())
        full = (base / dir_name / file_path).resolve()
        if not full.exists() or not str(full).startswith(str(base)):
            return "Not found", 404
        mime, _ = mimetypes.guess_type(str(full))
        return send_file(str(full), mimetype=mime)

    return app


# ── Standalone server entry (for browser mode) ────────────────────────
def start_web(host: str = "127.0.0.1", port: int = 5000):
    app = create_app()
    print(f"Starting Web UI at http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
