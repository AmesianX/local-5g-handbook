# 08. 음성과 문자: SIP 를 아는 사람을 위한 IMS

## 8.1 이미 아는 것에서 출발한다

VoIP 를 한 번이라도 다뤄 봤다면 SIP 를 안다. REGISTER 로 "나 여기 있다"를 알리고, INVITE 로 통화를 걸고, SDP 로 미디어 포트를 협상하고, RTP 로 음성을 보내고, BYE 로 끊는다. 프록시가 중간에서 Via 와 Record-Route 를 쌓는다. 이것을 알면 IMS 의 **8 할은 이미 아는 것**이다. IMS 는 SIP 에 통신사의 요구 다섯 가지를 얹은 것이고, 그 다섯 가지가 새로 배울 전부다.

| 독자가 아는 것 (SIP/VoIP) | IMS 에서의 이름 |
|---|---|
| outbound proxy (단말이 처음 말을 거는 프록시) | **P-CSCF** |
| registrar + 호 라우터 | **S-CSCF** |
| "이 사용자는 어느 registrar 가 맡나" 조회 | **I-CSCF** + HSS 의 LIR |
| 사용자 DB (Asterisk 의 sip.conf, Kamailio 의 subscriber 테이블) | **HSS** (우리는 PyHSS) |
| HTTP Digest 인증 | **AKAv1-MD5** (6 장의 MILENAGE 를 Digest 에 담은 것) |
| 미디어 릴레이 (rtpproxy, TURN) | **rtpengine** |
| DNS SRV/NAPTR 로 다음 홉 찾기 | IMS 도메인 `ims.mnc001.mcc001.3gppnetwork.org` 해석 |
| SIP MESSAGE 로 인스턴트 메시지 | **SMS over IMS** (본문이 3GPP SMS 바이트) |

새로 배울 다섯 가지는 이것이다. 첫째, **전화번호(E.164)로 걸고 다른 사업자에게도 걸린다** — 그래서 `tel:` URI 와 I-CSCF 가 있다. 둘째, **품질을 보장한다** — 그래서 P-CSCF 가 코어의 PCF 에 "이 통화에 음성 베어러를 열어라"고 요청하는 N5 가 있고, 7 장의 5QI 가 여기서 쓰인다. 셋째, **인증은 SIM 으로** — 그래서 HTTP Digest 안에 MILENAGE 가 들어간다. 넷째, **단말의 IP 와 코어의 세션이 묶여 있어야 한다** — 그래서 P-CSCF 가 소스 IP 로 PDU 세션을 확인한다. 다섯째, **문자는 1990 년대 SMS 바이트를 그대로 SIP 에 싼다.**

이 장은 우리 실험에서 통화와 문자가 성립하기까지 **차례로 만난 벽 일곱 개**를 그대로 따라간다. 벽마다 "왜 막혔는가"가 곧 "IMS 는 왜 이렇게 생겼는가"다.

## 8.2 왜 전화를 IP 위에 다시 세워야 했나

2G 와 3G 는 **회선 교환**이었다. 전화를 걸면 망이 음성 전용 경로를 통째로 잡아 줬다. 4G 는 **All-IP** 다. 음성 전용 경로가 없다. 그러면 전화는 "IP 패킷으로 음성을 보내는 앱"이 되어야 한다. 그런데 그냥 VoIP 앱으로 끝낼 수 없는 이유가 있었다.

스카이프 같은 VoIP 는 아이디로 걸고, 같은 앱끼리만 통하고, 품질은 되는 대로이고, 긴급통화가 안 되고, 계정은 앱 서버가 관리한다. 통신사 전화는 **전화번호**로 걸어야 하고, **다른 사업자 가입자**에게도 걸려야 하고, **끊기지 않아야** 하고, **112 가 되어야** 하고, **SIM 으로 인증하고 과금**해야 한다. 이 요구를 전부 만족하는 표준 VoIP 플랫폼을 3GPP 가 2000 년대 초(Release 5)에 정했고, 그것이 **IMS(IP Multimedia Subsystem)** 다. SIP 를 그대로 가져다 쓰고 위의 요구를 헤더와 절차로 얹었다. 5G 에서 IMS 로 하는 전화를 **VoNR**, 4G 에서는 **VoLTE** 라 하는데, 코어만 다르고 IMS 는 같다.

## 8.3 IMS 의 조각: 프록시 셋과 DB 하나

```
                        [HSS / PyHSS]  ← 가입자 DB + 인증 벡터 (Diameter Cx)
                          ▲        ▲
                     UAR  │        │  MAR, SAR, LIR
 [단말] ──SIP──▶ [P-CSCF] ──▶ [I-CSCF] ──▶ [S-CSCF] ──▶ (착신 S-CSCF → P-CSCF → 단말)
                    │                           │
                    │ N5 (Rx)                   │ ISC (iFC 가 시키는 대로)
                    ▼                           ▼
                  [PCF]                 [응용서버: SMSC …]
```

**P-CSCF(Proxy-CSCF)** 는 단말이 처음 만나는 프록시다. 독자가 아는 outbound proxy 에 **세션 보더 컨트롤러**의 역할이 더해졌다. 단말의 IP 가 코어의 어느 세션인지 확인하고(N5), 미디어 릴레이(rtpengine)를 붙이고, 통화마다 코어에 QoS 를 요청한다. **I-CSCF(Interrogating-CSCF)** 는 망의 입구다. 등록 때는 "이 가입자를 어느 S-CSCF 가 맡을까", 착신 때는 "이 번호의 S-CSCF 는 어디인가"를 HSS 에 묻는다. 로드밸런서 겸 디렉터리 조회다. **S-CSCF(Serving-CSCF)** 가 registrar 이자 호 제어의 중심이다. 인증하고, 등록 상태를 보관하고, 가입자의 서비스 규칙(iFC)에 따라 응용서버로 분기하고, 착신을 라우팅한다. **HSS** 는 IMS 가입자 DB 이고 인증 벡터를 만든다. 5G 코어의 UDM 과는 **별개**다. 4G 유산이기 때문이다.

CSCF 는 Call Session Control Function 이다. 셋 다 오픈소스 SIP 서버 Kamailio 에 각각 다른 설정을 올린 것이고, 우리 컨테이너 `pcscf`·`icscf`·`scscf` 가 그것이다. 한 대로 합쳐도 돌아간다. 셋으로 나눈 것은 "단말 쪽 경계(보안·QoS)", "망 입구(어디로)", "가입자 서비스(등록·라우팅)"로 **책임을 가른 것**이고, 상용망에서 수백만 가입자를 수십 대의 S-CSCF 가 나눠 맡으려면 I-CSCF 가 필요하다.

가입자 DB 가 **둘**이라는 점을 다시 짚는다. mongo 는 5G 등록과 세션용으로 Ki, DNN, 5QI, PCC 규칙을 가진다. mysql(PyHSS) 은 IMS 등록과 통화용으로 **같은 Ki** 를 따로 또 가지고, MSISDN, iFC, S-CSCF 할당을 가진다. 그래서 우리는 가입자를 **양쪽에** 넣었고, 6 장에서 말한 SQN 재동기가 생길 수 있다. 상용망은 UDM 이 HSS 를 흡수하거나 둘을 동기화한다.

## 8.4 등록: REGISTER 한 번에 조각 넷이 움직인다

통화 전에 **IMS 등록**이 있어야 한다. 5 장의 5G 등록과는 별개다. "나 여기 있다, 이 IP 이 포트로 불러라"를 IMS 에 알리는 것이다. 흐름은 독자가 아는 SIP 등록에 HSS 조회와 QoS 확인이 끼어든 것이다.

단말이 REGISTER 를 P-CSCF 에 보낸다. P-CSCF 는 받자마자 **N5** 로 PCF 에 묻는다. "이 소스 IP 의 PDU 세션이 있고, IMS 시그널링을 실을 QoS(5QI 5)인가?" 통과하면 I-CSCF 로 넘기고, I-CSCF 는 HSS 에 **UAR** 로 "이 가입자 등록 가능한가, S-CSCF 는 누구인가"를 묻고(응답 UAA), S-CSCF 로 넘긴다. S-CSCF 는 HSS 에 **MAR** 로 인증 벡터를 받고(MAA: RAND, AUTN, XRES, CK, IK), 단말에 **401** 을 돌려준다. `nonce` 에 RAND‖AUTN 이 들어 있다. P-CSCF 는 그 401 에서 `ck=`, `ik=` 를 **떼고** 단말에 전달한다. 단말은 6 장의 MILENAGE 를 돌려 RES 를 얻고, Digest 응답을 넣은 REGISTER 를 다시 보낸다. S-CSCF 가 RES 를 검증하고, HSS 에 **SAR** 로 "등록됐다, 이 가입자의 서비스 규칙을 줘"라고 하면(SAA: iFC XML), 단말에 **200 OK** 를 보낸다. 그리고 iFC 가 시키는 응용서버들에 "이 가입자 등록됐다"는 3rd-party REGISTER 를 보낸다.

우리가 받은 200 OK 의 두 헤더가 이 흐름의 결과다.

```
P-Associated-URI: <sip:821099994531@ims.mnc001.mcc001.3gppnetwork.org>, <tel:821099994531>, <sip:001011234567895@…>
Service-Route: <sip:orig@scscf.ims.mnc001.mcc001.3gppnetwork.org:6060;lr>
```

**P-Associated-URI** 는 "너는 이 세 이름으로 불린다"다. 전화번호 형식의 sip 주소, `tel:` 주소, 그리고 IMSI 형식의 sip 주소. HSS 의 `ims_subscriber.msisdn` 이 `tel:` 로 돌아온 것이고, **전화번호가 IMS 에 반영됐다**는 증거다. **Service-Route** 는 "앞으로 발신 요청은 이 S-CSCF 를 거쳐라"다. 이후 INVITE 의 Route 헤더에 넣는 값이다.

IMS 의 신원 용어를 정리한다. **IMPI(IMS Private Identity)** 는 인증용 비공개 ID 로 로그인 ID 에 해당한다. 우리는 `001011234567895@ims.mnc001.mcc001.3gppnetwork.org` 다. **IMPU(IMS Public Identity)** 는 남이 부르는 공개 ID 로 이메일 주소나 전화번호에 해당하고 여러 개 가질 수 있다. **realm(홈 도메인)** 은 IMS 망의 이름이다. 4a 에서 ISIM 이 비어 있어 IMPI 를 IMSI 에서 유도했다고 했는데, 그 규칙이 `IMSI@ims.mnc<MNC>.mcc<MCC>.3gppnetwork.org` 다. 이 `3gppnetwork.org` 도메인은 인터넷으로 나가지 않는다. 우리 `dns` 컨테이너가 푼다.

**벽 ①: `412 Register N5 QoS authorization failed`.** P-CSCF 의 첫 확인에서 두 번 걸렸다. 처음 호스트 브리지 IP(172.22.0.1)로 보냈을 때는 그 IP 에 **PDU 세션이 없어서**, 단말 IP(10.45.0.x)로 바꾼 뒤에는 세션은 있지만 **5QI 9 라서** 거절됐다. PCF 로그가 `Even the Default Bearer(QCI:9,ARP:8) cannot support IMS signalling` 이라고 정확히 말해 줬다. 7 장의 5QI 가 등록 첫 관문에서 바로 쓰인다. **IMS 등록은 반드시 단말의 PDU 세션 IP 에서, 5QI 5 를 실을 수 있는 세션으로** 보내야 한다. 상용 단말은 `ims` DNN 세션으로 보내므로 자동으로 만족한다. 우리 모뎀 펌웨어가 IMS 를 지원하지 않아 `internet` 세션의 등급을 5 로 올린 것은 실험실 고유의 우회였다.

## 8.5 통화: INVITE 한 번이 몇 바퀴를 도는가

등록된 A(모뎀 쪽)가 B(nr-UE 쪽)에게 건다. 독자가 아는 SIP 통화에 홉이 많이 끼어든 것인데, 그 홉 하나하나가 통신사의 요구 하나씩이다.

A 가 INVITE 를 P-CSCF 에 보낸다. SDP 에 자기 오디오 포트가 있다. P-CSCF 는 두 가지를 한다. **N5** 로 PCF 에 "이 통화의 미디어 QoS 를 허가해라"를 요청하고, **rtpengine** 에 "중계 포트를 열어라"고 해서 SDP 의 IP 와 포트를 rtpengine 것으로 **바꿔 쓴다.** 그리고 S-CSCF(A) 로 넘긴다. S-CSCF(A) 는 발신 처리를 한다. iFC 를 검사하고, 착신 번호를 정규화하고, 착신 도메인이 우리 망이니 I-CSCF 로 보낸다. I-CSCF 는 HSS 에 **LIR** 로 "B 의 S-CSCF 는 어디인가"를 묻고(LIA 에 S-CSCF 주소), 그쪽으로 넘긴다. S-CSCF(B) 는 착신 처리를 한다. B 의 등록된 Contact 주소를 꺼내고, 등록 때 저장된 경로(Path 헤더)로 P-CSCF(B) 에 보낸다. P-CSCF(B) 도 rtpengine 과 N5 를 거쳐 B 의 Contact 주소로 INVITE 를 보낸다. B 가 180 Ringing 과 200 OK 를 역순으로 돌려보내고, A 가 ACK 를 Route set 을 따라 보내면 통화가 성립한다. RTP 는 A ↔ rtpengine ↔ B 로 흐르고, BYE 로 끊으면 양쪽 P-CSCF 가 N5 로 QoS 를 해제한다.

한 통화에 SIP 요청 셋(INVITE, ACK, BYE)과 응답 여러 개가 **홉마다** 오간다. 우리 캡처에서 I-CSCF 와 S-CSCF 사이에만 UDP 패킷이 십여 개였던 이유다. 이제 우리가 만난 벽들이다.

**벽 ②: `500 Server error on LIR select next S-CSCF`.** 이 문구는 "LIR 이 실패했다"처럼 읽힌다. 아니었다. I-CSCF 설정을 열어 보니 이 문장은 `failure_route` 안, 즉 **다음 홉이 408 타임아웃을 냈을 때 들어오는 블록**에 있었다. 캡처에서 LIA 에는 S-CSCF 주소가 정상적으로 들어 있었다. 그러니까 LIR 은 성공했고, I-CSCF 가 S-CSCF 로 INVITE 를 넘긴 뒤 **그 뒤 어딘가**에서 응답이 없어 408 이 났고, 대체 S-CSCF 가 없어 500 으로 포장된 것이다. Kamailio 의 오류 문구는 **그 코드가 놓인 자리의 이름**이지 원인이 아니다. 원인은 다음 홉에 있었다.

**벽 ③: P-CSCF 가 단말에 TCP 로 보낸다.** 착신 P-CSCF 로그가 답이었다. `connect 10.46.0.7:5062 failed`, 그 위에 `tcp_main.c`. 우리 단말 쪽 소프트웨어는 UDP 만 듣고 있었는데 P-CSCF 는 TCP 로 연결하려 했다. 왜 TCP 인가. **S-CSCF 가 만든 INVITE 가 1317 바이트**였다. RFC 3261 §18.1.1 은 요청이 MTU 에서 200 을 뺀 크기(보통 1300 바이트)를 넘으면 **TCP 로 보내라**고 정한다. IMS 는 홉마다 Via, Record-Route, P-헤더가 붙어서 INVITE 가 금방 커진다. 그래서 **IMS 단말은 TCP 를 반드시 들어야 한다.** 우리 도구에 TCP listener 를 넣자 INVITE 가 도착했다. Contact 에 `;transport=udp` 를 넣어 UDP 를 강제하는 것도 시도했는데 **역효과**였다. P-CSCF 가 Contact 의 `alias=` 파라미터로 단말 주소를 파싱하는데 `transport=` 가 끼자 파싱이 깨져 `IP is <null>` 이 됐다. 표준만 믿고 프록시의 구현을 모르면 생기는 일이다.

**벽 ④: `404 Not here` 와 단방향 RTP.** INVITE 가 통했는데 BYE 에 404 가 오고 발신 쪽 RTP 수신이 0 이었다. 둘 다 **내 코드가 다이얼로그 안의 요청(ACK, BYE)을 잘못 만든** 버그였다. RFC 3261 §12.1.2 는 UAC 가 2xx 응답의 **Record-Route 를 Route 로 바꿔** 그 순서대로 넣고, Request-URI 는 **2xx 의 Contact(remote target)** 로 하라고 한다. 나는 Record-Route 를 이름 그대로 넣고 Request-URI 에 원래 호출 URI 를 썼다. 프록시는 그런 요청의 다이얼로그를 못 찾는다(404). ACK 가 B 에 안 닿으니 rtpengine 이 역방향을 열지 않아 RTP 가 한쪽만 흘렀다. 고친 뒤 ACK 도착, RTP 양방향 200/200, BYE 200 OK 가 됐다. SIP 를 아는 독자라면 "그걸 왜 틀려" 하겠지만, 실험용 도구를 급하게 짤 때 가장 자주 빠지는 구멍이다.

**벽 ⑤: `488 N5 QoS authorization failed for call`.** INVITE 가 통하자 P-CSCF 가 **통화 미디어용 QoS** 를 PCF 에 요청했고, PCF 가 `No PCC Rule in DB [QoS Index:1]` 로 거절했다. 7 장의 5QI 1 PCC 규칙을 양쪽 가입자에 넣자 통과했다. 영상은 같은 방식으로 5QI 2 다. 이 벽이 **IMS 와 코어가 연결되어 있다**는 가장 직접적인 증거다. SIP 통화가 성립하려면 PCF 가 음성 베어러를 열어 줘야 하고, 그 근거는 가입자 DB 의 PCC 규칙이다. 일반 VoIP 에는 없는 단계다.

## 8.6 미디어: rtpengine 이 사이에 있는 이유

SDP 를 보면 A 의 오디오 포트는 `10.45.0.6:40000` 이었는데 B 가 받은 SDP 는 `172.22.0.16:49288` 이었다. `172.22.0.16` 은 rtpengine 이다. 양쪽 P-CSCF 가 SDP 를 바꿔치기해서 RTP 가 단말끼리 직접 가지 않고 **rtpengine 을 거친다.** 독자가 아는 rtpproxy 나 TURN 과 같은 자리다.

왜 중계하는가. 두 단말이 서로 다른 DNN(10.45 와 10.46)에 있어서 직접 라우팅이 보장되지 않는다는 것이 첫째다. 중계점은 양쪽에서 닿는다. 둘째는 **QoS 적용점**이다. PCF 가 허가한 미디어가 여기를 지나는지 확인하고 과금한다. 셋째는 상용망의 합법 감청과 녹취 요구다. 넷째는 양쪽 코덱이 다를 때의 변환이다. 그래서 우리 RTP 카운트가 "발신 송신 200, 착신 수신 200" 으로 맞았지만 경로는 두 번 꺾인 것이다.

rtpengine 은 처음에 상대 주소를 모른다. **첫 RTP 패킷이 온 소스 주소를 기억(latch)** 하고 그쪽으로 역방향을 보낸다. 우리 발신 쪽 수신이 처음 세 개 빠진 것이 latch 전의 패킷이고, ACK 가 안 가던 때 역방향이 아예 안 열린 것도 latch 가 완성되지 않아서였다.

## 8.7 문자: SMS 바이트를 SIP 에 싸서 SMSC 로

11c 에서 SMS 의 바이트(TPDU)를 봤다. IMS 에서는 그 바이트를 **SIP MESSAGE 의 본문**에 담는다. 독자가 아는 SIP MESSAGE 인스턴트 메시징과 모양이 같고, 본문이 평문이 아니라 1990 년대 SMS 바이너리라는 점만 다르다.

단말이 MESSAGE 를 보내면 S-CSCF 가 **iFC** 를 본다. iFC(initial Filter Criteria) 는 HSS 가 등록 때 S-CSCF 에 내려 준 XML 규칙 목록으로, "이런 조건의 요청이 오면 이 응용서버로 보내라"다. 우리 `default_ifc.xml` 에 `<Method>MESSAGE</Method> <SessionCase>0</SessionCase> → smsc:5060` 이 있었다. **S-CSCF 는 SMS 가 무엇인지 모른다.** 규칙대로 SMSC 에 넘길 뿐이다. 이것이 IMS 의 확장 방식이다. 새 서비스는 응용서버 하나와 iFC 한 줄로 붙는다.

SMSC 는 TPDU 를 풀어 발신, 착신, 본문, 문자 인코딩(DCS)을 DB 에 저장하고 단말에 `202 Accepted` 를 보낸다. "받았다, 전달은 나중에"라는 뜻이다. 그리고 워커가 큐에서 꺼내 착신 번호를 `sip:번호@realm` 으로 바꿔 새 MESSAGE 를 만들어 S-CSCF(B) 로 보낸다. 거기서 P-CSCF(B) 를 거쳐 B 에 도착하면 B 가 200 OK 를 돌려준다.

**벽 ⑥: `text/plain` 으로 보내면 SMSC 의 DB 가 깨진다.** 처음엔 평문 본문으로 보냈다. SMSC 는 받아서 본문까지 읽었는데(200 OK), DB 에 넣을 때 DCS 가 비어 있어 SQL 문법 오류가 났다. 설정을 열어 보니 `text/plain` 경로(OTT 용)는 DCS 변수를 채우지 않는 **업스트림 버그**였다. 설정을 고치는 대신 **실제 단말과 같은 `application/vnd.3gpp.sms` + TPDU** 로 보냈다. 그 경로는 TPDU 에서 DCS 를 읽어 `8`(UCS2)로 채웠고 저장이 됐다. 응답도 3GPP 경로의 표준인 `202 Accepted` 로 바뀌었다.

**벽 ⑦: 저장은 됐는데 전달이 안 됨.** SMSC 워커가 `sip:821099994532@ims.mnc001.mcc001.3gppnetwork.org` 로 보내려는데 이름이 안 풀렸다. DNS 존에 `scscf.ims…`, `hss.ims…` 같은 **호스트 이름만** 있고 **도메인 자체(`@`)의 A 레코드가 없었다.** 독자가 아는 것으로 치면 `_sip._udp.example.com` SRV 는 있는데 `example.com` A 가 없어서, SRV 를 안 보는 클라이언트가 실패한 것이다. 이름이 안 풀리니 전송이 **조용히** 멈추고 큐에 남았다. `@ IN A <I-CSCF 주소>` 를 넣자 전달됐다. IMS 도메인의 SIP 진입점은 I-CSCF 이므로 그쪽이 맞다. 표준은 NAPTR/SRV 로 찾지만 Kamailio 의 uac 모듈은 A 를 봤다.

착신 B 가 받은 MESSAGE 는 `text/plain` 이었다. SMSC 가 착신 단말이 3GPP SMS 를 받을 수 있는지(등록 때 `+g.3gpp.smsip` 를 광고했는지) 보고 OTT 형식으로 내려 준 것이다. 한글 본문이 그대로 도착했다.

## 8.8 Diameter Cx: IMS 와 HSS 의 대화

IMS 조각들이 HSS 와 말하는 Diameter 는 4G 유산이고, 독자가 RADIUS 를 안다면 그 후손이다. 메시지는 **AVP(Attribute-Value Pair)** 의 나열이고, 11d 의 TLV 와 같은 발상이다. 우리 캡처(TCP 3875)에 네 쌍이 보였다. 등록 시작 때 I-CSCF 가 보내는 **UAR/UAA**("등록 가능한가, S-CSCF 는?"), 인증 때 S-CSCF 가 보내는 **MAR/MAA**("인증 벡터 줘"), 등록 확정 때의 **SAR/SAA**("등록됐다, iFC 줘"), 착신 INVITE 때 I-CSCF 가 보내는 **LIR/LIA**("이 번호의 S-CSCF 는?"). `Server-Name` AVP(602)에 `sip:scscf…:6060` 이, `Result-Code` AVP(268)에 `2001`(성공)이 실려 있었다. `tcpdump -A` 로 보면 문자열 AVP 는 그대로 읽힌다.

운영 함정 하나. I-CSCF 가 PyHSS 보다 **먼저 뜨면** Diameter 연결(`peer_connect`)에 실패하고 **재시도하지 않는다.** 우리는 코어를 여러 번 재기동하다 이 상태에 빠졐고, `docker restart icscf` 로 풀었다. 13 장에 둔다.

## 8.8a 패킷 해부: SIP 메시지, Diameter 헤더, RTP 헤더

### SIP 요청 한 통의 해부

SIP 는 텍스트라 비트 그림 대신 **줄 단위 해부**다. 우리 INVITE 가 P-CSCF 를 지나 S-CSCF 에 도착했을 때의 모습이다. 홉을 지날 때마다 **어느 줄이 늘어나는지**가 핵심이다.

```
INVITE sip:001011234567896@ims.mnc001.mcc001.3gppnetwork.org SIP/2.0     ← 요청 줄: 메서드, Request-URI(착신), 버전
Via: SIP/2.0/UDP 172.22.0.21:5060;branch=z9hG4bK…                        ← P-CSCF 가 쌓음 (응답이 되돌아올 길)
Via: SIP/2.0/UDP 10.45.0.6:5060;rport;branch=z9hG4bK…;received=10.45.0.6 ← 단말이 넣음. P-CSCF 가 received= 추가
Record-Route: <sip:mo@pcscf.ims.…:5060;lr>                               ← P-CSCF 가 쌓음 (다이얼로그 내 요청이 지날 길)
Route: <sip:orig@scscf.ims.…:6060;lr>                                     ← 단말이 등록 때 받은 Service-Route 를 넣음
Max-Forwards: 69                                                           ← 홉마다 1 씩 줄어든다. 루프 방지
From: <sip:001011234567895@ims.…>;tag=uhh52tpquu                          ← 발신. tag 가 다이얼로그 식별자의 반쪽
To: <sip:001011234567896@ims.…>                                           ← 착신. 200 OK 가 올 때 tag 가 붙어 돌아온다
Call-ID: 6orvpiki9xklza1r                                                  ← 이 통화의 고유 번호. From-tag, To-tag 와 셋이 다이얼로그를 정한다
CSeq: 1 INVITE                                                             ← 순번 + 메서드. 같은 다이얼로그 안에서 증가
Contact: <sip:001011234567895@10.45.0.6:5060;alias=10.45.0.6~5060~1>       ← 발신의 직접 주소. 상대가 다이얼로그 내 요청을 보낼 곳. alias 는 P-CSCF 가 붙임
P-Asserted-Identity: <sip:001011234567895@ims.…>, <tel:821099994531>       ← P-CSCF 가 "이 발신자는 인증됐다"고 보증해서 붙임. IMS 전용
P-Access-Network-Info: 3GPP-NR-FDD; utran-cell-id-3gpp=00101000001066C000  ← 단말이 어느 셀에서 왔나. IMS 전용
Content-Type: application/sdp
Content-Length: 243

v=0                                                                        ← SDP 시작
o=- 1234 1 IN IP4 10.45.0.6
c=IN IP4 172.22.0.16                                                       ← P-CSCF 가 rtpengine 주소로 바꿔 쓴 자리 (원래 10.45.0.6)
m=audio 49512 RTP/AVP 0 8 101                                              ← 포트도 rtpengine 것으로. 0=PCMU 8=PCMA 101=DTMF
a=rtpmap:0 PCMU/8000
```

읽는 법 세 가지. 첫째, **Via 는 응답의 길**이다. 프록시마다 자기 주소를 맨 위에 쌓고, 응답은 맨 위 Via 부터 벗기며 되돌아간다. 둘째, **Record-Route 는 다이얼로그 내 요청(ACK, BYE)의 길**이다. 200 OK 에 이 줄들이 그대로 담겨 단말에 오고, 단말은 그것을 **Route 로 바꿔** ACK 와 BYE 에 넣는다. 벽 ④가 이것을 안 해서 생겼다. 셋째, **다이얼로그는 Call-ID + From-tag + To-tag 세 값**으로 정해진다. 프록시가 "404 Not here, 그런 다이얼로그 없다"고 한 것은 이 셋 중 하나 또는 Route 가 안 맞았다는 뜻이다.

INVITE 가 홉마다 커지는 이유가 이 그림에 있다. P-헤더 둘, Via 한 줄, Record-Route 한 줄이 프록시마다 붙는다. 세 프록시를 지나면 수백 바이트가 늘어 1300 을 넘기고, 벽 ③의 TCP 전환이 일어난다.

### Diameter 헤더와 AVP (RFC 6733)

```
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +---------------+-----------------------------------------------+
 |  버전 = 1 (8)  |              메시지 길이 (24)                   |
 +-+-+-+-+-------+-----------------------------------------------+
 |R|P|E|T|여유(4) |              명령 코드 (24)                     |
 +-+-+-+-+-------+-----------------------------------------------+
 |                    응용 ID (32)   Cx = 16777216                 |
 +---------------------------------------------------------------+
 |                    Hop-by-Hop 식별자 (32)                        |
 +---------------------------------------------------------------+
 |                    End-to-End 식별자 (32)                        |
 +---------------------------------------------------------------+
 | AVP 들 …                                                       |

 AVP 하나:
 +---------------------------------------------------------------+
 |                      AVP 코드 (32)                              |
 +-+-+-+-----+---------------------------------------------------+
 |V|M|P|여유  |              AVP 길이 (24)                         |
 +-+-+-+-----+---------------------------------------------------+
 |              [벤더 ID (32)]  V = 1 일 때만. 3GPP = 10415          |
 +---------------------------------------------------------------+
 |                      데이터 …  (4 바이트 정렬 패딩)                |
```

| 필드 | 뜻 | 우리 캡처에서 |
|---|---|---|
| **R** (Request) | `1` 요청, `0` 응답 | LIR 은 1, LIA 는 0. 같은 명령 코드 302 |
| **P** (Proxiable) | 중계 가능 | |
| **E** (Error) | 프로토콜 오류 응답 | |
| **T** (Retransmit) | 재전송 | |
| **명령 코드** | `300` UAR/UAA, `301` SAR/SAA, `302` LIR/LIA, `303` MAR/MAA | 8.8 절의 네 쌍. 요청과 응답이 같은 코드, R 비트로 구분 |
| **응용 ID** | 어느 Diameter 응용인가 | Cx = `16777216` |
| **Hop-by-Hop / End-to-End** | 요청과 응답 짝 맞추기 (홉마다 / 끝에서 끝) | |
| AVP **V** | 벤더 전용 AVP (뒤에 벤더 ID 가 붙음) | 3GPP AVP 는 전부 V=1, 벤더 10415 |
| AVP **M** (Mandatory) | 받는 쪽이 이 AVP 를 모르면 거부해야 | |

자주 보는 AVP 코드다. `263` Session-Id, `264` Origin-Host, `296` Origin-Realm, `268` **Result-Code**(`2001` = DIAMETER_SUCCESS), `297` Experimental-Result(실패 사유), `1` User-Name(IMPI), `601` Public-Identity(IMPU, 벤더 10415), `602` **Server-Name**(S-CSCF 주소, 벤더 10415), `604` Server-Capabilities. 우리 LIA 캡처에서 `602` 에 `sip:scscf.ims…:6060` 이, `268` 에 `2001` 이 있었다. 11d 의 QMI TLV 와 같은 발상(코드, 길이, 값)이라는 것이 그림으로 보일 것이다.

### RTP 헤더 (RFC 3550)

```
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-------------+-------------------------------+
 |V=2|P|X|  CC   |M|     PT      |          일련번호 (16)           |
 +-+-+-+-+-+-+-+-+-+-------------+-------------------------------+
 |                        타임스탬프 (32)                            |
 +---------------------------------------------------------------+
 |                    SSRC 동기 소스 식별자 (32)                      |
 +---------------------------------------------------------------+
 |                         페이로드 (코덱 데이터)                     |
```

| 필드 | 뜻 | 우리 도구의 값 |
|---|---|---|
| **V** | 버전 2 | `struct.pack("!BBHII", 0x80, …)` 의 `0x80` = `10 0 0 0000` → V=2, P=0, X=0, CC=0 |
| **P** | 끝에 패딩 있음 | 0 |
| **X** | 확장 헤더 있음 | 0 |
| **CC** | 기여 소스 수 (믹서용) | 0 |
| **M** | 마커. 오디오는 무음 뒤 첫 패킷, 비디오는 프레임 마지막 패킷 | 0 |
| **PT** (Payload Type) | 코덱. `0` PCMU, `8` PCMA, `96~127` 동적(SDP 의 rtpmap 이 정의). 우리 비디오는 `96` = H.264 | 오디오 `0`, 비디오 `96` |
| **일련번호** | 패킷마다 1 씩. 손실·순서 검출 | 우리 도구가 `seq` 로 증가시킨 것 |
| **타임스탬프** | 샘플 단위 시각. PCMU 8 kHz 에서 20 ms = 160 | 오디오 +160, 비디오(90 kHz) +5400 |
| **SSRC** | 이 스트림의 고유 번호. 양방향이면 두 개 | 우리 도구가 난수로 정한 것 |

와이어샤크의 RTP 스트림 분석은 **일련번호의 빠진 곳**으로 손실을, **타임스탬프와 도착 시각의 차**로 지터를 센다. 우리가 "송신 200 수신 197" 이라고 한 것을 와이어샤크는 `Lost: 3 (1.5%)` 로 보여 준다.

## 8.8b 와이어샤크로 보기

통화 한 번을 캡처하고 필터 `sip` 을 치면 와이어샤크의 **전화 → VoIP 통화** 메뉴가 통화를 자동으로 묶어 준다. 거기서 "흐름 순서" 를 누르면 8.5 절의 그림이 **실제 패킷으로** 그려진다. P-CSCF, S-CSCF, I-CSCF 사이를 INVITE 가 몇 번 오가는지, 각 홉에서 Via 가 몇 줄 쌓이는지, 200 OK 의 Record-Route 가 몇 개인지 전부 보인다. INVITE 하나를 골라 길이를 보면 1300 바이트를 넘는 것을 확인할 수 있고, 그 다음 홉이 `tcp` 로 바뀐 것도 보인다. `sdp` 필터로 SDP 만 모으면 A 의 포트가 rtpengine 주소로 바뀌는 순간이 홉 단위로 보인다. 필터 `diameter` 는 같은 시간대의 UAR/MAR/SAR/LIR 을 보여 주고, 위 그림대로 AVP 를 펼치면 `Server-Name` 과 `Result-Code 2001` 이 읽힌다. 마지막으로 `rtp` 를 치고 **전화 → RTP → RTP 스트림** 을 열면 양방향 패킷 수, 손실, 지터가 표로 나온다. 우리가 "송신 200 / 수신 200" 이라고 세었던 것을 와이어샤크가 대신 세어 준다.

## 8.9 이 장의 요약: 벽 일곱 개가 가르쳐 준 것

| 벽 | 증상 | 원인 | IMS 의 어느 원리 |
|---|---|---|---|
| ① | `412 N5 QoS` | 단말 세션 IP 가 아니거나 5QI 9 | P-CSCF 는 PDU 세션과 묶인다 |
| ② | `500 LIR select next S-CSCF` | 다음 홉 408 을 failure_route 가 포장 | 오류 문구 ≠ 원인 |
| ③ | `connect …:5062 failed` | INVITE > 1300 B → TCP | IMS 단말은 TCP 필수 |
| ④ | `404 Not here`, RTP 단방향 | Route set / remote target 누락 | RFC 3261 §12 다이얼로그 |
| ⑤ | `488 N5 QoS … for call` | 5QI 1/2 PCC 규칙 없음 | 통화 = PCF 가 베어러를 열어야 |
| ⑥ | SMSC SQL 오류 | text/plain 경로의 DCS 미설정 | 3GPP SMS 형식을 써라 |
| ⑦ | SMS 큐에 멈춤 | 도메인 A 레코드 없음 | IMS 도메인 → I-CSCF |

| 질문 | 답 |
|---|---|
| 이미 아는 것 | SIP/RTP/Digest/릴레이/DNS. 이름만 바뀐다 |
| 새로 배울 다섯 | 번호와 상호접속 / QoS(N5, 5QI) / SIM 인증 / 세션-IP 묶임 / SMS 바이트 |
| P / I / S-CSCF | 단말 경계(outbound proxy+SBC) / 입구(디렉터리 조회) / registrar+라우터 |
| 등록 | REGISTER → N5 → UAR → MAR → 401 → MILENAGE → REGISTER → SAR → 200 OK |
| 통화 | INVITE 가 P→S→I(LIR)→S→P→단말. 각 P-CSCF 가 N5 와 rtpengine |
| rtpengine | 릴레이. 경로·QoS·감청·코덱. latch 로 역방향 |
| SMS | MESSAGE + vnd.3gpp.sms → iFC → SMSC → 저장 → 워커가 착신에 |
| Diameter Cx | UAR/MAR/SAR/LIR. AVP. I-CSCF 는 HSS 뒤에 떠야 |

## 점검 문제

1. P-CSCF 가 N5 로 PCF 에 묻는 것을 "등록 때"와 "통화 때" 각각 한 문장으로 쓰라.
2. INVITE 가 1317 바이트였다. 어느 헤더들이 크기를 만들었고, UDP 로 보내려면 무엇을 줄여야 하나?
3. Record-Route 를 Route 로 바꾸지 않으면 프록시가 왜 다이얼로그를 못 찾는가?
4. rtpengine 의 latch 가 완성되려면 어느 방향의 첫 패킷이 필요한가? ACK 가 안 가면 왜 latch 가 안 되나?
5. S-CSCF 가 SMS 를 모르는데 어떻게 SMSC 로 보내는가? 새 서비스를 IMS 에 붙이려면 무엇 둘이 필요한가?
6. SMSC 가 202 를 보낸 뒤 전달에 실패했다면 발신 단말은 알 수 있는가?
7. mongo 와 PyHSS 양쪽에 같은 Ki 를 넣었다. 한쪽만 바꾸면 무엇이 깨지는가?

## 직접 해보기

- `tcpdump -i br-b33ecd87724d udp port 5060 -A` 로 REGISTER 한 번의 **모든 홉**을 잡아, P→I→S 와 돌아오는 401/200 의 Via 가 어떻게 쌓이고 벗겨지는지 표로 만들라.
- `tools/ims_call.py` 의 SDP `c=` 를 틀린 IP 로 바꿔 통화하고, RTP 가 어디서 막히는지 `docker logs rtpengine` 으로 확인하라.
- PyHSS 의 `ims_subscriber.ifc_path` 를 MESSAGE 트리거가 없는 iFC 로 바꾸고 SMS 를 보내라. 어떤 응답이 오는가? 끝나면 복구하라.

---

> **검증 상태**: CSCF 역할·Cx 명령·iFC 는 TS 23.228/29.228/29.229. UDP→TCP 전환은 RFC 3261 §18.1.1, 다이얼로그 Route set 은 §12.1.2, AKAv1-MD5 는 RFC 3310. 모든 코드·로그·캡처는 이 배포 실측. rtpengine latch 는 rtpengine 문서 기준.

*다음 장: 09. 실험실 구성 — 컨테이너·네트워크·설정 정본을 처음부터 세우는 순서*
