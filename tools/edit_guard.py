# -*- coding: utf-8 -*-
"""다듬어 돌아온 원고가 사실을 건드리지 않았는지 원본과 대조한다.

사용:
    python3 tools/edit_guard.py 원본.md 다듬은.md
    python3 tools/edit_guard.py 원본.md 다듬은__1of3.md 다듬은__2of3.md 다듬은__3of3.md
    python3 tools/edit_guard.py 원본.md 다듬은.md --apply     # 통과하면 원본 자리에 쓴다

문장은 얼마든지 바뀌어도 된다. 바뀌면 안 되는 것은 코드, 숫자, 참조, 표시, 제목 번호다.
이 책의 사실은 실험으로 검증한 것이고 독자는 저장소로 같은 망을 복원하므로, 측정값
하나·명령 한 줄·절 번호 하나가 조용히 바뀌면 책이 거짓말을 하게 된다. 사람이 눈으로
대조하면 놓치므로 기계로 본다.

판정은 둘이다. ⛔ 는 반드시 되돌려야 하는 것이고(종료코드 1), ⚠ 는 사람이 한 번 볼 것이다.
"""
import collections, pathlib, re, sys

BOOK = pathlib.Path(__file__).resolve().parent.parent
UNIT = (r'(?:dBm|dBi|dBFS|dB|GHz|MHz|kHz|Hz|ms|μs|MS/s|Mbps|Gbps|kbps|MB/s|MB|GB|KB|'
        r'mW|W|V|mA|A|mm|cm|km|m|s|pps|fps|초|분|시간|배|%|비트|바이트|bit|B)')


def join_parts(paths):
    def order(p):
        m = re.search(r'__(\d+)of\d+', p.name)
        return int(m.group(1)) if m else 0
    paths = sorted(paths, key=order)
    return '\n\n'.join(p.read_text().strip('\n') for p in paths) + '\n'


def strip_memo(t):
    """편집자 메모와 저자 확인 표시는 따로 모으고 대조에서는 뺀다."""
    memos = re.findall(r'<!--\s*편집자 메모:(.*?)-->', t, re.S)
    t = re.sub(r'\n*<!--\s*편집자 메모:.*?-->\n*', '\n', t, flags=re.S)
    return t, [m.strip() for m in memos]


def fences(t):
    return re.findall(r'^```.*?^```', t, re.S | re.M)


def prose(t):
    return re.sub(r'^```.*?^```', '\n', t, flags=re.S | re.M)


def inline_codes(t):
    return collections.Counter(re.findall(r'`[^`\n]+`', prose(t)))


def headings(t):
    out = []
    for l in prose(t).split('\n'):
        m = re.match(r'^(#+)\s+((?:\d+[a-z]?\.)?\d*[a-z]?\.?\d*[a-z]?)', l)
        if l.startswith('#') and m:
            num = re.match(r'^(#+)\s+(\d+[a-z]?(?:\.\d+[a-z]?)?)?', l)
            out.append((len(m.group(1)), num.group(2) or ''))
    return out


def images(t):
    return collections.Counter(re.findall(r'!\[[^\]]*\]\(([^)]+)\)', t))


def markers(t):
    p = prose(t)
    return collections.Counter(re.findall(r'\[(?:측정|추정)\]|\[검증 필요[^\]]*\]', p))


def refs(t):
    p = re.sub(r'`[^`\n]+`', ' ', prose(t))
    p = re.sub(r'\]\([^)]*\)', ']', p)
    found = set()
    for m in re.finditer(r'사례\s?(\d+)', p): found.add(f'사례 {m.group(1)}')
    for m in re.finditer(r'그림\s?(\d+[a-z]?-\d+)', p): found.add(f'그림 {m.group(1)}')
    for m in re.finditer(r'부록\s?([A-D](?:\.\d+)?)', p): found.add(f'부록 {m.group(1)}')
    for m in re.finditer(r'(?<![\w.~∼\-/])(\d{1,2}[a-z]?)\s?장(?![가-힣]*짜리)', p):
        found.add(f'{m.group(1).lstrip("0") or "0"} 장')
    for m in re.finditer(rf'(?<![\w.§/\-−])(\d{{1,2}}[a-z]?)\.(\d{{1,2}}[a-z]?)(?![.\d])(?!\s?{UNIT}(?![가-힣A-Za-z]))', p):
        found.add(f'{m.group(1)}.{m.group(2)}')
    return found


def numbers(t):
    p = re.sub(r'`[^`\n]+`', ' ', prose(t))
    p = re.sub(r'\]\([^)]*\)', ']', p)
    p = re.sub(r'사례\s?\d+|그림\s?\d+[a-z]?-\d+', ' ', p)
    nums = collections.Counter()
    for m in re.finditer(r'(?<![\w.])[−\-+]?\d[\d,]*(?:\.\d+)?', p):
        nums[m.group(0).replace(',', '').replace('−', '-')] += 1
    return nums


def measured(t):
    """단위가 붙거나 소수점이 있는 숫자 = 측정·계산값으로 보고 엄격히 본다."""
    p = re.sub(r'`[^`\n]+`', ' ', prose(t))
    out = set()
    for m in re.finditer(rf'[−\-+]?\d[\d,]*(?:\.\d+)?\s?{UNIT}(?![A-Za-z가-힣])', p):
        out.add(re.sub(r'\s', '', m.group(0)).replace('−', '-').replace(',', ''))
    for m in re.finditer(r'(?<![\w.])\d+\.\d+(?![.\d])', p):
        out.add(m.group(0))
    return out


def footer(t):
    m = re.search(r'\*다음 장:[^\n]*\*', t)
    return m.group(0) if m else ''


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    apply = '--apply' in sys.argv
    if len(args) < 2:
        sys.exit(__doc__)
    orig_p = pathlib.Path(args[0])
    edits = [pathlib.Path(a) for a in args[1:]]
    o = orig_p.read_text()
    e_raw = join_parts(edits) if len(edits) > 1 else edits[0].read_text()
    e, memos = strip_memo(e_raw)
    hard, soft, info = [], [], []

    fo, fe = fences(o), fences(e)
    if fo != fe:
        miss = [x for x in fo if x not in fe]
        hard.append(f'코드 블록이 바뀌었다 (원본 {len(fo)}개, 다듬은 것 {len(fe)}개, 달라진 것 {len(miss)}개)')
        for x in miss[:3]: hard.append('   원본: ' + x.split('\n')[0][:60] + ' … ' + x.split('\n')[1][:60] if '\n' in x else x[:80])
    io, ie = inline_codes(o), inline_codes(e)
    if io != ie:
        gone = list((io - ie).elements()); new = list((ie - io).elements())
        hard.append(f'인라인 코드가 바뀌었다: 사라짐 {gone[:8]} / 새로 생김 {new[:8]}')
    ho, he = headings(o), headings(e)
    if [h for h in ho] != [h for h in he]:
        hard.append(f'제목 번호·순서가 바뀌었다: 원본 {[n for _,n in ho][:12]}… / 다듬은 것 {[n for _,n in he][:12]}…')
    if images(o) != images(e):
        hard.append(f'그림 줄이 바뀌었다: {dict(images(o) - images(e))} → {dict(images(e) - images(o))}')
    mo, me = markers(o), markers(e)
    if mo != me:
        hard.append(f'[측정]/[추정]/[검증 필요] 표시가 바뀌었다: 사라짐 {dict(mo - me)} / 새로 생김 {dict(me - mo)}')
    ro, re_ = refs(o), refs(e)
    if ro - re_:
        hard.append(f'참조가 사라졌다: {sorted(ro - re_)}')
    if re_ - ro:
        hard.append(f'원본에 없던 참조가 생겼다: {sorted(re_ - ro)}')
    meo, mee = measured(o), measured(e)
    if mee - meo:
        hard.append(f'원본에 없던 측정·계산값이 생겼다: {sorted(mee - meo)}')
    if meo - mee:
        soft.append(f'원본의 측정·계산값이 안 보인다(풀어 쓴 것인지 확인): {sorted(meo - mee)}')
    no, ne = numbers(o), numbers(e)
    newn = [n for n in (ne - no) if n not in meo]
    if newn:
        soft.append(f'원본에 없던 숫자: {sorted(set(newn))[:15]}')
    if footer(o) != footer(e):
        hard.append(f'"다음 장" 줄이 바뀌었다: {footer(o)!r} → {footer(e)!r}')
    for k in ('🔎', '⚠️'):
        if o.count(k) != e.count(k):
            soft.append(f'{k} 개수가 다르다: {o.count(k)} → {e.count(k)}')
    ratio = len(e) / max(1, len(o))
    if not 0.8 <= ratio <= 1.3:
        soft.append(f'분량이 {ratio:.0%} 다 (권장 80~130 %)')
    checks = re.findall(r'【저자 확인】[^\n]*', e)
    for c in checks: info.append('저자 확인: ' + c[:120])
    for m in memos: info.append('편집자 메모: ' + m[:200])

    print(f'원본 {orig_p.name} {len(o):,}자 → 다듬은 것 {len(e):,}자 ({ratio:.0%})')
    for x in hard: print('⛔', x)
    for x in soft: print('⚠', x)
    for x in info: print('📝', x)
    if not hard:
        print('✅ 사실을 건드린 흔적이 없다' + (' — 볼 것 있음' if soft or info else ''))
        if apply:
            if checks:
                print('   【저자 확인】 이 남아 있어 적용하지 않는다. 확인하고 지운 뒤 다시 돌려라.')
            else:
                orig_p.write_text(e.rstrip('\n') + '\n')
                print(f'   {orig_p} 에 적용했다')
    sys.exit(1 if hard else 0)


if __name__ == '__main__':
    main()
