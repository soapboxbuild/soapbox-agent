#!/usr/bin/env python3
"""Export a Soapbox template report (client-JS-populated, Paged.js-banned on screen) to a
consulting-grade, US-Letter, print-paginated PDF.

Pipeline: inject data into the template's <script id="report-data"> → serve locally → run in
Chromium so populateReport() fills the DOM → wait for the __reportReady sentinel (fallback: a
populated node) → apply print transforms (open <details>, all-series-on, running header/footer,
relocate multi-state <select> controls to an appendix) → run Paged.js with print.css (Letter
@page, full-bleed hero page 1, discreet running header page 2+, footer + page numbers,
keep-together) → page.pdf(preferCSSPageSize).

Usage:
  export_pdf.py --template portfolio-analysis --data data.json --out report.pdf \
    [--templates-dir <dir>] [--assets-dir <dir>] [--title "Client — Portfolio Analysis"]
"""
import argparse, json, os, re, shutil, sys, tempfile, threading, http.server, socketserver, functools

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
DEFAULT_TEMPLATES = os.path.normpath(os.path.join(SKILL, "..", "..", "templates"))
DEFAULT_ASSETS = os.path.join(SKILL, "assets")

# Runs in the page AFTER populateReport(), BEFORE Paged.js paginates.
TRANSFORM_JS = r"""(() => {
  const doc = document;
  // 1. Force every <details> open so collapsed content (cashflow, sources) prints in place.
  doc.querySelectorAll('details').forEach(d => d.open = true);
  // 2. Reset any interactive chart legend toggles to all-series-visible.
  doc.querySelectorAll('.leg-off').forEach(e => e.classList.remove('leg-off'));
  doc.querySelectorAll('[data-si].off').forEach(e => e.classList.remove('off'));
  // 3. Running header (page 2+) + footer, derived from the report's own header/meta.
  const title = (doc.querySelector('.doc-header-title,.port-name,.doc-title')||{}).textContent
                || (doc.title||'').replace(/\s*\|\s*Soapbox.*$/,'') || 'Soapbox Report';
  const sub   = (doc.querySelector('.doc-header-sub,.port-sub')||{}).textContent || '';
  const meta  = (doc.querySelector('.meta-strip,.meta-confidential')||{}).textContent || 'Soapbox Sustainability Intelligence · CONFIDENTIAL';
  // Prepend running header/footer elements so their `position: running()` value is live
  // from the FIRST page onward (Paged.js sources the value at the element's flow position).
  const mk = (cls, txt) => { const e = doc.createElement('div'); e.className = cls; e.textContent = txt; doc.body.insertBefore(e, doc.body.firstChild); };
  mk('print-runhdr-l', title.trim());
  mk('print-runhdr-r', (sub.split('·')[0]||'').trim());
  mk('print-runftr', meta.replace(/\s+/g,' ').trim());
  // 4. Multi-state <select> controls → appendix (render every option's state).
  const selects = [...doc.querySelectorAll('select')].filter(s => s.options && s.options.length > 1);
  if (selects.length) {
    const ap = doc.createElement('div'); ap.className = 'print-appendix';
    ap.innerHTML = '<h2>Appendix — Interactive Views</h2>';
    selects.forEach(s => {
      [...s.options].forEach(o => {
        const st = doc.createElement('div'); st.className = 'appendix-state';
        st.innerHTML = '<p style="font-weight:600;color:#64748B;font-size:11px">' + (o.textContent||'') + '</p>';
        ap.appendChild(st);
      });
    });
    (doc.querySelector('.report')||doc.body).appendChild(ap);
  }
  window.__printTransformed = true;
})();"""


def inject_data(html: str, data: dict, title: str | None) -> str:
    payload = dict(data)
    if title:
        payload.setdefault("_title", title)
    blob = json.dumps(payload).replace("</", "<\\/")
    pat = re.compile(r'(<script[^>]*id="report-data"[^>]*>)(.*?)(</script>)', re.DOTALL)
    if pat.search(html):
        return pat.sub(lambda m: m.group(1) + blob + m.group(3), html, count=1)
    # Placeholder-substitution templates (crrem, sustainability-passport): fall back to token replace.
    for k, v in payload.items():
        html = html.replace(f"[[{k}]]", str(v))
    return html


def serve(dir_: str):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=dir_)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--data", required=True, help="path to JSON data object")
    ap.add_argument("--out", required=True)
    ap.add_argument("--templates-dir", default=DEFAULT_TEMPLATES)
    ap.add_argument("--assets-dir", default=DEFAULT_ASSETS)
    ap.add_argument("--title", default=None)
    ap.add_argument("--timeout", type=int, default=45000)
    a = ap.parse_args()

    tpl_path = os.path.join(a.templates_dir, a.template, "layout-agent.html")
    html = open(tpl_path, encoding="utf-8").read()
    data = json.load(open(a.data, encoding="utf-8"))
    html = inject_data(html, data, a.title)

    # Wire Paged.js (manual) + print.css into the page head/body.
    head_add = '<link rel="stylesheet" href="print.css">'
    body_add = ('<script>window.PagedConfig={auto:false};</script>'
                '<script src="paged.polyfill.js"></script>')
    html = html.replace("</head>", head_add + "</head>", 1)
    html = html.replace("</body>", body_add + "</body>", 1)

    work = tempfile.mkdtemp(prefix="sbpdf_")
    open(os.path.join(work, "index.html"), "w", encoding="utf-8").write(html)
    shutil.copy(os.path.join(a.assets_dir, "print.css"), work)
    shutil.copy(os.path.join(a.assets_dir, "paged.polyfill.js"), work)

    httpd, port = serve(work)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="load", timeout=a.timeout)
        # Wait for populateReport(): prefer the durable sentinel, fall back to a populated node.
        try:
            page.wait_for_function("window.__reportReady === true", timeout=8000)
        except Exception:
            page.wait_for_function(
                "document.querySelectorAll('table tbody tr, .kpi, .slide').length > 2",
                timeout=8000)
        page.evaluate(TRANSFORM_JS)
        # Paginate with Paged.js (consumes print.css @page rules), then print.
        page.evaluate("(async () => { await window.PagedPolyfill.preview(); })()")
        page.wait_for_selector(".pagedjs_page", timeout=a.timeout)
        page.wait_for_timeout(1200)  # settle charts/fonts
        pages = page.eval_on_selector_all(".pagedjs_page", "els => els.length")
        page.pdf(path=a.out, prefer_css_page_size=True, print_background=True)
        browser.close()
    httpd.shutdown()
    print(json.dumps({"ok": True, "out": a.out, "pages": pages,
                      "bytes": os.path.getsize(a.out)}))


if __name__ == "__main__":
    main()
