# 부록 B. 명령 레퍼런스

이 실험실에서 실제로 쳤던 명령을 **작업 순서대로** 모았다. 설명은 한 줄로 줄이고, 왜 그렇게 하는지는 괄호 안 장 번호에서 찾는다. 모든 키·관리자 번호·주소 가운데 실험실마다 다른 것은 `<…>` 자리표시자로 바꿨다. 경로는 `~/work/private5g` 를 `$P5` 로, 업스트림 클론(`$P5/upstream` 이 가리키는 곳)을 `$UP` 로 쓴다.

⚠️ 표시가 붙은 명령은 전파를 내거나, 되돌릴 수 없거나, 망을 끊는다. 실행 전에 무엇이 일어나는지 다시 읽어라.

## B.1 호스트와 장치 확인 (9장)

```bash
lsusb | grep -E '2500:0020|2c7c:0801'        # B210(Ettus) 과 RM520N-GL(Quectel) 이 보이는가
lsusb -t                                      # B210 줄이 5000M 이면 USB 3.0. 480M 이면 케이블부터 의심
uhd_find_devices                              # 호스트에서 본 USRP 목록과 serial (컨테이너 밖, ~/.uhd/uhd.conf 사용)
ls -l /dev/ttyUSB* /dev/cdc-wdm0              # 모뎀 포트와 권한. ttyUSB2/3=AT, cdc-wdm0=QMI
ip -br link | grep wwan                       # 모뎀 네트워크 장치
mmcli -L                                      # ModemManager 목록. 우리 모뎀이 없어야 정상(udev 제외)
udevadm info /dev/cdc-wdm0 | grep MM_DEVICE_IGNORE
sudo udevadm control --reload && sudo udevadm trigger    # udev 규칙을 고친 뒤
```

## B.2 이미지와 설정 배포 (9장, 부록 C)

```bash
docker pull ghcr.io/herlesupreeth/docker_open5gs:master
docker tag  ghcr.io/herlesupreeth/docker_open5gs:master docker_open5gs
#   docker_kamailio, docker_pyhss, docker_mysql, docker_dns, docker_rtpengine,
#   docker_metrics, docker_srsran 도 같은 두 줄

$P5/bin/deploy-configs.sh --check             # 정본과 클론의 차이만 본다 (기대값: "차이 0 건")
$P5/bin/deploy-configs.sh                     # 정본 → 클론 복사
```

## B.3 코어 (5·9장)

```bash
$P5/bin/core-ctl.sh START                     # 배포 → compose up → "코어 준비 완료 (NF 5/5 …)" 까지 대기
$P5/bin/core-ctl.sh STATUS
$P5/bin/core-ctl.sh STOP
docker logs amf --since "$(docker inspect amf --format '{{.State.StartedAt}}')" | grep 'NFInstance associated'
docker exec amf tail -40 /open5gs/install/var/log/open5gs/amf.log     # 등록·인증 실패는 여기부터
docker exec amf grep -n 'tac\|mcc' /open5gs/install/etc/open5gs/amf.yaml   # 치환 결과 확인
```

## B.4 기지국 (10장) ⚠️ 송신

```bash
grep -o 'serial=[A-Z0-9]*' $P5/configs/srsran/gnb.yml   # 케이블에 묶인 SDR 의 serial 인가. 아니면 멈춘다
cd $UP && docker compose -p docker_open5gs -f srsgnb.yaml up -d      # ⚠️ 송신 시작
docker logs -f srsgnb                         # "gNB started", N2 연결, U/O 가 쏟아지지 않는지
docker logs srsgnb 2>&1 | grep dl_ssb_arfcn   # 셀 요약 한 줄: pci, 대역폭, ARFCN, SSB
docker stop srsgnb                            # 송신 정지. 케이블을 만지기 전에 반드시
```

시뮬레이션(전파 없음):

```bash
$P5/bin/ran-ctl.sh START n78                  # OAI gNB + OAI nr-UE, rfsim (TCP 로 샘플 교환)
$P5/bin/ran-ctl.sh START n3                   # srsRAN gNB + srsUE, ZMQ, 15 kHz
$P5/bin/ran-ctl.sh STOP                       # n78 과 n3 는 같은 IMSI 를 써서 동시 기동 금지
$P5/bin/selftest.sh n78                       # 코어→RAN→UE→터널→8.8.8.8→정본 일치, 6단계 자가진단
```

## B.5 SIM 카드 (4a장) ⚠️ ADM 은 틀린 횟수가 쌓이면 복구 불가

```bash
sudo systemctl start pcscd                    # 카드 리더 데몬. 카드 작업 때만
python3 pySim-read.py -p0                     # 리더 0번의 카드를 읽기만 한다
python3 pySim-shell.py -p0 --apdu-trace       # 대화형 셸, 오가는 APDU 바이트를 함께 출력
python3 pySim-shell.py -p0 --script write.txt # 스크립트로 한 번에 (관리자 키를 실수로 두 번 보내지 않게)
```

`write.txt` 의 모양 (값은 전부 자리표시자):

```
verify_adm <ADM1>
select ADF.USIM
select EF.IMSI
update_binary_decoded {"imsi":"<IMSI>"}
select ADF.USIM
select EF.USIM_AUTH_KEY
update_binary_decoded {…"k":"<KI>","op_opc":"<OPC>"…}
select MF
select ADF.USIM
select EF.MSISDN
update_record_decoded 1 {"alpha_id":"","len_of_bcd":7,"ton_npi":{…"international"…"isdn_e164"},"dialing_nr":"<MSISDN>"}
```

`<ADM1>` 은 카드 제조사가 준 값만 쓴다. 추측해서 넣지 않는다.

## B.6 모뎀: AT (11~13, 16)

셸 함수 (간이용. 2초 안에 끝나는 명령만 — 13.7 의 한계 참조):

```bash
PORT=/dev/ttyUSB3
at() {
  sudo stty -F $PORT 115200 raw -echo 2>/dev/null
  { printf '%s\r' "$1" | sudo tee $PORT >/dev/null; sudo timeout 2 cat $PORT; } 2>/dev/null \
    | tr -d '\r' | grep -vE "^$|^$1$"
}
```

| 할 일 | 명령 | 기대 |
|---|---|---|
| 정체 | `ATI`, `AT+CGMR` | 모델·펌웨어 버전 |
| 오류를 글자로 | `AT+CMEE=2` | `OK` |
| SIM 상태 | `AT+CPIN?` | `+CPIN: READY` |
| 카드 번호 | `AT+QCCID` | 쓴 ICCID |
| 가입자 번호 | `AT+CIMI` | 쓴 IMSI |
| 카드 교체 후 재초기화 | `AT+CFUN=0` → `AT+CFUN=1` | URC 줄줄이, 마지막에 등록 |
| 5G SA 만 | `AT+QNWPREFCFG="mode_pref",NR5G` | `OK` (적용은 재시작 후) |
| n78 만 스캔 | `AT+QNWPREFCFG="nr5g_band",78` | `OK` |
| 모뎀만 재시작 ⚠️ 데이터 끊김 | `AT+CFUN=1,1` | 모뎀이 USB 에서 빠졌다 다시 붙음 |
| 통신사 프로파일 | `AT+QMBNCFG="List"` | 활성 프로파일 확인 |
| 주변 망 스캔 | `AT+COPS=?` | 60~100초. `"00101",12` 가 우리 셀 |
| 등록 상태 | `AT+C5GREG=2` 후 `AT+C5GREG?` | `2,1,…` (1=홈 등록) |
| 셀 측정 | `AT+QENG="servingcell"` | RSRP·SINR·PCI·ARFCN (16) |
| 데이터 프로파일 | `AT+CGDCONT?` | `internet`, `ims` … |
| 세션 주소 | `AT+CGPADDR=1` | 10.45.0.x |
| 모뎀 자체 ping | `AT+QPING=1,"8.8.8.8"` | PC 경로와 무관하게 무선·코어 확인 |

## B.7 모뎀: QMI 와 데이터 경로 (14, 7장)

```bash
qmicli -d /dev/cdc-wdm0 --dms-get-revision                     # 읽기만 하는 첫 시험
cat /sys/class/net/wwan0/qmi/raw_ip                            # Y 여야 한다 (raw IP 모드)
qmicli -d /dev/cdc-wdm0 --wds-start-network="ip-type=4,apn=internet" --client-no-release-cid
#   → 출력의 CID 와 패킷 데이터 핸들을 적어 둔다. CID 를 놓으면 세션이 닫힌다
qmicli -d /dev/cdc-wdm0 --wds-get-current-settings --client-cid=<CID> --client-no-release-cid
#   → IPv4 주소, 서브넷(/29), 게이트웨이, DNS
sudo ip link set wwan0 up
sudo ip addr add <UE_IP>/29 dev wwan0
sudo ip route add <PCSCF_IP>/32 via <GW_FROM_QMI> dev wwan0    # IMS 만 무선으로 (8장)
qmicli -d /dev/cdc-wdm0 --nas-get-signal-info                  # RSRP/RSRQ/SINR 를 QMI 로
```

## B.8 측정 (17장)

```bash
ping -I wwan0 -c 20 10.45.0.1                 # 단말 → UPF. 무선 + 터널 왕복
ping -I wwan0 -c 20 8.8.8.8                   # 위 + NAT + 바깥
docker exec upf iperf3 -s -B 10.45.0.1 &      # 서버는 UPF 의 ogstun 쪽에
iperf3 -c 10.45.0.1 -B <UE_IP>       -t 15 -i 5     # 상향
iperf3 -c 10.45.0.1 -B <UE_IP> -R    -t 15 -i 5     # 하향
iperf3 -c 10.45.0.1 -B <UE_IP> -R -u -b 100M -t 15  # 하향 UDP — TCP 상향 ACK 병목과 분리
```

`-B` 로 `wwan0` 주소에 묶지 않으면 호스트 기본 경로(이더넷)로 나가 무선을 타지 않은 숫자가 나온다.

## B.9 캡처 (README 필터 표, 9.8)

```bash
docker network ls | grep open5gs              # 브리지 ID → br-<ID>
sudo tcpdump -i br-<ID> -w core.pcap          # NGAP, GTP-U, PFCP, HTTP/2, SIP, Diameter 전부
docker exec upf tcpdump -i ogstun -w - > ue_inner.pcap    # 터널을 벗긴 단말 패킷
sudo tcpdump -i wwan0 -w ue_side.pcap         # 단말 쪽에서 본 패킷
sudo modprobe usbmon && sudo tcpdump -i usbmon<버스번호> -w qmi.pcap   # QMI 바이트 (14)
```

기지국 내부 캡처는 `gnb.yml` 의 `pcap:` 블록에서 `mac_enable`, `ngap_enable`, `n3_enable` 등을 `true` 로 바꾸고 재기동한다(10.3).

## B.10 가입자와 IMS (6·8장)

```bash
docker exec mongo mongosh open5gs --quiet --eval \
  'db.subscribers.findOne({imsi:"<IMSI>"}).slice[0].session.map(s=>({dnn:s.name, qi:s.qos.index, pcc:(s.pcc_rule||[]).map(r=>r.qos.index)}))'
#   → 세션별 기본 5QI 와 PCC 규칙(음성 1, 영상 2)이 있는가

python3 tools/ims_call.py <PCSCF_IP> <SRC_IP> reg-a          # A 등록만 (AKAv1-MD5)
python3 tools/ims_call.py <PCSCF_IP> <SRC_IP> callee 10      # B 등록 후 착신 대기, 10초 통화
python3 tools/ims_call.py <PCSCF_IP> <SRC_IP> caller 10      # A 등록 후 B 에게 발신
VIDEO=1 python3 tools/ims_call.py <PCSCF_IP> <SRC_IP> caller 10   # SDP 에 m=video 추가 (8.6a)
#   → 5QI 2 PCC 규칙이 DB 에 있어야 PCF 가 Flow 를 연다 (7.8)

# MMS (8.7a). 알림의 URL 경로는 매번 다르게 — 같으면 단말이 중복으로 버린다 (사례 21)
MMS_TID=T1 python3 tools/mmsc.py serve 0.0.0.0 8099 image.jpg <A_MSISDN> <B_MSISDN> "제목"
PUSH=$(MMS_TID=T1 python3 tools/mmsc.py notify "http://<호스트>:8099/m/$(date +%s)" <크기> <A_MSISDN>)
python3 tools/ims_sms_mt.py 172.22.0.20 <B_MSISDN> <A_MSISDN> "hex:$PUSH"
python3 tools/ims_sms_mt.py 172.22.0.20 <B_MSISDN> <A_MSISDN> '<긴 본문>'   # UDH 살린 분할 문자 (8.7)
adb shell content query --uri content://telephony/carriers \
  --projection _id:name:type:mmsc --where "numeric='<MCCMNC>'"   # mmsc 칸이 비면 MMS 는 시작도 못 한다
python3 tools/ims_call.py <PCSCF_IP> <SRC_IP> sms-send 3 'sip:<B_MSISDN>@<REALM>' '<본문>' <B_MSISDN>   # TPDU 로 문자
python3 tools/ims_call.py <PCSCF_IP> <SRC_IP> sms-recv       # B 로 등록해 문자 수신
python3 tools/ims_call.py <PCSCF_IP> <SRC_IP>                # 둘 다 한 프로세스에서: 등록→통화→BYE
docker logs pcscf 2>&1 | tail -50             # 412/488/500 은 여기서 이유를 찾는다 (18장)
docker logs rtpengine 2>&1 | tail             # 미디어가 한쪽만 흐를 때
```

`tools/ims_call.py` 의 가입자 키 자리(`<KI_A>` 등)는 저장소본에서 비워 두었다. 자기 PyHSS·카드 값으로 채운다. `<SRC_IP>` 는 UA 가 묶일 주소로, 모뎀 쪽에서 쏠 때는 `wwan0` 의 IMS 세션 주소다(9.8 의 NAT 예외가 이 주소를 그대로 P-CSCF 에 보여 준다).

## B.11 되돌리기와 정리

```bash
$P5/bin/core-ctl.sh STOP && docker stop srsgnb            # 망 전체 정지 (컨테이너·볼륨 보존)
cp $P5/configs/_backup/<파일>.bak $P5/configs/<경로>       # 정본을 백업으로 되돌림
$P5/bin/deploy-configs.sh                                 # 그다음 배포, 재기동
sudo systemctl stop pcscd                                 # 카드 작업 끝
```
