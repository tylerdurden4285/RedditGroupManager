import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ensure_node_modules():
    if not (ROOT / 'node_modules').exists():
        subprocess.run(['npm', 'install', 'jsdom', 'dompurify', 'marked'], cwd=ROOT, check=True)


def sanitize_markdown(md: str) -> str:
    ensure_node_modules()
    script = """
const { JSDOM } = require('jsdom');
const window = new JSDOM('').window;
const DOMPurify = require('dompurify')(window);
const { marked } = require('marked');
let data = '';
process.stdin.on('data', chunk => data += chunk);
process.stdin.on('end', () => {
  const html = marked.parse(data);
  const clean = DOMPurify.sanitize(html);
  console.log(clean);
});
"""
    env = os.environ.copy()
    env['NODE_PATH'] = str(ROOT / 'node_modules')
    result = subprocess.run(['node', '-e', script], input=md, text=True, capture_output=True, check=True, env=env)
    return result.stdout.strip()


def test_markdown_sanitization():
    md = "# Title\n<script>alert('x')</script><img src='x' onerror=\"alert('x')\">"
    html = sanitize_markdown(md)
    assert '<script>' not in html
    assert 'onerror' not in html
