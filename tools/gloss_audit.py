# -*- coding: utf-8 -*-
"""굵게 표시한 외래어·기술 용어 옆에 그 자리에서 풀어 준 설명이 있는지 본다.

머리말 표기 규칙("굵은 글씨는 처음 나온 전문 용어이고 바로 옆에 뜻이 붙는다")의 점검 도구다.
약어 감사(acronym_audit.py)가 대문자 약어를 보는 자리에, 이 도구는 **한글 외래어 용어**를 본다.
남는 것은 대개 용어가 아니라 강조이므로, 숫자가 0 이어야 하는 종류의 검사가 아니라 **훑어볼 목록**이다.
사용: python3 tools/gloss_audit.py
"""
import io, re, glob

ORDER = ['00-', '00a', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '부록A', '부록B', '부록C', '부록D']
files=[]
for p in ORDER:
    files += [f for f in sorted(glob.glob('*.md')) if f.startswith(p) and f!='README.md' and '집필' not in f]
# 외래어로 보이는 한글 용어 + 라틴 문자가 섞인 굵은 용어
LOAN = re.compile(r'(트레이싱|패스스루|멀티플렉싱|멱등|파티션|서버리스|프록시|레이트|커넥션|비트레이트|샤딩|스트라이핑|폴링|핸드셰이크|오버헤드|버퍼|큐|뮤텍스|타임슬라이스|퀀텀|비트스트림|펌웨어|에일리어싱|양자화|스트림|스케줄러|캐시|스레드|프로세스|인터페이스|터널|세션|토큰|해시|디렉터리|레지스트리|컨테이너|이미지|브리지|소켓|포트|파서|프레임|패킷|라이브러리|드라이버|레지스터|인덱스|엔드포인트|미들웨어|워커|슬롯|심볼|샘플|게인|감쇠|변조|복조|직교|공명|편파|전치|열거)')
seen={}; rows=[]
for f in files:
    s=io.open(f,encoding='utf-8').read(); s=re.sub(r'```.*?```','',s,flags=re.S)
    for m in re.finditer(r'\*\*([^*\n]+)\*\*', s):
        t=m.group(1).strip()
        if len(t)>26 or re.search(r'[.!?]',t): continue
        if not LOAN.search(t): continue
        key=re.sub(r'[\s`]','',t)
        if key in seen: continue
        seen[key]=1
        after=s[m.end():m.end()+130]
        # 바로 뒤에 괄호풀이/대시풀이/'란 … 이다' 가 있으면 통과
        if re.match(r'^\s*[\(（]', after): continue
        if re.match(r'^\s*[—–]', after): continue
        if re.search(r'^[^.]{0,60}(란|이란|라 하|라 부|이라 하|이라 부|이다\.|를 뜻|을 뜻|다시 말해|즉 |는 것이고|이고,|인데,|다\. )', after): continue
        if re.search(r'[\(（][^)）]{6,}[\)）]', after[:60]): continue
        rows.append((f,t,after.replace('\n',' ')[:88]))
print(f"외래어·기술 용어 굵은 표기 {len(seen)}개 중, 바로 옆 풀이가 없는 것 {len(rows)}개\n")
cur=None
for f,t,a in rows:
    if f!=cur: print(f"── {f[:22]}"); cur=f
    print(f"   {t[:24]:<26} ▸{a}")
