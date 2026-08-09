"""Builds a manual PDF from a Markdown source in docs/.
Converts markdown -> self-contained HTML (images inlined as data URIs) ->
PDF via headless Edge's print-to-pdf. Run manually after editing a manual:
    python tools/build_manual_pdf.py            # builds MANUAL.md + MANUAL_PT.md
    python tools/build_manual_pdf.py MANUAL.md   # builds just one
"""
import base64
import mimetypes
import os
import re
import subprocess
import sys

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

DEFAULT_SOURCES = ["MANUAL.md", "MANUAL_PT.md"]

CSS = """
body { font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a1a; max-width: 780px;
       margin: 0 auto; padding: 20px 10px; line-height: 1.5; }
h1 { font-size: 26px; border-bottom: 3px solid #2ea043; padding-bottom: 8px; }
h2 { font-size: 20px; margin-top: 36px; border-bottom: 1px solid #ccc; padding-bottom: 4px;
     page-break-before: always; }
h1 + p, h2:first-of-type { page-break-before: avoid; }
h3 { font-size: 16px; margin-top: 24px; color: #1a1a1a; }
img { max-width: 380px; display: block; margin: 12px 0; border: 1px solid #ddd;
      border-radius: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.15); }
table { border-collapse: collapse; margin: 12px 0; width: 100%; }
th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; font-size: 14px; }
th { background: #2ea043; color: white; }
code { background: #f0f0f0; padding: 1px 5px; border-radius: 3px; font-size: 13px; }
pre code { display: block; padding: 10px; }
hr { border: none; border-top: 1px solid #ccc; margin: 24px 0; }
ol, ul { padding-left: 24px; }
"""


def inline_image(match):
    alt, src = match.group(1), match.group(2)
    img_path = os.path.join(DOCS, src)
    mime, _ = mimetypes.guess_type(img_path)
    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f'<img alt="{alt}" src="data:{mime};base64,{b64}">'


def build_one(md_filename):
    md_path = os.path.join(DOCS, md_filename)
    html_path = os.path.join(DOCS, "_build.html")
    pdf_path = os.path.join(DOCS, md_filename.replace(".md", ".pdf"))

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    html_body = re.sub(r'<img alt="([^"]*)" src="([^"]+)"\s*/?>', inline_image, html_body)

    full_html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html_body}</body></html>"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    subprocess.run([
        EDGE_PATH, "--headless=new", "--disable-gpu",
        f"--print-to-pdf={pdf_path}",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        "file:///" + html_path.replace("\\", "/"),
    ], check=True)

    os.remove(html_path)
    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    sources = sys.argv[1:] or DEFAULT_SOURCES
    for name in sources:
        build_one(name)
