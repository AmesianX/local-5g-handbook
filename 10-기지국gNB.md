# 10. 기지국: srsRAN gNB 를 띄우고, 그 안에서 벌어지는 일을 전부 들여다본다

## 10.1 이 장을 어떻게 읽을 것인가

기지국은 이 시스템의 **핵심 서비스**다. 코어의 열 개 조각은 전부 소프트웨어이고 독자가 아는 세상(REST, DB, 프로토콜 파서)에 산다. 기지국만이 **전파와 소프트웨어의 경계**에 서 있다. 그래서 가장 많이 틀어지고, 틀어지면 로그에 아무것도 안 남는다. 이 장은 그 기지국을 **처음 켠 날부터 단말이 붙은 날까지** 우리가 본 것을 순서대로 적는다. 중간에 우리가 틀린 것도 그대로 둔다.

우리 기지국은 **srsRAN Project** 의 gNB 다. 오픈소스 C++ 구현이고, 도커 컨테이너 `srsgnb` 안에서 돈다. 전파는 2 장의 B210 이 낸다. 이 장을 다 읽으면 `gnb.yml` 의 모든 줄이 무슨 뜻인지, 기동 로그의 모든 줄이 무엇을 보고하는지, 단말이 붙는 10 초 동안 기지국 안에서 무슨 일이 일어나는지, 그리고 **무엇을 바꿔도 되고 무엇을 바꾸면 전파법을 어기는지**를 알게 된다.

## 10.2 기지국이 하는 일을 한 장에: 전파 → IP

4 장에서 "기지국까지가 전파, 그 뒤는 IP" 라고 했다. 기지국은 그 변환을 하는 **층 더미**다. 아래부터 위로 올라간다.

```
                        srsRAN gNB 프로세스 안
   ┌─────────────────────────────────────────────────────────────────┐
   │  CU-CP   RRC (연결 관리)  ──────▶  NGAP ──────▶ AMF (N2, SCTP)    │  제어
   │          PDCP-C (제어 메시지 암호화)                              │
   ├─────────────────────────────────────────────────────────────────┤
   │  CU-UP   SDAP (QoS Flow ↔ 베어러)                                │  사용자
   │          PDCP-U (사용자 데이터 암호화)  ──▶  GTP-U ──▶ UPF (N3)   │
   ├─────────────────────────────────────────────────────────────────┤
   │  DU      RLC  (분할·재조립·ARQ 재전송)                            │
   │          MAC  (스케줄러: 누구에게 어느 PRB 를, HARQ, RACH)          │
   │          PHY 상위 (채널 코딩 LDPC/Polar, 변조, 자원 매핑)           │
   ├─────────────────────────────────────────────────────────────────┤
   │  Lower PHY   OFDM 변조/복조 (IFFT/FFT), CP, 타이밍                 │
   │          ──▶  I/Q 샘플 23.04 MS/s                                 │
   ├─────────────────────────────────────────────────────────────────┤
   │  Radio (UHD)   B210 드라이버. 샘플을 USB 로 보내고 받는다           │
   └─────────────────────────────────────────────────────────────────┘
                              │ USB 3.0
                           [B210] ──RF──▶ 모뎀
```

이름을 짚는다. **CU(Central Unit)** 와 **DU(Distributed Unit)** 는 5G 가 기지국을 둘로 쪼갠 이름이다. 상용망에서는 DU 가 안테나 가까이 수십 개 놓이고 CU 하나가 멀리서 그것들을 묶는다. CU 는 다시 제어(CP)와 사용자(UP)로 갈린다 — 4 장 코어에서 본 그 분리가 기지국 안에도 있다. srsRAN 은 이 셋을 **한 프로세스 안에 전부** 넣고 돈다. 그래서 우리 기동 로그에 세 이름이 다 나온다.

각 층이 하는 일을 **패킷 하나가 내려가는 순서**로 말하면 이렇다. UPF 에서 GTP-U 로 온 단말의 IP 패킷을 CU-UP 이 받아 GTP 헤더를 벗긴다(7.9a). **SDAP** 가 이 패킷의 QoS Flow(QFI)를 보고 어느 무선 베어러(DRB)에 실을지 정한다. **PDCP** 가 6 장의 K_UPenc 로 암호화하고 헤더를 압축한다. 여기까지가 CU 다. **RLC** 가 전파에 맞는 크기로 자르고, 깨지면 다시 보낼 수 있게 번호를 붙인다. **MAC** 이 스케줄러다. 이 슬롯에 이 단말에게 몇 개의 PRB 를 줄지, 어느 변조(MCS)로 보낼지를 3 장의 격자 위에서 매 0.5 ms 마다 정한다. 그리고 단말이 처음 접근하는 **RACH** 절차와 빠른 재전송 **HARQ** 를 담당한다. **상위 PHY** 는 비트를 채널 코드(데이터는 LDPC, 제어는 Polar)로 보호하고, QAM 심볼로 바꾸고, 격자의 자원 요소에 배치한다. **하위 PHY** 는 그 격자 한 슬롯을 IFFT 로 시간 파형으로 바꾸고 CP 를 붙여 I/Q 샘플을 만든다(3.3). **Radio** 층은 UHD 라이브러리로 그 샘플을 B210 에 밀어 넣는다. 올라오는 방향은 거꾸로다.

이 그림에서 **설정 파일이 건드리는 것**은 Radio(어느 장치, 어느 게인), 하위 PHY(샘플레이트, 주파수), MAC/PHY(대역폭, SCS, PCI, TDD 패턴), CU-CP(PLMN, TAC, AMF 주소)다. RLC, PDCP, SDAP 는 기본값으로 둔다.

## 10.3 설정 파일 전체를 한 줄씩

우리 `configs/srsran/gnb.yml` 이다. 전부 보여 주고 전부 설명한다. 플레이스홀더(`AMF_IP`, `PLMN`, `TAC`)는 컨테이너 기동 시 `srsran_init.sh` 가 `.env` 값으로 치환한다(5.6).

```yaml
cu_cp:
  amf:
    addr: AMF_IP                     # → 172.22.0.10
    bind_addr: SRS_GNB_IP            # → 172.22.0.37
    supported_tracking_areas:
      - tac: TAC                     # → 1
        plmn_list:
          - plmn: "PLMN"             # → "00101"
            tai_slice_support_list:
              - sst: 1

ru_sdr:
  device_driver: uhd
  device_args: type=b200,serial=5JKRCXX,fpga=/mnt/srsran/libresdr_alphafox02.bin,num_recv_frames=64,num_send_frames=64
  clock: internal
  sync: internal
  srate: 23.04
  otw_format: sc12
  tx_gain: 80
  rx_gain: 36

cell_cfg:
  dl_arfcn: 623334
  band: 78
  channel_bandwidth_MHz: 20
  common_scs: 30
  plmn: "PLMN"
  tac: TAC
  pci: 1

log:
  filename: /mnt/srsran/gnb.log
  all_level: warning

pcap:
  mac_enable: false
  mac_filename: /mnt/srsran/gnb_mac.pcap
  ngap_enable: false
  ngap_filename: /mnt/srsran/gnb_ngap.pcap
  f1ap_enable: false
  f1ap_filename: /mnt/srsran/gnb_f1ap.pcap
  e1ap_enable: false
  e1ap_filename: /mnt/srsran/gnb_e1ap.pcap
  e2ap_enable: false
  e2ap_cu_cp_filename: /mnt/srsran/cu_cp_e2ap.pcap
  e2ap_cu_up_filename: /mnt/srsran/cu_up_e2ap.pcap
  e2ap_du_filename: /mnt/srsran/du_e2ap.pcap
  n3_enable: false
  n3_filename: /mnt/srsran/gnb_n3.pcap
```

### `cu_cp.amf` — 기지국이 코어를 찾는 법

`addr` 은 AMF 의 주소다. 기지국은 뜨면서 이 주소의 **SCTP 포트 38412** 로 연결을 건다. SCTP 는 TCP 와 비슷하지만 메시지 경계를 유지하고 여러 스트림을 한 연결에 담는 전송 계층이고, N2 는 그 위에서 NGAP 를 나른다. `bind_addr` 은 기지국 자기 주소다. 컨테이너가 여러 네트워크에 붙어 있을 때 어느 쪽으로 나갈지 정한다. **이 두 값이 틀리면 로그에 `N2: Connection to AMF … completed` 가 안 뜨고 기지국은 셀을 띄운 채로 코어 없이 돈다.** 단말은 셀을 보지만 등록은 영원히 안 된다. 11f 의 `+C5GREG: 2,2`(찾는 중)가 계속되는 증상이다.

`supported_tracking_areas` 는 "이 기지국이 어느 TAC 의 어느 PLMN 을 서비스하는가"를 AMF 에 알리는 값이다. 연결 직후 **NG Setup** 이라는 NGAP 메시지에 실려 가고, AMF 는 자기 설정의 PLMN/TAC 과 비교해서 **맞으면 받고 틀리면 끊는다.** 우리 코어 `amf.yaml` 의 `plmn_support` 와 `tai` 가 그 비교 상대다. 두 설정이 같은 `.env` 에서 치환되기 때문에 우연히 어긋날 일은 없지만, 코어와 기지국을 따로 받아 쓰는 사람은 여기서 하루를 보낸다. `sst: 1` 은 슬라이스이고 7.3 의 S-NSSAI 다. 슬라이스는 SST(종류)와 SD(같은 종류 안의 세부 구분, 24비트) 두 칸인데 우리 설정에는 `sd` 줄이 없다. 없으면 어떻게 되는가를 이 이미지의 소스(커밋 11c9bbab 의 `apps/units/flexible_o_du/o_du_high/du_high/du_high_config.h`)에서 찾으면 `uint32_t sd = 0xffffffU;` 다. 3GPP 에서 SD 값 `0xFFFFFF` 는 "SD 없음"을 뜻하는 예약값이므로, 기지국은 "SST 1, SD 없음"을 알린다. 코어의 가입자 설정도 SD 없이 SST 1 만 갖고 있어서 둘이 맞는다. 코어 쪽 가입자에 SD 를 넣고 기지국에는 안 넣으면, 등록은 되는데 PDU 세션에서 슬라이스 불일치로 거절되는 하루짜리 함정이 생긴다.

### `ru_sdr` — 전파를 내는 장치

`device_driver: uhd` 는 Ettus 의 드라이버 라이브러리를 쓴다는 뜻이다. srsRAN 은 ZeroMQ(전파 없이 소켓으로 샘플을 주고받는 시뮬레이션)도 지원하는데, 그것은 `zmq` 다. 우리 `srsgnb_zmq` 컨테이너가 그것이다.

`device_args` 가 가장 중요한 줄이다. 쉼표로 나뉜 네 조각이다. `type=b200` 은 B200 계열 장치를 찾으라는 것이다. **`serial=5JKRCXX`** 는 그중 이 시리얼의 장치만 쓰라는 것이다 — 이 조각이 없으면 UHD 는 먼저 발견한 B200 을 잡고, 우리는 그 상태로 9 분 동안 **안테나가 달린 다른 장치**로 송신했다(10.7 에서 다시). `fpga=/mnt/srsran/libresdr_alphafox02.bin` 은 2.5 에서 말한 복제 보드 전용 FPGA 이미지다. 컨테이너 안 경로이고, 호스트의 `upstream/srsran/` 디렉터리가 `/mnt/srsran` 으로 마운트된다. `num_recv_frames=64,num_send_frames=64` 는 UHD 가 USB 전송에 쓰는 버퍼 수다. 기본값(16 또는 32)보다 늘려서 USB 지터를 흡수한다. 이것을 줄이면 콘솔에 `U`/`O` 가 늘고, 늘리면 지연이 조금 는다.

`clock: internal`, `sync: internal` 은 B210 안의 발진기를 기준으로 쓰라는 것이다. 상용 기지국은 **GPS**(Global Positioning System — 흔히 위치 찾기로만 알지만, 위성마다 원자시계가 실려 있어서 수신기는 지구 어디서나 같은 정밀 시각과 1 초 펄스를 얻는다) 수신기를 달아 그것으로 시각과 주파수를 맞춘다. 여러 기지국이 같은 시간에 같은 슬롯을 쏴야 하기 때문이다. TDD 에서 이웃 기지국 하나가 몇 마이크로초 늦게 하향을 쏘면 옆 셀의 상향 수신 구간을 덮어 버린다. 우리는 기지국이 하나라 내부 클럭으로 충분하다. 단, B210 의 내부 발진기는 수 ppm 의 오차가 있어서 3.35 GHz 에서 수 kHz 가 틀어질 수 있다. 단말은 그 정도는 추적한다.

`srate: 23.04` 는 2 장의 샘플레이트, 초당 2304 만 복소 샘플이다. 대역폭 20 MHz 의 1.152 배이고, 이 비율은 LTE 때부터 쓰는 "30.72 MS/s 의 3/4" 관습에서 왔다. 이 값을 바꾸면 B210 의 마스터 클럭이 거기에 맞춰지고, 로그의 `Asking for clock rate 23.040000 MHz` 가 그것이다. `otw_format: sc12` 는 2.6 의 샘플 하나 3 바이트다.

`tx_gain: 80` 과 `rx_gain: 36` 은 dB 다. B210 의 송신 게인 범위는 0 에서 89.75 까지이고, 수신은 0 에서 76 까지다. **이 두 값은 이 장의 10.8 절에서 따로 다룬다.** 우리가 65 에서 80 으로 올려야 단말이 붙었기 때문이다.

### `cell_cfg` — 셀의 정체

`dl_arfcn: 623334` 는 3.6 의 공식으로 3350.01 MHz 다. 이것이 **채널 중심 주파수**다. srsRAN 은 이 값과 대역폭에서 SSB 자리를 **자동으로** 계산한다 — GSCN 격자 위에서 채널 안에 들어가는 자리 하나를 고른다(어느 자리를 고르는지는 10.6). 그래서 로그의 `dl_ssb_arfcn=623040`(3345.6 MHz)은 우리가 쓴 값이 아니라 계산된 값이다. 10.6 에서 이 두 숫자를 왜 이렇게 골랐는지 본다.

`band: 78` 은 TDD 대역이다. srsRAN 은 대역 번호에서 "TDD 인가 FDD 인가", "상향 주파수는 어디인가"(TDD 는 같음)를 표로 찾는다. `channel_bandwidth_MHz: 20` 과 `common_scs: 30` 에서 PRB 수 51 이 나온다(3.5). `plmn` 과 `tac` 는 셀이 **SIB1 로 방송**하는 값이다. 단말이 `AT+COPS=?` 에서 `00101` 을 본 것은 이 값을 읽은 것이다. `pci: 1` 은 3.6 의 물리 셀 번호다. SSB 의 PSS/SSS 패턴이 이 번호로 정해진다.

이 설정에 **없는** 것이 하나 있다. TDD 패턴이다. srsRAN 은 `tdd_ul_dl_cfg` 를 안 쓰면 기본값을 쓴다. 설정 레퍼런스에 적힌 기본값은 `dl_ul_tx_period: 10`(슬롯), `nof_dl_slots: 6`, `nof_dl_symbols: 8`, `nof_ul_slots: 3`, `nof_ul_symbols: 0` 이다. 즉 **10 슬롯(30 kHz 에서 5 ms) 주기에 하향 6, 전환 1(앞 8 심볼 하향), 상향 3** — 3.7 의 그 패턴이다. 바꾸려면 `cell_cfg` 아래에 `tdd_ul_dl_cfg: {dl_ul_tx_period: 10, nof_dl_slots: 7, nof_dl_symbols: 8, nof_ul_slots: 2, nof_ul_symbols: 0}` 처럼 넣는다. 주기와 슬롯 수의 합이 맞아야 기동된다. 이 기본값은 레퍼런스 문서만이 아니라 이 이미지의 소스(`du_high_config_cli11_schema.cpp`)에서 확인했다. TDD 대역인데 `tdd_ul_dl_cfg` 가 없으면 정확히 위 다섯 숫자를 채워 넣는 코드가 있다.

같은 함수 바로 아래에 이 설정에 **없는 두 번째 것**이 있다. 단말이 처음 손을 드는 PRACH(10.5)의 설정이다. `prach_config_index` 를 안 주면 FDD 는 16, FR1 의 TDD 는 **159** 를 넣는다. 소스의 주석은 "5 ms 주기의 TDD 에 맞고, 159 가 가장 많이 시험됐다"이다. 이 인덱스는 TS 38.211 의 표 한 줄을 가리키는데, 그 줄이 PRACH 프리앰블의 형식과 "몇 번째 프레임의 몇 번째 슬롯에 PRACH 기회를 두는가"를 정한다. 상향 슬롯이 아닌 곳에 PRACH 기회를 두면 단말이 손을 들 수 없으므로, 인덱스는 TDD 패턴과 짝이 맞아야 한다. TDD 패턴을 바꿀 때 PRACH 인덱스를 같이 봐야 하는 이유가 이것이다. 나머지 기본값도 같은 구조체에 있다. 루트 시퀀스 번호 1(프리앰블 부호의 시작점 — 이웃 셀과 겹치지 않게 고른다), 제로 상관 구간 0(셀 반경이 작다는 가정), 프리앰블 목표 수신 전력 −100 dBm(10.8 에서 다시), 응답 대기 창은 `10 << μ`, 30 kHz(μ=1)에서 20 슬롯 = 10 ms.

### `log` 와 `pcap`

`all_level: warning` 이면 경고 이상만 파일에 남는다. 그래서 우리 `gnb.log` 가 정상 운전 중에는 0 바이트였다. 디버깅할 때는 `info` 로 올리거나 층별로 `mac_level: debug` 처럼 준다. `pcap` 은 MAC, NGAP, N3, 그리고 기지국 안쪽의 두 프로토콜 각각을 pcap 파일로 떨어뜨릴 수 있다. 그 둘은 처음 나오는 이름이다. 앞 절에서 기지국을 CU 와 DU 로 쪼갰는데, 쪼갠 이상 둘 사이에도 프로토콜이 있어야 한다. **F1AP(F1 Application Protocol)** 는 CU 와 DU 사이 F1 인터페이스의 제어 메시지이고("이 단말에게 이런 베어러를 만들어라"를 CU 가 DU 에 지시한다), **E1AP(E1 Application Protocol)** 는 CU 를 다시 CU-CP 와 CU-UP 으로 나눈 그 사이 E1 인터페이스의 제어 메시지다("이 세션의 GTP-U 터널을 열어라"를 CU-CP 가 CU-UP 에 지시한다). NGAP 이 기지국과 AMF 사이의 말이었듯이, 이 둘은 기지국 **안쪽** 조각끼리의 말이다. 상용망에서는 이 메시지가 실제로 선을 타고 다른 장비로 가지만, srsRAN 은 세 조각을 한 프로세스에 넣었으므로 함수 호출로 건넨다. 그래도 같은 메시지 형식을 거치기 때문에 pcap 으로 뽑아 와이어샤크의 `f1ap`, `e1ap` 필터로 열 수 있다 — 기지국 내부의 대화를 패킷으로 보는 드문 기회다. **`ngap_enable: true` 로 켜면 N2 의 모든 메시지가 와이어샤크로 열리는 파일이 되고, `mac_enable: true` 면 전파 위의 MAC 프레임까지 보인다.** 5 장의 와이어샤크 절은 브리지를 캡처했지만, 기지국 자체가 뱉는 pcap 이 더 깨끗하다. 단 MAC pcap 은 초당 수 MB 라 잠깐만 켠다.

## 10.4 기동 로그를 한 줄씩

`docker compose -f srsgnb.yaml up -d` 뒤 `docker logs srsgnb` 가 보여 준 것이다. 전부 싣고 전부 읽는다.

```
--== srsRAN gNB (commit 11c9bbabb6) ==--
```
빌드 커밋이다. 문제가 나면 이 해시로 소스를 연다. 우리 컨테이너 이미지는 `docker_srsran` 이고 `upstream/srsran/Dockerfile` 이 이 커밋을 체크아웃한다.

```
Lower PHY in triple executor mode.
```
하위 PHY(OFDM 변복조와 샘플 입출력을 맡는 맨 아래층)가 전용 스레드 세 개로 돈다는 뜻이다. 소스(`apps/services/worker_manager/worker_manager.cpp` 의 `create_lower_phy_executors`)를 열면 세 스레드의 이름과 실시간 우선순위가 그대로 있다. `lower_phy_tx`(송신 — IFFT 와 샘플 내보내기, 최고 우선순위), `lower_phy_ul`(상향 복조, 한 단계 아래), `lower_phy_rx`(샘플 받기, 그 아래). 이와 별개로 장치 입출력을 맡는 `radio` 스레드가 하나 더 있다. 어느 모드로 갈지는 실행 시점에 CPU 수로 정한다(`ru_sdr_config.h`). 사용 가능한 CPU 가 4 개 미만이면 `single`(한 스레드가 전부), 8 개 미만이면 `dual`(하향 하나, 상향 하나), 그 이상이면 `triple` 이다. 모드가 낮을수록 한 스레드가 할 일이 늘어 슬롯 마감을 놓칠 가능성이 커지고, 놓치면 아래에서 볼 `late`/`underflow` 가 찍힌다. 우리 32 스레드 박스는 당연히 `triple` 이었다. 이 결정은 컨테이너에 CPU 제한(`--cpus`)을 걸면 바뀐다는 점을 기억해 둘 만하다.

```
Available radio types: uhd and zmq.
[INFO] [UHD] linux; GNU C++ version 11.2.0; Boost_107400; UHD_4.1.0.5-3
```
UHD 가 자기 빌드 환경을 밝히는 줄이다. `linux` 는 운영체제, `GNU C++ version 11.2.0` 은 UHD 를 컴파일한 g++ 버전, `Boost_107400` 은 링크한 Boost C++ 라이브러리 버전(1.74.0 을 숫자 하나로 쓴 것), 마지막이 UHD 자체의 버전이다. 앞의 둘은 "이 바이너리가 어느 배포판에서 빌드됐나"를 알려 주는 지문이라, 다른 배포판의 UHD 라이브러리를 섞어 쓰다 심볼 오류가 날 때 첫 단서가 된다. 컨테이너 안의 UHD 가 4.1.0.5 다. 호스트는 4.6 이었다. **두 버전이 다르다는 것이 중요하다.** 호스트에서 `uhd_usrp_probe` 로 FPGA 를 올린 뒤 컨테이너의 gNB 가 그 장치를 쓰면, 컨테이너의 UHD 가 "내 버전과 FPGA 이미지가 맞나"를 검사한다. 복제 보드 이미지는 버전 검사를 느슨하게 통과하지만, 정품 이미지를 섞어 쓰면 여기서 거부된다.

```
Making USRP object with args 'type=b200,serial=5JKRCXX,fpga=/mnt/srsran/libresdr_alphafox02.bin,num_recv_frames=64,num_send_frames=64'
[INFO] [B200] Detected Device: B210
[INFO] [B200] Operating over USB 3.
```
세 줄이 2 장의 전부다. `device_args` 가 그대로 UHD 에 넘어가고, 시리얼이 맞는 장치를 찾았고, **USB 3 이다.** 이 줄이 `USB 2.` 이면 더 읽을 필요 없이 멈추고 케이블을 본다. 우리는 그 줄을 보고도 포트를 의심하며 반나절을 썼다(10.7).

```
[INFO] [B200] Initialize CODEC control...
[INFO] [B200] Initialize Radio control...
[INFO] [B200] Performing register loopback test... Register loopback test passed
[INFO] [B200] Performing register loopback test... Register loopback test passed
```
AD9361 칩(2.4)의 레지스터를 써 보고 읽어서 FPGA 와 RF 칩 사이의 **SPI**(Serial Peripheral Interface) 선이 살았는지 확인한다. SPI 는 칩끼리 레지스터를 읽고 쓰는 데 쓰는 3~4 가닥짜리 동기식 직렬 버스다. 11a 의 UART 와 달리 클럭 선이 따로 있어 양쪽이 보레이트를 미리 약속할 필요가 없다. 플래시 칩 덤프하려고 SPI 클립을 물려 본 적이 있다면 바로 그 버스다. 두 번인 것은 채널 A 와 B 다. 여기서 실패하면 FPGA 이미지가 보드에 안 맞는 것이다.

```
[INFO] [B200] Setting master clock rate selection to 'automatic'.
[INFO] [B200] Asking for clock rate 16.000000 MHz... Actually got clock rate 16.000000 MHz.
[INFO] [MULTI_USRP] Setting master clock rate selection to 'manual'.
[INFO] [B200] Asking for clock rate 23.040000 MHz... Actually got clock rate 23.040000 MHz.
```
UHD 가 먼저 기본 16 MHz 로 칩을 깨우고, srsRAN 이 `srate: 23.04` 를 요구하면 마스터 클럭을 그 값으로 다시 맞춘다. 두 줄의 `automatic` 과 `manual` 은 누가 마스터 클럭을 정하느냐의 차이다. `automatic` 이면 UHD 가 요청받은 샘플레이트를 보고 알아서 마스터 클럭을 고르고(필요하면 FPGA 안에서 샘플을 솎아 내는 데시메이션을 쓴다), `manual` 이면 응용 프로그램이 정확한 클럭 값을 지정한다. srsRAN 은 샘플 타이밍을 직접 계산하므로 UHD 가 중간에 클럭을 바꾸지 못하게 `manual` 로 고정한 뒤 23.04 MHz 를 요구하고, 그 결과 마스터 클럭과 샘플레이트가 같아져(1:1) FPGA 의 솎아 내기 없이 칩의 샘플이 그대로 나온다. AD9361 은 임의의 클럭을 못 낸다. 칩 안의 **PLL**(Phase-Locked Loop, 위상 고정 루프)이 기준 발진기 하나를 정수·분수 배로 곱하고 나눠 원하는 주파수를 만드는데, 그 곱셈·나눗셈 조합으로 정확히 만들 수 있는 값만 낸다. CPU 의 기본 클럭에 배수를 곱해 코어 클럭을 만드는 것과 같은 장치다. 그런데 23.04 MHz 는 정확히 맞는 값이다. `Actually got` 이 요구값과 다르면 샘플레이트가 어긋나 단말이 주파수 오프셋으로 못 붙는다.

```
Cell pci=1, bw=20 MHz, 1T1R, dl_arfcn=623334 (n78), dl_freq=3350.01 MHz, dl_ssb_arfcn=623040, ul_freq=3350.01 MHz
```
이 한 줄이 `cell_cfg` 의 **해석 결과**다. 3 장과 11f 의 모든 값이 여기 있다. `1T1R` 은 송신 안테나 하나, 수신 안테나 하나 — B210 은 2T2R 이 가능하지만 우리 설정이 안테나를 하나만 썼다. `ul_freq` 가 `dl_freq` 와 같은 것이 TDD 의 표시다. `dl_ssb_arfcn` 이 `dl_arfcn` 과 다른 것은 위에서 말한 자동 계산이다.

```
N2: Connection to AMF on 172.22.0.10:38412 completed
==== gNB started ===
```
SCTP 연결과 NG Setup 이 끝났다. AMF 로그에는 같은 순간 `gNB-N2 accepted[172.22.0.37]` 가 찍힌다(5.3). 이 줄 뒤부터 B210 은 **SSB 를 20 ms 마다 쏘고 있다.** 로그에는 아무것도 더 안 찍힌다. `all_level: warning` 이라 정상 동작은 침묵이다.

### 정상이 아닐 때 로그가 하는 말: 실시간 실패

침묵이 깨지는 경우가 있다. 이 실험실의 10월 4~5일 기동분 로그(`upstream/srsran/gnb.log.2026-10-05`, 106만 줄)가 그 견본이다. 처음 몇 줄은 이렇다.

```
2026-10-04T18:10:58.341735 [GNB     ] [I] Built in Release mode using commit 11c9bbabb6 on branch HEAD
2026-10-04T18:10:58.744341 [GNB     ] [W] DRM KMS polling is enabled, which may hinder performance. You can disable it using the "srsran_performance" script
2026-10-04T18:12:30.147605 [RF      ] [W] Real-time failure in RF: underflow
2026-10-04T18:12:30.150721 [RF      ] [W] Real-time failure in RF: late
```

`DRM KMS polling` 경고는 리눅스의 그래픽 드라이버(DRM, Direct Rendering Manager)가 모니터 연결 상태를 주기적으로 훑는(KMS, Kernel Mode Setting 의 폴링) 기능이 켜져 있다는 뜻이다. 그 폴링이 잠깐씩 CPU 를 붙잡아 실시간 스레드의 마감을 흔들 수 있어서 srsRAN 이 기동 때 검사해 경고한다. 저장소의 `srsran_performance` 스크립트가 이것과 CPU 절전 설정을 함께 끈다. 우리는 끄지 않고 운용했다.

`Real-time failure in RF` 는 2장에서 콘솔의 `U`, `O`, `L` 한 글자로 봤던 것의 긴 이름이다. **underflow** 는 송신 버퍼가 비었다는 것 — 기지국이 다음 샘플을 제때 만들지 못해 B210 이 보낼 것이 없었다. **overflow** 는 반대로 수신 버퍼가 넘쳤다는 것 — B210 이 보낸 샘플을 호스트가 제때 가져가지 못했다. **late** 는 샘플이 도착은 했는데 그 샘플에 붙은 송신 예정 시각이 이미 지났다는 것이다. 어느 쪽이든 그 순간의 무선 프레임은 깨지고, 몇 번이면 단말이 견디지만 계속되면 셀을 놓친다. 이 로그에서 RF 실패는 기동 직후 몇십 줄로 끝났다.

문제는 그다음이었다. 10월 5일 01:53 부터 이 로그는 같은 줄로 채워졌다.

```
2026-10-05T01:53:19.868026 [PHY     ] [W] [    3.19] Real-time failure in low-phy: PRACH request overflow for sector 0, slot 3.19 and start symbol 0.
2026-10-05T01:53:19.883383 [PHY     ] [W] [    4.19] Real-time failure in low-phy: PRACH request overflow for sector 0, slot 4.19 and start symbol 0.
```

대괄호 안 `3.19` 는 "시스템 프레임 3 의 슬롯 19"다(10 ms 프레임 하나에 30 kHz 슬롯 20개, 0~19). 프레임 번호가 하나씩 오르며 매번 슬롯 19 에서 찍혔고, 시간당 약 17만 7천 줄, 초당 약 49 줄 — 이 셀의 PRACH 기회가 오는 자리마다 한 줄씩 찍힌 것으로 보인다. 같은 슬롯 번호(19)에서만 찍힌다는 것 자체가 PRACH 기회의 위치를 로그로 알려 주는 셈인데, 인덱스 159 의 표 값과 직접 대조하지는 않았다 [검증 필요: TS 38.211 표 6.3.3.2-3 의 159 행]. 프레임은 10 ms 인데 초당 49 줄이라는 점도 "매 프레임"과 정확히 맞지는 않는다 — 로그 기록 자체가 밀렸을 수 있다. 뜻은 "상위 PHY 가 '이 슬롯의 PRACH 를 받아 달라'고 하위 PHY 에 요청을 넣으려 했는데 요청 큐가 이미 차 있었다"이다. 하위 PHY 가 이전 PRACH 요청을 처리하지 못하고 쌓아 두고 있었다는 뜻이고, 그 상태에서는 단말이 손을 들어도 기지국이 보지 못한다. 그날 밤 이 로그가 찍히는 동안 붙어 있던 단말은 없었다. 원인을 당시에는 가려내지 못했다. 그런데 10.7 의 두 번째 사고를 조사하다 같은 시기의 기지국 컨테이너 출력에 `LIBUSB_TRANSFER_ERROR` 가 수십만 줄 있다는 것이 드러났다 — 그날 B210 은 USB 2 로 붙어 있었다. 수신 샘플이 제때 오지 않으면 하위 PHY 는 PRACH 구간의 샘플을 다 받지 못해 처리를 끝내지 못하고, 다음 요청이 밀려 들어오면 큐가 넘친다. 이것이 가장 유력한 설명이다 [검증 필요: USB 3 에서 같은 설정으로 이 줄이 0 인지 — 지금 기동분은 0 줄이다]. 지금 기동분의 `gnb.log` 에는 이 줄이 한 줄도 없다. 교훈은 둘이다. **로그 파일 크기 자체가 건강 지표다** — 정상 운전 중인 `warning` 레벨 로그는 0 바이트에 가깝고, 몇백 MB 로 불어나 있으면 무언가 매 슬롯 실패하고 있다. 그리고 **PRACH 쪽 실패는 하향 쪽이 멀쩡해도 생긴다** — 셀은 보이는데(SSB 는 나가는데) 아무도 못 붙는 증상의 후보로 기억해 둔다.

## 10.5 단말이 붙는 10 초 동안 기지국 안에서 일어나는 일

로그가 침묵하는 동안 기지국은 가장 바쁘다. 모뎀이 `AT+CFUN=1` 을 친 뒤부터 AMF 가 `Registration complete` 를 찍기까지 기지국 안의 순서를 적는다. 이것을 보려면 `mac_enable: true` 와 `ngap_enable: true` 로 pcap 을 켜고 와이어샤크로 열어야 한다.

**1. 단말이 SSB 를 찾는다.** 기지국은 3.6 의 SSB 를 20 ms 주기로 쏜다. 단말은 n78 의 GSCN 격자를 훑다가 3345.6 MHz 에서 PSS 를 잡고, SSS 로 PCI 1 을 알고, PBCH 에서 MIB 를 읽는다. MIB 에 "SIB1 은 이 자리에 있다"가 있다. 기지국은 이 단계에서 단말의 존재를 **모른다.** 방송만 하고 있다.

**2. 단말이 SIB1 을 읽는다.** SIB1 에 PLMN 00101, TAC 1, 셀 ID, 그리고 **RACH 설정**(어느 슬롯 어느 주파수로 접근 요청을 보내라)이 있다. 모뎀의 `AT+COPS=?` 가 `"Open5GS","00101"` 을 보인 것은 SIB1 을 읽었다는 뜻이다. 아직도 기지국은 단말을 모른다.

**3. RACH — 단말이 처음 말을 건다.** 단말이 SIB1 이 정한 자리에 **프리앰블**(짧은 패턴 신호)을 보낸다. MAC 의 RACH 처리기가 그것을 잡고 **이 순간 처음으로 단말을 인지한다.** 기지국은 **RAR(Random Access Response)** 로 답하는데, 거기에 임시 식별자 **TC-RNTI** 와 **타이밍 어드밴스**(11f 의 TA — "너는 이만큼 일찍 보내라")가 들어 있다. 케이블 직결이라 TA 는 0 근처다.

**4. RRC 연결.** 단말이 `RRC Setup Request` 를 보내고, CU-CP 의 RRC 가 `RRC Setup` 으로 답하면서 SRB1(제어 메시지용 베어러)을 만든다. 단말은 `RRC Setup Complete` 를 보내는데, **그 안에 NAS Registration Request 가 들어 있다.** 5.4 의 "봉투 안의 봉투"다. 기지국은 RRC 를 열어 보지만 NAS 는 열지 않는다.

**5. NGAP Initial UE Message.** CU-CP 가 그 NAS 덩어리를 `InitialUEMessage` 에 담아 AMF 에 보낸다. 5.3 의 AMF 로그 첫 줄이 이 순간이다. 기지국은 여기서 `RAN_UE_NGAP_ID` 를 할당한다 — 로그의 `[0]` 이다.

**6. 인증과 보안이 지나간다.** AMF 와 단말 사이의 Authentication Request/Response, Security Mode Command/Complete 가 전부 `DownlinkNASTransport` / `UplinkNASTransport` 라는 NGAP 메시지에 실려 기지국을 **투명하게** 지난다. 기지국이 하는 일은 봉투를 옮기는 것뿐이다.

**7. Initial Context Setup.** 인증이 끝나면 AMF 가 `InitialContextSetupRequest` 를 보낸다. 여기에 **보안 키 K_gNB**(6.6 의 키 계층에서 기지국 몫)와 단말 능력 정보가 있다. CU-CP 는 이 키로 **RRC 보안을 켜고**(`SecurityModeCommand`, RRC 층의 것 — NAS 의 그것과 별개), 단말 능력을 묻고(`UECapabilityEnquiry`), 그 결과를 AMF 에 보낸다. 이 지점부터 RRC 메시지도 암호화된다.

**8. PDU 세션 자원 설정.** 단말이 세션을 요청하고 SMF 가 IP 를 주면(7.3), AMF 가 `PDUSessionResourceSetupRequest` 를 기지국에 보낸다. 안에 **UPF 의 주소와 상향 TEID**, 그리고 QoS Flow 목록이 있다. CU-UP 은 그 TEID 로 GTP-U 터널을 열고(7.9a), 자기 쪽 **하향 TEID** 를 만들어 응답에 넣는다. CU-CP 는 `RRCReconfiguration` 으로 단말에 **DRB**(데이터 베어러)를 만들어 주고, SDAP 에 "QFI 1 은 DRB 1 로" 매핑을 건다. 단말이 `RRCReconfigurationComplete` 를 보내면 데이터가 흐른다.

**9. 데이터가 흐르는 동안.** MAC 스케줄러가 매 슬롯 돈다. 단말이 보고하는 CQI 로 MCS 를 정하고, 버퍼 상태로 PRB 를 배분하고, HARQ 로 깨진 블록을 다시 보낸다. 단말은 CQI 와 함께 **RI**(Rank Indicator)도 보고한다. "지금 전파 상태로는 서로 다른 데이터 줄기를 몇 개까지 겹쳐 보내도 구분해 받을 수 있다"는 숫자다. 우리 실험실은 송신 안테나가 하나(1T1R)라 RI 는 늘 1 이고, 이 값은 2·4 안테나 기지국에서 처리량을 배로 만드는 열쇠가 된다. 11f 의 CQI/MCS/RI 가 여기서 살아 움직인다. `mac_enable` pcap 에서 매 슬롯의 DCI(스케줄링 명령)를 볼 수 있다.

**10. 놓기.** 데이터가 몇 초 끊기면 CU-CP 의 비활성 타이머가 만료되고, `UEContextReleaseRequest` 를 AMF 에 보낸다. AMF 로그의 `UE Context Release [Action:2]` 가 그것이다. RRC 가 `RRCRelease` 를 보내고 단말은 IDLE 로 간다. 기지국은 단말을 다시 잊는다. 다음 데이터가 생기면 3 단계 RACH 부터 다시다.

이 열 단계에서 **기지국이 단말의 신원을 아는 순간은 없다.** IMSI 도 SUPI 도 기지국을 거치지만 열리지 않는다. 기지국이 가진 것은 RNTI(무선 임시 번호), RAN_UE_NGAP_ID, 그리고 K_gNB 다. 4 장의 설계 철학이 열 단계 전부에 박혀 있다.

## 10.6 주파수 계획: 왜 623334 인가

이것은 설정값 하나이지만 **이 장에서 가장 신중해야 하는 결정**이다. 틀리면 상용망을 방해하고 법을 어긴다.

출발점은 1 장의 사실이다. 한국 n78 은 3.4~3.7 GHz 를 세 사업자가 100 MHz 씩 쓴다. 그 아래 3.3~3.4 GHz 는 우리가 확인한 범위에서 이동통신 사업자에게 할당된 기록이 없는 구간이다 [검증 필요: 과학기술정보통신부 주파수 분배표에서 3.3~3.4 GHz 의 현재 용도]. 할당이 없다는 것이 비어 있다는 뜻은 아니다 — 다른 용도(예: 다른 무선 업무)가 있을 수 있다. 우리 셀은 적어도 상용 이동통신 할당과는 겹치지 않는 그 구간에 들어가야 한다. 20 MHz 폭이니 채널의 상단이 3.4 GHz 보다 **충분히 아래**여야 하고, 보호 대역까지 고려하면 중심을 3.35 GHz 근처로 두면 상단이 3.36 GHz 에서 끝나 40 MHz 여유가 생긴다.

그 다음 제약이 **SSB 격자**다(3.6). 단말은 SSB 를 1.44 MHz 간격의 GSCN 격자에서만 찾는다. 채널 중심을 아무 데나 두면 srsRAN 이 "이 채널 안에 격자 점이 있는가"를 계산하고, 있으면 그중 한 점에 SSB 를 둔다. 3350.01 MHz 중심의 20 MHz 채널은 3340.01 에서 3360.01 까지이고, 그 안에는 격자 점이 여럿 있다(3000 + 1.44 × N 이므로 3341.28, 3342.72, … 3345.6, … 3349.92, …). srsRAN 이 고른 것은 3345.6 MHz(GSCN 7739)였고, 그래서 `dl_ssb_arfcn=623040` 이 자동으로 나왔다. 중심에 가장 가까운 점은 3349.92 인데 그것이 아니었다는 것은, srsRAN 이 "중심에서 가까운 순"이 아니라 SSB 가 PRB 경계와 맞물리는 조건(아래의 k_SSB)을 만족하는 점을 자기 순서로 찾는다는 뜻이다 [검증 필요: srsRAN 의 SSB 위치 선택 함수 확인]. 채널 중심을 1 MHz 만 옮기면 SSB 자리가 바뀌거나 채널 안에 격자 점이 없어 기동이 거부된다.

그 다음 제약이 **ARFCN 자체의 격자**다. n78 의 채널 래스터는 15 kHz 이고, 3 GHz 이상에서는 ARFCN 한 칸이 정확히 15 kHz 이므로 n78 범위(620000~653333) 안의 정수면 어느 것이든 래스터 위에 있다(TS 38.104 표 5.4.2.3-1. 30 kHz 래스터를 고르면 두 칸 간격). 그리고 채널 대역폭과 SCS 의 조합에서 **PointA**(자원 격자의 원점)와 SSB 의 부반송파 오프셋(k_SSB)이 정수로 맞아야 한다. srsRAN 이 이것을 전부 검사하고 안 맞으면 기동 때 오류를 낸다. 즉 **ARFCN 을 바꾸고 싶으면 1.44 MHz 의 정수 배로 통째로 옮기는 것이 안전하다.** 그러면 SSB 오프셋이 그대로 유지된다. 우리 `docs/frequency-plan.md` 에 "269.28 MHz = 187 × 1.44" 같은 계산이 있는 이유다.

인터넷의 예제는 다르다. OAI 와 srsRAN 의 공개 설정 파일에는 `641280`(3619.2 MHz), `632628`(3489.42 MHz) 같은 값이 많다. 전부 **유럽이나 미국 기준**이고 한국에서는 SKT 나 LG U+ 의 한가운데다. 예제를 복사하기 전에 3.6 의 공식으로 MHz 를 구하고 1 장의 표와 대조하는 것이 **첫 번째 할 일**이다.

> ⚠️ 그래도 이것은 "덜 위험한 선택"일 뿐이다. 할당되지 않은 구간이라고 송신이 허락된 것은 아니다. 공중 방사는 무선국 허가 뒤에만 한다. 우리 실험은 케이블 직결과 40 dB 감쇠기가 전제이고, 차폐함이 오기 전까지 안테나는 달지 않는다.

## 10.7 우리가 틀린 것들: 장치 두 대와 케이블

이 절은 우리가 하루를 쓴 두 사고를 **조사 순서대로** 적는다. 교훈만 적으면 다음 사람이 같은 함정을 못 알아본다.

### 사고 1: 엉뚱한 장치로 9 분 송신

기지국을 처음 띄운 날, 모뎀이 셀을 못 봤다. `AT+COPS=?` 에 상용 사업자만 떴다. 기지국 로그는 멀쩡했다 — `Operating over USB 3.`, `gNB started`. 우리는 모뎀 쪽을 의심했다. ModemManager 가 포트를 잡고 있었고(11d), 그것을 떼느라 시간을 썼다. 그 사이 사용자가 한마디 했다. "다른 걸 쏜 거 아니야? B210 두 대야."

`lsusb` 를 다시 쳤다. B210 이 **하나**만 보였다. 시리얼 `RF01FPI`. 사용자가 두 번째를 꽂자 `WestBridge` 상태의 장치가 하나 더 나타났고, 펌웨어를 올리니 `5JKRCXX` 였다. 그리고 사용자가 말했다. **"방금 꽂은 게 쓰는 거야. 다른 건 안테나 달렸어."**

우리 `device_args` 는 `type=b200` 뿐이었다. UHD 는 먼저 발견한 장치를 잡았고, 그것은 안테나가 달린 `RF01FPI` 였다. 기지국은 9 분 동안 그 장치로 3350 MHz 를 **공중에** 쐈다. 모뎀은 케이블로 다른 장치에 묶여 있었으니 당연히 셀을 못 봤다. 로그에는 아무 이상이 없었다 — 기지국 입장에서는 정상 송신이었으니까.

출력을 계산하면 `tx_gain 65` 는 B210 최대(약 10 dBm)에서 25 dB 아래, 약 −15 dBm, 0.03 mW 다 [추정]. 상용 대역과 40 MHz 떨어져 있었다. 그것이 누구에게도 영향을 주지 않았다고 우리는 증명할 수 없다. 조건이 조금만 달랐다면 — 업스트림 예제의 3.6 GHz 설정이었다면 — 상용망 한가운데였다. 그래서 세 가지를 바꿨다. `device_args` 에 `serial=5JKRCXX` 를 박았다. 안테나 달린 장치를 USB 에서 **분리**했다 — 설정이 틀려도 물리적으로 송신이 불가능하게. 그리고 송신 전 점검 절차에 `lsusb | grep -i ettus` 로 장치 수를 세는 줄을 넣었다. 이 책의 안전 원칙 첫 줄이 이 사고에서 왔다.

### 사고 2: USB 2.0 의 반나절

`5JKRCXX` 를 꽂고 펌웨어를 올렸는데 `Operating over USB 2.` 가 떴다. 우리는 포트를 의심했다. `lsusb -t` 를 보니 그 장치가 `Bus 003`, 480M 루트허브 아래에 있었다. "USB 2 전용 포트다, 옮겨라" 고 했다. 사용자가 옮겼다. 여전히 480M 이었다. 사용자가 USB 3 허브를 끼웠다. 허브는 5000M 으로 열거됐는데 B210 은 그 허브의 USB 2 쪽에 붙었다. 사용자가 재부팅했다. 같았다.

그 사이 우리는 **`RF01FPI` 가 USB 3 으로 올라간 포트**를 알고 있었다. 사용자가 그 장치의 **케이블째로** `5JKRCXX` 에 옮겨 꽂았다. `Operating over USB 3.` 그리고 `5000M`. 범인은 케이블이었다. B210 의 USB 3 Micro-B 커넥터는 USB 2 Micro-B 케이블도 받아들이고, 꽂히면 동작도 한다. 2.0 속도로.

이 사고가 드러낸 더 큰 것이 있다. 열흘 전의 "RF 송신 성공" 기록을 확인하니, 그날의 기지국 컨테이너 로그가 **61 만 줄**이었고 그중 60 만 7 천 줄이 `usb rx6 transfer status: LIBUSB_TRANSFER_ERROR` 였다. 그날도 USB 2 였던 것이다. SSB 는 아주 가끔만 나가도 단말이 잡기 때문에 `AT+COPS=?` 에 셀이 한 번 보였고, 우리는 그것을 "RF 경로 검증 완료"로 기록했다. 등록이 안 된 이유를 "USIM 이 없어서"로만 적었다. 틀린 기록은 아니었지만 **USB 가 이미 깨져 있었다는 사실을 빠뜨렸다.** 기록할 때 "셀이 보였다"와 "링크가 안정적이다"를 구분하지 않은 것이 열흘 뒤 반나절로 돌아왔다.

케이블을 바꾼 뒤 새 세션의 USB 오류는 **0 줄**이었다.

## 10.8 송신 게인: 65 에서 80 으로, 그리고 왜 더 올리지 않는가

USB 3 가 되고 시리얼을 고정한 뒤에도 모뎀은 셀을 못 봤다. `AT+COPS=?` 에 상용망만 떴다. 이번에는 기지국 로그도 USB 도 멀쩡했다. 남은 변수는 **신호 세기**였다.

`tx_gain 65` 로 열흘 전에 셀이 보였다는 기록이 있었다. 그런데 그 기록이 10.7 에서 신뢰를 잃었다. 그래서 15 dB 올려 80 으로 재기동했다. 바로 `(2,"Open5GS","Open5GS","00101",12)` — 등록까지 됐다. 그때 모뎀이 보고한 RSRP 는 −110 dBm 이었고, 데이터 세션을 올린 뒤 다시 보니 −71 dBm 이었다. 둘 다 **그대로 믿을 값이 아니었다.** 1.8 절에서 경로별로 다시 재 보니 모뎀의 네 수신 경로가 각각 −112, −103, −102, −71 을 보고하고 있었고, 화면에 뜨던 한 숫자는 상태에 따라 그중 다른 경로의 값이었다. 케이블이 물린 경로의 실제 값은 **−112(ANT1)와 −103(ANT2)** 다.

이 숫자들을 1 장의 방식으로 놓고 보자. B210 데이터시트의 송신 출력은 `>10 dBm`(주파수 조건 없이 한 줄)이고 게인 범위는 0~89.75 dB 다. 게인 80 은 최대에서 약 10 dB 아래이니 **0 dBm, 1 mW** 근처다. 거기서 케이블 손실 2~3 dB 와 감쇠기 40 dB 를 빼면 모뎀 입력 총전력은 약 −43 dBm, 부반송파 하나로는 −71 dBm 이어야 한다(1.8 의 링크 예산). 그런데 케이블이 물린 경로의 실측은 −103 과 −112 였다. **30~40 dB 가 설명되지 않는다.** 가능한 곳은 셋이다. 복제 보드의 실제 출력이 정품 사양보다 낮을 수 있다. 감쇠기의 실제 감쇠량이 표기와 다를 수 있다. **MHF4** 피그테일과 커넥터 접촉에서 손실이 있을 수 있다. MHF4 는 노트북 Wi-Fi 카드의 안테나 단자처럼 손톱만 한 초소형 동축 커넥터(일본 커넥터 제조사 I-PEX(아이펙스)가 정한 규격 이름)이고, 피그테일은 그 단자에서 **SMA**(SubMiniature version A — B210 보드 가장자리에 달린 금색 나사식 커넥터가 이것이다) 같은 큰 커넥터로 이어 주는 짧은 동축 선이다. 작은 만큼 끼움 상태에 따라 손실이 들쭉날쭉하고, 실제로 같은 규격으로 물린 두 경로가 9 dB 차이났다(−103 vs −112). 가리는 방법은 12.5 의 게인 스윕을 **경로별로** 하는 것이다.

그러면 왜 65 에서는 안 됐나. 케이블 경로의 실측 −103(ANT2)에서 15 dB 를 더 빼면 **−118 dBm** 이다. 11f 의 표에서 "매우 나쁨"을 넘어 모뎀의 탐지 문턱 근처다. 셀을 못 찾은 것이 당연한 수준이고, 게인을 80 으로 올려 −103 이 되자 찾은 것도 앞뒤가 맞는다. 화면의 −71 을 기준으로 삼았을 때는 "−86 이면 충분히 좋은데 왜?" 라는 풀리지 않는 질문이었는데, 경로별 실측으로 보니 질문 자체가 사라졌다. 게다가 게인 65 의 그 세션은 USB 2 상태였을 가능성도 있다. 즉 "65 에서 안 됐다"는 결론 자체가 다른 변수와 섞여 있었다. 지금 80 에서 안정됐으니 **65 로 내려서 다시 재는 것**이 정직한 다음 실험이고, 12 장의 과제로 둔다.

수신 게인 `rx_gain: 36` 은 우리가 한 번도 바꾸지 않은 업스트림 기본값이다(`configs/_backup/gnb.yml.orig.bak` 에도 36). 바꿀 필요가 없었던 이유는 상향 방향에는 **단말 쪽 전력 제어**가 있기 때문이다. 기지국은 SIB1 으로 "PRACH 프리앰블이 내 수신단에 몇 dBm 으로 도착하길 원한다"(preambleReceivedTargetPower)를 방송하고, 단말은 하향 신호로 잰 경로 손실을 더해 자기 송신 전력을 정한다. 이 이미지의 기본 목표값은 소스상 `preamble_rx_target_pw = -100` dBm 이다. 그래서 감쇠기 40 dB 가 끼어 있든 아니든 단말은 그만큼 세게 또는 약하게 쏴서 기지국 입구에서 약 −100 dBm 을 맞추려 한다. 수신 게인은 그 −100 dBm 근처 신호가 B210 의 ADC 범위에서 너무 작지도(양자화 잡음에 묻힘) 너무 크지도(포화) 않게 놓는 값이고, 36 dB 는 그 범위 안에 있었다 — 상향 11 Mbps 가 나오고 PRACH 가 한 번에 붙었다는 것이 우리가 가진 증거의 전부다. 상향 수신 전력을 직접 재 보지는 않았다 [검증 필요: 기지국 MAC pcap 또는 `info` 로그의 상향 SNR 로 확인].

왜 더 올리지 않는가. 두 이유다. 하나는 포화다. B210 의 송신 증폭기는 최대 근처에서 비선형이 되어 신호가 일그러지고(스펙트럼이 옆으로 번진다), 그러면 모뎀의 SINR 이 오히려 떨어진다. 다른 하나는 안전이다. 게인이 높을수록 케이블과 커넥터에서 새는 전파도 세진다. 모뎀이 붙는 **가장 낮은 게인에서 10 dB 여유**를 두는 것이 원칙이다. 지금 80 은 그 기준에서 높은 쪽이고, 12 장의 게인 스윕에서 적정값을 정한다.

## 10.9 바꿀 수 있는 것, 바꾸면 안 되는 것

이 장의 모든 설정값을 "실험실에서 바꿔도 되는가"로 나눈다.

**자유롭게 바꾸는 것**: `tx_gain`, `rx_gain`(장비 보호 범위 안에서), `pci`(1~1007), `tac`(코어와 함께), `log` 와 `pcap` 전부, `num_recv/send_frames`.

**계산하고 바꾸는 것**: `channel_bandwidth_MHz` 와 `common_scs` — PRB 수와 USB 대역폭(2.6)이 같이 변한다. 10 MHz 로 줄이면 PRB 24, 처리량 절반, USB 부담 절반. 40 MHz 로 늘리면 PRB 106, srate 46.08, USB 3 에서도 빡빡하고 복제 보드에서는 `U` 가 는다. `dl_arfcn` — 반드시 10.6 의 절차로. `tdd_ul_dl_cfg` — 상향을 늘리면 상향 속도가 늘고 하향이 준다.

**바꾸면 안 되는 것**: `plmn` 을 상용 사업자 값(450-xx)으로 바꾸는 것. 단말이 상용 SIM 으로 우리 셀에 붙으려 시도하게 만든다. `band` 를 우리 장비와 허가가 없는 대역으로. `device_args` 의 `serial`. 그리고 **안테나를 다는 것** — 차폐함 밖에서는 어떤 게인에서도.

## 10.10 실패 양상 사전

기지국이 "안 된다"는 말은 열 가지 다른 상태를 뜻한다. 증상에서 원인으로 가는 표다. 전부 우리가 겪었거나 겪을 수 있는 것이다.

| 증상 | 어디를 보나 | 원인 |
|---|---|---|
| 컨테이너가 바로 죽는다 | `docker logs srsgnb` 첫 20 줄 | 설정 파일 문법, 플레이스홀더 미치환(`PLMN` 글자 그대로), ARFCN 격자 불일치 |
| `No devices found` | `lsusb`, `uhd_find_devices` | 장치 안 꽂힘, 다른 프로세스가 점유, 시리얼 불일치 |
| `fx3 state 5` 또는 FPGA 로드 실패 | 로그의 `Loading FPGA` 다음 줄 | 정품 이미지를 복제 보드에, 또는 이미지 경로 틀림 |
| `Operating over USB 2.` | 그 줄 | **케이블**. 그 다음 포트. 보드는 마지막 |
| 콘솔에 `U`, `O`, `L` 이 계속 | 콘솔 | USB 대역 부족(2.6), CPU 부족, 샘플레이트 과다. `L` 은 late(샘플이 늦게 도착) |
| `LIBUSB_TRANSFER_ERROR` 반복 | 로그 | USB 2 또는 불량 케이블/포트. 10.7 |
| `gNB started` 는 떴는데 `N2: Connection to AMF` 가 없다 | 로그, `docker exec srsgnb ss -tn` | AMF 주소/포트, 코어 미기동, SCTP 가 도커 네트워크를 못 넘음 |
| N2 연결 뒤 바로 끊김 | AMF 로그 | NG Setup 거절 — PLMN/TAC 불일치 |
| 단말이 셀을 못 본다 (`COPS=?` 에 없음) | 모뎀 `+QENG`, 기지국 pcap | 엉뚱한 장치(10.7), 게인 부족(10.8), SSB 가 격자 밖, RF 경로 단선, 모뎀 밴드 제한(`+QNWPREFCFG`) |
| 셀은 보이는데 RACH 가 안 된다 | `mac_enable` pcap 에 프리앰블 없음 | 상향 경로 문제 — 모뎀 ANT(안테나) 포트가 수신 전용, 상향 감쇠 과다, `rx_gain` 부족 |
| RACH 되고 RRC 되는데 등록 거절 | AMF 로그 `Registration reject` 사유 | 가입자 없음, PLMN 불일치, 인증 실패(Ki/OPc) — 기지국 문제 아님 |
| 등록 되는데 느리다 | 모뎀 `+QENG` 의 SINR, MCS | 게인 포화, 간섭(누설), 1T1R 한계 |

마지막 두 줄이 중요하다. **RRC 연결까지 됐으면 기지국은 자기 일을 다 한 것이다.** 그 뒤는 코어(5~7 장)다. 어디까지 됐는지를 먼저 가르면 보는 로그가 반으로 준다.

## 10.11 지금 네 장비에서

이 장을 읽었으면 다음을 순서대로 한다.

1. `lsusb | grep -i ettus` — 장치 수를 센다. 둘 이상이면 `sudo lsusb -s <bus>:<dev> -v | grep iSerial` 로 시리얼을 확인하고, 송신하지 않을 장치는 뽑는다.
2. `grep device_args configs/srsran/gnb.yml` — `serial=` 이 있는지 본다. 없으면 띄우지 않는다.
3. `grep -E 'dl_arfcn|channel_bandwidth|common_scs' configs/srsran/gnb.yml` — 3.6 의 공식으로 중심 주파수를 계산하고 1 장의 표와 대조한다.
4. `docker compose -p docker_open5gs -f srsgnb.yaml up -d && sleep 15 && docker logs srsgnb` — 10.4 의 줄들이 순서대로 나오는지, 특히 `Operating over USB 3.` 과 `N2: Connection … completed` 를 확인한다.
5. `docker logs --since 1m srsgnb | grep -c LIBUSB` — 0 이어야 한다. LIBUSB 는 UHD 가 B210 과 USB 로 말할 때 쓰는 리눅스 사용자 공간 USB 라이브러리 libusb 의 오류 접두어다. 이 줄이 하나라도 있으면 10.7 의 USB 2 사고를 다시 의심한다.
6. 모뎀에서 `AT+COPS=?` — `00101` 이 보여야 한다. 안 보이면 10.10 표의 "단말이 셀을 못 본다" 줄.
7. `pcap.ngap_enable: true` 로 바꿔 재기동하고, 모뎀을 `CFUN=0/1` 한 뒤 `/mnt/srsran/gnb_ngap.pcap` 을 와이어샤크로 연다. 10.5 의 열 단계가 `ngap` 필터로 보여야 한다.

## 10.12 이 장의 요약

| 질문 | 답 |
|---|---|
| 기지국은 무엇인가 | 전파 ↔ IP 변환의 층 더미. CU-CP(RRC, NGAP) / CU-UP(SDAP, PDCP, GTP-U) / DU(RLC, MAC, PHY) / Radio(UHD) |
| 설정의 핵심 줄 | `device_args` 의 `serial=`, `dl_arfcn`, `tx_gain`, `amf.addr`, `plmn`/`tac` |
| 기동 로그에서 꼭 볼 줄 | `Operating over USB 3.`, `Cell pci=…`, `N2: Connection … completed` |
| 단말이 붙는 순서 | SSB → SIB1 → RACH → RRC → NGAP Initial UE → (인증 투명 전달) → Context Setup(K_gNB) → PDU Session Resource(TEID, DRB) → 데이터 → Release |
| 기지국이 모르는 것 | 단말의 신원. RNTI, NGAP ID, K_gNB 만 가진다 |
| 주파수 선택 | 상용 할당 밖 + GSCN 격자 안 + PointA·k_SSB 정합. 옮길 땐 1.44 MHz 정수 배 |
| 우리가 틀린 것 | 시리얼 미지정으로 엉뚱한 장치 송신 9 분 / USB 2 케이블 반나절 / "셀이 보였다"를 "링크가 된다"로 기록 |
| 게인 | 80 에서 케이블 경로 RSRP −103/−112(화면의 −71 은 종단 포트의 찌꺼기). 더 올리지 않는 이유는 포화와 누설 |
| 실패를 가르는 선 | RRC 연결까지 되면 기지국은 끝. 그 뒤는 코어 |

## 점검 문제

1. `device_args` 에서 `serial=` 을 빼면 어떤 위험이 생기는가? 우리 사례로 설명하라.
2. `Operating over USB 2.` 가 떴다. 의심할 순서를 셋 적고 각각 어떻게 확인하는지 쓰라.
3. `dl_arfcn` 을 623334 에서 640008 로 바꾸면 중심 주파수는 얼마가 되고, 한국에서 어떤 문제가 생기는가?
4. 단말이 붙는 열 단계 중 기지국이 단말의 존재를 처음 아는 단계는? 그 전까지 기지국은 무엇을 하고 있는가?
5. `N2: Connection to AMF` 가 안 뜨는데 `gNB started` 는 떴다. 모뎀에는 무엇이 보이고 무엇이 안 되는가?
6. `AT+QENG` 의 RSRP 한 칸만 보고 게인을 정하면 왜 위험한가? `AT+QRSRP` 의 네 칸으로 무엇을 추가로 알 수 있는가?
7. `tdd_ul_dl_cfg` 로 상향 슬롯을 2 개로 늘리면 하향 TCP 처리량이 오를 수도 있는 이유는?

## 직접 해보기

- `pcap.mac_enable: true` 로 10 초만 켜고, 와이어샤크에서 `mac-nr` 필터로 RACH 프리앰블과 RAR 을 찾아라. RAR 안의 타이밍 어드밴스 값을 읽어라.
- `tx_gain` 을 80 에서 5 dB 씩 내리며 모뎀의 `+QENG` RSRP 와 등록 성공 여부를 기록하라. 등록이 안 되는 첫 게인을 찾고 거기에 10 dB 를 더한 값이 적정 게인이다.
- `channel_bandwidth_MHz: 10` 으로 바꿔 띄우고 로그의 PRB 수, 콘솔의 `U`/`O` 빈도, iperf 처리량을 20 MHz 와 비교하라. 2 장의 USB 계산과 3 장의 PRB 계산이 맞는지 본다.

---

> **출처**: CU/DU 분리와 층 역할은 TS 38.401/38.300. NGAP 메시지 이름은 TS 38.413. RACH/RRC 절차는 TS 38.321/38.331. 기동 로그·설정·사고 서술은 전부 이 실험실 실측. B210 출력 `>10 dBm`·게인 범위는 Ettus B200/B210 데이터시트. RSRP↔총전력 27.9 dB 는 10·log₁₀(51×12) 계산. srsRAN TDD 기본값은 공식 설정 레퍼런스(docs.srsran.com, config_ref) 의 `tdd_ul_dl_cfg` 항목.

*다음 장: 11. 모뎀과 제어 인터페이스*
