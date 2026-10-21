# 05. 5G 코어와 서비스 기반 구조: 조각들이 서로를 찾고 말하는 법

## 5.1 코어는 REST API 의 묶음이다

4 장에서 5G 코어가 "제어 평면을 역할별로 쪼갠 것"이라고 했다. 쪼갰으면 서로 말을 해야 한다. 그 말하는 방식이 이 장의 주제이고, 이름은 **SBI(Service Based Interface, 서비스 기반 인터페이스)**다. 이름이 거창하지만 뜻은 독자가 매일 하는 일이다.

각 조각(이제부터 **NF, Network Function** 이라 부른다)은 **HTTP/2 서버**가 되어 자기가 할 수 있는 일을 REST API 로 내놓는다. 다른 조각이 그 일이 필요하면 **HTTP/2 클라이언트**가 되어 호출한다. 응답은 JSON 이다. 그것이 전부다. 4G 의 Diameter 는 "A 와 B 사이에 전용 인터페이스를 정의한다"는 방식이었다. 인터페이스 하나마다 이름이 붙고, 그 이름이 곧 "누구와 누구 사이의 전용 선"이었다. S6a(4G 의 이동성 관리 서버가 가입자 DB 에 인증 정보를 묻는 선), Gx(정책 서버가 데이터 게이트웨이에 과금·품질 규칙을 내리는 선), Rx(IMS 가 정책 서버에 통화용 품질을 요청하는 선)처럼 말이다. 새 조각을 넣으려면 새 인터페이스를 정의해야 했다. 5G 는 "B 가 API 를 열어 두면 누구든 부른다"로 바꿨다. 그래서 구성도가 선으로 이어진 그림이 아니라 **버스**에 조각들이 매달린 그림으로 바뀌었다.

```
   AMF    SMF    PCF    AUSF    UDM    UDR    NSSF    BSF
    │      │      │      │       │      │      │       │
 ═══╧══════╧══════╧══════╧═══════╧══════╧══════╧═══════╧═══  SBI (HTTP/2, 이 배포에서는 TCP 7777)
                                 │
                                NRF  ← 전화번호부
```

우리 로그에 찍힌 경로를 보면 이것이 정말 REST 라는 것이 보인다.

```
/nsmf-pdusession/v1/sm-contexts/{smContextRef}/modify
/npcf-policyauthorization/v1/app-sessions
/nnrf-nfm/v1/nf-instances/{nfInstanceId}
```

경로의 첫 조각에 규칙이 있다. `n` 다음에 **그 API 를 제공하는 NF 의 이름**, 하이픈, 서비스 이름이다. `nsmf-pdusession` 은 "SMF 가 제공하는 PDU 세션 서비스"이고, `npcf-policyauthorization` 은 "PCF 가 제공하는 정책 인가 서비스"다. 경로만 보면 **누가 서버이고 누가 손님인지**를 안다. 첫 줄은 AMF 가 SMF 를 부른 것이고, 둘째 줄은 IMS 의 P-CSCF 가 PCF 를 부른 것이다. P-CSCF(Proxy Call Session Control Function)는 단말이 전화를 걸 때 처음 만나는 SIP 프록시이고, SIP 는 4 장에서 본 인터넷 전화의 호 설정 프로토콜이다. 와이어샤크 필터 `sip` 로 보면 HTTP 와 닮은 텍스트 요청·응답이다. 8 장에서 자세히 본다.

왜 하필 HTTP/2 인가. 코어는 초당 수만 건의 작은 요청을 주고받는다. HTTP/1.1 로 하면 요청 하나에 연결 하나를 잡거나, 한 연결에서 앞 요청이 끝날 때까지 뒤가 기다려야 한다(헤드오브라인 블로킹). HTTP/2 는 한 연결 안에 요청 수천 개를 **동시에** 흘릴 수 있고(멀티플렉싱), 매 요청마다 반복되는 헤더를 압축하며(HPACK), 서버가 먼저 알림을 보낼 수단이 있다. 코어의 요구에 정확히 맞는다. 본문은 JSON 이고 스키마는 **OpenAPI** 로 정의되어 있어서, 3GPP 사이트에서 YAML 파일을 받아 Swagger 로 열면 모든 코어 API 를 읽을 수 있다. 통신 표준이 소프트웨어 엔지니어의 도구로 읽히게 된 첫 세대다.

## 5.2 NRF: 조각들이 서로를 찾는 전화번호부

조각이 열 개이고 각자 컨테이너에서 따로 뜬다면, AMF 는 SMF 가 **어디 있는지** 어떻게 아는가. 설정 파일에 주소를 박아 둘 수도 있지만, 그러면 조각을 늘리거나 옮길 때마다 전부 고쳐야 한다. 5G 는 독자가 마이크로서비스에서 쓰는 것과 똑같은 답을 골랐다. **서비스 레지스트리**다. 그 이름이 **NRF(NF Repository Function)** 이고, Consul 이나 etcd, 쿠버네티스의 서비스 디스커버리와 같은 자리다.

동작은 세 단계이고, 세 단계가 전부 우리 로그에 있다.

실제 AMF 의 기동 로그(10월 13일 23:28 기동분, 시각과 소스 위치는 줄였다)로 따라간다.

```
11.285  Setup NF EndPoint(addr) [172.22.0.12:7777]      ← NRF
11.285  Setup NF EndPoint(addr) [172.22.0.35:7777]      ← SCP
11.287  [5151d970-…] NF registered [Heartbeat:10s]
11.289  [5120ef54-…] (NRF-profile-get) NF registered
11.289  [UDM] NFInstance associated [5120ef54-…]
11.289  Setup NF EndPoint(addr) [172.22.0.13:7777]      ← UDM
11.289  [nudm-ueau] NFService associated [5120f6d4-…]
11.289  [nudm-uecm] NFService associated [5120f792-…]
```

첫 두 줄이 이 구조의 출발점이다. AMF 가 기동할 때 **설정 파일로 아는 주소는 NRF(.12)와 SCP(.35) 둘뿐**이다. 다른 조각의 주소는 전부 여기서부터 알아낸다.

첫째는 **등록**이다. 셋째 줄의 `NF registered [Heartbeat:10s]` 는 AMF 자신이 NRF 에 "나는 AMF 이고 주소는 이것이며 이런 서비스를 제공한다"는 **프로파일**을 올리고 등록된 것이다(`PUT /nnrf-nfm/v1/nf-instances/{자기 UUID}`). `Heartbeat:10s` 는 10 초마다 살아 있다고 알리겠다는 약속이다. 알림이 끊기면 NRF 는 그 NF 를 목록에서 지운다.

둘째는 **구독**이다. 각 NF 는 "UDM 이 새로 생기거나 바뀌거나 죽으면 나에게 알려 달라"고 NRF 에 구독을 건다. 변화가 생기면 NRF 가 **콜백**으로, 즉 구독자의 URI 를 HTTP/2 로 호출해서 알린다. 로그에 `(NRF-notify)` 가 붙은 줄이 그 콜백이 온 순간이다.

셋째는 **발견과 연결**이다. 넷째 줄 `(NRF-profile-get) NF registered` 는 AMF 가 NRF 에서 UDM 의 프로파일을 받아 왔다는 뜻이고(발견. 일반형은 `GET /nnrf-disc/v1/nf-instances?target-nf-type=UDM&requester-nf-type=AMF`), 다섯째 줄 `[UDM] NFInstance associated` 가 "UDM 은 이 인스턴스다"라고 묶은 순간, 여섯째 줄이 그 주소(.13), 마지막 두 줄이 그 UDM 이 제공하는 서비스 두 개(`nudm-ueau` 인증 벡터, `nudm-uecm` 등록 관리)를 묶은 순간이다. 9 장의 `wait_core_ready` 가 기다리는 줄이 바로 이 `NFInstance associated` 다. 그 뒤로는 NRF 를 거치지 않고 직접 부른다. NRF 는 **길을 알려 주는 곳**이지 모든 요청이 지나는 곳이 아니다.

이 구조가 우리 운영 절차 하나를 설명한다. 코어를 기동한 직후에는 등록이 아직 끝나지 않아 AMF 가 SMF 를 찾지 못한다. 그 순간에 단말이 등록을 시도하면 거절된다. 그래서 우리 기동 스크립트의 `wait_core_ready` 는 **AMF 의 로그에 핵심 NF 다섯 개(AUSF·UDM·PCF·SMF·NSSF)의 `NFInstance associated` 가 다 찍힐 때까지** 기다렸다가 "코어 준비 완료 (NF 5/5, 10초)" 를 찍는다(9.7). 쿠버네티스의 readiness probe 와 같은 역할이다. 이것을 생략하면 "가끔 첫 단말이 안 붙는" 현상을 쫓게 된다.

NRF 곁에 조연이 둘 있다. **SCP(Service Communication Proxy)** 는 NF 사이에 끼어들 수 있는 API 게이트웨이다. 라우팅, 부하 분산, 재시도를 대신해 준다. 서비스 메시의 사이드카 프록시와 같은 자리이고, 우리 배포에도 `scp` 컨테이너가 있다. **BSF(Binding Support Function)** 는 아주 작은 조회 서비스인데, "단말 IP `10.45.0.6` 의 세션은 **어느 PCF** 가 담당하고 있나"를 기억한다. 이것이 필요한 이유는 8 장에서 나온다. IMS 의 P-CSCF 가 통화 QoS 를 요청하려면 그 단말의 PCF 를 찾아야 하는데, P-CSCF 는 코어 바깥(4G 유산)에 있어서 SMF 의 내부 상태를 모른다. 그래서 BSF 에 IP 로 묻는다.

🔎 지금 당신의 장비에서. NRF 가 전화번호부 노릇을 했는지는 AMF 쪽 로그 한 줄로 안다.

```bash
docker logs amf 2>&1 | grep -c 'NFInstance associated'     # 5 가 나와야 한다
```

다섯이 안 되면 조각 하나가 아직 등록하지 못한 것이고, 그 상태로 단말을 붙이면 9.7 절의 `504` 를 만난다. **컨테이너가 떴다는 것과 망이 준비됐다는 것은 다르다.**

## 5.3 단말 하나가 붙을 때 코어 안에서 일어나는 일

이 장에서 가장 중요한 그림이다. 모뎀에서 `AT+CFUN=1` 을 친 순간부터(CFUN 은 functionality 의 줄임으로, 모뎀 무선부의 전원 스위치다. `1` 이 켬, `0` 이 끔이고 13 에서 다시 본다) `+C5GREG: 1` 이 뜰 때까지, 코어 조각들이 **어떤 순서로 누구를 부르는지**를 AMF 로그와 함께 따라간다. 이 순서를 알면 어디서 멈췄는지를 로그 한 줄로 짚을 수 있다.

```
 UE         gNB        AMF         AUSF       UDM/UDR      SMF       UPF       PCF
 │─RRC 연결─▶│                                                              
 │─NAS Registration Request (SUCI)─▶│                                       
 │           │ N2 InitialUEMessage  │                                       
 │           │                      │─인증 요청─▶│                            
 │           │                      │            │─벡터 요청─▶│  RAND·AUTN 생성 
 │           │                      │◀─RAND, AUTN, HXRES─│◀────────────────│
 │◀─NAS Authentication Request (RAND, AUTN)─│                               
 │ [SIM 이 MILENAGE 계산, AUTN 검증]         │                               
 │─NAS Authentication Response (RES*)─────▶│                               
 │           │                      │─RES* 검증─▶│                          
 │◀─NAS Security Mode Command ───────────────│  (이후 NAS 는 암호화·무결성 보호) 
 │─Security Mode Complete──────────────────▶│                               
 │           │                      │─UDM 에 등록·가입정보 조회──────▶│         
 │◀─NAS Registration Accept ─────────────────│  ← 모뎀에 +C5GREG: 1 이 뜨는 순간 
 │─Registration Complete───────────────────▶│                               
 │─NAS PDU Session Establishment Request──▶│                               
 │           │                      │─CreateSMContext (REST)──────────▶│      
 │           │                      │                                  │─정책─▶│
 │           │                      │                                  │─N4 PFCP─▶│
 │           │                      │                                  │ IP 할당   
 │◀─NAS PDU Session Accept (IP, DNS, QoS)─│◀─────────────────────────│      
 │           │◀─N2 PDU Session Resource Setup (GTP 터널 정보)─│              
 │═══ 데이터 (N3 GTP-U) ═══▶│═══════════════════════════════════════════▶│═══▶ 인터넷
```

이 그림을 AMF 로그 한 줄씩에 대응시키면 이렇다.

가장 먼저 `gNB-N2 accepted[172.22.0.37]` 가 찍힌다. 기지국이 SCTP 로 AMF 에 붙은 것이고, 단말과 무관하게 기지국이 뜰 때 한 번 일어난다. 그 다음 단말이 전파로 기지국에 RRC 연결을 맺고 첫 NAS 메시지를 보내면, 기지국이 그것을 N2 에 담아 보내고 AMF 가 `InitialUEMessage` 를 찍는다.

바로 뒤에 `RAN_UE_NGAP_ID[0] AMF_UE_NGAP_ID[1] TAC[1] CellID[0x66c000]` 가 나온다. 이 줄은 두 가지를 말한다. 하나는 이 단말이 어느 셀(0x66c000. 이 번호가 16 의 NCI(NR Cell Identity), 즉 망 전체에서 셀 하나를 가리키는 36 비트 번호다)의 어느 추적 영역(TAC 1)에서 왔는가. 다른 하나는 기지국과 AMF 가 이 단말을 부를 **임시 번호**를 각각 하나씩 정했다는 것이다. 기지국은 0 번, AMF 는 1 번이라 했다. 왜 번호가 둘인가. TCP 가 양쪽 포트 번호를 쓰는 것과 같은 이유다. 한쪽 번호만 쓰면 한쪽이 재시작하거나 핸드오버가 일어날 때 충돌한다. 그리고 여기에 **IMSI 가 없다**는 것이 중요하다. N2 에서 단말은 임시 번호로만 불린다. 4 장의 "기지국은 가입자를 모른다"가 로그에서 보이는 자리다.

그 다음 `[suci-0-001-01-0-0-0-1234567895] Unknown UE by SUCI` 가 찍힌다. 단말이 자기를 **SUCI** 라는 형식으로 밝혔고(6장), AMF 는 이 SUCI 를 처음 본다는 뜻이다. **이것은 오류가 아니다.** 처음 보는 단말이면 당연히 모른다. 이 로그를 보고 "등록이 실패했다"고 오해하는 사람이 많은데, 바로 다음 줄이 `Registration request` 이고 절차는 정상 진행 중이다.

인증 왕복(AUSF, UDM 과의 대화)은 AMF 로그에 자세히 찍히지 않는다. 6 장에서 따로 본다. 인증이 끝나면 `[imsi-001011234567895] Registration complete` 가 찍힌다. 주목할 점은 **이제 SUCI 가 아니라 IMSI 로 찍힌다**는 것이다. 인증이 통과해서 망이 이 단말의 진짜 신원을 확정했다는 표시다. 그 다음 `Configuration update command` 는 망이 단말에게 추적 영역 목록 같은 설정을 내린 것이다.

이어서 단말이 세션을 요청한다. 이때 AMF 가 찍는 줄에는 처음 보는 칸 이름이 여럿 있으니 먼저 이름부터 푼다. SUPI(Subscription Permanent Identifier)는 5G 에서 가입자의 영구 ID 이고, SIM 가입자라면 `imsi-` 접두어를 붙인 IMSI 그대로다. DNN(Data Network Name)은 4G 의 APN 과 같은 것으로, 단말이 어느 데이터망(`internet`, `ims`)에 붙고 싶은지를 적은 이름이다. LBO(Local Breakout)는 로밍 중일 때 방문한 망에서 곧바로 인터넷으로 내보낼지를 뜻하는 플래그이고, 집 망인 우리는 `0` 이다. `S_NSSAI` 는 이 세션이 어느 **망 슬라이스**(같은 코어를 용도별로 나눈 논리 망)에 속하는지를 고르는 값으로 두 칸이 있다. SST(Slice/Service Type)는 슬라이스 종류로 `1` 이 일반 모바일 브로드밴드이고, SD(Slice Differentiator)는 같은 종류 안의 구분자로 `0xffffff` 가 "구분 없음"이다. 이 이름들을 알고 나면 `UE SUPI[imsi-…895] DNN[ims] LBO[0] S_NSSAI[SST:1 SD:0xffffff] smContextRef[NULL]` 는 "이 단말이 `ims` 라는 데이터망으로, 기본 슬라이스에서 세션을 원하는데 아직 SMF 쪽 세션 객체(`smContextRef`)가 비어 있다"로 읽힌다. AMF 는 SMF 의 REST 를 부른다. 세션을 새로 만드는 호출은 `POST /nsmf-pdusession/v1/sm-contexts` 이고, SMF 가 만든 세션 객체의 주소(`smContextRef`)를 돌려준다. 그 뒤 기지국이 터널 준비를 마쳤다는 등 세션 상태가 바뀔 때마다 AMF 가 `POST /nsmf-pdusession/v1/sm-contexts/{ref}/modify` 로 알린다. 앞 절의 경로 목록에 있던 `…/modify` 가 그것이다. SMF 가 IP 를 할당하면 SMF 로그에 `UE SUPI[…] DNN[internet] IPv4[10.45.0.3]` 이 찍힌다. UPF 쪽 로그는 F-SEID(Fully qualified Session Endpoint ID)로 세션을 부른다. F-SEID 는 UPF 와 SMF 사이 제어 프로토콜(PFCP)의 세션 번호이고, 양쪽이 하나씩 붙이므로 UP(User Plane, 즉 UPF 쪽이 붙인 번호)와 CP(Control Plane, 즉 SMF 쪽이 붙인 번호) 두 칸이다. 그 줄이 `UE F-SEID[UP:0x770 CP:0x392] APN[internet]` 이다. 7 장에서 이 부분을 자세히 본다.

마지막으로 `UE Context Release [Action:2]` 가 등록 몇 초 뒤에 찍힌다. 이것도 오류가 아니다. 단말이 데이터를 보내지 않으면 망은 무선 연결(RRC)을 놓아서 전파와 배터리를 아낀다. 단말은 등록된 채로 IDLE 상태가 된다. 16 에서 볼 Quectel 모뎀의 `AT+QENG` 응답에 NOCONN(no connection — 등록은 되어 있지만 무선 연결은 없다는 뜻)으로 뜨는 상태가 이것이다. 데이터가 생기면 다시 연결한다.

## 5.4 NAS: 기지국이 열어 보지 못하는 봉투

4 장에서 "NAS 는 기지국을 투명하게 지난다"고 했다. 여기서 정확히 하자. 단말과 기지국 사이의 대화를 **AS(Access Stratum)** 라 하고, 단말과 **코어** 사이의 대화를 **NAS(Non-Access Stratum)** 라 한다. AS 는 RRC 라는 프로토콜로 무선 연결을 관리한다. NAS 는 등록, 인증, 세션 같은 "코어의 일"이다.

NAS 메시지는 RRC 메시지 안에 **바이트 덩어리**로 실려 간다. 기지국은 그 덩어리를 N2 의 NGAP 메시지에 그대로 옮겨 담아 AMF 로 보낸다. 내용을 해석하지 않는다. 그리고 위 그림의 `Security Mode Command` 이후에는 NAS 가 **암호화와 무결성 보호**를 받으므로, 기지국이 열어 보려 해도 볼 수 없다. 6 장의 키 계층에서 기지국은 NAS 키를 받지 않는다.

NAS 는 다시 **두 층**이다. **5GMM(Mobility Management)** 은 AMF 와의 대화로, 등록·인증·보안·위치를 다룬다. 우리 로그의 `[gmm]` 접두어가 이것이다. **5GSM(Session Management)** 은 SMF 와의 대화로, PDU 세션을 만들고 바꾸고 없앤다. `[gsm]` 접두어다. 그런데 단말은 SMF 와 직접 연결이 없다. 5GSM 메시지도 AMF 를 거친다. 이때 **AMF 는 5GSM 의 내용을 열어 보지 않고 SMF 로 전달만 한다.** 위에서 본 `sm-contexts/…/modify` 호출이 그 전달이다. 즉 "열어 보지 않고 넘기는" 층이 기지국에 한 번, AMF 에 한 번, 두 겹으로 있다. 조각마다 **자기 일만 본다**는 원칙이 끝까지 가는 것이다.

## 5.5 우리 배포의 컨테이너 26 개를 지도에 놓기

`docker ps` 에 나온 이름을 전부 분류한다. 모르는 이름이 하나도 없어야 한다. 묶어 보면 네 덩어리다.

**5G 코어의 제어 조각**이 열 개다. 전화번호부 `nrf`, API 프록시 `scp`, 출입국 관리 `amf`(SCTP 38412 에서 기지국을 받는다), 인증 셋 `ausf`·`udm`·`udr`, 세션 `smf`, 정책 셋 `pcf`·`bsf`·`nssf`. 전부 TCP 7777 에서 HTTP/2 를 듣는다. **사용자 평면**은 `upf` 하나이고, 그 안에 `ogstun` 이라는 TUN 인터페이스가 단말 IP 대역의 게이트웨이(10.45.0.1)로 서 있다.

**저장소**가 둘이다. `mongo` 는 5G 코어의 가입자 DB 이고 UDR 이 이것을 읽는다. `mysql` 은 IMS 쪽 DB 로, PyHSS 와 CSCF 들이 쓴다. CSCF(Call Session Control Function)는 IMS 의 SIP 프록시들을 통틀어 부르는 이름이고, 앞에 붙는 P·I·S 한 글자로 역할이 갈린다(8장). 가입자 DB 가 **둘**이라는 점을 기억하라. 4G 유산(IMS)과 5G 가 공존하는 모습이고, 그래서 가입자를 추가할 때 양쪽에 넣어야 했다.

**IMS** 가 일곱 개다. SIP 프록시 셋 `pcscf`·`icscf`·`scscf`, 가입자·인증 `pyhss`(Diameter 3875), 문자 센터 `smsc`, 음성 중계 `rtpengine`, 그리고 내부 DNS `dns`(bind). 8 장에서 전부 만난다.

**관리와 관측**으로 `webui`(가입자 입력 화면, 9999), `grafana`(3000), `metrics`(9090) 가 있다. 그리고 env 파일에는 4G 코어 조각(`hss`, `pcrf`, `mme`, `sgwc`, `sgwu`) 주소도 있지만 우리는 띄우지 않았다. 마지막으로 **RAN** 쪽에 실장비 기지국 `srsgnb`, 시뮬레이션 기지국 `oaignb_rfsim`, 소프트 단말 `oainrue` 가 있다.

세어 보면 **제어 10, 사용자 1, 저장소 2, IMS 7, 관측 3** 으로 compose 파일이 정의하는 것이 23 개이고, 거기에 **RAN 3** 을 더해 26 개다(RAN 의 둘은 시뮬레이션용이라 실장비 시험 때는 띄우지 않는다. `configs/compose/sa-vonr-deploy.yaml` 의 `container_name` 을 세면 23 이 나온다). 많아 보여도 각자 한 가지 일만 한다. 이름을 보고 어느 덩어리인지 바로 말할 수 있으면 이 절은 끝난 것이다.

## 5.6 설정의 정본은 한 곳이다

컨테이너마다 설정 파일이 있다. `amf.yaml`, `smf.yaml`, `upf.yaml`, `gnb.yml` 등이다. 그런데 그 안의 주소, PLMN, TAC, IP 대역은 **전부 `.env` 한 파일에서** 온다. 각 컨테이너의 기동 스크립트가 설정 파일의 플레이스홀더(`AMF_IP`, `MCC`, `PLMN`, `UE_IPV4_INTERNET_APN_SUBNET` …)를 env 값으로 `sed` 치환한다. 10 장에서 볼 `srsran_init.sh` 가 기지국 설정의 `PLMN` 을 `001`+`01` 로 바꾸는 것이 같은 방식이다.

이 구조에서 운영 원칙 하나가 나온다. **설정을 바꿀 때는 `configs/env/env` 한 곳을 고치고 `deploy-configs.sh` 로 배포한다. 컨테이너 안의 파일을 직접 고치면 재기동 때 사라진다.** 우리가 단말 IP 대역을 `192.168.100.0/24` 에서 `10.45.0.0/16` 으로 바꾼 것은 env 두 줄(`UE_IPV4_INTERNET`, `UE_IPV4_IMS`)이었고, `ip_utils.py` 가 거기서 서브넷과 게이트웨이를 파생시켜 `smf.yaml` 과 `upf.yaml` 에 넣었다. 반면 DNS 존의 A 레코드는 급해서 컨테이너 안에서 먼저 고쳤고, 그 뒤 클론의 `dns/ims_zone` 에 반영했고, 마지막으로 정본 `configs/dns/ims_zone` 과 배포 매핑에 올렸다(부록 C). 세 단계를 다 거치기 전까지는 사라질 수 있는 수정이었다. 13 장의 사례 하나가 이것이다.

## 5.6a 패킷 해부: NAS 메시지의 머리

TCP 헤더를 비트 단위로 그려 놓고 플래그를 하나씩 설명하듯, 이 책의 프로토콜도 그렇게 본다. 등록 때 단말이 보낸 NAS 메시지는 기지국이 열어 보지 못하는 봉투라고 했다. 그 봉투의 겉면이 이렇게 생겼다 (TS 24.501).

```
 바이트  0                   1                   2
        +-------------------+-------------------+-------------------+
 평문   | 확장 프로토콜 식별자 | 여유 | 보안 헤더 종류 | 메시지 종류        |  ← 5GMM 평문 메시지 (3 바이트 머리)
 NAS    |   EPD = 0x7E      | 0000 |   0000      |  0x41 등          |
        |                   | 상위 4비트 | 하위 4비트 |                   |
        +-------------------+-------------------+-------------------+
        | 그 다음부터 메시지 종류별 정보 요소(IE) 들이 TLV 로 이어진다        |
```

| 필드 | 크기 | 뜻 | 값 읽기 |
|---|---|---|---|
| **EPD** (Extended Protocol Discriminator) | 8 bit | 이 메시지가 어느 층의 것인가 | `0x7E` = 5GMM (AMF 와의 대화), `0x2E` = 5GSM (SMF 와의 대화). 5.4절의 두 층이 첫 바이트 하나로 갈린다 |
| **보안 헤더 종류** | 4 bit | 보호되었는가 | `0` 평문 / `1` 무결성만 / `2` 무결성+암호화 / `3`,`4` 는 새 보안 컨텍스트로 보호 |
| 여유 | 4 bit | 0 | |
| **메시지 종류** | 8 bit | 무슨 메시지인가 | 아래 표 |

5GMM 메시지 종류 중 등록에 나오는 것들이다. 와이어샤크 필터 `nas-5gs.mm.message_type == 0x41` 처럼 쓴다.

| 값 | 메시지 | 방향 | 5.3절 그림의 자리 |
|---|---|---|---|
| `0x41` | Registration request | 단말→AMF | 첫 메시지. SUCI 가 여기 들어 있다 |
| `0x42` | Registration accept | AMF→단말 | 모뎀에 `+C5GREG: 1` 이 뜨는 순간 |
| `0x43` | Registration complete | 단말→AMF | |
| `0x44` | Registration reject | AMF→단말 | 거절 사유 코드가 함께 온다 |
| `0x56` | Authentication request | AMF→단말 | RAND(망이 뽑은 128 bit 난수), AUTN(망이 진짜라는 증명 토큰). 6장 |
| `0x57` | Authentication response | 단말→AMF | RES\*. RES 는 RESponse 의 줄임으로, 카드가 계산한 답이다 |
| `0x5D` | Security mode command | AMF→단말 | 이 뒤부터 보안 헤더 종류가 1 이상 |
| `0x5E` | Security mode complete | 단말→AMF | |
| `0x67` | UL NAS transport | 단말→AMF | 5GSM 메시지를 **싸서** 나르는 봉투. UL 은 uplink, 단말→망 방향이다 |
| `0x68` | DL NAS transport | AMF→단말 | DL 은 downlink, 즉 반대 방향이다 |

마지막 두 줄이 5.4절의 "AMF 는 5GSM 을 열어 보지 않고 전달한다"의 패킷 모습이다. 세션 요청(5GSM `0xC1`)은 5GMM 의 `UL NAS transport` 안에 **페이로드로** 들어가 있고, AMF 는 그 페이로드를 꺼내 SMF 에 넘긴다. 봉투 안에 봉투가 있는 것이다.

보안 모드 이후의 메시지는 겉이 하나 더 생긴다.

```
        +-------------------+-------------------+-------------------+-------------------+
 보호된 | EPD = 0x7E        | 보안 헤더 종류 = 2 | 여유 |                                   |
 NAS    +-------------------+-------------------+-------------------+-------------------+
        |                    메시지 인증 코드 MAC (32 bit)                                 |
        +-------------------+---------------------------------------------------------------+
        | 일련번호 (8 bit)   |  ← 여기부터 암호화된 평문 NAS (위 3 바이트 머리 + IE 들)          |
        +-------------------+---------------------------------------------------------------+
```

**MAC** 은 6 장의 K_NASint 로 만든 무결성 서명이고, **일련번호**는 재생 방지용 카운터다. 그 뒤가 K_NASenc 로 암호화된 원래 메시지다. 와이어샤크는 이 지점부터 `Ciphered message` 라고만 표시한다. 기지국도 같은 처지다 — 키가 없다.

5GSM 쪽 머리는 두 바이트가 더 있다.

```
        +-------------------+-------------------+-------------------+-------------------+
 5GSM   | EPD = 0x2E        | PDU 세션 ID (8)    | 절차 트랜잭션 ID PTI (8) | 메시지 종류 (8) |
        +-------------------+-------------------+-------------------+-------------------+
```

**PDU 세션 ID** 는 단말이 세션에 붙인 번호(1~15)다. 모뎀의 `+CGDCONT` 프로파일 번호와 흔히 같게 잡히지만 표준이 둘을 같은 번호로 묶지는 않는다 [검증 필요: 우리 모뎀에서 cid 와 PDU 세션 ID 대조]. **PTI** 는 요청과 응답을 짝 맞추는 번호다. 메시지 종류 `0xC1` 이 PDU session establishment request, `0xC2` 가 accept, `0xC3` 가 reject 다. 7 장의 IP 할당 결과가 `0xC2` 의 정보 요소 안에 들어 있다.

## 5.6b 와이어샤크로 보기

호스트에서 `tcpdump -i br-b33ecd87724d -w reg.pcap` 를 켠 채 모뎀을 `AT+CFUN=0` → `AT+CFUN=1` 하면 등록 전 과정이 한 파일에 담긴다. 와이어샤크로 열고 필터 `ngap` 을 치면 5.3절의 그림이 그대로 나온다. `InitialUEMessage` 를 펼치면 그 안에 `NAS-PDU` 가 있고(NAS-PDU 는 NGAP 메시지에 통째로 실린 NAS 메시지 바이트다. PDU, Protocol Data Unit 은 한 층이 주고받는 메시지 한 덩어리를 부르는 말이다), 와이어샤크가 그것을 `nas-5gs` 로 다시 해석해서 위 표의 `0x41 Registration request` 와 그 안의 SUCI 필드까지 보여 준다. `0x56 Authentication request` 의 RAND 와 AUTN 도 바이트로 보인다. `0x5D Security mode command` 이후 NAS 는 `Ciphered` 로 표시되고 내용이 안 보인다 — 6 장의 키 계층이 작동한 자리다. 필터를 `http2` 로 바꾸면 같은 시간대에 AMF 가 SMF 를 부른 `POST /nsmf-pdusession/v1/sm-contexts` 와 JSON 본문이 보인다. 두 필터를 번갈아 보면 "단말이 보낸 한 메시지가 코어 안에서 REST 몇 번으로 번지는지"가 눈에 들어온다.

🔎 지금 당신의 장비에서. SBI 가 정말 HTTP/2 인지 패킷으로 확인한다.

```bash
sudo tcpdump -i <브리지> -n -A -c 40 'tcp port 7777' | grep -i -m5 ':path\|:status\|nnrf\|namf'
```

`:path` 와 `:status` 는 HTTP/2 의 의사 헤더(pseudo-header)다. REST 경로가 `/nnrf-nfm/...`, `/namf-comm/...` 처럼 **조각 이름으로 시작**하는 것이 보이면 5.1 절의 "코어는 REST API 의 묶음"이 그대로 확인된 것이다. 와이어샤크를 쓸 수 있으면 표시 필터 `http2` 가 더 편하다(5.6b).

## 5.7 이 장의 요약

| 질문 | 답 |
|---|---|
| SBI 란 | 각 NF 가 HTTP/2 REST 서버. 경로 `n<제공NF>-<서비스>/v1/…` 로 누가 서버인지 안다 |
| 왜 HTTP/2 | 멀티플렉싱·헤더 압축·콜백. 초당 수만 건의 작은 요청에 맞다. OpenAPI 로 공개 |
| NRF | 서비스 레지스트리. 등록 → 구독(콜백) → 발견·직접 연결. `NF registered`, `NFInstance associated` |
| SCP / BSF | API 프록시 / "이 단말 IP 는 어느 PCF" 조회 |
| 등록 순서 | RRC → NAS 등록(SUCI) → 인증 → 보안 모드 → 등록 수락 → PDU 세션(SMF·PCF·UPF) |
| `Unknown UE by SUCI` | 오류 아님. 처음 보는 단말 |
| 임시 번호 둘 | RAN_UE_NGAP_ID / AMF_UE_NGAP_ID. N2 에 IMSI 는 없다 |
| NAS 두 층 | 5GMM(AMF, `[gmm]`) / 5GSM(SMF, `[gsm]`). AMF 는 5GSM 을 열지 않고 전달 |
| `UE Context Release` | 정상. 데이터 없으면 RRC 를 놓고 IDLE 로 |
| 설정 정본 | `.env` 한 곳 → 플레이스홀더 치환. 컨테이너 안 직접 수정 금지 |

## 점검 문제

1. `/npcf-policyauthorization/v1/app-sessions` 를 부르는 쪽과 받는 쪽을 말하고, 그 호출이 언제 일어나는지 8 장을 읽기 전에 추측하라.
2. NRF 가 죽으면 **이미 연결된** AMF–SMF 통신은 끊기는가? 새 단말의 등록은 어떻게 되는가?
3. `Unknown UE by SUCI` 다음에 `Registration complete` 가 IMSI 로 찍히는 이유를 인증 흐름으로 설명하라.
4. AMF 가 5GSM 메시지를 열어 보지 않는 설계의 이점을 두 가지 들라.
5. 기동 직후 `wait_core_ready` 를 생략하면 어떤 증상이 생기고 왜 "가끔"인가?
6. 컨테이너 안에서 `smf.yaml` 을 직접 고쳐 IP 대역을 바꿨다. 무엇이 문제인가?

---

*다음 장: 06. 가입자 식별과 인증 — SUCI 가 IMSI 를 숨기는 법, MILENAGE 를 바이트로, 그리고 우리가 "망 인증 OK" 를 찍은 계산*
