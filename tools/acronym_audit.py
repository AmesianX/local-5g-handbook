# 약어 감사: 장 순서대로 읽으며 각 약어의 책 전체 첫 등장 자리에 풀이 패턴이 있는지 본다.
# 사용: python3 tools/acronym_audit.py  (README 집필 기준 "모든 용어는 처음 나온 자리에서 푼다"의 점검 도구)
import re, glob
order = ['01','02','03','04-','04a','05','06','07','08','09','10','11-','12','13','14','15','16','17','18','부록A','부록B','부록C','부록D']
files = []
for p in order:
    m = [f for f in sorted(glob.glob('*.md')) if f.startswith(p) and f!='README.md']
    files += m
seen = {}   # acronym -> (file, defined?)
acr = re.compile(r'\b([A-Z][A-Z0-9\-]{1,7}[A-Za-z]?)\b')
# 이름(제품·회사·학회·커넥터·단자 라벨)은 풀이 대상이 아니다. 약어가 아니라 고유명사다.
names = set('TOJOIN USENIX LG SKT KT BIOS RJ45 USB-C TC35 SC FX3 USRP RM520N RM520N-GL RM530N RG520N RG52xF RG530F RG50xQ RM5xxQ ANT1 ANT2 ANT3 ANT4 TRXA TRXB RXA RXB RX2 RX3 MB'.split())
# 비유로 끌어오는 개발자 상식 용어도 풀이 대상이 아니다(집필기준: 유명한 것은 짧게).
skip = set('CSS MPEG-2 PXE EADDRINUSE SMTP SSD DNS TLS DHCP SNI OK ERROR USB PC CPU RAM ROM IP TCP UDP DNS DHCP NAT HTTP HTTPS JSON REST API URL ID DB SQL TLS SSH CLI OS GC AES MD5 HMAC XOR LDAP RADIUS MAC WIFI VXLAN GRE TUN VPN RFC RTT MTU TTL ASCII BCD HEX CSV XML YAML PDF GPL MIT LAN VLAN ARP ICMP SHA HMAC-SHA GET POST PUT NULL'.split())
# 정의로 인정하는 패턴: 용어 표기 **ACR** 또는 ACR( 또는 (ACR, 또는
# 'ACR 는/은/이란/라 한다' 근처에 한글 설명.
# 굵은 글씨는 용어 표기에도 강조에도 쓰므로, 한글이 섞인 굵은 구절은 용어 표기로 보지 않는다.
#       (`**MMS 능력까지 붙어서**` 를 MMS 의 정의로 읽어 사례 21 의 MMS/MMSC/WAP 셋을 놓쳤다.
#        반대로 `**AMF, SMF, UPF, …**` 처럼 약어만 묶은 굵은 글씨는 용어 표기다.)
hangul = re.compile(r'[가-힣]')
def bold_spans(text):
    """파일 전체에서 굵은 글씨 구간을 구한다. 창을 잘라서 ** 를 짝지으면
       창이 구간 한가운데서 시작할 때 짝이 하나씩 밀려 전부 어긋난다."""
    return [(m.start(), m.end(), m.group(1)) for m in re.finditer(r'\*\*([^*\n]+)\*\*', text)]
def bold_term(a, spans, s, e):
    """창과 겹치는 굵은 글씨 중, 한글이 없고 약어 a 를 품은 것이 있으면 용어 표기로 본다."""
    for bs, be, inner in spans:
        if be <= s or bs >= e: continue
        if hangul.search(inner): continue
        if re.search(r'\b'+re.escape(a)+r'\b', inner): return True
    return False
report = []
for f in files:
    text = open(f).read()
    # 코드블록 제외
    text_nocode = re.sub(r'```.*?```', '', text, flags=re.S)
    # 인라인 코드(명령·로그 문자열)도 제외: 본문 용어가 아니다
    text_nocode = re.sub(r'`[^`\n]*`', '', text_nocode)
    # 제목 줄은 이름만 대고 정의는 바로 아래 본문이 한다
    text_nocode = re.sub(r'(?m)^#.*$', '', text_nocode)
    text_nocode = re.sub(r'<?https?://\S+', '', text_nocode)   # URL
    # 그림의 대체텍스트와 따옴표 안의 글자는 '보여 주는 증거'이지 책이 도입하는 용어가 아니다.
    # 지우지 않고 자리표시자로 바꾼다 — 지우면 **"…"** 가 **** 가 되어 굵은 글씨 짝이 밀린다.
    text_nocode = re.sub(r'!\[[^\]]*\]\([^)]*\)', '\u25a1', text_nocode)
    text_nocode = re.sub(r'"[^"\n]{0,60}"', '\u25a1', text_nocode)
    spans = bold_spans(text_nocode)
    for m in acr.finditer(text_nocode):
        a = m.group(1).rstrip('-')
        if a in skip or len(a) < 2 or a.isdigit(): continue
        if re.fullmatch(r'[A-Z]\d+|N\d|[0-9A-F]{2,}', a): continue
        if a in names: continue
        if a in seen or a.upper() in seen: continue
        # 첫 등장 위치 주변 120자
        s = max(0, m.start()-80); e = min(len(text_nocode), m.end()+120)
        ctx = text_nocode[s:e].replace('\n',' ')
        defined = bold_term(a, spans, s, e) or \
                  bool(re.search(re.escape(a)+r'\s*\(', ctx)) or \
                  bool(re.search(re.escape(a)+r"(/[A-Z0-9]+)?[\"'\s]*[\(—]", ctx)) or bool(re.search(r'\([^)]*\b'+re.escape(a)+r'\b[^)]*[,:)]', ctx)) or \
                  bool(re.search(re.escape(a)+r'\s*(는|은|이란|란|이라|라고|를|을)\s', ctx) and re.search(r'(다\.|이다|한다|라 하고|라 부른|뜻|줄임|약자)', ctx))
        seen[a] = (f, defined, ctx.strip())
und = [(a,v) for a,v in seen.items() if not v[1]]
print(f"약어 총 {len(seen)}개, 첫 등장에서 설명 패턴이 안 보이는 것 {len(und)}개\n")
for a,(f,d,ctx) in sorted(und, key=lambda x: order.index(next(p for p in order if x[1][0].startswith(p)))):
    print(f"[{f[:12]}] {a:10s} … {ctx[:110]}")
