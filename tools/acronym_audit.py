# 약어 감사: 장 순서대로 읽으며 각 약어의 책 전체 첫 등장 자리에 풀이 패턴이 있는지 본다.
# 사용: python3 tools/acronym_audit.py  (README 집필 기준 "모든 용어는 처음 나온 자리에서 푼다"의 점검 도구)
import re, glob
order = ['01','02','03','04-','04a','05','06','07','08','09','10','11a','11b','11c','11d','11e','11f','12','13','부록A','부록B','부록C','부록D']
files = []
for p in order:
    m = [f for f in sorted(glob.glob('*.md')) if f.startswith(p) and f!='README.md']
    files += m
seen = {}   # acronym -> (file, defined?)
acr = re.compile(r'\b([A-Z][A-Z0-9\-]{1,7}[A-Za-z]?)\b')
skip = set('OK ERROR USB PC CPU RAM ROM IP TCP UDP DNS DHCP NAT HTTP HTTPS JSON REST API URL ID DB SQL TLS SSH CLI OS GC AES MD5 HMAC XOR LDAP RADIUS MAC WIFI VXLAN GRE TUN VPN RFC RTT MTU TTL ASCII BCD HEX CSV XML YAML PDF GPL MIT LAN VLAN ARP ICMP SHA HMAC-SHA GET POST PUT NULL'.split())
# 정의로 인정하는 패턴: **ACR**  또는 ACR( 또는 (ACR, 또는 'ACR 는/은/이란/라 한다' 근처에 한글 설명
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
    for m in acr.finditer(text_nocode):
        a = m.group(1).rstrip('-')
        if a in skip or len(a) < 2 or a.isdigit(): continue
        if re.fullmatch(r'[A-Z]\d+|N\d|[0-9A-F]{2,}', a): continue
        if a in seen: continue
        # 첫 등장 위치 주변 120자
        s = max(0, m.start()-80); e = min(len(text_nocode), m.end()+120)
        ctx = text_nocode[s:e].replace('\n',' ')
        defined = bool(re.search(r'\*\*[^*]*'+re.escape(a)+r'[^*]*\*\*', ctx)) or \
                  bool(re.search(re.escape(a)+r'\s*\(', ctx)) or \
                  bool(re.search(re.escape(a)+r"(/[A-Z0-9]+)?[\"'\s]*[\(—]", ctx)) or bool(re.search(r'\('+re.escape(a)+r'[,)]', ctx)) or \
                  bool(re.search(re.escape(a)+r'\s*(는|은|이란|란|이라|라고|를|을)\s', ctx) and re.search(r'(다\.|이다|한다|뜻|줄임|약자)', ctx))
        seen[a] = (f, defined, ctx.strip())
und = [(a,v) for a,v in seen.items() if not v[1]]
print(f"약어 총 {len(seen)}개, 첫 등장에서 설명 패턴이 안 보이는 것 {len(und)}개\n")
for a,(f,d,ctx) in sorted(und, key=lambda x: order.index(next(p for p in order if x[1][0].startswith(p)))):
    print(f"[{f[:12]}] {a:10s} … {ctx[:110]}")
