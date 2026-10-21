#!/usr/bin/env python3
"""책 마크다운 전체를 읽기용 단일 HTML(reader.html)로 묶는다.

변환은 pandoc 에 맡기고(외부 CDN 의존 없음), 장 전환·검색·읽던 위치는 페이지 안의
작은 스크립트가 맡는다. 사용: python3 tools/build_reader.py
"""
import glob, html, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent.parent
ORDER = ['00', '01', '02', '03', '04-', '04a', '05', '06', '07', '08', '09', '10',
         '11-', '12', '13', '14', '15', '16', '17', '18',
         '부록A', '부록B', '부록C', '부록D']

TITLES = {}


def pick_files():
    out, used = [], set()
    for key in ORDER:
        for f in sorted(HERE.glob('*.md')):
            if f.name.startswith(key) and f.name not in used:
                out.append(f); used.add(f.name); break
    return out


def convert(path):
    """pandoc 으로 마크다운 → HTML 조각."""
    r = subprocess.run(
        ['pandoc', '--from=gfm', '--to=html5', '--no-highlight', str(path)],
        capture_output=True, text=True, check=True)
    return r.stdout


def chapter_meta(path, body_md):
    """장 번호·제목·부제를 뽑는다."""
    first = next((l for l in body_md.split('\n') if l.startswith('# ')), '# ' + path.stem)
    full = first[2:].strip()
    if path.stem.startswith('00'):
        return '머리말', '로컬 5G 망 구축', ''
    m = re.match(r'^(부록\s*[A-D]|[0-9]+[a-z]?)\.\s*(.+)$', full)
    if m:
        num, rest = m.group(1).replace('부록 ', '부록 '), m.group(2)
    else:
        num, rest = path.stem[:4], full
    if ':' in rest:
        title, sub = rest.split(':', 1)
    elif ' — ' in rest:
        title, sub = rest.split(' — ', 1)
    else:
        title, sub = rest, ''
    return num.strip(), title.strip(), sub.strip()


def section_links(frag):
    """장 안의 h2 를 목차용으로 뽑는다."""
    return re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', frag, re.S)


def strip_tags(s):
    return re.sub(r'<[^>]+>', '', s).strip()


def main():
    files = pick_files()
    chapters, nav = [], []
    for i, f in enumerate(files):
        md = f.read_text(encoding='utf-8')
        frag = convert(f)
        num, title, sub = chapter_meta(f, md)
        cid = 'c%02d' % i
        secs = [(sid, strip_tags(t)) for sid, t in section_links(frag)]
        nav.append((cid, num, title, sub, secs))
        chapters.append(
            f'<article class="ch" id="{cid}" data-num="{html.escape(num)}" '
            f'data-title="{html.escape(title)}" hidden>\n{frag}</article>')
        print(f'  {f.name:42s} {len(frag)//1024:4d} KB  h2 {len(secs):2d}')

    toc = []
    for cid, num, title, sub, secs in nav:
        subs = ''.join(
            f'<a class="sec" href="#{cid}" data-ch="{cid}" data-sec="{sid}">{html.escape(t)}</a>'
            for sid, t in secs)
        toc.append(
            f'<div class="navitem"><a class="chap" href="#{cid}" data-ch="{cid}">'
            f'<span class="num">{html.escape(num)}</span>'
            f'<span class="t">{html.escape(title)}</span></a>'
            f'<div class="secs">{subs}</div></div>')

    tpl = (HERE / 'tools' / 'reader_template.html').read_text(encoding='utf-8')
    out = tpl.replace('<!--TOC-->', '\n'.join(toc)).replace('<!--CHAPTERS-->', '\n'.join(chapters))
    dst = HERE / 'reader.html'
    dst.write_text(out, encoding='utf-8')
    print(f'\n{dst}  ({dst.stat().st_size/1024:.0f} KB, 장 {len(files)}개)')


if __name__ == '__main__':
    sys.exit(main())
