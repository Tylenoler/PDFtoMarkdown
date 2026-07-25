"""Flask Web UI for pdf2md."""

import os
import tempfile
from pathlib import Path

from flask import Flask, render_template_string, request, jsonify

from pdf2md.converter import Converter
from pdf2md.utils.helpers import collect_pdf_files

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>PDF → Markdown</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, system-ui, sans-serif; background: #f5f5f5; padding: 2rem; color: #333; }
  .container { max-width: 800px; margin: 0 auto; }
  h1 { font-size: 1.5rem; margin-bottom: 1rem; }
  .box { background: #fff; border-radius: 8px; padding: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,.1); margin-bottom: 1rem; }
  input[type=file] { display: block; margin-bottom: 1rem; }
  input[type=text] { width: 100%; padding: .5rem; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 1rem; }
  button { background: #0066cc; color: #fff; border: none; padding: .6rem 1.2rem; border-radius: 4px; cursor: pointer; }
  button:hover { background: #0052a3; }
  button:disabled { opacity: .5; cursor: not-allowed; }
  .info { font-size: .875rem; color: #666; margin-top: .5rem; }
  #status { margin-top: 1rem; padding: .5rem; border-radius: 4px; }
  #status.running { background: #fff3cd; }
  #status.done { background: #d4edda; }
  #status.error { background: #f8d7da; }
  .result a { color: #0066cc; }
  hr { margin: 1.5rem 0; border: none; border-top: 1px solid #eee; }
</style>
</head>
<body>
<div class="container">
  <h1>PDF → Markdown 转换</h1>
  <div class="box">
    <h3>上传单个 PDF</h3>
    <input type="file" id="fileInput" accept=".pdf">
    <button id="uploadBtn" onclick="uploadPdf()">转换</button>
    <div id="status"></div>
  </div>
  <div class="box">
    <h3>批量转换文件夹</h3>
    <p class="info">将 PDF 文件放入一个文件夹，输入文件夹路径:</p>
    <input type="text" id="folderInput" placeholder="例如: C:\Users\...\pdfs">
    <button onclick="convertFolder()">批量转换</button>
  </div>
</div>
<script>
async function uploadPdf() {
  const file = document.getElementById('fileInput').files[0];
  if (!file) return;
  const btn = document.getElementById('uploadBtn');
  const status = document.getElementById('status');
  btn.disabled = true;
  status.className = 'running';
  status.textContent = '转换中...';
  try {
    const form = new FormData();
    form.append('file', file);
    const r = await fetch('/convert', { method: 'POST', body: form });
    const data = await r.json();
    if (r.ok) {
      status.className = 'done';
      status.innerHTML = `转换完成！<a href="${data.result_url}" target="_blank">查看结果</a>`;
    } else {
      throw new Error(data.error || '转换失败');
    }
  } catch (e) {
    status.className = 'error';
    status.textContent = '错误: ' + e.message;
  } finally {
    btn.disabled = false;
  }
}
async function convertFolder() {
  const path = document.getElementById('folderInput').value.trim();
  if (!path) return;
  const status = document.getElementById('status');
  status.className = 'running';
  status.textContent = '转换中...';
  try {
    const r = await fetch('/convert-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
    const data = await r.json();
    if (r.ok) {
      status.className = 'done';
      status.innerHTML = `转换完成！共 ${data.count} 个文件。<a href="${data.result_url}" target="_blank">查看结果</a>`;
    } else {
      throw new Error(data.error || '转换失败');
    }
  } catch (e) {
    status.className = 'error';
    status.textContent = '错误: ' + e.message;
  }
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/convert", methods=["POST"])
def convert_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files allowed"}), 400

    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    file.save(tmp.name)
    tmp.close()

    out_dir = Path(tempfile.mkdtemp(prefix="pdf2md_"))
    try:
        converter = Converter(output_dir=out_dir)
        converter.convert(tmp.name)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp.name)

    return jsonify({
        "result_url": f"/view/{out_dir.name}",
        "output_dir": str(out_dir),
    })


@app.route("/convert-folder", methods=["POST"])
def convert_folder():
    data = request.get_json()
    folder = data.get("path", "")
    pdfs = collect_pdf_files(folder)
    if not pdfs:
        return jsonify({"error": "No PDF files found"}), 400

    out_root = Path(tempfile.mkdtemp(prefix="pdf2md_batch_"))
    count = 0
    for pdf in pdfs:
        out_dir = out_root / pdf.stem
        converter = Converter(output_dir=out_dir)
        converter.convert(pdf)
        count += 1

    return jsonify({
        "count": count,
        "result_url": f"/view/{out_root.name}",
    })


@app.route("/view/<dir_name>")
def view_result(dir_name: str):
    """Simple file listing for a result directory."""
    import glob
    base = Path(tempfile.gettempdir())
    result_dir = base / dir_name
    if not result_dir.exists():
        return "Result not found", 404
    files = sorted(result_dir.rglob("*"))
    items = []
    for f in files:
        if f.is_file():
            items.append(f'<li><a href="/file/{dir_name}/{f.relative_to(result_dir).as_posix()}">{f.name}</a></li>')
    return f"<html><body><h3>转换结果</h3><ul>{''.join(items)}</ul></body></html>"


@app.route("/file/<dir_name>/<path:file_path>")
def serve_file(dir_name: str, file_path: str):
    import mimetypes
    base = Path(tempfile.gettempdir())
    full = (base / dir_name / file_path).resolve()
    if not full.exists() or not str(full).startswith(str(base)):
        return "Not found", 404
    mime, _ = mimetypes.guess_type(str(full))
    from flask import send_file
    return send_file(str(full), mimetype=mime)


def start_web(host: str = "127.0.0.1", port: int = 5000):
    print(f"Starting Web UI at http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
