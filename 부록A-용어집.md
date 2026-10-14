# 부록 A. 용어집

이 책에 나온 용어를 한곳에 모았다. 각 항목은 **무엇인가**를 한두 문장으로 말하고, 측정값이면 **단위와 대략의 좋은 값**, 그리고 **이 실험실에서 어디서 보이는가**와 **자세한 장**을 단다. 본문에서 처음 나온 자리에 더 긴 설명이 있으니, 여기서 막히면 화살표의 장으로 간다. 좋은 값의 범위는 업계에서 흔히 쓰는 어림값이지 표준이 정한 경계가 아니다.

영문 약어는 알파벳순, 우리말 용어는 그 뒤에 가나다순으로 둔다. 같은 개념의 4G 이름과 5G 이름이 다르면 둘 다 싣고 서로 가리킨다.

---

## 숫자

**3GPP** (3rd Generation Partnership Project) — 휴대전화 표준을 만드는 국제 협의체. 3G 때 만들어졌지만 4G·5G 표준도 여기서 나온다. 문서 번호 `TS 38.xxx` 는 5G 무선, `TS 23/24/29.xxx` 는 코어 구조·절차·API 다. → 3, 4장

**5GC** (5G Core) — 5G 코어망 전체. AMF, SMF, UPF 등 조각들의 묶음. 우리 배포에서는 Open5GS 컨테이너 열한 개. → 5장

**5GMM / 5GSM** (5G Mobility Management / Session Management) — NAS 메시지의 두 갈래. 5GMM 은 등록·인증·보안처럼 "단말이 망에 있는가", 5GSM 은 PDU 세션처럼 "데이터 통로가 있는가"를 다룬다. NAS 헤더의 첫 바이트(EPD)로 구분한다. → 5.6a

**5QI** (5G QoS Identifier) — 트래픽의 품질 등급 번호. 1 = 대화형 음성(GBR), 2 = 대화형 영상(GBR), 5 = IMS 시그널링, 9 = 일반 인터넷(기본값). 4G 의 QCI 와 같은 표. 우리 통화가 성립하려면 IMS 세션이 5, 음성 PCC 규칙이 1, 영상이 2 여야 했다. → 7.8, 8장, 13장

**8N1** — 시리얼 통신의 가장 흔한 틀. 데이터 8비트, 패리티 없음(None), 정지 비트 1. 한 글자 앞뒤에 시작·정지 비트가 붙어 10비트가 된다. → 11a

## A

**ACK** (Acknowledgement) — 받았다는 확인. TCP 의 그것과 같은 뜻이고, 무선 쪽에서는 HARQ 의 ACK/NACK 가 있다. TDD 에서는 하향 TCP 의 ACK 가 상향 슬롯을 기다려야 해서 하향 속도를 묶는다. → 3, 7장

**ADC / DAC** (Analog-to-Digital / Digital-to-Analog Converter) — 전압을 숫자로, 숫자를 전압으로 바꾸는 부품. 사운드카드에 있는 그것. B210 은 12비트. → 2장

**ADM1** (Administrative key 1) — SIM 의 관리자 비밀번호. 가입자 데이터(IMSI, 키)를 쓸 때 필요하다. 틀린 횟수가 다 차면 **복구할 방법이 없다**. 카드 제조사가 카드별로 준다. → 4a장

**AKA** (Authentication and Key Agreement) — 망과 SIM 이 같은 비밀키를 가졌음을 서로 증명하고 세션 키를 나눠 갖는 절차. 챌린지-응답이다. → 6장

**AKAv1-MD5** — IMS 등록에서 AKA 결과를 HTTP Digest 인증에 끼워 넣은 방식. SIP `401 Unauthorized` 의 `WWW-Authenticate` 헤더에 RAND·AUTN 이 들어간다. → 8장

**AMF** (Access and Mobility Management Function) — 5G 코어의 출입국 관리소. 기지국과 N2(NGAP)로 말하고, 등록·인증·이동 관리를 한다. 4G 의 MME 에 해당. `amf` 컨테이너, SCTP 38412. → 5장

**AMF 필드** (Authentication Management Field) — AKA 의 AUTN 안에 들어가는 16비트 값. 위의 AMF(코어 조각)와 이름만 같다. 우리 가입자는 `8000`. → 6장

**APDU** (Application Protocol Data Unit) — SIM 카드와 주고받는 메시지 단위. `CLA INS P1 P2 [Lc 데이터] [Le]` → 응답 데이터 + SW1 SW2. ISO 7816-4. → 4a장

**APN** (Access Point Name) — 단말이 어느 데이터 망으로 나갈지 고르는 이름. 4G 용어. 5G 의 DNN. 우리 값 `internet`, `ims`. → 7장, 11c

**ARFCN** (Absolute Radio Frequency Channel Number) — 주파수를 정수로 부르는 번호. 와이파이의 채널 번호와 같은 역할. 5G 는 NR-ARFCN 이라 하고 3~24 GHz 구간에서 F = 3000 MHz + 15 kHz × (N − 600000). 우리 `dl_arfcn=623334` 는 3350.01 MHz. 엔지니어 모드에 그대로 뜬다. → 3, 10.6, 11f

**ARP** (Allocation and Retention Priority) — QoS 의 자원 할당·선점 우선순위. 네트워크의 ARP(주소 해석)와 이름만 같다. → 7장

**AT 명령** — 모뎀에게 글자로 내리는 명령. `AT` 로 시작한다(ATtention). 1층 V.250 기본 명령, 2층 3GPP 27.007/27.005, 3층 제조사(`+Q…`), 4층 비공개. → 11a~11c

**ATR** (Answer To Reset) — SIM 에 전원이 들어오면 카드가 먼저 내놓는 바이트열. 지원 속도·규약을 알린다. → 4a장

**AUSF** (Authentication Server Function) — 5G 코어에서 인증 판정을 하는 조각. UDM 이 만든 벡터로 단말의 응답(RES*)을 검사한다. → 5, 6장

**AUTN** (Authentication Token) — 망이 단말에게 보내는 "나는 진짜 망이다" 증명. SQN 과 MAC 을 담는다. SIM 이 이것을 검사해 가짜 망을 거부한다. → 6장

**AVP** (Attribute-Value Pair) — Diameter 메시지의 필드 단위. 코드·플래그·길이·값의 TLV 구조. → 8장

## B

**B210** — Ettus Research 의 USB SDR. 70 MHz~6 GHz, 2×2, 12비트, 최대 56 MHz 대역폭. 우리 것은 LibreSDR 호환판. → 2, 9, 10장

**BCD** (Binary-Coded Decimal) — 십진 숫자 하나를 4비트(니블)에 넣는 표기. SIM 과 SMS 의 번호는 두 자리씩 니블을 **뒤집어** 넣는다(`82 10` → `28 01`). → 4a, 11c

**BLER** (Block Error Rate) — 무선으로 보낸 전송 블록 가운데 한 번에 복호되지 못한 비율. 스케줄러는 보통 첫 전송 BLER 10% 근처를 목표로 MCS 를 고른다. 0 에 가까우면 MCS 를 더 올릴 여지가 있다는 뜻. → 11f

**BSF** (Binding Support Function) — "이 단말 IP 의 세션은 어느 PCF 가 맡는가"를 기억하는 조회 서비스. P-CSCF 가 통화 정책을 요청할 PCF 를 찾을 때 쓴다. → 5, 8장

## C

**CA** (Carrier Aggregation) — 여러 주파수 묶음을 동시에 써서 속도를 더하는 기술. 우리 셀은 하나뿐이라 해당 없음. → 11f

**CK / IK** (Cipher Key / Integrity Key) — AKA 가 끝나면 SIM 과 망이 각자 계산해 갖는 128비트 키 둘. 여기서 5G 키 계층(K_AUSF → K_SEAF → K_AMF → K_gNB …)이 파생된다. → 6장

**CQI** (Channel Quality Indicator) — 단말이 "지금 채널이면 이 정도 변조까지 받을 수 있다"고 기지국에 보고하는 0~15 의 숫자. 기지국이 MCS 를 고르는 근거. 높을수록 좋다. → 11f

**CSCF** (Call Session Control Function) — IMS 의 SIP 프록시 셋. P-(단말 쪽 관문), I-(도메인 입구, 담당 S 찾기), S-(실제 등록·라우팅). 우리 `pcscf`, `icscf`, `scscf`(Kamailio). → 8장

**CU / DU** (Central Unit / Distributed Unit) — 5G 기지국을 상위 계층(CU)과 하위 계층(DU)으로 쪼갠 구조. 그 사이 프로토콜이 F1AP, CU 의 제어/사용자 평면 사이가 E1AP. srsRAN 은 한 프로세스 안에서 이 분할을 그대로 갖고 있다. → 10장

## D

**dB / dBm** — dB 는 두 전력의 비를 로그로(10 dB = 10 배), dBm 은 1 mW 를 기준으로 한 절대 전력. 0 dBm = 1 mW, +23 dBm = 200 mW, −100 dBm = 0.1 pW. 곱셈이 덧셈이 되어 링크 계산이 쉬워진다. → 1장

**DCI** (Downlink Control Information) — 기지국이 매 슬롯 "누구에게 어느 PRB 를 어떤 MCS 로 준다"를 알리는 제어 메시지. 스케줄러의 결정이 담긴다. 기지국 MAC pcap 에서 보인다. → 10, 12장

**DCS** (Data Coding Scheme) — SMS 본문의 부호화. `0x00` 7비트 GSM 문자, `0x08` UCS2. text/plain 으로 보낸 문자에서 이 값이 비어 SMSC 가 SQL 오류를 낸 것이 13장 사례다. → 8, 11c, 13

**Diameter** — 4G 코어와 IMS 의 인증·정책 프로토콜. RADIUS 의 후손. 메시지는 명령 코드 + AVP 들. 우리 배포에서는 CSCF ↔ PyHSS(Cx: UAR/MAR/SAR/LIR). → 4, 8장

**DIAG** — Qualcomm 계열 모뎀의 바이너리 진단 프로토콜. 우리 모뎀의 `ttyUSB0`. AT 와 별개의 포트다. → 11c, 11e

**DNN** (Data Network Name) — 5G 에서 APN 을 부르는 이름. 같은 개념. → 7장

**DRB** (Data Radio Bearer) — 무선 구간에서 사용자 데이터를 나르는 논리 통로. QoS 흐름들이 여기 매핑된다. → 7장

**DTE / DCE** (Data Terminal / Data Circuit-terminating Equipment) — 시리얼 연결의 양 끝. PC 가 DTE, 모뎀이 DCE. RS-232 신호선(RTS/CTS, DTR/DSR, DCD)의 방향이 여기서 정해진다. → 11b

## E

**E.164** — 국제 전화번호 체계. 국가 코드 + 국내 번호, 최대 15자리. SIM 과 SMS 의 번호 형식 바이트 `0x91` 의 아래 니블 `1` 이 "E.164". → 4, 4a, 11c

**ECIES** — 공개키로 데이터를 암호화하는 방식의 하나. SUCI 가 IMSI 를 숨길 때 쓴다(방식 1 = X25519, 방식 2 = secp256r1). 우리 실험은 방식 0(널, 숨기지 않음). → 6장

**EF / DF / MF / ADF** — SIM 의 파일시스템. MF 는 루트(`3F00`), DF 는 디렉터리, ADF 는 USIM·ISIM 같은 응용의 디렉터리, EF 는 실제 데이터가 든 파일. → 4a장

**EPD** (Extended Protocol Discriminator) — NAS 메시지 첫 바이트. `0x7E` 5GMM, `0x2E` 5GSM. → 5.6a

## F

**F1AP / E1AP** — CU-DU 사이, CU 의 제어·사용자 평면 사이의 기지국 내부 프로토콜. 와이어샤크 필터 `f1ap`, `e1ap`. → 10장

**FFT / IFFT** — 시간 신호를 주파수 성분으로(FFT), 주파수 성분을 시간 신호로(IFFT). OFDM 송신은 IFFT 한 번, 수신은 FFT 한 번이다. → 3장

**FPGA** — 전원을 켤 때마다 회로를 새로 올리는 칩. B210 은 UHD 가 이미지를 올려야 동작하며, LibreSDR 은 전용 이미지가 필요하다. → 2, 9장

## G

**GBR** (Guaranteed Bit Rate) — 대역폭을 보장받는 QoS 등급. 음성 5QI 1, 영상 5QI 2 가 여기 속한다. → 7장

**gNB** — 5G 기지국. 4G 는 eNB. 우리 배포에서는 `srsgnb` 컨테이너의 srsRAN Project. → 10장

**GSCN** (Global Synchronization Channel Number) — SSB 가 놓일 수 있는 주파수 격자의 번호. 3 GHz 이상에서 1.44 MHz 간격. 단말은 이 격자만 훑어 셀을 찾는다. → 3, 10.6

**GTP-U** (GPRS Tunnelling Protocol – User plane) — 기지국과 UPF 사이에서 단말 IP 패킷을 감싸는 UDP 2152 터널. VXLAN 과 같은 발상이고 TEID 가 VNI 자리다. → 7장

## H

**HARQ** (Hybrid Automatic Repeat reQuest) — 무선 구간의 빠른 재전송. 수신 측이 실패한 블록을 버리지 않고 재전송분과 합쳐 복호한다. TCP 재전송보다 훨씬 아래, 수 ms 단위. → 3, 11f

**HSS** (Home Subscriber Server) — 4G/IMS 의 가입자 DB 서버. 우리 배포에서는 PyHSS 가 IMS 의 HSS 역할. 5G 에서는 UDM/UDR 이 대응. → 4, 8장

## I

**I/Q** (In-phase / Quadrature) — 전파 한 순간의 세기와 위상을 복소수 하나로 담은 샘플. SDR 이 주고받는 데이터의 정체. → 2장

**ICCID** — SIM 카드 자체의 일련번호(카드 뒷면 19~20자리). 가입자 번호(IMSI)와 별개. `AT+QCCID`. → 4a, 11c

**IMEI** — 단말 기계의 고유 번호. SIM 을 바꿔도 그대로. `AT+CGSN`. → 4, 11c

**IMPI / IMPU** (IMS Private / Public User Identity) — IMS 의 계정 이름(인증용)과 공개 주소(전화 걸 때 쓰는 SIP/tel URI). ISIM 이 비어 있으면 IMSI 에서 유도한다. → 4a, 8장

**IMS** (IP Multimedia Subsystem) — 전화·문자를 SIP 로 처리하는 망. 4G VoLTE, 5G VoNR 의 바탕. 우리 배포의 컨테이너 일곱 개. → 8장

**IMSI** — SIM 에 든 가입자 번호. MCC(3) + MNC(2~3) + 가입자 번호. 우리 시험 IMSI 는 `00101…`. `AT+CIMI`. → 4, 6장

**ISIM** — SIM 카드 안의 IMS 용 응용. IMPI/IMPU/도메인을 담는다. 우리 카드에서는 비어 있었다. → 4a장

## K

**K / Ki** — 가입자 비밀키 128비트. SIM 과 코어 DB 에만 있고 카드 밖으로 읽히지 않게 설계됐다. 이 책에서는 항상 `<KI>`. → 4a, 6장

## L

**LCP / IPCP** — PPP 의 링크 협상(LCP)과 IP 주소 협상(IPCP). 다이얼업의 주소 받기가 이것이었다. 5G 에서는 NAS 의 PDU 세션 수락이 그 자리를 대신한다. → 11b, 7장

## M

**MAC** — 문맥에 따라 둘. (1) 무선 계층의 Medium Access Control: 스케줄링·HARQ 를 하는 기지국 계층. (2) 인증의 Message Authentication Code: AUTN 안의 위조 방지 값. 이더넷 MAC 주소와는 무관. → 6, 10장

**MCC / MNC** (Mobile Country / Network Code) — 국가 번호와 사업자 번호. 합쳐서 PLMN. 한국 MCC 450, 시험용 001/01. → 4장, 부록 D

**MCS** (Modulation and Coding Scheme) — 기지국이 고른 변조(QPSK~256QAM)와 부호율의 조합 번호. 높을수록 한 번에 많이 싣는다. CQI 를 보고 정한다. → 3, 11f, 12

**MILENAGE** — AKA 에 쓰는 표준 알고리즘 묶음(f1~f5). AES 기반. K, OPc, RAND 로 RES, CK, IK, AK, MAC 을 만든다. 우리는 파이썬으로 독립 구현해 PyHSS 와 바이트 단위 일치를 확인했다. → 6장

**MIMO** (Multiple Input Multiple Output) — 안테나 여럿으로 같은 주파수에 여러 흐름을 동시에 보내는 기술. 우리는 1T1R(송신 1, 수신 1)이라 해당 없음. → 3장

**MSISDN** — 전화번호. 망 DB(UDM/HSS)와 SIM 의 EF.MSISDN 에 있다. → 4, 4a장

## N

**N2 / N3 / N4 / N5 / N6** — 5G 코어 구간 이름. N2 기지국↔AMF(NGAP), N3 기지국↔UPF(GTP-U), N4 SMF↔UPF(PFCP), N5 P-CSCF↔PCF(통화 정책), N6 UPF↔바깥 인터넷. → 4, 5, 7, 8장

**NAS** (Non-Access Stratum) — 단말과 AMF/SMF 가 직접 말하는 계층. 기지국은 열어 보지 않고 나른다. 보안 모드 뒤에는 암호화된다. → 5장

**NGAP** — 기지국과 AMF 사이 제어 프로토콜. SCTP 38412. 와이어샤크 `ngap`. → 5, 10장

**NR** (New Radio) — 5G 무선 규격의 이름. NR-SA 는 5G 단독(코어도 5G), NSA 는 LTE 에 기대는 방식. 우리는 SA. → 3장

**NRF** (Network Repository Function) — 5G 코어 조각들의 서비스 레지스트리. 각 조각이 등록하고 서로를 찾는다. Consul 과 같은 역할. → 5장

**NSSF** (Network Slice Selection Function) — 슬라이스 선택. 우리는 SST 1 하나뿐. → 5장

## O

**OFDM** (Orthogonal Frequency Division Multiplexing) — 넓은 대역을 수백·수천 개의 부반송파로 나눠 동시에 싣는 방식. LTE·5G·와이파이의 바탕. → 3장

**OP / OPc** — 사업자 상수와 그것을 가입자 키로 섞은 값. MILENAGE 의 입력. SIM 에는 보통 OPc 를 넣는다. 이 책에서는 `<OPC>`. → 4a, 6장

## P

**PCC 규칙** (Policy and Charging Control) — PCF 가 SMF 에게 "이 흐름을 이 5QI 로 열어라"고 내리는 규칙. Open5GS 에서는 가입자 문서의 세션 아래 `pcc_rule`. 없으면 통화가 `No PCC Rule in DB` 로 거절된다. → 7.8, 8, 13장, 부록 C

**PCF** (Policy Control Function) — 5G 코어의 정책 서버. 4G 의 PCRF. → 5, 7, 8장

**PCI** (Physical Cell ID) — 셀의 물리 번호 0~1007. PSS/SSS 에서 바로 나온다. 이웃 셀과 겹치면 안 된다. 우리 `pci=1`. → 3, 10, 11f

**PDCP / RLC / SDAP** — 기지국 무선 계층들. SDAP 는 QoS 흐름 → 무선 통로 매핑, PDCP 는 암호화·헤더 압축·순서 맞추기, RLC 는 분할·재조립과 재전송. → 7, 10장

**PDU 세션** — 단말과 데이터 망 사이의 논리 통로. 주소 하나, DNN 하나, QoS 흐름 여럿. 다이얼업 PPP 세션의 후손. → 7장

**PFCP** (Packet Forwarding Control Protocol) — SMF 가 UPF 에 규칙(PDR 매칭, FAR 전달, QER 속도, URR 계수)을 설치하는 UDP 8805 프로토콜. OpenFlow 와 같은 발상. → 7장

**PIN / PUK** — SIM 의 사용자 비밀번호와 그 잠금 해제 번호. PIN 3회, PUK 10회 틀리면 잠긴다(PUK 소진은 카드 사망). → 4a장

**PLMN** (Public Land Mobile Network) — 사업자 망 하나. 번호는 MCC+MNC. 셀이 SIB1 으로 방송하고 모뎀의 `AT+COPS` 에 보인다. 우리 `00101`. → 3, 4장, 부록 D

**PRB** (Physical Resource Block) — 부반송파 12개 × 슬롯 하나. 스케줄러가 나눠 주는 최소 단위. 20 MHz·30 kHz 에서 51개. → 3장

**PSS / SSS / PBCH** — SSB 의 세 부분. PSS·SSS 로 시간을 맞추고 셀 번호를 알고, PBCH 로 셀의 기본 정보(MIB)를 읽는다. → 3장

**PyHSS** — 파이썬으로 만든 HSS. 우리 IMS 의 가입자·인증 서버, Diameter 3875. → 8장

## Q

**QAM / QPSK** — 변조 방식. 한 심볼에 QPSK 는 2비트, 16QAM 4비트, 64QAM 6비트, 256QAM 8비트. 신호가 깨끗할수록 높은 것을 쓴다. → 3장

**QFI** (QoS Flow Identifier) — GTP-U 확장 헤더에 실리는 QoS 흐름 번호. → 7장

**QMI** (Qualcomm MSM Interface) — Qualcomm 계열 모뎀의 바이너리 제어 프로토콜. TLV 구조, 서비스 번호(CTL 0x00, WDS 0x01, DMS 0x02, NAS 0x03, UIM 0x0B …)와 클라이언트 ID(CID). `/dev/cdc-wdm0`, `qmicli`. → 11d

## R

**RACH / PRACH** (Random Access Channel) — 단말이 셀을 찾은 뒤 처음 "나 여기 있다"고 손드는 절차와 그 채널. 4단계(프리앰블 → 응답 → 연결 요청 → 충돌 해소). → 9, 10장

**RAN** (Radio Access Network) — 무선 접속망. 기지국 쪽 전부. → 4장

**RAND / RES / XRES** — AKA 의 챌린지(무작위 128비트), 단말의 응답, 망이 미리 계산해 둔 기대 응답. 5G 에서는 RES*/XRES* 로 한 번 더 감싼다. → 6장

**RI** (Rank Indicator) — 단말이 보고하는 "동시에 받을 수 있는 흐름 수". 1T1R 에서는 항상 1. → 11f

**RmNet / raw IP** — 모뎀이 USB 로 이더넷 흉내 없이 IP 패킷만 보내는 방식. `/sys/class/net/wwan0/qmi/raw_ip = Y`. → 11d

**RRC** (Radio Resource Control) — 단말과 기지국 사이 무선 제어 계층. 상태는 IDLE(쉼), INACTIVE(기억만), CONNECTED(통신 중). 엔지니어 모드의 상태 표시가 이것이다. → 4, 10, 11f

**RSRP** (Reference Signal Received Power) — 셀의 기준 신호 한 부반송파의 수신 전력. 단위 dBm. 어림값으로 −80 이상 아주 좋음, −80~−90 좋음, −90~−100 보통, −100 아래 나쁨. 우리 직결 측정 −71 dBm. 5G 에서는 SSB 로 재서 SS-RSRP 라 부른다. → 1, 11f

**RSRQ** (Reference Signal Received Quality) — RSRP 를 전체 수신 전력(RSSI)에 비춘 값. 단위 dB. −10 이상 좋음, −10~−15 보통, −15 아래 나쁨. 간섭이 많으면 RSRP 가 좋아도 나빠진다. 우리 −10~−11. → 11f, 13장

**RSSI** (Received Signal Strength Indicator) — 대역 전체에서 받은 총 전력(신호 + 잡음 + 간섭). 와이파이에서 흔히 보는 그 숫자. → 1, 11f

**RTP / RTCP** — 음성·영상 미디어를 나르는 UDP 프로토콜과 그 통계 짝. SSRC 로 흐름을 구분한다. 우리 실측 오디오 50 pps 양방향. → 8장

**rtpengine** — RTP 를 중계하는 미디어 프록시. 우리 `rtpengine` 컨테이너. → 8장

## S

**SBI** (Service Based Interface) — 5G 코어 조각끼리의 HTTP/2 + JSON REST API. TCP 7777, 와이어샤크 `http2`. → 5장

**SCP** (Service Communication Proxy) — 코어 조각 사이 요청을 중계하는 프록시. API 게이트웨이와 같은 역할. → 5장

**SCS** (Subcarrier Spacing) — 부반송파 간격. 15/30/60/120 kHz. 넓을수록 슬롯이 짧다. n78 은 30 kHz. srsUE 는 15 kHz 만 받아서 OAI 단말을 썼다. → 3장

**SCTP** — 메시지 경계를 보존하고 다중 스트림·다중 경로를 지원하는 전송 프로토콜. NGAP(38412)가 이 위에 탄다. → 5, 10장

**SDP** — SIP 본문에 실리는 미디어 협상 서술(`m=audio`, `c=`, 코덱). → 8장

**SIB1** (System Information Block 1) — 셀이 방송하는 첫 시스템 정보. PLMN, TAC, 접속 방법. → 3, 11f

**SINR** (Signal to Interference plus Noise Ratio) — 신호 대 간섭·잡음비. 단위 dB. 20 이상 아주 좋음, 13~20 좋음, 0~13 보통, 0 아래 나쁨. 변조 차수를 정하는 가장 직접적인 숫자. 우리 19 dB. → 1, 3, 11f

**SIP** — IMS 의 시그널링 프로토콜. HTTP 와 닮은 글자 기반. REGISTER, INVITE, ACK, BYE, MESSAGE. 와이어샤크 `sip`. → 8장

**SMF** (Session Management Function) — 5G 코어의 세션 관리자. 주소 풀에서 IP 를 고르고(DHCP 역할), UPF 에 PFCP 규칙을 설치한다. → 5, 7장

**SMSC / SMSF** — 문자 저장·전달 센터와, 5G 코어에서 NAS 문자를 SMSC 로 넘기는 조각. 우리 배포에는 `smsc`(IMS 경로)만 있고 SMSF 는 없다. → 8, 11c

**SQN** (Sequence Number) — AKA 의 재사용 방지 카운터. SIM 과 망이 각자 들고 있다가 어긋나면 재동기화한다. → 6장

**SSB** (SS/PBCH Block) — 셀이 주기적으로 쏘는 동기 신호 묶음. 와이파이 비콘처럼 "여기 셀이 있다"를 알린다. 우리 `dl_ssb_arfcn=623040`(3345.6 MHz). → 3, 10.6

**SST / SD** (Slice/Service Type, Slice Differentiator) — 네트워크 슬라이스 번호와 그 세부 구분. 우리 SST 1, SD 없음. → 5, 10장

**SUCI / SUPI** — SUPI 는 가입자의 진짜 식별자(IMSI 기반), SUCI 는 그것을 공개키로 숨긴 것. 무선으로는 SUCI 만 나간다. → 6장

**SW1 SW2** (Status Word) — APDU 응답 끝 두 바이트. `90 00` 성공, `63 Cx` 비밀번호 틀림(남은 횟수 x), `6A 88` 해당 없음. HTTP 상태 코드 자리. → 4a장

## T

**TA** (Timing Advance) — 단말이 기지국과의 거리만큼 상향 신호를 미리 보내는 시간 보정. 거리에 비례한다. 직결 실험에서는 0 근처. → 11f

**TAC / TAI** (Tracking Area Code / Identity) — 셀들을 묶은 구역 번호. 대기 중인 단말은 구역 단위로만 위치를 알리고, 망은 구역 단위로 페이징한다. 우리 TAC 1. → 4, 9, 11f

**TDD / FDD** — 송수신을 시간으로 나누는가(TDD), 주파수로 나누는가(FDD). n78 은 TDD. srsRAN 기본 패턴은 10슬롯 주기에 하향 6, 특수 1, 상향 3. → 3장

**TEID** (Tunnel Endpoint Identifier) — GTP-U 헤더의 32비트 터널 번호. 단말 세션마다 방향별로 하나. → 7장

**TPDU** (Transfer Protocol Data Unit) — SMS 의 바이트 단위 메시지(SMS-SUBMIT, SMS-DELIVER). TS 23.040. 바깥에 RP(중계 계층), NAS 경로에서는 CP 가 더 붙는다. → 8, 11c

**TS** (Technical Specification) — 3GPP 표준 문서. 번호로 분야가 갈린다. → 3장

## U

**UDM / UDR** (Unified Data Management / Repository) — 5G 가입자 데이터의 관리 로직과 저장소. 우리 배포에서 UDR 은 MongoDB 를 읽는다. → 5, 6장

**UE** (User Equipment) — 단말. 우리 실험에서는 RM520N-GL 모뎀과 OAI 소프트 단말. → 4장

**UHD** (USRP Hardware Driver) — Ettus SDR 의 드라이버 라이브러리. 펌웨어·FPGA 적재와 샘플 송수신을 맡는다. → 2, 9장

**UPF** (User Plane Function) — 5G 코어의 사용자 평면. GTP-U 를 벗겨 `ogstun` 으로 내보내고 NAT 한다. 4G 의 SGW-U+PGW-U. → 5, 7장

**URC** (Unsolicited Result Code) — 묻지 않아도 모뎀이 먼저 보내는 AT 줄(`RING`, `+C5GREG: …`, `+QIND: …`). → 11c

**USIM** — SIM 카드 안의 3G 이후 가입자 응용. IMSI, 키, MILENAGE 설정을 담는다. → 4a장

## V

**V.250** — ITU-T 의 AT 기본 명령 표준(옛 V.25ter). Hayes 명령의 국제 표준화. → 11b, 11c

**VoNR / VoLTE** — 5G·4G 에서 IMS 로 하는 음성 통화. → 8장

## W

**wwan0** — 모뎀이 리눅스에 만든 네트워크 인터페이스. DHCP 없이 QMI 로 받은 주소를 손으로 붙인다. → 7, 11d

---

## 우리말 용어

**감쇠기** — 신호 세기를 정해진 dB 만큼 줄이는 부품. 우리 경로에 40 dB / 2 W. 모뎀의 +23 dBm 이 B210 수신단을 태우지 않게 한다. → 1, 9장

**경로 손실** — 송신기에서 수신기까지 가는 동안 줄어드는 전력. 거리 제곱과 주파수 제곱에 비례해 커진다. → 1장

**대역폭** — 신호가 차지하는 주파수 폭. 우리 셀 20 MHz. 처리량의 상한을 정한다. → 1, 3장

**베이스밴드** — (1) 반송파를 벗긴 0 Hz 중심의 신호. (2) 휴대폰에서 무선 통신을 맡는 별도 프로세서와 그 펌웨어. 문맥으로 구분한다. → 2, 11e

**보호 대역** — 채널 양 끝에서 필터가 깔끔히 자르지 못해 비워 두는 부분. 20 MHz 에 PRB 51개만 들어가는 이유. → 3장

**부반송파** — OFDM 이 대역을 잘게 나눈 한 줄기. 30 kHz 간격. → 3장

**샘플 레이트** — 초당 샘플 수. 우리 23.04 MS/s. 대역폭보다 커야 한다. → 2장

**슬롯 / 심볼** — 시간 격자의 단위. 30 kHz 에서 슬롯 하나 0.5 ms, 슬롯당 OFDM 심볼 14개. → 3장

**엔지니어 모드** — 휴대폰·모뎀이 무선 측정값(RSRP, SINR, PCI, ARFCN …)을 보여 주는 숨은 화면. 우리 모뎀에서는 `AT+QENG="servingcell"`. 이 용어집이 그 화면의 사전이다. → 11f

**잡음 지수** (NF, Noise Figure) — 수신기가 신호에 더하는 잡음의 양(dB). B210 은 8 dB 미만. → 2장

**종단기** (터미네이터) — 동축 단자 끝을 50 Ω 으로 막는 마개. 안 쓰는 단자가 안테나가 되지 않게 한다. → 9장

**차폐함** — 전파가 새지 않게 막는 금속 시험 상자. → 9장, 부록 D

**페이징** — 대기 중인 단말을 망이 부르는 방송. TAC 구역 단위로 한다. → 4장

**피그테일** — 다른 규격의 커넥터를 잇는 짧은 동축 케이블. 우리 것은 SMA ↔ MHF4. → 9, 10장

**핸드셰이크 소리** — 다이얼업 모뎀이 연결할 때 내던 소리. 응답 톤, V.8 협상, 회선 탐색, 학습 구간이 차례로 들린다. → 11b
