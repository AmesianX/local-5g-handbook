# -*- coding: utf-8 -*-
"""reader.html 을 그대로 펴서 PDF 로 찍는다.  사용: python3 tools/make_pdf.py

읽기 페이지는 한 번에 한 장만 보여 주므로, 인쇄할 때는 모든 장을 펼치고
사이드바·검색 같은 화면 전용 요소를 숨긴다. 쪽 번호는 크롬의 머리말·꼬리말로 넣는다.
"""
import pathlib, subprocess, sys
from playwright.sync_api import sync_playwright

BOOK = pathlib.Path(__file__).resolve().parent.parent
SRC  = BOOK / 'reader.html'
OUT  = BOOK / '로컬5G망구축하기.pdf'

PRINT_CSS = """
@page { size: A4; margin: 20mm 16mm 18mm 16mm; }
/* 표지에는 머리말도 쪽번호도 찍지 않는다 (여백 상자를 없애면 사라진다) */
@page :first { margin: 0; }
#cover { padding: 0 20mm; }
/* 한 줄이 너무 길면 눈이 줄을 놓친다. 본문 폭을 묶는다. */
article, #cover, #toc { max-width:150mm; margin:0 auto !important; }
html, body { background:#fff !important; }
#bar, #side, nav, aside, header, #res, input, button { display:none !important; }
main, #a, #b, #c { max-width:none !important; width:auto !important;
                   margin:0 !important; padding:0 !important; }
article { display:block !important; }
article[hidden] { display:block !important; }
#cover { text-align:center; break-after: page; }\n#toc { break-after: page; }\narticle + article, #toc + article { break-before: page; }
h1 { break-after: avoid; font-size:19pt; margin:0 0 10pt; }
h2 { break-after: avoid; font-size:13pt; margin:16pt 0 6pt; }
h3 { break-after: avoid; font-size:11pt; }
p, li { font-size:10.4pt; line-height:1.72; orphans:3; widows:3; }
pre, table, figure, blockquote { break-inside: avoid; }
pre code { font-size:7.0pt !important; line-height:1.45; }
pre.w2 code { font-size:6.2pt !important; }
pre.w3 code { font-size:5.4pt !important; }
pre.w4 code { font-size:4.7pt !important; }
table { font-size:8.6pt; width:100%; }
img { max-width:100% !important; max-height:none !important; break-inside:avoid; }
img + em, p > em:only-child { font-size:9pt; color:#555; }
a { color:inherit; text-decoration:none; }
"""

HEADER = ('<div style="font-size:7pt;color:#888;width:100%;padding:0 16mm;'
          'font-family:sans-serif;">로컬 5G 망 구축하기 — 해커를 위한 이동통신 실무서</div>')
FOOTER = ('<div style="font-size:7.5pt;color:#888;width:100%;text-align:center;'
          'font-family:sans-serif;"><span class="pageNumber"></span></div>')


COVER_JS = """(meta) => {
  const esc = t => t.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  const cover = document.createElement('div');
  cover.id = 'cover';
  cover.innerHTML = `
    <div style="height:72mm"></div>
    <div style="font-size:30pt;font-weight:700;letter-spacing:-.5px">로컬 5G 망 구축하기</div>
    <div style="font-size:13pt;color:#555;margin-top:7mm">해커를 위한 이동통신 실무서</div>
    <div style="margin-top:34mm;font-size:9.5pt;color:#777;line-height:1.9">
      기지국 하나, 코어 하나, SIM 한 장으로 전화가 오가기까지<br>
      이 책의 모든 숫자와 로그는 한 실험실에서 실제로 얻은 것이다
    </div>
    <div style="margin-top:46mm;font-size:9pt;color:#999">
      AmesianX · 2026 · MIT License
    </div>`;
  const toc = document.createElement('div');
  toc.id = 'toc';
  let h = '<div style="font-size:17pt;font-weight:700;margin-bottom:9mm">차례</div>';
  for (const m of meta) {
    h += `<div style="margin:0 0 3.6mm 0">
            <span style="display:inline-block;width:13mm;color:#999;font-size:9pt">${esc(m.num)}</span>
            <span style="font-size:11pt;font-weight:600">${esc(m.title)}</span></div>`;
    if (m.secs.length)
      h += `<div style="margin:0 0 5mm 13mm;color:#666;font-size:8.6pt;line-height:1.75">
              ${m.secs.map(esc).join(' · ')}</div>`;
  }
  toc.innerHTML = h;
  const host = document.querySelector('article').parentElement;
  host.insertBefore(toc, host.firstChild);
  host.insertBefore(cover, host.firstChild);
}"""


META_JS = """() => [...document.querySelectorAll('article')].map(a => ({
    num: a.dataset.num || '', title: a.dataset.title || '',
    secs: [...a.querySelectorAll('h2')].map(h => h.textContent.trim()) }))"""


def main():
    if not SRC.exists():
        sys.exit('reader.html 이 없다. 먼저 python3 tools/build_reader.py')
    UNHIDE = ("() => { const a=[...document.querySelectorAll('article')]; "
              "a.forEach(x => { x.hidden=false; x.removeAttribute('hidden'); "
              "x.style.display='block'; }); return a.length; }")
    front = BOOK / '.pdf-front.pdf'
    body = BOOK / '.pdf-body.pdf'
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()

        # ① 표지·차례 — 머리말도 쪽번호도 없이
        pg.goto(SRC.as_uri(), wait_until='load'); pg.wait_for_timeout(1200)
        meta = pg.evaluate(META_JS)
        pg.evaluate(COVER_JS, meta)
        pg.evaluate("() => document.querySelectorAll('article').forEach(a => a.remove())")
        pg.add_style_tag(content=PRINT_CSS)
        pg.emulate_media(media='print'); pg.wait_for_timeout(500)
        pg.pdf(path=str(front), format='A4', print_background=True,
               prefer_css_page_size=True)

        # ② 본문 — 머리말과 쪽번호를 넣는다
        pg.goto(SRC.as_uri(), wait_until='load'); pg.wait_for_timeout(1200)
        n = pg.evaluate(UNHIDE)
        pg.add_style_tag(content=PRINT_CSS)
        pg.emulate_media(media='print'); pg.wait_for_timeout(1200)
        pg.pdf(path=str(body), format='A4', print_background=True,
               display_header_footer=True,
               header_template=HEADER, footer_template=FOOTER,
               prefer_css_page_size=True)
        b.close()

    subprocess.run(['pdfunite', str(front), str(body), str(OUT)], check=True)
    front.unlink(); body.unlink()
    mb = OUT.stat().st_size / 1024 / 1024
    print(f'  {OUT.name}  ({mb:.1f} MB, 장 {n} 개)')


if __name__ == '__main__':
    main()
