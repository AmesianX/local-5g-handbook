#!/usr/bin/env python3
"""원고 일관성 검사.

장을 넣거나 빼거나 옮길 때마다 조용히 어긋나는 것들을 한 번에 잡는다.
실제로 3장이 5장으로 밀렸는데 그림 파일명이 fig-3-* 로 남아 있었다 —
사람 눈으로는 안 보이고, PDF 를 뽑고 나서야 이상하다고 느낀다.

    python3 check.py        # 0 이면 정상, 1 이면 문제 있음
"""
import pathlib, re, sys

root = pathlib.Path(__file__).parent
mds = sorted(root.glob("*.md"))
bad = []

refs = set()
for p in mds:
    t = p.read_text(encoding="utf-8")

    # 1) 이미지·문서 링크가 실제로 있는가
    for m in re.finditer(r'!\[[^\]]*\]\(([^)\s]+)\)|<img src="([^"]+)"', t):
        s = m.group(1) or m.group(2)
        if s.startswith("http"):
            continue
        refs.add(s)
        if not (root / s).exists():
            bad.append(f"{p.name}: 없는 이미지 {s}")
    for m in re.finditer(r'\]\(([^)#\s]+\.md)(#[^)]*)?\)', t):
        if not (root / m.group(1)).exists():
            bad.append(f"{p.name}: 없는 문서 {m.group(1)}")

    # 2) 그림 번호가 장 번호와 맞는가 (fig-<장>-<n>)
    ch = re.match(r"(\d+)", p.name)
    if ch:
        for m in re.finditer(r"images/fig-(\d+)-", t):
            if int(m.group(1)) != int(ch.group(1)):
                bad.append(f"{p.name}: fig-{m.group(1)}-* 은 {ch.group(1)}장 것이 아니다")

# 3) 쓰이지 않는 이미지
for f in sorted(root.glob("images/**/*")):
    if f.is_file() and str(f.relative_to(root)) not in refs:
        bad.append(f"쓰이지 않는 이미지: {f.relative_to(root)}")

# 4) 장 번호가 비었는가
nums = sorted({int(m.group(1)) for p in mds if (m := re.match(r"(\d+)", p.name))})
missing = [n for n in range(nums[0], nums[-1] + 1) if n not in nums]
if missing:
    bad.append(f"빠진 장 번호: {missing}")

print(f"장 {len(mds)}개 · 이미지 참조 {len(refs)}개")
for b in bad:
    print("  ✗", b)
print("문제 없음" if not bad else f"문제 {len(bad)}건")
sys.exit(1 if bad else 0)
