# 11d. AT 를 넘어서: QMI·MBIM·ModemManager, 그리고 데이터 경로가 PPP 에서 wwan0 까지 온 길

> 상태: 골격 초안 — 풀어쓰기 예정 (문체 기준은 README 참조)

> 11c 까지 AT 명령을 전부 봤다. 그런데 우리 실험에서 PDU 세션을 올린 것은 AT 가 아니라 `qmicli` 였고, 데이터는 `wwan0` 이라는 네트워크 장치로 흘렀다. 왜 AT 로 끝내지 않았는가? 이 절은 **AT 가 모자라는 지점**과, 그 자리를 채운 **바이너리 제어 프로토콜**과 **데이터 경로**를 설명한다. 우리가 겪은 ModemManager 와의 충돌이 왜 일어났는지도 여기서 풀린다.

## 11d.1 AT 가 모자라는 다섯 가지 이유

AT 는 1981년의 설계다. 사람이 터미널에서 한 줄씩 치는 것을 전제로 했다. 2000년대에 모뎀이 스마트폰과 라우터 안으로 들어가면서 다음 문제가 드러났다.

| 문제 | 무슨 뜻인가 | 결과 |
|---|---|---|
| **글자 파싱** | 모든 값이 글자. `"00066C000"` 을 숫자로 바꾸려면 따옴표를 떼고 16진 변환을 해야 한다 | 느리고, 버전마다 형식이 조금씩 달라 파서가 깨진다 |
| **한 번에 한 명령** | 앞 명령의 `OK` 가 올 때까지 다음을 못 보낸다 | 동시에 여러 상태를 다루기 어렵다 |
| **URC 끼어들기** | 응답 중간에 `+QIND:` 가 섞인다(11c.3) | 파서가 복잡해지고 경쟁 조건이 생긴다 |
| **구조 없음** | "이 필드는 정수, 저 필드는 문자열"이라는 선언이 없다 | 코드가 문서를 보고 손으로 맞춰야 한다 |
| **데이터 부적합** | IP 패킷을 글자로 보낼 수는 없다 | 데이터 모드(PPP)로 들어가면 제어를 못 한다 |

소프트웨어 엔지니어라면 이 다섯 줄을 보고 바로 떠올릴 것이다. **"구조화된 바이너리 RPC 가 필요하다."** 그것이 QMI 와 MBIM 이다.

## 11d.2 QMI: Qualcomm 의 바이너리 제어 프로토콜

**QMI(Qualcomm MSM Interface)**는 Qualcomm 이 자사 모뎀 칩용으로 만든 제어 프로토콜이다. 우리 모뎀(RM520N-GL)은 Qualcomm 칩을 쓰므로 QMI 를 말한다. 공개 표준은 아니지만 리눅스 `libqmi` 가 역공학과 Qualcomm 의 부분 공개 문서로 거의 전부를 구현했다.

### 생김새: 서비스 → 메시지 → TLV

QMI 는 세 겹이다. 독자가 아는 것에 대응시키면 **gRPC 의 서비스/메서드/필드**와 같다.

```
┌──────────────────────────────────────────────┐
│ QMUX 헤더                                     │
│   서비스 종류 (service type)   예: WDS=1, NAS=3 │  ← "어느 서버에"
│   클라이언트 ID (CID)                          │  ← "어느 세션으로"
├──────────────────────────────────────────────┤
│ 메시지 헤더                                   │
│   트랜잭션 ID                                 │  ← 요청과 응답 짝 맞추기
│   메시지 ID                 예: 0x0020 Start Network │  ← "어느 메서드"
├──────────────────────────────────────────────┤
│ TLV 들 (Type-Length-Value)                     │
│   T=0x01 L=4 V=…    APN 문자열                 │  ← "인자들"
│   T=0x02 L=1 V=0x04 IP 종류                    │
└──────────────────────────────────────────────┘
```

**TLV(Type-Length-Value)**는 "이 필드의 종류, 길이, 값"을 붙여 보내는 방식이다. 필드를 빼거나 새로 넣어도 파서가 안 깨진다. 모르는 T 는 건너뛰면 된다. AT 의 "몇 번째 쉼표 뒤가 무슨 뜻"보다 훨씬 튼튼하다. (네트워크 쪽에서 보던 LLDP, RADIUS 속성, BGP 경로 속성과 같은 발상이다.)

### 서비스 목록: 무엇이 어디에 있나

| 서비스 | 번호 | 역할 | AT 로 치면 |
|---|---|---|---|
| CTL | 0 | 클라이언트 ID 발급·반납 | (없음) |
| **WDS** | 1 | Wireless Data Service — **데이터 세션 시작·중지·설정 조회** | `+CGDCONT`, `+CGACT`, `+CGPADDR` |
| DMS | 2 | Device Management — IMEI, 펌웨어, 전원 | `+CGSN`, `+CGMR`, `+CFUN` |
| **NAS** | 3 | Network Access — 등록, 신호, 사업자 | `+C5GREG`, `+COPS`, `+CSQ` |
| WMS | 5 | Wireless Messaging — SMS | `+CMGS` 등 |
| UIM | 11 | SIM 카드 접근 | `+CPIN`, `+CIMI` |
| PDC | 36 | 사업자 프로파일 | 제조사 명령 |

우리가 쓴 것은 **WDS** 뿐이다. 나머지는 AT 로 했다. 왜 섞어 썼는지는 11d.6 에서.

### 클라이언트 ID: 우리가 겪은 "세션이 죽는" 이유

QMI 에서 모든 요청은 **클라이언트 ID(CID)** 로 묶인다. 프로그램이 WDS 서비스에 "나 클라이언트 하나 달라"고 하면 CTL 이 번호를 준다. 그 CID 로 Start Network 를 하면 **데이터 세션은 그 CID 에 매여 있다.** CID 를 반납하면 세션도 같이 정리된다.

`qmicli` 는 기본적으로 명령이 끝나면 CID 를 반납한다. 그래서 우리는 이 옵션을 썼다.

```
qmicli -d /dev/cdc-wdm0 --wds-start-network="ip-type=4,apn=internet" --client-no-release-cid
```

`--client-no-release-cid` 가 없으면 **명령이 끝나는 순간 세션이 내려간다.** 이것이 QMI 를 처음 쓰는 사람이 반드시 한 번 겪는 함정이다.

그리고 11c 에서 미뤄 둔 질문의 답이 여기 있다. **ModemManager 가 `inhibit` 에서 풀려나며 모뎀을 다시 잡을 때, 자기가 모르는 CID 의 세션을 정리한다.** 그래서 우리 링크가 반복해서 죽었다. 11d.5 에서 ModemManager 가 왜 그렇게 하는지 본다.

### 오류 하나 읽기: `interface-in-use-config-match`

우리가 본 QMI 오류다.

```
error: couldn't start network: QMI protocol error (14): 'CallFailed'
verbose call end reason (2,241): [internal] interface-in-use-config-match
```

읽는 법: "같은 설정(APN internet, IPv4)의 세션이 **이미** 이 인터페이스에 있다." 모뎀은 같은 APN 으로 두 번 붙이지 않는다. AT 로 `+CGACT=1,1` 을 먼저 했기 때문에 QMI 가 거부한 것이다. **제어 경로를 하나로 통일해야 한다**는 교훈이다. 해결은 `CFUN=0/1` 로 전부 지우고 QMI 로만 올리는 것이었다.

## 11d.2a 패킷 해부: QMI 메시지의 머리

11d.2 의 세 겹을 바이트로 그린다. `qmicli --verbose` 나 `libqmi` 의 로그에 이 모양으로 찍힌다.

```
 QMUX 헤더 (6 바이트)
 +-------------+---------------------+-------------+-------------+-------------+
 | I/F 종류 =01 |     길이 (16)        | 제어 플래그  | 서비스 종류  | 클라이언트 ID |
 +-------------+---------------------+-------------+-------------+-------------+
 SDU (서비스 데이터)
 +-------------+---------------------+---------------------+---------------------+
 | 메시지 종류/  | 트랜잭션 ID (16)     |   메시지 ID (16)      |   길이 (16)          |
 | 제어 (8)     |  (CTL 서비스는 8)    |                     |                     |
 +-------------+---------------------+---------------------+---------------------+
 | TLV 들:  종류(8) | 길이(16) | 값 …   반복                                          |
```

| 필드 | 뜻 | 우리 `wds-start-network` 에서 |
|---|---|---|
| **I/F 종류** | 항상 `0x01` (QMUX) | |
| **제어 플래그** | `0x00` 요청(제어점→서비스), `0x80` 응답/지시(서비스→제어점) | 요청 0x00, 응답 0x80 |
| **서비스 종류** | 11d.2 표. `0x01` WDS, `0x03` NAS, `0x02` DMS, `0x0B` UIM | `0x01` |
| **클라이언트 ID** | CTL 이 발급한 번호. 세션이 이것에 매인다 | `--client-no-release-cid` 가 지킨 그 번호 |
| **메시지 종류** | `0x00` 요청, `0x02` 응답, `0x04` 지시(묻지 않은 알림, AT 의 URC 와 같다) | |
| **트랜잭션 ID** | 요청과 응답 짝 맞추기 | |
| **메시지 ID** | 무슨 명령인가. WDS `0x0020` Start Network, `0x0021` Stop Network, `0x002D` Get Current Settings, `0x0022` Get Packet Service Status | `0x0020` |
| **TLV** | 인자. Start Network 의 `0x14` APN 문자열, `0x19` IP 종류. 응답의 `0x01` Packet Data Handle | APN "internet", IP 종류 4 |

AT 와 비교하면 차이가 분명하다. AT 는 `AT+CGACT=1,1\r` 이라는 글자이고 뜻은 사람이 문서를 보고 쉼표 위치로 안다. QMI 는 "서비스 1, 메시지 0x0020, TLV 0x14 = 'internet'" 이고 뜻은 바이트 위치에 박혀 있다. 그래서 파서가 안 깨진다. Diameter 의 AVP(8 장), PFCP 의 IE(7 장), SIM 의 BER-TLV(4a 장)가 전부 같은 "종류-길이-값" 가족이고, 이 책에서 네 번째로 만나는 것이다.

## 11d.3 MBIM: USB 표준이 된 제어 프로토콜

**MBIM(Mobile Broadband Interface Model)**은 USB-IF(USB 표준 기구)가 2013년에 정한 **공개 표준**이다. Windows 가 "모뎀 제조사마다 드라이버를 따로 깔지 말자"고 밀어서 생겼다. 구조는 QMI 와 비슷하다(서비스를 UUID 로, 명령을 CID 로, 인자를 구조체로). 리눅스는 `cdc_mbim` 드라이버와 `libmbim` 으로 지원한다.

같은 Quectel 모뎀이 **USB 구성(composition)**을 바꿔 QMI 모드로도 MBIM 모드로도 보일 수 있다. 제조사 명령으로 고른다. Quectel 은 `AT+QCFG="usbnet",<n>` 으로 USB 구성을 바꾸는데, 우리가 받은 두 매뉴얼(RG50xQ V1.1.1, RG520N…RM520N V1.0.0)의 텍스트에서는 이 항목을 찾지 못했다. 이 명령의 인자 값은 이 책에서 확인하지 못했고, 바꾸려면 그 펌웨어의 매뉴얼로 확인해야 한다. 우리 모뎀은 꺼낸 그대로 QMI 모드(`cdc-wdm0` + `qmi_wwan`)였다.

| | QMI | MBIM |
|---|---|---|
| 누가 정했나 | Qualcomm (비공개) | USB-IF (공개) |
| 칩 | Qualcomm 만 | 제조사 무관 |
| 리눅스 | `qmi_wwan` + `libqmi` | `cdc_mbim` + `libmbim` |
| Windows | 제조사 드라이버 | 기본 내장 |
| 기능 깊이 | 칩의 모든 것 | 표준 범위만 |

실험실에서는 **QMI 가 더 깊이 들어간다.** 상용 제품이라면 MBIM 이 이식성이 좋다.

## 11d.4 스마트폰 안에서는: RIL

폰 안에서 안드로이드는 모뎀을 **RIL(Radio Interface Layer)**로 다룬다. 안드로이드 전화 앱 → 텔레포니 프레임워크 → **RIL 데몬(rild)** → **제조사 RIL 라이브러리** → AT 또는 QMI → 베이스밴드. 제조사 라이브러리가 "안드로이드가 원하는 요청"을 "이 모뎀이 알아듣는 명령"으로 번역한다.

중요한 점은 **이 번역기가 AP(앱 프로세서) 쪽에서 돈다**는 것이다. 즉 AP 가 루트를 뺏기면 공격자는 RIL 을 통해 모뎀에 명령을 내릴 수 있다. 11e 의 출발점이다.

## 11d.5 ModemManager: 리눅스 데스크톱의 모뎀 관리자

리눅스 데스크톱/서버에서 모뎀을 자동으로 찾아 인터넷에 붙여 주는 데몬이 **ModemManager** 다. NetworkManager 와 짝을 이룬다. 노트북에 LTE 모듈이 있으면 이것이 알아서 붙인다.

### 무엇을 하는가

1. USB 장치가 꽂히면 **모든 포트를 열어 본다.** AT 를 쳐서 답하면 `at`, QMI 가 답하면 `qmi`, NMEA 가 나오면 `gps`, 아무것도 아니면 `ignored`. 우리 실험에서 본 그 분류다.
   ```
   ports: cdc-wdm0 (qmi), ttyUSB0 (ignored), ttyUSB1 (gps), ttyUSB2 (at), ttyUSB3 (at), wwan0 (net)
   ```
2. 제조사 **플러그인**(`quectel`)을 골라 제조사 명령을 쓴다.
3. SIM 을 읽고, 망에 등록하고, 요청이 오면 **자기 CID 로** 데이터 세션을 올린다.
4. **포트를 점유한다.** AT 포트를 열어 둔 채 URC 를 듣는다.

### 왜 우리와 충돌했나

ModemManager 는 **"이 모뎀은 내 것"**이라는 전제로 돈다. 그래서 세 가지가 부딪혔다.

| ModemManager 의 행동 | 우리에게 생긴 일 |
|---|---|
| AT 포트 `ttyUSB2/3` 를 열어 둔다 | 우리 `pyserial` 이 보낸 명령의 답을 ModemManager 가 먼저 읽어 갔다 → 빈 응답 |
| 모뎀을 재점검할 때 자기 CID 가 아닌 세션을 정리한다 | `inhibit` 해제 직후 QMI 세션이 죽어 링크가 끊겼다 |
| 자기 방식으로 세션을 올리려 한다 | `mmcli --simple-connect` 가 우리 코어의 APN 설정과 맞지 않아 `cm error` |

해결책은 두 단계였다.

1. 임시: `mmcli --inhibit-device=<uid>` — ModemManager 에게 "이 장치에서 손 떼라"고 하되, **명령이 떠 있는 동안만** 유효하다. 그래서 한 스크립트 안에서 inhibit 를 띄우고 작업을 끝내는 식으로 썼다.
2. 영구: **udev 규칙**으로 이 모뎀을 ModemManager 가 아예 보지 않게 했다.
   ```
   ACTION=="add|change", SUBSYSTEM=="usb", ATTRS{idVendor}=="2c7c", ATTRS{idProduct}=="0801", ENV{ID_MM_DEVICE_IGNORE}="1"
   ```
   `ID_MM_DEVICE_IGNORE=1` 은 ModemManager 가 udev 속성으로 확인하는 약속이다. 서비스는 살려 둬서 다른 모뎀은 계속 관리한다.

> 💡 **일반화**: 실험실에서 모뎀을 **직접** 제어할 때는 그 모뎀을 OS 의 자동 관리에서 빼는 것이 첫 단계다. ModemManager 뿐 아니라 NetworkManager 가 `wwan0` 을 건드리는 것도 막아야 한다(`NM_UNMANAGED`). 안 그러면 "왜 가끔 되고 가끔 안 되나"를 며칠 쫓게 된다. 우리가 그랬다.

## 11d.6 데이터 경로의 진화: PPP → 이더넷 흉내 → raw IP

제어는 됐고, 이제 **IP 패킷이 실제로 어디로 흐르는가**다. 역사 순서로 보면 설계 이유가 보인다.

### 1세대: PPP over 시리얼

11b.8 의 방식이다. `ATD*99#` 로 데이터 모드에 들어가고 PPP 프레임에 IP 를 싸서 시리얼로 보낸다.

문제: 시리얼은 바이트 스트림이라 **프레임 경계**를 PPP 가 만들어야 한다(HDLC 식 `0x7E` 플래그와 바이트 스터핑). 패킷마다 CPU 가 그 작업을 하고, 제어 명령을 내리려면 데이터 모드를 빠져나와야 한다. 수 Mbps 를 넘으면 버겁다.

### 2세대: USB 로 이더넷 흉내 — CDC-ECM / NCM

USB 가 널리 퍼지자 "모뎀이 USB 이더넷 어댑터인 척하자"는 방식이 나왔다. **CDC-ECM**(간단), **CDC-NCM**(여러 패킷을 묶어 효율 개선). PC 에는 `usb0` 같은 이더넷 장치가 생기고, DHCP 로 IP 를 받는다. 편하지만 **이더넷 헤더 14바이트가 매 패킷에 붙는** 낭비가 있다. 무선 구간에는 MAC 주소라는 개념이 없는데 흉내 내느라 붙이는 것이다.

### 3세대: raw IP — RmNet 과 QMAP

Qualcomm 은 이더넷 흉내를 버렸다. **RmNet** 은 USB 로 **IP 패킷을 그대로** 보낸다. 리눅스 `qmi_wwan` 드라이버가 이것을 `wwan0` 으로 노출하고, **raw_ip 모드**를 켜면 이더넷 헤더 없이 IP 패킷만 오간다.

```
$ cat /sys/class/net/wwan0/qmi/raw_ip
Y
```

우리가 본 `Y` 가 그 표시다. 거기에 **QMAP** 이라는 얇은 헤더를 붙이면 **세션 여러 개(인터넷 APN + IMS APN)를 `wwan0` 하나로 다중화**할 수 있다. 우리 실험에서는 한 번에 하나만 썼다.

### raw IP 의 대가: IP 를 손으로 설정해야 한다

이더넷 흉내가 없으니 **DHCP 도 없다.** IP 는 QMI 로 물어서 손으로 붙여야 한다. 우리가 한 그대로다.

```
qmicli … --wds-get-current-settings            # IP 10.45.0.3, 마스크 /29, 게이트웨이 10.45.0.4
ip addr add 10.45.0.3/29 dev wwan0
ip route add 10.45.0.1/32 via 10.45.0.4 dev wwan0
```

마스크가 `/29` 이고 게이트웨이가 "다음 주소"인 것은 **모뎀이 만든 가짜 서브넷**이다. 실제 망에는 그런 서브넷이 없다. 모뎀이 PC 쪽 IP 스택을 만족시키려고 꾸며 준 것이다. 이것을 모르면 "게이트웨이 10.45.0.4 가 핑이 안 돼요"라고 헤맨다. 실제 상대는 UPF(7장)다.

> 🔎 **직접 확인**: `ip -d link show wwan0` 로 링크 타입을 보라. 이더넷이 아니라 `rawip` 또는 `none` 이다. `tcpdump -i wwan0` 를 하면 이더넷 헤더 없이 IP 부터 시작한다.

### 한 표로

| 세대 | 전송 | PC 쪽 장치 | IP 설정 | 오버헤드 | 제어와의 관계 |
|---|---|---|---|---|---|
| PPP | 시리얼 | `ppp0` | IPCP | 프레이밍 + CPU | 데이터 모드 들어가면 제어 불가 |
| ECM/NCM | USB | `usb0` (이더넷) | DHCP | 이더넷 헤더 | 별도 제어 채널 |
| **RmNet raw IP** | USB | **`wwan0`** | **QMI 로 조회 후 수동** | 최소 | **QMI 와 짝** |

## 11d.7 우리 실험의 제어 지도: 무엇을 어느 길로 했나

이 절의 결론을 실험 기록으로 정리한다.

| 할 일 | 쓴 길 | 이유 |
|---|---|---|
| 모뎀 정보, SIM 확인, IMSI | AT (`ATI`, `+CPIN?`, `+CIMI`, `+QCCID`) | 읽기만, 글자로 충분 |
| 5G 전용·n78 전용 강제 | AT (`+QNWPREFCFG`) | 제조사 명령, QMI 에 같은 깊이 없음 |
| 등록 상태, 셀 측정 | AT (`+C5GREG?`, `+QENG`) | 사람이 읽기 편함 |
| 모뎀 재초기화 | AT (`+CFUN=0/1`) | |
| 망 스캔 | AT (`+COPS=?`) | |
| **데이터 세션 올리기** | **QMI (`--wds-start-network`)** | AT 로 올리면 `wwan0` 에 안 붙는다. 이 펌웨어의 `+QNETDEVCTL` 이 없어서 AT 로는 바인딩 불가 |
| **IP/게이트웨이 조회** | **QMI (`--wds-get-current-settings`)** | raw IP 라 DHCP 없음 |
| 데이터 흘리기 | `wwan0` raw IP | |
| ModemManager 배제 | `mmcli --inhibit-device` → udev 규칙 | |

읽는 법: **상태를 보는 것은 AT, 세션을 만드는 것은 QMI.** 이 분업이 실험실에서 가장 덜 꼬인다. 제품을 만든다면 전부 QMI(또는 MBIM)로 통일한다.

## 11d.8 이 절의 요약

| 질문 | 답 |
|---|---|
| AT 로 왜 안 끝내나? | 글자 파싱·직렬 실행·URC·구조 없음·데이터 부적합. 바이너리 RPC 가 필요했다. |
| QMI 란? | Qualcomm 의 서비스/메시지/TLV 바이너리 프로토콜. `cdc-wdm0` + `libqmi`. |
| CID 가 왜 중요한가? | 세션이 CID 에 매인다. 반납하면 세션이 죽는다. `--client-no-release-cid`. |
| MBIM 이란? | USB-IF 공개 표준. 같은 역할, 칩 무관. |
| ModemManager 는 왜 방해했나? | 모뎀을 자기 것으로 전제. AT 포트 점유, 남의 세션 정리. udev `ID_MM_DEVICE_IGNORE` 로 제외. |
| `wwan0` 은 왜 DHCP 가 없나? | raw IP(RmNet). 이더넷 흉내를 버렸다. QMI 로 IP 를 묻고 손으로 붙인다. |
| `/29` 게이트웨이는 뭔가? | 모뎀이 PC 를 위해 꾸민 가짜 서브넷. 실제 상대는 UPF. |

## 점검 문제

1. TLV 방식이 AT 의 쉼표 구분 방식보다 버전 변화에 강한 이유를 설명하라.
2. `qmicli --wds-start-network` 뒤에 `--client-no-release-cid` 를 빠뜨리면 무슨 일이 일어나는가?
3. `interface-in-use-config-match` 가 났을 때 가장 먼저 의심할 것은?
4. `wwan0` 에서 `tcpdump` 를 하면 이더넷 헤더가 없는 이유는?
5. ModemManager 를 완전히 끄는 대신 udev 로 한 장치만 제외한 이유는?

## 직접 해보기

- `qmicli -d /dev/cdc-wdm0 --nas-get-signal-info` 와 `AT+QENG="servingcell"` 을 같은 순간에 쳐서 RSRP 가 같은지 비교하라. 같은 값을 **두 길**로 읽은 것이다.
- `qmicli … --wds-get-packet-service-status` 로 세션 상태를 보고, 그 다음 CID 를 반납(`--client-cid=<n>` 없이 아무 명령)한 뒤 다시 보라.
- `ls -l /dev/cdc-wdm0 /dev/ttyUSB*` 로 권한과 그룹을 확인하라. 누가 이 파일을 열 수 있는가가 11e 의 주제다.

---

> **출처**: QMI 서비스 번호는 libqmi `src/libqmi-glib/qmi-enums.h` 의 `QmiService` 열거형에서 대조했다 — `CTL 0x00, WDS 0x01, DMS 0x02, NAS 0x03, QOS 0x04, WMS 0x05, PDS 0x06, VOICE 0x09, UIM 0x0B, PBM 0x0C, PDC 0x24(=36)`. MBIM 은 USB-IF 의 2013 년 규격. `AT+QCFG="usbnet"` 인자는 미확인(본문 참조). QMAP·raw_ip 동작은 커널 `qmi_wwan` 문서.

*다음 절: 11e. 공격 표면과 신뢰 경계 — 베이스밴드 분리, 가짜 기지국, USB 로 노출된 AT 로 폰이 뚫린 사례*
