# -*- coding: utf-8 -*-
"""각 절이 '그래서 무엇을 돌리게 되는가' 에 착지하는지 본다.

집필기준: "이 책은 구축서다. 모든 절은 '그래서 지금 네 장비에서 이것을 치고 이것이
보여야 한다' 로 끝나야 한다. 원리 설명은 그 명령과 그 출력을 이해하기 위해서만 존재한다."

착지로 인정하는 것: 설정 키 이름, 실행할 명령, 로그에서 찾을 문자열, 🔎 블록.
요약·점검 문제·직접 해보기·사례는 세지 않는다(그 자체가 착지다).
사용: python3 tools/landing_audit.py
"""
import io, re, glob

KNOB = re.compile(
    r'tx_gain|rx_gain|dl_arfcn|ssb_arfcn|channel_bandwidth|common_scs|otw_format|srate'
    r'|device_args|serial=|tdd_ul_dl_cfg|nof_ul_slots|pci:|amf\.addr|plmn|tac'
    r'|gnb\.yml|\.env|amf\.yaml|smf\.yaml|upf\.yaml|ims_zone|register\.cfg|mo\.cfg|mt\.cfg'
    r'|AT\+|ATI|ATD|docker |lsusb|dmesg|uhd_|iperf|ping |qmicli|mmcli|tcpdump|journalctl'
    r'|pySim|mongosh|adb |curl |grep |python3 tools/|bin/[a-z-]+\.sh|systemctl'
    r'|🔎|5QI|PCC 규칙|pcc_rule|UE_IPV4|MCC=|MNC=|content query')
SKIP_T = ('점검', '직접', '요약', '사례')
# 성격상 손잡이가 없는 문서: 머리말, 용어집(색인), 법규 고지
SKIP_F = ('00', '부록A', '부록D')

ORDER = ['00','01','02','03','04-','04a','05','06','07','08','09','10',
         '11-','12','13','14','15','16','17','18','부록A','부록B','부록C','부록D']
files = []
for p in ORDER:
    files += [f for f in sorted(glob.glob('*.md'))
              if f.startswith(p) and f != 'README.md' and '집필' not in f]

print(f"{'장':<26}{'절':>4}{'착지':>5}{'비율':>7}   착지 안 한 절")
print('-' * 86)
T = L = 0
for f in files:
    s = io.open(f, encoding='utf-8').read()
    secs = re.split(r'(?m)^## ', s)[1:]
    miss, n, l = [], 0, 0
    for p in secs:
        title = p.split('\n')[0].strip()
        if title.startswith(SKIP_T) or '요약' in title: continue
        n += 1
        if KNOB.search(p): l += 1
        else: miss.append(title[:30])
    if not n: continue
    counted = not f.startswith(SKIP_F)
    if counted: T += n; L += l
    mark = "" if counted else "  (합계 제외)"
    print(f"{f[:25]:<26}{n:>4}{l:>5}{l*100//n:>6}%   {(', '.join(miss))[:38]}{mark}")
print('-' * 86)
print(f"{'합계':<26}{T:>4}{L:>5}{L*100//T:>6}%")
