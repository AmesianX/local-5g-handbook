# -*- coding: utf-8 -*-
"""reader.html 을 그대로 펴서 PDF 로 찍는다.  사용: python3 tools/make_pdf.py

읽기 페이지는 한 번에 한 장만 보여 주므로, 인쇄할 때는 모든 장을 펼치고
사이드바·검색 같은 화면 전용 요소를 숨긴다. 쪽 번호는 크롬의 머리말·꼬리말로 넣는다.

차례는 **본문을 먼저 찍고 그 PDF 에서 실제 쪽을 읽어다** 만든다. 쪽수를 계산으로
맞히려 들면(요소 높이 ÷ 한 쪽 높이) break-inside·break-before 때문에 틀린다.
찍힌 것을 읽으면 틀릴 수가 없다.
"""
import datetime, pathlib, re, subprocess, sys
from playwright.sync_api import sync_playwright

BOOK = pathlib.Path(__file__).resolve().parent.parent
SRC  = BOOK / 'reader.html'
OUT  = BOOK / '로컬5G망구축하기.pdf'

PRINT_CSS = """
/* 판면: A4 210×297 에서 좌우 18mm 를 빼면 글 폭 174mm 다. 예전에는 여기에 더해
   article 을 150mm 로 묶어 양옆 24mm 를 더 비웠고(합쳐 60mm), A4 가 절반쯤 비어
   보였다. 글 폭을 늘린 만큼 글자도 10.4 → 10.8pt 로 키운다. 한 줄 약 45 자로,
   줄이 길어 눈이 미끄러지는 범위(50 자 이상)에 들어가지 않는다. */
@page { size: A4; margin: 18mm 18mm 16mm 18mm; }
#cover { padding: 0 20mm; }
article, #toc { max-width:none; margin:0 auto !important; }
#cover { max-width:none; }
html, body { background:#fff !important; }
#bar, #side, nav, aside, header, #res, input, button { display:none !important; }
main, #a, #b, #c { max-width:none !important; width:auto !important;
                   margin:0 !important; padding:0 !important; }
article { display:block !important; }
article[hidden] { display:block !important; }
#cover { text-align:center; break-after: page; }
#imprint { break-after: page; padding-top:84mm; }
#imprint .t { font-size:15pt; font-weight:700; }
#imprint .s { font-size:10pt; color:#666; margin:2.5mm 0 9mm; }
#imprint table { width:auto; font-size:9.4pt; border-collapse:collapse; }
#imprint th { text-align:left; font-weight:600; color:#888;
              padding:1.3mm 9mm 1.3mm 0; white-space:nowrap; vertical-align:top; }
#imprint td { padding:1.3mm 0; }
#imprint p { font-size:9pt; color:#666; line-height:1.75; margin:7mm 0 0;
             max-width:120mm; text-align:left; }
#toc { break-after: page; }
article + article, #toc + article { break-before: page; }
h1 { break-after: avoid; font-size:19pt; margin:0 0 10pt; }
h2 { break-after: avoid; font-size:13pt; margin:16pt 0 6pt; }
h3 { break-after: avoid; font-size:11pt; }
p, li { font-size:10.8pt; line-height:1.68; orphans:3; widows:3; }
p { text-align:justify; text-justify:inter-character; word-break:keep-all; }
/* 표는 쪽을 넘겨 흐르게 한다. 통째로 안 쪼개지게 묶어 두면, 남은 자리보다 큰 표가
   다음 쪽으로 통으로 밀리면서 그 자리에 구멍이 남는다(머리말 1 쪽 아래 3분의 1이
   그렇게 비어 있었다). 대신 **행**은 쪼개지 않고, 머리행은 새 쪽에서 되풀이한다. */
table { break-inside: auto; }
thead { display: table-header-group; }
tr, thead, tfoot { break-inside: avoid; }
pre, figure, blockquote { break-inside: avoid; }
pre code { font-size:7.0pt !important; line-height:1.45; }
pre.w2 code { font-size:6.2pt !important; }
pre.w3 code { font-size:5.4pt !important; }
pre.w4 code { font-size:4.7pt !important; }
table { font-size:8.6pt; width:100%; }
img { max-width:100% !important; max-height:none !important; break-inside:avoid; }
img + em, p > em:only-child { font-size:9pt; color:#555; }
a { color:inherit; text-decoration:none; }

/* --- 차례 ---------------------------------------------------------------
   한 항목을 한 줄로 둔다. 예전에는 절 제목을 ' · ' 로 이어 붙였는데, A4 폭에서
   문단으로 뭉쳐 읽히지 않았고 한글이라 낱말 중간에서 끊겼다("대역이/라는 말").
   keep-all 로 낱말을 지키고, 점선 지시선으로 제목과 쪽번호를 잇는다. */
#toc { word-break: keep-all; line-break: strict; }
#toc .row { display:flex; align-items:baseline; break-inside:avoid; }
#toc .ch  { margin:4.6mm 0 1.4mm; }
#toc .ch:first-of-type { margin-top:0; }
#toc .sec { margin:0 0 1.0mm 13mm; }
#toc .num { flex:0 0 13mm; color:#999; font-size:9pt; }
#toc .ttl { font-size:11pt; font-weight:600; }
#toc .sec .ttl { font-size:8.9pt; font-weight:400; color:#555; }
#toc .dots { flex:1 1 auto; align-self:center;
             border-bottom:1px dotted #c8c8c8; margin:0 2mm; min-width:6mm; }
#toc .pg { flex:0 0 auto; color:#888; font-size:8.8pt;
           font-variant-numeric:tabular-nums; }
#toc .ch .pg { color:#555; font-size:9.6pt; }
#toc .part { break-inside:avoid; break-after:avoid; margin:9mm 0 4mm;
             padding-bottom:1.6mm; border-bottom:1.2px solid #333;
             font-size:10pt; font-weight:700; letter-spacing:.4px; }
#toc .part:first-of-type { margin-top:2mm; }
#toc .part .pn { color:#888; font-weight:600; margin-right:3mm; }
#toc .part .pt { color:#666; font-weight:400; margin-left:2mm; font-size:9pt; }
"""

# 표지·차례에만 거는 규칙. 예전에는 이 @page :first 가 PRINT_CSS 안에 있어서
# **본문 렌더의 첫 쪽에도** 걸렸고, 여백이 0 이 되어 머리말(장 제목)이 쪽 머리말과
# 겹쳐 찍혔다. 표지 쪽에만 필요한 규칙이므로 앞머리를 찍을 때만 붙인다.
FRONT_CSS = """
@page :first { margin: 0; }
"""

HEADER = ('<div style="font-size:7pt;color:#888;width:100%;padding:0 16mm;'
          'font-family:sans-serif;">로컬 5G 망 구축하기 — 해커를 위한 이동통신 실무서</div>')
FOOTER = ('<div style="font-size:7.5pt;color:#888;width:100%;text-align:center;'
          'font-family:sans-serif;"><span class="pageNumber"></span></div>')


COVER_JS = """({meta, book}) => {
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
    <div style="margin-top:40mm;font-size:10pt;color:#555">${esc(book.author)}</div>
    <div style="margin-top:3mm;font-size:9pt;color:#999">${esc(book.pubdate)}</div>`;

  // 판권지. 책에 반드시 있어야 하는 쪽이다 — 누가, 언제, 무엇을 근거로 펴냈는지.
  // 날짜는 지어내지 않는다: 펴낸 날은 이 PDF 를 찍은 날, 본문 기준일은 본문
  // 파일의 마지막 커밋 날짜, 수정은 그 커밋 해시다.
  const imprint = document.createElement('div');
  imprint.id = 'imprint';
  imprint.innerHTML = `
    <div class="t">로컬 5G 망 구축하기</div>
    <div class="s">해커를 위한 이동통신 실무서</div>
    <table>
      <tr><th>지은이</th><td>${esc(book.author)}</td></tr>
      <tr><th>펴낸 날</th><td>${esc(book.pubdate)}</td></tr>
      <tr><th>본문 기준일</th><td>${esc(book.srcdate)} (${esc(book.rev)})</td></tr>
      <tr><th>분량</th><td>${esc(book.volume)}</td></tr>
      <tr><th>라이선스</th><td>MIT License</td></tr>
      <tr><th>저장소</th><td>${esc(book.repo)}</td></tr>
    </table>
    <p>이 책에 나오는 모든 수치·로그·캡처는 한 실험실에서 실제로 얻은 것이다.
       계산으로 메운 값에는 본문에서 그렇다고 적었다.</p>
    <p>이 책이 다루는 실험은 전파를 실제로 방사하는 부분을 포함한다.
       차폐함 밖으로 내보내기 전에 <b>부록 D</b> 를 먼저 읽을 것.</p>`;
  const toc = document.createElement('div');
  toc.id = 'toc';
  const pg = p => p ? `<span class="pg">${p}</span>` : '<span class="pg"></span>';
  let h = '<div style="font-size:17pt;font-weight:700;margin-bottom:9mm">차례</div>';
  let part = null;
  for (const m of meta) {
    if (m.part && m.part[0] !== part) {
      part = m.part[0];
      h += `<div class="part"><span class="pn">${esc(m.part[0])}</span>` +
           `${esc(m.part[1])}<span class="pt">${esc(m.part[2])}</span></div>`;
    }
    h += `<div class="row ch">
            <span class="num">${esc(m.num)}</span>
            <span class="ttl">${esc(m.title)}</span>
            <span class="dots"></span>${pg(m.page)}</div>`;
    for (const s of m.secs)
      h += `<div class="row sec">
              <span class="ttl">${esc(s.t)}</span>
              <span class="dots"></span>${pg(s.page)}</div>`;
  }
  toc.innerHTML = h;
  const host = document.querySelector('article').parentElement;
  host.insertBefore(toc, host.firstChild);
  host.insertBefore(imprint, host.firstChild);
  host.insertBefore(cover, host.firstChild);
}"""


# key 는 쪽을 찾을 때 쓰는 **h1 전문**이고, title 은 차례에 찍는 짧은 제목이다.
# 둘을 섞으면 안 된다: data-title 은 "전파와 주파수" 지만 쪽 맨 위에 찍히는 글자는
# "01. 전파와 주파수: 보이지 않는 파동을 다루는 법" 이다. 짧은 쪽으로 맞추면 쪽
# 맨 앞 대조가 전부 빗나가고, 본문 표 안에 우연히 들어 있는 같은 낱말에 걸린다
# (실측: 01 장이 5 쪽인데 4 쪽의 표에 걸려 차례가 한 쪽씩 틀렸다).
META_JS = """() => [...document.querySelectorAll('article')].map(a => ({
    num: a.dataset.num || '', title: a.dataset.title || '',
    key: (a.querySelector('h1') || {}).textContent || a.dataset.title || '',
    secs: [...a.querySelectorAll('h2')].map(h => ({ t: h.textContent.trim() })) }))"""


# 부(部) 구성. 머리말 "구성" 절에 적힌 그대로다(1~3 / 4~8 / 9~18 / 부록).
# reader.html 은 장만 알고 부를 모르므로 여기서 묶는다. 장이 늘면 이 표에 넣는다.
PARTS = [
    ('Part I',   '기초',        '전파, 샘플, 변조',          ('01', '02', '03')),
    ('Part II',  '망의 구조',   '세대, SIM, 코어, 인증, 세션', ('04', '04a', '05', '06', '07', '08')),
    ('Part III', '구축과 실험', '실험실, 기지국, 모뎀, 시험', ('09', '10', '11', '12', '13',
                                                              '14', '15', '16', '17', '18')),
    ('Part IV',  '부록',        '용어, 명령, 설정, 법규',     ('부록 A', '부록 B', '부록 C', '부록 D')),
]
PART_OF = {num: (p, name, sub) for p, name, sub, nums in PARTS for num in nums}

_WS = re.compile(r'\s+')


def _squeeze(s):
    """공백을 전부 없앤다.

    pdftotext 는 줄 끝에서 개행을 넣는데, 한글은 낱말 중간에서도 줄이 바뀐다.
    공백을 살려 두고 맞추면 '대역이라는' 이 '대역이 라는' 이 되어 못 찾는다.
    """
    return _WS.sub('', s)


def page_texts(pdf):
    """PDF 각 쪽의 글자를 쪽 순서대로 돌려준다 (공백 제거본)."""
    raw = subprocess.run(['pdftotext', '-q', str(pdf), '-'],
                         check=True, capture_output=True).stdout.decode('utf-8', 'replace')
    pages = raw.split('\f')
    if pages and not pages[-1].strip():
        pages.pop()          # pdftotext 는 마지막 쪽 뒤에도 \f 를 붙인다 — 쪽수가 1 늘어난다
    return [_squeeze(p) for p in pages]


def page_count(pdf):
    out = subprocess.run(['pdfinfo', str(pdf)], check=True,
                         capture_output=True).stdout.decode('utf-8', 'replace')
    return int(re.search(r'^Pages:\s+(\d+)', out, re.M).group(1))


HDR_KEY = _squeeze('로컬 5G 망 구축하기 — 해커를 위한 이동통신 실무서')


def _head(page):
    """쪽 머리말을 떼어낸 본문 첫 글자부터를 돌려준다."""
    return page[len(HDR_KEY):] if page.startswith(HDR_KEY) else page


def locate(meta, pages):
    """본문 PDF 에서 각 장·절이 처음 나오는 쪽을 찾아 meta 에 적는다(본문 기준 1쪽부터).

    장은 **쪽 맨 앞에 제목이 오는지**로 찾는다. 그냥 '들어 있는가'로 찾으면
    앞 장이 뒤 장을 인용한 자리에 걸린다(실측: 10 장 제목이 9 장 본문에 있어
    장 경계가 9 장 한복판으로 잡혔고 9 장 절 11 개가 범위 밖으로 밀렸다).
    장은 article + article { break-before: page } 로 반드시 새 쪽에서 시작하므로
    이 조건이 정확하다.

    절은 **그 장이 시작한 쪽부터 다음 장 앞까지만** 뒤진다. '점검 문제',
    '직접 해보기' 처럼 모든 장에 같은 이름으로 있는 절이 앞 장으로 끌려가면
    안 되기 때문이다. 못 찾으면 장의 쪽을 쓴다 — 틀린 쪽보다 낫다.
    """
    starts, miss = [], 0
    for m in meta:
        key = _squeeze(m.get('key') or m['title'])
        frm = starts[-1] + 1 if starts else 0
        hit = next((i for i in range(frm, len(pages))
                    if key and _head(pages[i]).startswith(key)), None)
        if hit is None:      # 제목이 쪽 맨 앞에 안 잡히면 들어 있기만 해도 받는다
            hit = next((i for i in range(frm, len(pages)) if key and key in pages[i]), None)
        if hit is None:
            hit = frm
            miss += 1
        starts.append(hit)
        m['page'] = hit + 1
    for mi, m in enumerate(meta):
        lo = starts[mi]
        hi = starts[mi + 1] + 1 if mi + 1 < len(meta) else len(pages)
        cur = lo
        for s in m['secs']:
            key = _squeeze(s['t'])
            hit = next((i for i in range(cur, hi) if key and key in pages[i]), None)
            if hit is None:
                hit = cur
                miss += 1
            else:
                cur = hit          # 절은 순서대로 나오므로 뒤로만 간다
            s['page'] = hit + 1
    return miss


def git(*args, default=''):
    """저장소에서 사실을 읽어 온다. 없으면 빈 값 — 날짜를 지어내지 않는다."""
    try:
        r = subprocess.run(['git', '-C', str(BOOK)] + list(args),
                           capture_output=True, check=True)
        return r.stdout.decode('utf-8', 'replace').strip() or default
    except Exception:
        return default


def book_info(body_pages):
    today = datetime.date.today()
    src = git('log', '-1', '--format=%ad', '--date=short', '--', '*.md')
    return {
        'author': 'AmesianX',
        'pubdate': f'{today.year}년 {today.month}월 {today.day}일 펴냄',
        'srcdate': src or '(저장소 없음)',
        'rev': git('rev-parse', '--short', 'HEAD', default='(커밋 없음)'),
        'volume': f'본문 {body_pages}쪽',
        'repo': 'github.com/AmesianX/local-5g-handbook',
    }


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

        # ① 본문을 먼저 찍는다 — 차례의 쪽번호를 여기서 읽어야 한다
        pg.goto(SRC.as_uri(), wait_until='load'); pg.wait_for_timeout(1200)
        meta = pg.evaluate(META_JS)
        n = pg.evaluate(UNHIDE)
        pg.add_style_tag(content=PRINT_CSS)
        pg.emulate_media(media='print'); pg.wait_for_timeout(1200)
        pg.pdf(path=str(body), format='A4', print_background=True,
               display_header_footer=True,
               header_template=HEADER, footer_template=FOOTER,
               prefer_css_page_size=True)

        body_pages = page_texts(body)
        miss = locate(meta, body_pages)
        for m in meta:
            m['part'] = PART_OF.get(m['num'])

        # ② 표지·차례 — 머리말도 쪽번호도 없이.
        #    차례에 적는 쪽번호는 **본문 기준**이다. 꼬리말의 쪽번호도 본문에서
        #    1 부터 다시 세고 앞머리(표지·차례)에는 번호를 안 붙이니, 둘이 그대로
        #    맞는다. 앞머리 쪽수를 더하면 차례만 그만큼 틀린다.
        pg.goto(SRC.as_uri(), wait_until='load'); pg.wait_for_timeout(1200)
        pg.evaluate(COVER_JS, {'meta': meta, 'book': book_info(len(body_pages))})
        pg.evaluate("() => document.querySelectorAll('article').forEach(a => a.remove())")
        pg.add_style_tag(content=PRINT_CSS)
        pg.add_style_tag(content=FRONT_CSS)
        pg.emulate_media(media='print'); pg.wait_for_timeout(500)
        pg.pdf(path=str(front), format='A4', print_background=True,
               prefer_css_page_size=True)
        front_pages = page_count(front)
        b.close()

    subprocess.run(['pdfunite', str(front), str(body), str(OUT)], check=True)
    front.unlink(); body.unlink()
    mb = OUT.stat().st_size / 1024 / 1024
    secs = sum(len(m['secs']) for m in meta)
    note = f', 쪽 못 찾음 {miss}' if miss else ''
    print(f'  {OUT.name}  ({mb:.1f} MB, 장 {n} 개, 차례 {len(meta)}+{secs} 줄, '
          f'앞머리 {front_pages} 쪽{note})')


if __name__ == '__main__':
    main()
