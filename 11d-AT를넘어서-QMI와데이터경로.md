# 11d. AT 를 넘어서: QMI·MBIM·ModemManager, 그리고 데이터 경로가 PPP 에서 wwan0 까지 온 길

> 11c 까지 우리는 AT 명령을 전부 봤다. 그런데 이 실험실에서 모뎀의 PDU 세션을 실제로 올린 것은 AT 가 아니라 `qmicli` 라는 프로그램이었고, 데이터는 `wwan0` 이라는 네트워크 장치로 흘렀다. 처음부터 그렇게 계획한 것이 아니다. AT 로 세션을 올렸는데 PC 쪽으로 패킷이 한 개도 오지 않았고, 그 이유를 쫓다가 QMI 로 넘어갔고, QMI 로 넘어가자 이번에는 세션이 이유 없이 죽기 시작했다. 이 절은 그 반나절을 순서대로 따라간다. 따라가다 보면 AT 가 왜 모자라는지, 그 빈자리를 채운 바이너리 제어 프로토콜이 바이트 단위로 어떻게 생겼는지, 모뎀이 IP 패킷을 PC 에 넘기는 길이 어떻게 진화했는지, 그리고 리눅스 데스크톱의 모뎀 관리자가 왜 우리 링크를 끊었는지가 차례로 드러난다.

## 11d.1 AT 로 세션을 올렸는데 PC 로는 아무것도 오지 않았다

모뎀이 우리 망에 등록된 직후의 기록부터 보자. 11c 에서 배운 2층 명령 그대로, 데이터 세션을 켜고(`AT+CGACT=1,1`), 받은 주소를 묻고(`AT+CGPADDR`), Quectel 전용 핑 명령으로 인터넷이 되는지 확인했다.

```
CGACT  -> OK
CGPADDR-> +CGPADDR: 1,"10.45.0.2"||OK
ping   -> OK||+QPING: 0,"8.8.8.8",32,63,255||+QPING: 0,"8.8.8.8",32,58,255||...
          ||+QPING: 0,4,4,0,58,70,62
```

(`||` 는 우리 파이썬 스크립트가 응답의 줄바꿈 `\r\n` 을 한 줄로 이어 붙이려고 바꿔 넣은 표시다.) 네 번 보내 네 번 받았고 왕복 58~70 ms 다. 여기서 성공이라고 생각하기 쉽다. 그런데 이 핑을 보낸 것이 누구인지 정확히 봐야 한다. `AT+QPING` 은 PC 가 핑을 보내라는 명령이 아니라 **모뎀이 자기 안에서** 핑을 보내라는 명령이다. 이 모뎀의 펌웨어 안에는 작은 TCP/IP 스택이 따로 들어 있어서, 모뎀 혼자서 ICMP 패킷을 만들고 받은 응답을 글자로 바꿔 시리얼 포트로 알려 준다. 즉 이 출력이 증명하는 것은 "모뎀까지는 인터넷이 된다"이고, "PC 에서 인터넷이 된다"는 아직 아무것도 증명되지 않았다.

PC 쪽을 보자. 커널은 모뎀이 꽂힐 때 이미 네트워크 장치 하나를 만들어 두었다. 부팅 로그(`dmesg`)에 이렇게 찍혀 있었다.

```
qmi_wwan 7-1:1.4: cdc-wdm0: USB WDM device
qmi_wwan 7-1:1.4 wwan0: register 'qmi_wwan' at usb-0000:c8:00.4-1, WWAN/QMI device, 5a:9c:6d:12:7c:c1
```

`wwan0` 이 그 장치다. 상태를 보니 내려가 있었고, 옆의 sysfs 파일 하나가 `Y` 를 말하고 있었다(이 `Y` 의 뜻은 11d.6 에서 푼다).

```
$ ip -br addr show wwan0
wwan0            DOWN
$ cat /sys/class/net/wwan0/qmi/raw_ip
Y
```

모뎀이 받은 주소 `10.45.0.2` 를 이 장치에 손으로 붙이고 핑을 쳤다. 그 전에 Quectel 매뉴얼에서 "모뎀의 데이터 세션을 PC 의 네트워크 장치에 연결하라"는 명령인 `AT+QNETDEVCTL` 을 찾아 시도했는데, 이 펌웨어에서는 셋 다 `ERROR` 였다.

```
QNETDEVCTL? -> ERROR
데이터콜 ON -> ERROR          (AT+QNETDEVCTL=1,1,1)
QNETDEVCTL? -> ERROR
```

그래도 장치는 올라가 있으니 패킷이 흐를지 모른다고 생각하고 핑을 쳤다.

```
--- 10.45.0.1 ping statistics ---
3 packets transmitted, 0 received, 100% packet loss, time 2038ms

wwan0 통계
    RX:  bytes packets errors dropped  missed   mcast
             0       0      0       0       0       0
    TX:  bytes packets errors dropped carrier collsns
           556       7      0       2       0       0
```

이 두 줄이 문제를 정확히 말한다. **보낸 것(TX)은 7개 556바이트로 USB 를 타고 모뎀까지 갔고, 받은 것(RX)은 0이다.** 모뎀 안에는 세션이 있고 모뎀 혼자서는 인터넷에 나갈 수 있다. 그런데 PC 에서 들어온 패킷을 그 세션에 실어 줄 연결이 없다. 비유하자면 와이어샤크로 VPN 클라이언트의 TUN 장치를 잡았는데 패킷이 나가기만 하고 터널 반대편으로는 아무것도 안 들어오는 상황, 즉 터널 프로세스가 장치를 열고는 있는데 실제 터널에 연결을 안 해 준 상황과 같다. 모뎀 안에서 "이 세션의 패킷은 USB 의 이 통로로 내보낸다"는 연결이 AT 로는 만들어지지 않았던 것이다.

그 연결을 만드는 방법이 이 펌웨어에서는 AT 가 아니라 QMI 였다. 왜 그렇게 설계됐는지를 이해하려면, AT 라는 약속이 어디서 한계에 부딪혔는지를 먼저 봐야 한다.

🔎 지금 할 일: 모뎀을 꽂고 `dmesg | grep -E 'qmi_wwan|cdc-wdm|ttyUSB'` 로 커널이 만든 장치를 확인하고, `ip -s link show wwan0` 의 TX/RX 숫자를 기억해 둔다. 이 절 끝까지 이 두 숫자가 진단의 기준이다.

## 11d.2 AT 가 모자라는 자리

AT 는 1981년에 사람이 터미널에서 한 줄씩 치는 것을 전제로 만든 약속이다(11b). 그 전제는 모뎀이 PC 옆의 상자였던 시절에는 아무 문제가 없었다. 문제는 2000년대에 모뎀이 스마트폰과 라우터 안으로 들어가 사람 대신 **프로그램**이 모뎀을 다루게 되면서 생겼다. 프로그램 입장에서 AT 를 다루는 일이 얼마나 불편한지는 우리가 11c 에서 쓴 파서를 떠올리면 바로 보인다.

첫째, 모든 값이 글자다. `+C5GREG` 응답의 셀 번호 `"00066C000"` 을 숫자로 쓰려면 따옴표를 떼고 16진 문자열을 정수로 바꿔야 하고, 펌웨어 판본에 따라 따옴표가 있다가 없다가 하면 파서가 그 자리에서 깨진다. 11f 에서 보겠지만 같은 `+QENG` 응답의 같은 15번째 자리가 매뉴얼 판본에 따라 부반송파 간격이었다가 송신 전력이었다가 한다. 필드의 뜻이 "몇 번째 쉼표 뒤"라는 위치로만 정해지기 때문이다.

둘째, 한 번에 하나만 묻는다. 앞 명령의 `OK` 가 올 때까지 다음 명령을 보낼 수 없다. 신호 세기를 1초마다 읽으면서 동시에 데이터 세션을 올리려면 프로그램이 직접 줄을 세워야 한다.

셋째, 모뎀이 묻지도 않은 말을 끼워 넣는다. 11c 에서 본 **URC**(Unsolicited Result Code, 모뎀이 요청 없이 먼저 보내는 알림 줄)가 응답 한가운데 섞여 들어온다. 우리 기록에도 `AT+CFUN=0` 의 응답 `OK` 뒤에 `+QIURC: "pdpdeact",1` 과 `+C5GREG: 0` 이 따라붙었다. 파서는 "이 줄이 내 명령의 답인가, 끼어든 알림인가"를 매번 판단해야 한다.

넷째, 구조가 선언되지 않는다. "이 필드는 32비트 정수, 저 필드는 문자열"이라는 정의가 프로토콜 안에 없고 PDF 매뉴얼에만 있다. 사람이 매뉴얼을 읽고 코드에 손으로 옮겨야 한다.

다섯째, IP 패킷을 실을 수 없다. AT 는 글자 줄이라 바이너리 패킷을 그대로 나를 수 없다. 그래서 옛날에는 `ATD` 로 **데이터 모드**에 들어가 그 시리얼 선 전체를 PPP 프레임 전용으로 넘겨줬는데(11b), 그 동안에는 같은 선으로 명령을 보낼 수 없었다.

소프트웨어 엔지니어라면 이 다섯 가지를 읽으면서 이미 답을 떠올렸을 것이다. **구조가 정의된 바이너리 RPC(Remote Procedure Call, 원격 함수 호출)와, 그것과 분리된 데이터 통로.** 제어는 작은 메시지로 따로 주고받고, 패킷은 네트워크 장치로 따로 흘린다. Qualcomm 이 이 생각을 자기 칩에 구현한 것이 QMI 이고, USB 표준 기구가 같은 생각을 제조사 중립으로 정리한 것이 MBIM 이다. 우리 모뎀(Quectel RM520N-GL)은 Qualcomm 칩을 쓰므로 QMI 를 말한다.

## 11d.3 QMI: 서비스, 메시지, TLV

**QMI** 는 Qualcomm MSM Interface 의 약자다. MSM(Mobile Station Modem)은 Qualcomm 이 자기 모뎀 칩 계열에 붙여 온 이름이다. QMI 는 공개 표준이 아니지만, 리눅스의 **libqmi** 라이브러리가 Qualcomm 의 부분 공개 자료와 관찰을 바탕으로 거의 전부를 구현해 두었고, 우리가 쓴 `qmicli` 는 그 라이브러리의 명령줄 도구다. libqmi 저장소에는 메시지 하나하나의 번호와 필드를 적은 JSON 정의 파일(`data/qmi-service-wds.json` 등)이 있어서, 이 절의 바이트 번호는 전부 그 파일과 대조했다.

QMI 의 구조는 세 겹이다. 가장 바깥이 "어느 서비스에게 보내는가", 그 안이 "그 서비스의 어느 명령인가", 가장 안쪽이 "그 명령의 인자들"이다. gRPC 를 써 봤다면 서비스·메서드·필드라는 세 층과 정확히 같은 모양이라고 보면 된다. 차이는 이 모든 것이 이름이 아니라 작은 정수 번호로 적혀 있다는 점이다.

가장 안쪽 인자는 **TLV**(Type-Length-Value) 방식으로 싣는다. 인자마다 "이 값의 종류 번호(Type), 값의 길이(Length), 값 자체(Value)"를 붙여 보내는 방식이다. 이 방식의 장점은 받는 쪽이 모르는 종류 번호를 만나도 길이만큼 건너뛰면 그만이라는 데 있다. 새 펌웨어가 새 인자를 추가해도 옛 프로그램이 깨지지 않고, 선택 인자는 그냥 빼고 보내면 된다. "세 번째 쉼표 뒤"에 뜻을 매다는 AT 와 정반대다. 와이어샤크에서 이 모양을 이미 여러 번 봤을 것이다. 스위치가 뿌리는 **LLDP**(Link Layer Discovery Protocol, 이웃 장비가 자기 이름과 포트를 알리는 2계층 광고) 프레임을 열면 시스템 이름, 포트 설명이 TLV 로 줄줄이 늘어서 있고, **RADIUS**(인증 서버 프로토콜)의 속성, **BGP**(Border Gateway Protocol, 인터넷 사업자끼리 경로를 교환하는 프로토콜) UPDATE 메시지의 경로 속성도 같은 방식이다. 이 책에서도 이미 네 번 만났다. SIM 의 BER-TLV(4a장), PFCP 의 IE(7장), Diameter 의 AVP(8장), 그리고 이제 QMI 다.

서비스는 번호로 구분한다. 모뎀 펌웨어 안에는 여러 개의 작은 서버가 떠 있고, 각자 번호를 하나씩 갖는다. 우리가 실제로 쓴 서비스와, 쓰지 않았지만 화면에서 자주 보게 될 서비스의 번호를 libqmi 의 열거형(`QmiService`)에서 옮기면 다음과 같다.

0번 **CTL**(control)은 다른 서비스를 쓰기 위한 접수창구다. 프로그램이 "WDS 서비스를 쓰고 싶다"고 CTL 에 말하면 CTL 이 **클라이언트 ID** 라는 번호표를 하나 내준다. 이 번호표가 이 절 후반부의 주인공이다.

1번 **WDS**(Wireless Data Service)는 데이터 세션 담당이다. 세션을 시작하고(Start Network), 끝내고(Stop Network), 지금 받은 IP 주소와 게이트웨이를 알려 준다(Get Current Settings). AT 로 치면 `+CGDCONT`, `+CGACT`, `+CGPADDR` 이 하던 일이고, 우리가 이 실험실에서 실제로 쓴 유일한 QMI 서비스다.

2번 **DMS**(Device Management Service)는 장치 관리다. IMEI, 펌웨어 판본, 전원 상태를 다룬다. AT 의 `+CGSN`, `+CGMR`, `+CFUN` 자리다.

3번 **NAS**(Network Access Service)는 망 접속 담당이다. 등록 상태, 신호 세기, 사업자 선택을 다룬다. 5장의 NAS(Non-Access Stratum, 단말과 AMF 사이의 시그널링 층)와 철자가 같지만 전혀 다른 것이다. QMI 의 NAS 는 "모뎀 안에서 망 접속 상태를 알려 주는 서비스"이고, 그 안에서 보여 주는 등록 상태의 원천이 5장의 NAS 메시지다. AT 의 `+C5GREG`, `+COPS`, `+CSQ` 자리다.

4번 QOS(Quality of Service, 세션별 품질 정보)와 6번 PDS(Position Determination Service, GPS 위치)는 이 실험에서 쓰지 않았다. 5번 **WMS**(Wireless Messaging Service)는 SMS 를 다루고 AT 의 `+CMGS` 자리다. 9번 VOICE 는 회선 음성 통화, 11번(16진 `0x0B`) **UIM**(User Identity Module, SIM 카드 접근)은 `+CPIN`, `+CIMI` 자리이고, 12번(`0x0C`) PBM(Phone Book Manager)은 SIM 의 전화번호부, 36번(`0x24`) **PDC**(Persistent Device Configuration)는 11c 에서 `AT+QMBNCFG` 로 본 사업자 프로파일, 즉 MBN(사업자마다 다른 모뎀 동작 설정을 묶은 바이너리 파일)을 관리한다.

우리가 직접 본 번호 발급 장면도 있다. `qmicli --verbose` 를 붙이면 libqmi 가 CTL 과 주고받는 과정을 그대로 찍어 준다.

```
[Debug] [/dev/cdc-wdm0] allocating new client ID...
<<<<<< QMUX:
<<<<<<   service = "ctl"
<<<<<<   translated = [ service = 'dms' cid = '1' ]
...
<<<<<<   translated = [ service = 'nas' cid = '3' ]
```

DMS 서비스용 번호표 1번, NAS 서비스용 번호표 3번을 받았다는 뜻이다. 번호표는 서비스마다 따로 센다.

🔎 지금 할 일: `qmicli -d /dev/cdc-wdm0 --dms-get-revision --verbose` 처럼 읽기만 하는 명령 하나를 `--verbose` 로 쳐서, CTL 에게 번호표를 받고 → 그 번호로 요청하고 → 번호표를 반납하는 세 번의 왕복을 직접 본다.

## 11d.4 패킷 해부: 우리가 받은 `CallFailed` 를 바이트로

이제 QMI 메시지를 바이트 단위로 연다. 추상적인 예시 대신, 우리가 실제로 받은 오류 하나를 기준으로 삼는다. AT 세션이 살아 있는 상태에서 QMI 로 세션을 올리려 했을 때 `qmicli` 가 찍은 출력이다.

```
error: couldn't start network: QMI protocol error (14): 'CallFailed'
call end reason (1): generic-unspecified
verbose call end reason (2,241): [internal] interface-in-use-config-match
[/dev/cdc-wdm0] Client ID not released:
	Service: 'wds'
	    CID: '15'
```

이 글자들은 모뎀이 보낸 바이너리 응답을 libqmi 가 번역한 것이다. 거꾸로, 그 요청과 응답이 선 위에서 어떤 바이트였는지를 libqmi 정의 파일로 복원해 보자. (아래 바이트는 우리가 캡처한 것이 아니라 libqmi 의 메시지 정의에 우리 값을 넣어 다시 만든 것이다. 트랜잭션 번호는 임의로 1 을 넣었다. 실제 캡처 방법은 이 절 끝에 있다.)

먼저 요청이다. `--wds-start-network="ip-type=4,apn=internet"` 은 다음 28바이트가 된다.

```
 오프셋  바이트                                        뜻
 ─────  ───────────────────────────────────────────  ─────────────────────────────
 QMUX 헤더 (6바이트)
 00     01                                           I/F 종류 = QMUX
 01     1B 00                                        길이 = 27 (I/F 바이트를 뺀 나머지 전체, 리틀 엔디언)
 03     00                                           제어 플래그 = 제어점(PC) → 서비스
 04     01                                           서비스 = WDS
 05     0F                                           클라이언트 ID = 15  ← CTL 이 준 번호표
 SDU 헤더 (7바이트)
 06     00                                           메시지 종류 = 요청
 07     01 00                                        트랜잭션 ID = 1
 09     20 00                                        메시지 ID = 0x0020 Start Network
 0B     0F 00                                        TLV 전체 길이 = 15
 TLV
 0D     14 | 08 00 | 69 6E 74 65 72 6E 65 74          T=0x14 APN, L=8, V="internet"
 18     19 | 01 00 | 04                               T=0x19 IP Family Preference, L=1, V=4 (IPv4)
```

필드를 하나씩 읽는다. 맨 앞 `01` 은 이 덩어리가 QMUX 메시지라는 표시다. **QMUX** 는 QMI Multiplexer, 즉 "여러 서비스로 가는 메시지를 한 통로에 섞어 보내는 봉투"이고, 이 6바이트가 IP 헤더처럼 목적지(서비스 번호)와 발신자(클라이언트 ID)를 적는 자리다. 길이 필드는 2바이트 **리틀 엔디언**이다. 네트워크 프로토콜에 익숙한 독자에게는 이것이 첫 번째 어색함일 것이다. 와이어샤크에서 보던 IP·TCP 헤더는 전부 빅 엔디언(네트워크 바이트 순서)인데 QMI 는 모뎀 칩의 ARM(휴대폰·모뎀 칩 대부분이 쓰는 프로세서 설계) 코어가 메모리에 정수를 두는 순서를 그대로 쓴다. `1B 00` 은 0x001B = 27 이다. 제어 플래그 `00` 은 "PC 쪽(제어점, control point)이 서비스에게 보냄"이고, 모뎀이 보내는 응답에서는 `80` 이 된다.

그 뒤 SDU(Service Data Unit, 서비스가 실제로 읽는 본문)의 첫 바이트가 메시지 종류다. `00` 요청, `02` 응답, `04` 지시(indication)다. **지시**는 모뎀이 묻지도 않았는데 보내는 알림이고, AT 의 URC 와 같은 역할을 하지만 URC 와 달리 응답과 뒤섞일 염려가 없다. 메시지 종류가 바이트 하나로 명시되어 있기 때문이다. 트랜잭션 ID 는 요청과 응답의 짝을 맞추는 번호이고(CTL 서비스만 이 칸이 1바이트다), 메시지 ID `0x0020` 이 "Start Network" 라는 메서드 이름이다. 마지막으로 TLV 들이 온다. APN 문자열이 종류 `0x14`, IP 종류 선호가 `0x19` 이고, 값 4 는 libqmi 열거형에서 IPv4 다.

이제 모뎀의 응답이다. 우리가 받은 오류를 같은 방식으로 복원하면 이렇다.

```
 QMUX:  01 | 1F 00 | 80 | 01 | 0F                    길이 31, 서비스 → 제어점, WDS, 클라이언트 15
 SDU :  02 | 01 00 | 20 00 | 13 00                   응답, 트랜잭션 1, Start Network, TLV 19바이트
 TLV :  02 | 04 00 | 01 00  0E 00                    T=0x02 결과: 실패(1), 오류 14 = CallFailed
        10 | 02 00 | 01 00                           T=0x10 Call End Reason = 1 generic-unspecified
        11 | 04 00 | 02 00  F1 00                    T=0x11 Verbose Call End Reason: 종류 2(internal), 이유 241
```

모든 QMI 응답의 첫 TLV 는 종류 `0x02` 의 **결과 TLV** 다. 앞 2바이트가 성공(0)·실패(1), 뒤 2바이트가 오류 번호다. libqmi 의 `qmi-errors.h` 에서 14번이 `QMI_PROTOCOL_ERROR_CALL_FAILED` 이므로 `qmicli` 가 `QMI protocol error (14): 'CallFailed'` 라고 찍었다. 그다음 `0x11` TLV 가 진짜 이유를 담는다. 첫 2바이트는 이유의 **분류**다. libqmi 열거형에서 1은 Mobile IP, 2는 모뎀 내부(internal), 3은 호 관리자(CM, Call Manager), 6은 3GPP 망이 보낸 거절 사유다. 즉 분류 2는 "망까지 가지도 않고 모뎀 안에서 거절했다"는 뜻이다. 뒤 2바이트 241(`0xF1`)이 `INTERFACE_IN_USE_CONFIG_MATCH`, 우리말로 "같은 설정의 세션이 이미 이 인터페이스에서 쓰이고 있다"다.

이 한 줄을 읽을 수 있게 되면 진단이 끝난다. 같은 APN(`internet`), 같은 IP 종류(IPv4)로 AT 가 이미 올려 둔 세션이 모뎀 안에 살아 있고, 모뎀은 같은 설정의 세션을 두 개 만들지 않는다. 우리는 이것을 AT 로 먼저 내리려 했다.

```
CGACT=0,1 -> ERROR
CGPADDR   -> +CGPADDR: 1,"10.45.0.2"||OK
=== QMI 데이터콜 재시도 ===
verbose call end reason (2,241): [internal] interface-in-use-config-match
	    CID: '16'
```

세션을 끄는 `AT+CGACT=0,1` 조차 `ERROR` 였고 주소는 그대로 남았다. 재시도한 QMI 는 같은 241을 받았고, 번호표만 16번으로 하나 더 늘었다. 결국 모뎀의 무선 부분을 통째로 껐다 켜서(`AT+CFUN=0` → `AT+CFUN=1`) 모든 세션을 지운 뒤 QMI 로만 올렸다.

```
CFUN=0 -> OK||+QIURC: "pdpdeact",1||+C5GREG: 0
CFUN=1 -> OK||+CPIN: READY||+QUSIM: 1||+QIND: SMS DONE||+C5GREG: 1,"000001","00066C000",11,1,"01"||+QIND: PB DONE
CGPADDR-> +CGPADDR: 1,"0.0.0.0"||OK
=== QMI start-network ===
[/dev/cdc-wdm0] Network started
	Packet data handle: '3800158448'
	    CID: '17'
=== 설정 조회 (cid=17) ===
           IP Family: IPv4
        IPv4 address: 10.45.0.3
    IPv4 subnet mask: 255.255.255.248
IPv4 gateway address: 10.45.0.4
    IPv4 primary DNS: 8.8.8.8
  IPv4 secondary DNS: 8.8.4.4
```

`CFUN=0` 의 응답에 `+QIURC: "pdpdeact",1` 이 섞여 나온 것이 보인다. Quectel 의 URC 로 "1번 PDP 컨텍스트(데이터 세션)가 내려갔다"는 알림이다. 다시 켜자 SIM 준비(`+CPIN: READY`), 등록(`+C5GREG: 1,...`)이 URC 로 줄줄이 따라왔고, 주소는 `0.0.0.0` 으로 비었다. 그 상태에서 QMI Start Network 가 성공했다. 성공 응답에는 결과 TLV(성공 0, 오류 0) 뒤에 종류 `0x01` 의 **Packet Data Handle** 이 4바이트로 붙어 온다. 3800158448 은 16진 `0xE281D0F0` 이고 선 위에서는 `F0 D0 81 E2` 순서다. 이 핸들은 세션의 손잡이라서, 나중에 이 세션을 끌 때 Stop Network(`0x0021`)의 종류 `0x01` TLV 에 그대로 넣어 보낸다.

마지막 `Get Current Settings`(`0x002D`)의 응답도 같은 식이다. IPv4 주소는 종류 `0x1E`, 게이트웨이는 `0x20`, 서브넷 마스크는 `0x21`, 1차 DNS 는 `0x15` 에 담기고, 넷 다 **4바이트 리틀 엔디언 정수**다. 그래서 `10.45.0.3` 은 선 위에서 `03 00 2D 0A` 로 거꾸로 보인다. 헥스 덤프를 직접 읽을 때 처음 한 번은 반드시 걸리는 함정이다.

QMI 오류를 읽는 습관을 정리하면 이렇다. `CallFailed` 같은 결과 TLV 의 이름만 보지 말고, 반드시 verbose 이유의 **분류 번호**를 본다. 2(internal)면 모뎀 안의 문제이니 모뎀 상태와 우리 요청을 의심하고, 6(3GPP)이면 코어가 거절한 것이니 SMF·AMF 로그(5장, 7장)를 연다.

🔎 지금 할 일: 같은 메시지를 실제로 잡아 보려면 `sudo modprobe usbmon` 뒤 와이어샤크에서 모뎀이 붙은 버스의 `usbmonN` 을 캡처하고, `qmicli` 로 읽기 명령 하나를 보낸다. 제어 전송의 데이터 부분에서 `01 xx 00 00 ...` 으로 시작하는 위 모양이 보인다. 더 쉬운 길은 `qmicli --verbose` 가 찍는 헥스 덤프다.

## 11d.5 바이트가 지나가는 길: 누가 어디서 처리하는가

위 28바이트가 `qmicli` 에서 모뎀 안의 WDS 서버까지 가는 동안 누가 손을 대는지를 우리 배포의 실제 이름으로 따라간다. `lsusb -t` 에 모뎀이 이렇게 보였다.

```
/:  Bus 007.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/1p, 480M
    |__ Port 001: Dev 003, If 0, Class=Vendor Specific Class, Driver=option, 480M
    |__ Port 001: Dev 003, If 1, Class=Vendor Specific Class, Driver=option, 480M
    |__ Port 001: Dev 003, If 2, Class=Vendor Specific Class, Driver=option, 480M
    |__ Port 001: Dev 003, If 3, Class=Vendor Specific Class, Driver=option, 480M
    |__ Port 001: Dev 003, If 4, Class=Vendor Specific Class, Driver=qmi_wwan, 480M
```

USB 장치 하나가 다섯 개의 **인터페이스**(If 0~4)를 내놓고 있다. USB 장치는 한 개의 물리 장치가 여러 개의 독립된 기능을 동시에 드러낼 수 있고, 그 기능 하나가 인터페이스다. 0~3번은 `option` 이라는 드라이버가 맡아 `/dev/ttyUSB0~3` 시리얼 포트로 만들었고(11a), 4번은 `qmi_wwan` 드라이버가 맡았다. 그리고 `qmi_wwan` 은 이 4번 인터페이스 하나에서 **두 개의 장치**를 만든다. 제어용 문자 장치 `/dev/cdc-wdm0` 과 데이터용 네트워크 장치 `wwan0` 이다. 위 `dmesg` 두 줄이 정확히 그 둘이다. 덧붙여 이 모뎀은 480M, 즉 USB 2.0 속도로 붙어 있다. 2장에서 B210 이 USB 3 이 아니면 안 됐던 것과 달리, 모뎀은 실측 55 Mbps 를 나르는 데 USB 2.0 의 480 Mbps 로 충분하다.

요청이 내려가는 길은 이렇다.

① **`qmicli`(사용자 공간, libqmi-glib)** 가 위 28바이트를 만든다. 서비스 번호, 클라이언트 ID, 트랜잭션 ID 를 채우는 것도, 응답의 TLV 를 풀어 `Packet data handle:` 같은 글자로 찍는 것도 이 라이브러리다.

② **`/dev/cdc-wdm0` 에 `write()`** 한다. 이 문자 장치는 커널의 `cdc_wdm` 코드가 제공한다. CDC-WDM 은 USB 통신 기기 표준(CDC, Communications Device Class)의 한 부분인 WDM(Wireless Mobile Device Management) 규격이고, 하는 일은 단순하다. 쓴 바이트를 해석하지 않고 USB **제어 전송**의 SEND_ENCAPSULATED_COMMAND 요청에 그대로 실어 보낸다. 즉 커널은 QMI 를 모른다. 봉투를 열어 보지 않는 우체부다.

③ **모뎀 펌웨어의 QMUX 라우터**가 받는다. 첫 바이트로 QMUX 임을 확인하고, 서비스 번호 `01` 을 보고 WDS 서버에게 넘기고, 클라이언트 ID `0F` 를 보고 "15번 손님의 요청"으로 기록한다. WDS 서버가 세션을 만들 수 있는지 판단하고, 이번처럼 같은 설정의 세션이 있으면 241로 거절한다. 세션을 만들 수 있으면 여기서부터는 5장·7장의 세계다. 모뎀은 5G NAS 의 PDU Session Establishment Request 를 만들어 기지국을 거쳐 AMF 로 보내고, SMF 가 주소를 정하고, 그 결과가 돌아와야 WDS 응답이 나간다. 우리가 Start Network 한 번에 수 초를 기다리는 이유가 그 왕복이다.

④ **응답이 올라오는 길**은 반대다. 모뎀은 USB 의 인터럽트 엔드포인트로 "응답이 준비됐다"는 신호(RESPONSE_AVAILABLE)만 보내고, `cdc_wdm` 이 그 신호를 받아 GET_ENCAPSULATED_RESPONSE 로 실제 바이트를 가져와 `read()` 대기 중인 `qmicli` 에게 넘긴다.

데이터 패킷은 이 길을 전혀 타지 않는다. 우리 셸에서 `ping -I wwan0` 을 치면 커널의 IP 스택이 패킷을 `wwan0` 에 넘기고, `qmi_wwan`(내부적으로 리눅스의 `usbnet` 공용 코드)이 같은 4번 인터페이스의 **벌크 엔드포인트**(대용량 전송용 USB 통로)로 밀어 넣는다. 모뎀 펌웨어의 데이터 경로가 그 패킷을 받아 Start Network 로 만들어진 세션에 실어 무선으로 보낸다. 제어는 제어 전송으로, 데이터는 벌크 전송으로, 같은 인터페이스 위에서 완전히 다른 통로를 쓴다. 11d.2 의 다섯 번째 문제("데이터 모드에 들어가면 제어를 못 한다")가 이렇게 풀렸다.

11d.1 의 미스터리도 이제 설명된다. AT 로 만든 세션은 모뎀 안에 있었지만 4번 인터페이스의 데이터 통로에 묶이지 않았다. `wwan0` 에서 나간 7개의 패킷은 벌크 엔드포인트로 모뎀까지 갔지만, 모뎀 쪽에서 그 통로와 연결된 세션이 없어 버려졌다. QMI 의 Start Network 는 바로 그 연결을 만드는 명령이다. AT 로도 그 연결을 만들어 주는 Quectel 명령(`AT+QNETDEVCTL`)이 펌웨어에 따라 있지만, 우리 펌웨어(`RM520NGLAAR03A03M4G`)에는 없었다.

한 가지 더 알아 둘 것이 있다. `/dev/cdc-wdm0` 은 여러 프로그램이 동시에 열면 서로의 응답을 가로챌 수 있는 단일 통로다. 그래서 libqmi 에는 `qmi-proxy` 라는 중계 프로세스가 있고, ModemManager 는 이 중계를 통해 모뎀과 대화한다. `qmicli` 도 `-p` 옵션을 주면 같은 중계를 쓴다. 우리는 `-p` 없이 장치를 직접 열었다. 다음 절의 충돌을 이해하는 데 필요한 배경이다.

🔎 지금 할 일: `ls -l /dev/cdc-wdm0`, `readlink -f /sys/class/net/wwan0/device` 로 두 장치가 같은 USB 인터페이스(`...:1.4`)에서 나왔음을 확인한다. `sudo fuser -v /dev/cdc-wdm0` 로 지금 누가 그 통로를 열고 있는지도 본다.

## 11d.6 클라이언트 ID: 세션은 번호표에 매여 있다

QMI 에서 데이터 세션은 그것을 만든 클라이언트 ID 에 매여 있다. 번호표를 반납하면 모뎀은 그 손님이 만든 세션을 같이 정리한다. 커넥션을 닫으면 그 커넥션에서 시작한 트랜잭션이 롤백되는 데이터베이스를 떠올리면 된다. 문제는 `qmicli` 가 기본적으로 **명령이 끝나면 번호표를 반납한다**는 것이다. 그래서 세션을 올리는 명령에는 반드시 이 옵션을 붙여야 한다.

```
qmicli -d /dev/cdc-wdm0 --wds-start-network="ip-type=4,apn=internet" --client-no-release-cid
```

`--client-no-release-cid` 가 없으면 `Network started` 가 찍히고 `qmicli` 가 종료하는 순간 세션이 내려간다. 옵션을 붙이면 `qmicli` 는 종료하면서 반납하지 않은 번호를 알려 준다. 우리 출력의 `Client ID not released: Service: 'wds' CID: '17'` 이 그 줄이다. 이후 같은 세션에 대해 묻거나 끌 때는 그 번호를 `--client-cid=17` 로 넘겨야 한다. 우리 스크립트가 출력에서 `CID: '17'` 을 정규식으로 뽑아 다음 명령에 넘긴 이유다.

번호가 실험 기록에서 15, 16, 17, 18, 19 로 계속 늘어난 것도 이것으로 읽힌다. 실패한 시도도 번호표를 하나씩 받았고, 반납하지 않았으니 모뎀 쪽에는 "주인 없는 번호표"가 쌓였다. 실험실에서는 문제가 되지 않지만, 장시간 도는 제품 코드라면 실패 경로에서 번호표를 반납하는 것까지 짜야 한다.

## 11d.7 `apn=ims` 를 줬는데 SMF 는 `internet` 이라고 했다

8장의 IMS 시험을 위해 모뎀에 IMS 전용 세션을 하나 더 올리려 했다. APN(5G 이름으로는 DNN, Data Network Name, "이 세션을 어느 데이터 망에 붙일 것인가")을 `ims` 로 주고 Start Network 를 보냈다.

```
=== QMI: ims APN 세션 ===
[/dev/cdc-wdm0] Network started
	Packet data handle: '3797919664'
	    CID: '18'
=== 설정 (cid=18) ===
        IPv4 address: 10.45.0.4
    IPv4 subnet mask: 255.255.255.248
IPv4 gateway address: 10.45.0.5
```

성공했다. 그런데 주소가 `10.45.0.x` 다. 우리 망에서 `internet` 세션은 10.45.0.0/16, `ims` 세션은 10.46.0.0/16 에서 주소를 받도록 SMF 를 설정해 두었다(7장). 코어 쪽 기록을 열었다.

```
[smf] INFO: UE SUPI[imsi-001011234567895] DNN[internet] IPv4[10.45.0.4] IPv6[] (../src/smf/npcf-handler.c:647)
```

SMF 는 이 세션을 `internet` 으로 받았다. 우리가 TLV `0x14` 에 `ims` 를 넣어 보냈는데 모뎀이 그것을 무시하고 기본 프로파일로 세션을 올린 것이다. 모뎀 안에 저장된 프로파일 목록을 QMI 로 꺼내 봤다.

```
Profile list retrieved:
	[1] 3gpp - profile1
		APN: 'internet'
		APN type: 'default'
		PDP type: 'ipv4'
	[2] 3gpp - profile2
		APN: 'ims'
		APN type: 'ims'
		PDP type: 'ipv4-or-ipv6'
	[3] 3gpp -
		APN: 'sos'
		APN type: 'emergency'
```

2번 프로파일이 `ims` 다. 그래서 APN 문자열 대신 프로파일 번호를 직접 지정했다(`--wds-start-network="3gpp-profile=2"`, TLV `0x31` Profile Index 3GPP).

```
Network cancelled... releasing resources
[/dev/cdc-wdm0] Network stopped
verbose call end reason (3,1140): [cm] (null)
```

이번에는 거절이다. 분류 3은 모뎀의 호 관리자(CM)이고, 이유 1140은 libqmi 가 이름을 갖고 있지 않은 번호라 `(null)` 로 찍혔다. 여기서 더 파고들 단서가 QMI 쪽에는 없었다. 대신 AT 쪽에서 IMS 기능을 묻는 명령 두 개, 3GPP 의 IMS 등록 상태 조회 `AT+CIREG?` 와 Quectel 의 IMS 설정 `AT+QIMSCFG?` 가 둘 다 `ERROR` 였다. 이 두 결과를 합친 우리의 결론은 **이 펌웨어 변종은 모뎀 자체의 IMS 기능이 빠져 있어서 `ims` 형 프로파일로는 세션을 열지 않는다**는 것이다. 1140이 정확히 무엇을 뜻하는지는 확인하지 못했다 [검증 필요]. 그래서 8장의 통화 시험에서는 모뎀을 IMS 단말로 쓰지 않고, `internet` 세션을 그냥 IP 통로로 써서 PC 의 소프트웨어 IMS 클라이언트가 P-CSCF(172.22.0.21)와 직접 대화하게 했다. 그 경로가 UPF 의 NAT 를 타지 않게 예외 규칙을 둔 것이 7장의 `! -d 172.22.0.21/32` 다.

이 에피소드의 교훈은 하나다. **QMI 가 "성공"이라고 말해도 코어 로그로 확인한다.** 모뎀은 우리가 준 인자를 조용히 무시할 수 있고, 그것을 알려 주는 것은 SMF 의 `DNN[...]` 한 칸뿐이었다.

## 11d.8 세션이 이유 없이 죽기 시작했다: ModemManager

QMI 로 세션이 올라간 뒤 처리량을 재고 통화 시험을 준비하는 동안, 링크가 반복해서 죽었다. 어느 순간 핑이 이렇게 됐다.

```
2 packets transmitted, 0 received, 100% packet loss, time 1023ms
```

세션을 다시 올리면 몇 분은 되다가 또 죽었다. 이 현상의 주범으로 지목한 것이 **ModemManager** 다. ModemManager 는 리눅스 데스크톱·서버에서 모뎀을 자동으로 찾아 인터넷에 붙여 주는 시스템 데몬이고, NetworkManager 와 짝을 이룬다. 노트북에 LTE 모듈이 있으면 사용자가 아무것도 안 해도 붙는 것이 이 데몬 덕분이다. 하는 일을 순서대로 적으면, USB 장치가 꽂히면 그 장치의 모든 포트를 열어 AT 를 쳐 보고 QMI 를 말해 보며 각 포트의 정체를 분류하고, 제조사 플러그인을 골라 붙이고, SIM 을 읽고 망에 등록하고, 요청이 오면 자기 클라이언트 ID 로 데이터 세션을 올린다. 그리고 AT 포트를 열어 둔 채 URC 를 계속 듣는다. 우리 모뎀이 처음 꽂혔을 때 `mmcli -m` 출력이 그 분류 결과다.

```
  System   |                drivers: qmi_wwan, option
           |                 plugin: quectel
           |           primary port: cdc-wdm0
           |                  ports: cdc-wdm0 (qmi), ttyUSB0 (ignored), ttyUSB1 (gps),
           |                         ttyUSB2 (at), ttyUSB3 (at), wwan0 (net)
```

`ttyUSB0` 을 `ignored` 로 분류한 것도 눈여겨볼 만하다. 이 포트는 Qualcomm 의 진단(DIAG) 포트이고 AT 로 말을 걸어도 답하지 않기 때문에 ModemManager 가 건드리지 않는다. `ttyUSB1` 은 위성 위치 문장(NMEA)을 내보내는 GPS 포트다.

ModemManager 는 "이 모뎀은 내 것"이라는 전제로 돈다. 그래서 우리와 세 군데서 부딪혔다. 첫째, AT 포트를 쥐고 있었다. 처음 AT 를 보내려 했을 때 응답이 비어서 돌아왔고, 포트를 누가 쥐고 있는지 봤더니 이랬다.

```
                     사용자      PID 접근 명령
/dev/ttyUSB2:        root       1416 F.... ModemManager
/dev/ttyUSB3:        root       1416 F.... ModemManager
```

시리얼 포트는 한 바이트 스트림이라 두 프로세스가 동시에 읽으면 먼저 읽은 쪽이 가져간다. 우리 `pyserial` 이 보낸 명령의 응답을 ModemManager 가 먼저 읽어 간 것이다. 둘째, 자기 방식으로 세션을 올리려 했다. 셋째, 그리고 이것이 링크가 죽은 원인으로 우리가 지목한 것인데, 모뎀의 세션 상태를 자기 기준으로 정리했다.

대처는 두 단계였다. 처음에는 ModemManager 의 **inhibit**(억제) 기능을 썼다. `mmcli --inhibit-device=<장치 uid>` 는 "이 장치에서 손을 떼라"는 명령이고, 이 `mmcli` 프로세스가 떠 있는 동안만 효력이 있다. 그래서 우리는 매 작업마다 inhibit 를 백그라운드로 띄우고, 그 안에서 AT·QMI 작업을 하고, 끝나면 그 프로세스를 죽이는 식으로 스크립트를 짰다.

그런데 그 스크립트의 출력에는 매번 이런 줄이 섞여 있었다.

```
[1]+  나감 1                sudo mmcli --inhibit-device="$DEV" > /dev/null 2>&1
```

bash 가 알려 주는 "백그라운드 작업 1번이 종료 코드 1로 끝났다"는 줄이다. 즉 **inhibit 를 걸어 둔 줄 알았던 프로세스가 이미 실패해서 죽어 있던 경우가 있었다.** 당시에는 이 줄을 읽지 않고 지나갔다. 왜 실패했는지는 기록이 없다. 하나 짐작되는 것은 이 스크립트가 장치 uid 를 `mmcli -L` 의 모뎀 목록에서 뽑았는데, ModemManager 가 그 순간 모뎀을 목록에 올리지 않고 있었다면 uid 가 빈 문자열이 되어 `mmcli` 가 바로 오류로 끝났을 것이라는 점이다 [검증 필요]. 실제로 한 번은 `mmcli -L` 이 `No modems were found` 를 돌려준 기록도 있다.

그리고 나중에 `mmcli` 의 매뉴얼을 다시 읽다가, 처음 가정을 뒤흔드는 문장을 찾았다. inhibit 를 걸면 ModemManager 가 **그 모뎀을 비활성화하고, 따라서 진행 중인 연결을 끊는다**고 적혀 있다. 그리고 inhibit 를 풀면 ModemManager 는 모뎀을 다시 잡는다. 우리가 매 작업마다 inhibit 를 새로 걸고 풀었다는 것은, 바로 앞 작업에서 우리가 올려 둔 QMI 세션을 다음 작업의 inhibit 가 끊었을 수 있다는 뜻이다. 처음 우리는 "ModemManager 가 다시 잡으면서 자기가 모르는 클라이언트 ID 의 세션을 정리한다"고 설명했는데, 매뉴얼이 보장하는 것은 그보다 단순한 사실, **inhibit 자체가 연결을 끊는다**는 것이다. ModemManager 가 다시 잡을 때 정확히 어떤 QMI 메시지로 무엇을 정리하는지는 소스에서 확인하지 못했다 [검증 필요]. 확실한 것은 다음 단계의 결과다.

두 번째 단계는 ModemManager 에게 이 모뎀을 아예 보이지 않게 하는 것이었다. 서비스 자체를 끄는 방법도 있지만, 그러면 나중에 다른 WWAN 장치를 꽂았을 때 그것까지 관리를 못 받는다. 그래서 **udev 규칙**으로 이 모뎀 하나만 뺐다. udev 는 커널이 장치를 만들 때 사용자 공간에서 규칙에 따라 이름을 붙이고 속성을 다는 리눅스의 장치 관리자이고, ModemManager 는 장치에 `ID_MM_DEVICE_IGNORE=1` 이라는 속성이 붙어 있으면 손대지 않는다. 이 속성은 ModemManager 가 바로 이런 용도로 사용자에게 열어 둔 약속이다.

```
# /etc/udev/rules.d/99-private5g-modem-ignore.rules
ACTION=="add|change", SUBSYSTEM=="usb", ATTRS{idVendor}=="2c7c", ATTRS{idProduct}=="0801", ENV{ID_MM_DEVICE_IGNORE}="1"
ACTION=="add|change", SUBSYSTEM=="tty", ATTRS{idVendor}=="2c7c", ATTRS{idProduct}=="0801", ENV{ID_MM_DEVICE_IGNORE}="1"
ACTION=="add|change", SUBSYSTEM=="net", ATTRS{idVendor}=="2c7c", ATTRS{idProduct}=="0801", ENV{ID_MM_DEVICE_IGNORE}="1"
```

`2c7c:0801` 은 Quectel 의 USB 제조사 번호와 RM520N-GL 의 제품 번호다. USB 장치 자체, 그것이 만든 시리얼 포트, 네트워크 장치 세 갈래에 모두 같은 속성을 달았다. 규칙을 다시 읽히고(`udevadm control --reload`), 이미 꽂힌 장치에 다시 적용하고(`udevadm trigger --action=change`), ModemManager 를 재시작한 뒤 확인했다.

```
=== ModemManager 가 보는 모뎀 (없어야 정상) ===
No modems were found
=== AT 포트 점유 (비어야 정상) ===
(출력 없음)
```

이후로는 inhibit 없이 AT 와 QMI 를 썼고, 세션은 더 이상 죽지 않았다. 통화 시험은 두 번 연속 전 구간이 성립했고, 그 뒤의 문자·영상 시험(8장)까지 링크는 한 번도 끊기지 않았다. 원인에 대한 우리 설명에는 빈칸이 있지만, 처방의 효과는 측정으로 확인됐다.

같은 이유로 NetworkManager 가 `wwan0` 을 건드리지 않게 하는 것도 직접 제어의 조건이다. NetworkManager 는 udev 속성 `NM_UNMANAGED=1` 이 붙은 장치를 관리하지 않는다. 우리 박스에서는 NetworkManager 에 모뎀 연결이 하나도 설정되어 있지 않아 따로 손대지 않았다.

이 절을 일반화하면 이렇다. **모뎀을 직접 제어하려면 첫 단계로 그 모뎀을 OS 의 자동 관리에서 빼낸다.** 그렇지 않으면 "왜 가끔 되고 가끔 안 되나"를 며칠 쫓게 된다. 우리는 반나절을 썼다.

🔎 지금 할 일: `mmcli -L` 로 ModemManager 가 지금 어떤 모뎀을 쥐고 있는지 보고, `sudo fuser -v /dev/ttyUSB* /dev/cdc-wdm0` 로 포트 점유를 확인한다. 직접 제어할 모뎀이면 `lsusb` 로 VID(USB 제조사 번호)와 PID(제품 번호)를 확인해 위 규칙을 자기 장치 번호로 쓴다. 적용 확인은 `udevadm info /dev/ttyUSB2 | grep ID_MM`.

## 11d.9 데이터 경로의 진화: PPP → 이더넷 흉내 → raw IP

제어가 해결됐으니 이제 IP 패킷이 실제로 어디로 흐르는지를 본다. 11d.1 에서 본 `raw_ip = Y` 와, 모뎀이 준 `/29` 라는 이상한 서브넷이 여기서 풀린다. 역사 순서로 보면 각 설계가 왜 나왔는지 보인다.

첫 세대는 11b 에서 본 **PPP over 시리얼**이다. `ATD*99#` 으로 데이터 모드에 들어가고, IP 패킷을 PPP 프레임에 싸서 시리얼 선으로 보낸다. 시리얼은 바이트가 끝없이 이어지는 흐름이라 "어디서 한 패킷이 끝나는가"를 PPP 가 직접 표시해야 한다. 그래서 **HDLC**(High-level Data Link Control, 1970년대 메인프레임 통신에서 나온 프레임 규약) 방식을 빌려 패킷 앞뒤에 `0x7E` 깃발 바이트를 두고, 패킷 안에 `0x7E` 가 나오면 이스케이프 바이트로 바꾸는 바이트 스터핑을 한다. 와이어샤크에서 PPP 캡처를 열면 보이는 그 모양이다. 문제는 이 작업을 패킷의 모든 바이트에 대해 CPU 가 해야 한다는 것과, 데이터 모드에 있는 동안 같은 선으로 제어 명령을 못 보낸다는 것이다. 수 Mbps 를 넘기면 버겁다. 지금도 거의 모든 LTE/5G 모뎀이 `ATD*99#` 을 받아 주지만, 우리는 이 길을 쓰지 않았다.

두 번째 세대는 **USB 로 이더넷 흉내 내기**다. USB 가 퍼지자 모뎀이 "나는 USB 이더넷 어댑터다"라고 자기를 소개하는 방식이 나왔다. USB 표준(CDC)의 **ECM**(Ethernet Control Model, 패킷마다 USB 전송 한 번)과 그것을 개선해 여러 패킷을 한 번에 묶어 보내는 **NCM**(Network Control Model)이 대표다. PC 에는 `usb0` 같은 평범한 이더넷 장치가 생기고, 모뎀이 그 안에서 작은 DHCP 서버까지 흉내 내 IP 를 준다. 쓰기는 편하지만 대가가 있다. 무선 구간에는 MAC 주소라는 개념이 없는데, 이더넷인 척하느라 모든 패킷에 14바이트 이더넷 헤더를 붙였다 뗐다 하고 ARP 질의에도 답해야 한다.

세 번째 세대가 Qualcomm 의 **RmNet**, 즉 raw IP 다. 이더넷 흉내를 버리고 USB 벌크 통로로 **IP 패킷만** 보낸다. 리눅스 `qmi_wwan` 드라이버는 이 방식을 `wwan0` 으로 드러내고, sysfs 의 `raw_ip` 파일로 모드를 고른다. 커널 문서(`Documentation/ABI/testing/sysfs-class-net-qmi`)에 따르면 기본값은 `N`(802.3 이더넷 프레임)이고, 펌웨어가 raw IP 로 설정되어 있으면 사용자 공간이 이것을 `Y` 로 바꿔야 하며, 드라이버와 펌웨어의 모드를 맞추는 책임은 사용자 공간에 있다. 우리 박스에서 이미 `Y` 였던 것은 ModemManager 가 처음 모뎀을 잡았을 때 맞춰 둔 것으로 보인다 [검증 필요]. `raw_ip` 가 `Y` 인 `wwan0` 에서 `tcpdump` 를 하면 이더넷 헤더 없이 IP 헤더부터 시작하는 패킷이 보인다. 와이어샤크는 이것을 링크 타입 "Raw IP" 로 표시한다.

raw IP 에 얇은 머리글을 하나 더 붙이면 세션 여러 개를 한 장치로 나를 수 있다. 그 머리글이 **QMAP**(Qualcomm MAP, 다중화 헤더)이고, 같은 커널 문서의 `add_mux` 파일에 번호를 쓰면 세션마다 `qmimux0` 같은 장치가 따로 생긴다. 인터넷 세션과 IMS 세션을 동시에 PC 로 받고 싶을 때 쓰는 구조다. 우리 실험은 한 번에 세션 하나만 썼으므로 쓰지 않았다.

raw IP 의 대가는 **DHCP 가 없다**는 것이다. 이더넷 흉내가 없으니 그 위의 DHCP 도 없다. IP 는 QMI 의 Get Current Settings 로 묻고 손으로 붙인다. 우리가 한 그대로다.

```
qmicli -d /dev/cdc-wdm0 --wds-get-current-settings --client-cid=17 --client-no-release-cid
                                          # 10.45.0.3, 마스크 255.255.255.248, 게이트웨이 10.45.0.4
ip link set wwan0 up
ip addr add 10.45.0.3/29 dev wwan0
ip route add 172.22.0.21/32 via 10.45.0.4 dev wwan0
```

여기서 `/29` 와 게이트웨이 `10.45.0.4` 는 **실제 망에 존재하지 않는 숫자**다. SMF 는 이 단말에게 주소 하나(`10.45.0.3`)를 줬을 뿐이고, 5G 코어 어디에도 10.45.0.0/29 라는 서브넷이나 `.4` 라는 라우터는 없다. 모뎀이 PC 의 IP 스택을 만족시키려고, 받은 주소 주변으로 8칸짜리 가짜 서브넷을 꾸미고 그 안의 이웃 주소 하나를 게이트웨이라고 불러 준 것이다. 실제 상대는 7장의 UPF 다.

이 가짜 게이트웨이가 얼마나 가짜인지 우리 기록 하나가 보여 준다. 몇 번째 재연결에서 모뎀은 이렇게 답했다.

```
IP=10.45.0.7 GW=10.45.0.8
Error: Nexthop has invalid gateway.
3 packets transmitted, 3 received, 0% packet loss
```

`10.45.0.7/29` 의 서브넷은 `10.45.0.0~10.45.0.7` 이다. 모뎀이 준 게이트웨이 `.8` 은 **그 서브넷 밖**이라 리눅스가 경로 추가를 거부했다. 그런데 핑은 3개 모두 돌아왔다. raw IP 장치에는 ARP 가 없으므로 다음 홉 주소를 실제로 찾아가는 일이 없고, `wwan0` 으로 내보낸 패킷은 게이트웨이 값과 상관없이 전부 같은 USB 통로로 모뎀에 들어간다. `ping -I wwan0` 처럼 장치를 직접 지정하면 경로 테이블의 게이트웨이를 아예 보지 않는다. 즉 raw IP 링크에서 게이트웨이는 장식이다. 그래서 더 정직한 경로 설정은 게이트웨이 없이 `ip route add 172.22.0.21/32 dev wwan0` 이다. 이것을 모르면 "게이트웨이 10.45.0.4 로 핑이 안 가요"를 붙잡고 헤맨다. 그 주소에는 아무도 없다.

세 세대를 한 번에 놓고 보면 이렇다.

| 세대 | 전송 | PC 쪽 장치 | IP 설정 | 패킷당 부담 | 제어와의 관계 |
|---|---|---|---|---|---|
| PPP | 시리얼 | `ppp0` | PPP 의 IPCP 협상 | 바이트 스터핑, CPU | 데이터 모드 동안 제어 불가 |
| ECM/NCM | USB | `usb0` (이더넷) | DHCP | 이더넷 헤더 14바이트, ARP | 별도 제어 채널 |
| RmNet raw IP | USB 벌크 | `wwan0` | QMI 로 묻고 손으로 | 없음 (QMAP 쓰면 몇 바이트) | QMI 와 짝 |

🔎 지금 할 일: `ip -d link show wwan0` 로 링크 종류가 이더넷이 아님을 확인하고, `tcpdump -i wwan0 -c 3 -XX` 로 첫 바이트가 `45`(IPv4, 헤더 20바이트)로 시작하는지 본다. 이더넷 장치였다면 처음 12바이트가 MAC 주소다.

## 11d.10 MBIM: 같은 생각의 공개 표준

QMI 가 Qualcomm 만의 것이라는 점은 운영체제를 만드는 쪽에 불편했다. 모뎀 제조사마다 드라이버와 관리 프로그램을 따로 깔아야 했기 때문이다. Microsoft 가 이것을 정리하자고 밀었고, USB 표준을 관리하는 USB-IF(USB Implementers Forum)가 **MBIM**(Mobile Broadband Interface Model)을 공개 표준으로 내놓았다. 구조는 QMI 와 거의 같다. 서비스를 UUID 로 구분하고, 그 안의 명령을 번호로 부르고, 인자를 정해진 구조체로 싣는다. Windows 는 MBIM 을 기본 드라이버로 지원하고, 리눅스는 `cdc_mbim` 드라이버와 `libmbim`(`mbimcli`)으로 지원한다.

같은 Quectel 모뎀이 USB 구성(composition)을 바꾸면 QMI 장치로도 MBIM 장치로도 보일 수 있다. 바꾸는 명령은 Quectel 의 `AT+QCFG="usbnet",<번호>` 다. QCFG 는 Quectel Configuration, 즉 Quectel 이 모뎀의 각종 설정을 한데 모아 둔 3층 명령이다. 그런데 우리가 가진 두 매뉴얼, 같은 5G 모듈 세대의 앞선 판인 RG50xQ&RM5xxQ V1.1.1 과 우리 모듈을 직접 다루는 **RG520N&RG52xF&RG530F&RM520N&RM530N V1.0.0**(제목에 늘어선 이름은 같은 칩을 쓰는 Quectel 형제 모듈들이다. RG 는 기판에 납땜하는 형태, RM 은 우리가 쓴 M.2 카드 형태의 계열 이름이고, 뒤의 숫자와 끝 글자가 세대와 변종이다)의 본문에서는 이 항목을 찾지 못했다. 그래서 인자 번호와 각 번호의 뜻은 이 책에서 확인하지 못했다 [검증 필요]. 바꿀 필요가 생기면 자기 펌웨어의 매뉴얼로 확인하고, 바꾼 뒤에는 모뎀이 USB 에서 다시 열거되므로 11d.5 의 장치 이름이 전부 바뀐다는 점을 기억한다. 우리 모뎀은 받은 그대로 QMI 모드였다.

둘 중 무엇을 쓸지는 목적에 달렸다. QMI 는 Qualcomm 칩의 거의 모든 기능에 닿고, MBIM 은 표준이 정한 범위만 다루지만 칩 제조사와 무관하다. 실험실처럼 칩 깊숙이 들어가야 하는 곳에서는 QMI 가 낫고, 여러 제조사의 모뎀을 똑같이 다뤄야 하는 제품에서는 MBIM 이 낫다.

## 11d.11 스마트폰 안에서는: RIL

지금까지는 PC 에 꽂힌 모뎀의 이야기였다. 휴대폰 안에서도 구조는 같다. 휴대폰에는 앱이 도는 프로세서(**AP**, Application Processor)와 전파를 다루는 모뎀 프로세서(**BP**, Baseband Processor, 줄여서 베이스밴드)가 따로 있고, 둘은 칩 안의 통로로 AT 나 QMI 를 주고받는다. 안드로이드에서는 그 대화를 **RIL**(Radio Interface Layer)이 맡는다. 전화 앱이 통화를 걸면 안드로이드 텔레포니 프레임워크가 요청을 만들고, RIL 데몬(`rild`)이 그것을 제조사가 만든 RIL 라이브러리에 넘기고, 그 라이브러리가 "이 모뎀이 알아듣는 말"인 AT 나 QMI 로 번역해 베이스밴드에 보낸다. 우리 실험실에서 `qmicli` 와 `pyserial` 이 하던 일을 폰에서는 이 라이브러리가 한다.

중요한 점은 이 번역기가 **AP 쪽에서 돈다**는 것이다. 따라서 AP 가 장악되면 RIL 을 거쳐 모뎀에 명령을 내릴 수 있다. 반대로 USB 로 AT 포트가 바깥에 노출되어 있으면 AP 를 거치지도 않고 모뎀에 닿을 수 있다. 이 경계들이 11e 의 주제다.

## 11d.12 우리 실험의 제어 지도

이 절에서 일어난 일을 "무엇을 어느 길로 했나"로 정리한다.

| 할 일 | 쓴 길 | 이유 |
|---|---|---|
| 모뎀 정보, SIM 상태, IMSI | AT (`ATI`, `+CPIN?`, `+CIMI`, `+QCCID`) | 읽기만 하니 글자로 충분 |
| 5G 단독·n78 전용 강제 | AT (`+QNWPREFCFG`) | 제조사 명령, QMI 쪽 동등 기능을 찾지 않음 |
| 등록 상태, 셀 측정 | AT (`+C5GREG?`, `+QENG`) | 사람이 읽기 쉬움 (11f) |
| 무선부 재초기화, 세션 전부 지우기 | AT (`+CFUN=0` → `+CFUN=1`) | |
| 주변 망 스캔 | AT (`+COPS=?`) | `AT+QSCAN` 은 NR 미지원 |
| **데이터 세션 올리기** | **QMI** (`--wds-start-network`) | AT 세션은 `wwan0` 에 묶이지 않음, `+QNETDEVCTL` 없음 |
| **IP·게이트웨이 조회** | **QMI** (`--wds-get-current-settings`) | raw IP 라 DHCP 없음 |
| 데이터 흘리기 | `wwan0` raw IP | |
| ModemManager 배제 | `mmcli --inhibit-device` → udev `ID_MM_DEVICE_IGNORE` | inhibit 는 연결을 끊는다 |

한 줄로 줄이면 **상태를 보는 것은 AT, 세션을 만드는 것은 QMI** 다. 실험실에서는 이 분업이 가장 덜 꼬인다. 단, AT 와 QMI 로 같은 세션을 동시에 만지면 11d.4 의 241번 오류를 만난다. 세션은 한 길로만 만든다. 제품을 만든다면 전부 QMI(또는 MBIM)로 통일한다.

## 11d.13 요약

| 질문 | 답 |
|---|---|
| AT 로 세션을 올렸는데 왜 PC 로 안 왔나 | 세션이 `wwan0` 의 데이터 통로에 묶이지 않았다. 그 연결을 만드는 것이 QMI Start Network 다 |
| QMI 는 무엇인가 | Qualcomm 의 서비스(번호)·메시지(번호)·TLV 바이너리 RPC. `/dev/cdc-wdm0` + libqmi |
| QMI 바이트의 특징 | QMUX 6바이트 + SDU 7바이트 + TLV. 정수는 리틀 엔디언 (`10.45.0.3` = `03 00 2D 0A`) |
| 오류는 어떻게 읽나 | 결과 TLV(0x02) 다음 verbose 이유(0x11)의 분류 번호. 2 = 모뎀 내부, 6 = 망 거절 |
| 커널은 QMI 를 아는가 | 모른다. `cdc_wdm` 은 바이트를 USB 제어 전송에 싣기만 한다. 해석은 libqmi 와 모뎀 펌웨어 |
| 클라이언트 ID 가 왜 중요한가 | 세션이 거기 매인다. `--client-no-release-cid` 없이는 명령 종료와 함께 세션이 내려간다 |
| `apn=ims` 는 왜 무시됐나 | 이 펌웨어는 IMS 기능이 없는 변종으로 보인다. QMI 성공을 SMF 로그로 확인할 것 |
| ModemManager 는 왜 문제였나 | 포트를 쥐고, inhibit 할 때 연결을 끊는다. udev `ID_MM_DEVICE_IGNORE=1` 로 이 모뎀만 뺐다 |
| `wwan0` 에 왜 DHCP 가 없나 | raw IP. 이더넷 흉내를 버렸다. QMI 로 묻고 손으로 붙인다 |
| `/29` 와 게이트웨이는 무엇인가 | 모뎀이 꾸민 가짜. raw IP 에서 게이트웨이는 장식이고 실제 상대는 UPF |

## 점검 문제

1. `AT+QPING` 이 성공했는데 PC 에서 `wwan0` 으로 핑이 안 된다. 두 결과가 모순되지 않는 이유를 "누가 핑을 보냈는가"로 설명하라.
2. TLV 방식이 AT 의 쉼표 위치 방식보다 펌웨어 판본 변화에 강한 이유를, 모르는 종류 번호를 만났을 때 파서가 하는 일로 설명하라.
3. `verbose call end reason (6, ...)` 을 받았다. 다음에 열어 볼 로그는 모뎀 쪽인가 코어 쪽인가?
4. QMI 응답의 IPv4 주소 TLV 값이 `05 00 2D 0A` 다. 점 표기 주소로 바꿔라.
5. `--client-no-release-cid` 를 빠뜨리면 무슨 일이 일어나는가? 데이터베이스 연결에 빗대 설명하라.
6. ModemManager 서비스를 통째로 끄지 않고 udev 로 한 장치만 뺀 이유는?
7. 모뎀이 준 게이트웨이가 서브넷 밖이라 `ip route` 가 거부했는데 핑은 됐다. 왜인가?

## 직접 해보기

- 같은 순간에 `qmicli -d /dev/cdc-wdm0 --nas-get-signal-info` 와 `AT+QENG="servingcell"` 을 쳐서 RSRP 가 같은지 비교하라. 같은 측정값을 두 길로 읽는 것이다. 다르면 두 명령이 측정을 갱신하는 주기를 의심하라.
- `qmicli --wds-get-packet-service-status --client-cid=<n> --client-no-release-cid` 로 세션 상태를 보고, `--wds-stop-network=<handle> --client-cid=<n>` 으로 내린 뒤 다시 보라. 핸들과 번호표가 각각 어디에 쓰이는지 손으로 확인한다.
- `usbmon` 으로 `qmicli --dms-get-ids` 한 번을 캡처해 와이어샤크에서 열고, 11d.4 의 표를 들고 QMUX 헤더 6바이트와 결과 TLV 를 직접 찾아라.
- `ls -l /dev/cdc-wdm0 /dev/ttyUSB*` 로 권한과 그룹을 확인하라. 이 파일을 누가 열 수 있는가가 11e 의 출발점이다.

---

> **출처와 확인 범위**: QMI 서비스 번호는 libqmi `src/libqmi-glib/qmi-enums.h` 의 `QmiService`(CTL 0x00, WDS 0x01, DMS 0x02, NAS 0x03, QOS 0x04, WMS 0x05, PDS 0x06, VOICE 0x09, UIM 0x0B, PBM 0x0C, PDC 0x24). WDS 메시지 번호(Start 0x0020, Stop 0x0021, Packet Service Status 0x0022, Current Settings 0x002D)와 TLV 번호·바이트 순서는 libqmi `data/qmi-service-wds.json`, 오류 14 와 verbose 이유 분류(1 Mobile IP, 2 internal, 3 CM, 6 3GPP)·241 은 `qmi-errors.h`·`qmi-enums-wds.h` 와 대조했다. 11d.4 의 바이트 열은 그 정의로 복원한 것이고 캡처가 아니다. inhibit 가 연결을 끊는다는 것은 `mmcli(1)` 매뉴얼, `ID_MM_DEVICE_IGNORE` 가 사용자용 제외 속성이라는 것은 ModemManager 의 변경 기록 파일, `raw_ip`·`add_mux` 동작은 커널 `Documentation/ABI/testing/sysfs-class-net-qmi`. `AT+QCFG="usbnet"` 인자, CM 이유 1140 의 뜻, ModemManager 가 재점유 때 보내는 정확한 메시지는 미확인.

*다음 절: 11e. 공격 표면과 신뢰 경계 — 베이스밴드 분리, 가짜 기지국, USB 로 노출된 AT, SIM 툴킷, 그리고 실험실 위생*
