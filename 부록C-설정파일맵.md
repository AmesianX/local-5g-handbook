# 부록 C. 설정 파일 맵: 어떤 값이 어느 파일에서 와서 어느 프로세스가 읽는가

이 망에서 무언가를 바꾸려 할 때 가장 먼저 부딪히는 질문은 "그 값이 어디 있느냐"다. AMF 의 주소는 `amf.yaml` 에 있는 것처럼 보이지만 실제로는 `.env` 에서 오고, 단말 IP 대역은 `smf.yaml` 에 써 있지만 그 줄을 고치면 다음 기동 때 사라진다. 이 부록은 그 지도를 한 장으로 모은다. 9장 9.5절의 원칙 — **정본은 `private5g/configs/`, 클론은 배포 사본, 컨테이너 안은 기동 때마다 다시 만들어지는 결과물** — 을 전제로 읽는다.

## C.1 값이 흐르는 세 단계

```
① 정본                          ② 배포 사본 (클론)                 ③ 컨테이너 안 (런타임)
private5g/configs/env/env  ──▶  docker_open5gs/.env  ──(env_file)──▶ 각 컨테이너의 환경변수
                                                                        │
private5g/configs/srsran/   ──▶  docker_open5gs/srsran/ ──(볼륨)──▶ /mnt/srsran/gnb.yml
   gnb.yml                                                              │ 기동 스크립트가
                                                                        ▼ 자리표시자를 sed 치환
                                                     /open5gs/install/etc/open5gs/amf.yaml 등
        bin/deploy-configs.sh 가 ①→② 를 복사         (치환 결과. 여기서 고치면 재기동 때 사라짐)
        (cmp 로 다른 것만, --check 는 차이만 출력)
```

①→② 는 `deploy-configs.sh` 가 하고, `core-ctl.sh START` 가 기동 전에 이것을 먼저 부른다. ②→③ 은 도커와 각 컨테이너의 `*_init.sh` 가 한다. 예를 들어 `amf_init.sh` 는 클론의 `amf/amf.yaml` 을 컨테이너 안으로 복사한 뒤 `AMF_IP`, `MCC`, `MNC`, `TAC` 같은 글자를 `sed` 로 env 값으로 바꾼다. 그래서 **값을 바꾸려면 ①을 고치고, 확인은 ③에서 한다.**

```bash
bin/deploy-configs.sh --check                     # ①과 ②가 같은가
docker exec amf grep -n 'tac\|mcc' /open5gs/install/etc/open5gs/amf.yaml   # ③에 실제로 뭐가 들어갔나
```

## C.2 정본 목록 (deploy-configs.sh 매핑)

| 정본 (`private5g/configs/…`) | 배포 위치 (클론) | 읽는 주체 | 다루는 장 |
|---|---|---|---|
| `env/env` | `.env` | 모든 컨테이너(env_file) → 각 `*_init.sh` | 5.6, 9.6 |
| `dns/ims_zone` | `dns/ims_zone` | `dns` 컨테이너(bind) | 8, 13 |
| `compose/sa-vonr-deploy.yaml` | `sa-vonr-deploy.yaml` | docker compose (코어·IMS 전체 정의) | 9, 11e |
| `srsran/gnb.yml` | `srsran/gnb.yml` | `srsgnb` 의 `gnb` 프로세스 | 10 전체 |
| `srsran/libresdr_alphafox02.bin` | `srsran/…bin` | `srsgnb` 안 UHD (FPGA 적재) | 2, 9.2, 10 |
| `srsran/gnb_zmq_n78.yml` | `srsran/…` | 시뮬레이션 기지국(ZMQ) | 3 |
| `pcscf/route/register.cfg` | `pcscf/route/` | `pcscf` 의 Kamailio | 8 |
| `pcscf/route/mo.cfg` | `pcscf/route/` | `pcscf` (발신 통화 경로) | 8 |
| `pcscf/route/mt.cfg` | `pcscf/route/` | `pcscf` (착신 통화 경로) | 8 |
| `oai/gnb.sa.band78…usrpb210.conf` | `oai/…` | OAI 기지국(실장비용, 미사용) | 3 |
| `srslte/ue_5g_zmq*.conf` | `srslte/…` | srsUE(n3 시뮬레이션) | 3 |

OAI 시뮬레이션 프로파일(`compose/oai_n78_rfsim.yaml` 과 `configs/oai/gnb.n78.rfsim.conf`, `nr-ue.n78.rfsim.conf`)은 클론에 의존하지 않고 `private5g/` 안에서 직접 뜬다.

## C.3 우리가 업스트림 기본값에서 바꾼 것 전부

업스트림(`herlesupreeth/docker_open5gs`)의 기본값과 다른 곳은 아래가 전부다. 각 줄의 "왜"가 본문 어디에 있는지 함께 적는다. 새로 실험실을 꾸리는 독자는 이 표를 체크리스트로 쓰면 된다.

**`.env`**

- `MCC=001`, `MNC=01`, `TAC=1` — 시험용 PLMN(부록 D.5). 업스트림 기본도 001/01 이지만 반드시 확인한다.
- `DOCKER_HOST_IP=<HOST_LAN_IP>` — 호스트의 LAN 주소. 실험실마다 다르다.
- `UE_IPV4_INTERNET=10.45.0.0/16`, `UE_IPV4_IMS=10.46.0.0/16` — 기본값 `192.168.100.0/24`·`192.168.101.0/24` 가 우리 LAN 과 겹쳐서 바꿨다(9.6). 이 두 줄에서 `smf.yaml`·`upf.yaml` 의 풀과 게이트웨이, UPF 의 NAT 규칙이 전부 파생된다.

**`srsran/gnb.yml`** (10장이 한 줄씩 해부)

- `device_args: type=b200,serial=5JKRCXX,fpga=/mnt/srsran/libresdr_alphafox02.bin,num_recv_frames=64,num_send_frames=64` — 장치 고정(9.2, 10.7 사고 1), LibreSDR 전용 FPGA, USB 버퍼 수.
- `otw_format: sc12` — USB 위의 샘플을 12비트로 보내 대역폭을 줄인다(2장).
- `tx_gain: 80`, `rx_gain: 36` — 40 → 65 → 80 으로 올린 과정은 10.8. 바꾸기 전 값은 `configs/_backup/gnb.yml.gain65.bak` 등에 남아 있다.
- `dl_arfcn: 623334`, `band: 78`, `channel_bandwidth_MHz: 20`, `common_scs: 30` — 주파수 계획(10.6). 기동 로그상 SSB 는 `dl_ssb_arfcn=623040`(3345.6 MHz) 로 선택됐다.
- `pci: 1`.

**`dns/ims_zone`**

- `@  1D IN A  ICSCF_IP` 한 줄 추가 — IMS 도메인 자체의 A 레코드. SMSC 가 `sip:<번호>@ims.mnc001.mcc001.3gppnetwork.org` 로 문자를 넘길 때 이 이름을 풀어야 하는데, 업스트림 존에는 서브도메인(`pcscf.`, `scscf.` …)만 있고 도메인 자체가 없어 전달이 조용히 멈췄다(8장 벽 ⑦, 13장). 처음에는 컨테이너 안에서 고쳤고, 그다음 클론에 반영했고, 이 부록을 쓰면서 정본(`configs/dns/`)과 배포 매핑에 올렸다. 세 단계를 다 거치기 전까지는 클론을 새로 받는 순간 사라질 수 있는 수정이었다.

**`pcscf/route/{register,mo,mt}.cfg`**

- P-CSCF 가 PCF 에 보내는 N5 정책 요청(JSON, `Npcf_PolicyAuthorization`) 안의 미디어 컴포넌트마다 있던 `"qosReference": "qosVoNR"` 줄을 지웠다(발신 4곳, 착신 4곳, 등록 1곳). 원본은 `configs/_backup/*.qosref.bak`(2026-09-21). **바꾼 이유는 당시 기록에 남아 있지 않다.** 우리가 소스에서 확인한 것은 다음뿐이다. 로컬에 받아 둔 Open5GS 소스(`src/pcf/npcf-handler.c`, 2026-09-19 커밋 bb810d3)의 PCF 는 `qosReference` 가 오면 자기 설정의 `qos_profile` 목록에서 같은 이름을 찾고, 없으면 `"Unknown qosReference - check PCF qos_profiles config"` 로 거절한다. `qosReference` 가 없으면 미디어 종류로 정한다 — AUDIO 는 QoS 인덱스 1, VIDEO 는 2. 우리 PCF 설정에는 `qosVoNR` 이라는 프로파일이 없다. 그러므로 이 줄을 지운 것이 PCF 가 음성에 5QI 1, 영상에 5QI 2 를 고르게 한 경로와 일치한다. 다만 실제로 돌고 있는 PCF 이미지는 `v2.8.0-48-gf87da61` 이고 그 커밋이 로컬 소스에 없어 같은 코드인지 확인하지 못했다 [검증 필요].

**`sa-vonr-deploy.yaml`** (코어·IMS compose 정의)

- PyHSS REST(8080), webui(9999), grafana(3000), metrics(9090) 의 `ports:` 를 `0.0.0.0` 공개에서 `127.0.0.1:` 로 바꿨다. 업스트림 기본은 호스트의 모든 인터페이스에 공개라, 인증 없는 PyHSS API 가 LAN 에 열려 있었다(11e.4). 원본은 `configs/_backup/sa-vonr-deploy.yaml.pre-loopback.bak`.

**호스트 쪽 (컨테이너 밖)**

- `/etc/udev/rules.d/99-private5g-modem-ignore.rules` — ModemManager 가 우리 모뎀(2c7c:0801)을 건드리지 않게 한다(9.3, 13장).
- `~/.uhd/uhd.conf` — 시리얼별 FPGA 이미지 지정. 호스트에서 UHD 도구를 직접 쓸 때만 읽힌다(9.6).

## C.4 파일이 아닌 설정: 데이터베이스에 든 것

망의 일부 설정은 파일이 아니라 **DB 안에** 있다. 이것들은 `deploy-configs.sh` 가 다루지 않고, 컨테이너를 지워도 도커 볼륨에 남는다. 반대로 볼륨을 지우면 사라진다.

**`mongo` — 5G 코어 가입자(Open5GS).** 가입자마다 IMSI, 키(K, OPc), AMF 필드, 그리고 DNN 별 세션 설정이 한 문서에 들어 있다. 우리가 넣거나 바꾼 것은 이렇다. `ims` DNN 세션의 기본 5QI 를 5 로(8장 — 5QI 9 면 PCF 가 IMS 시그널링을 거절), 그리고 **5QI 1 PCC 규칙**(음성. 없으면 PCF 가 `No PCC Rule in DB [QoS Index:1]` 로 거절, 13장)과 **5QI 2 PCC 규칙**(영상). 2026-10-14 에 DB 를 다시 읽어 보니 통화에 쓴 가입자 둘은 `internet`·`ims` 두 세션 모두에 PCC 규칙 [1, 2] 가 들어 있었고, 그중 하나는 `internet` 세션 기본 5QI 도 5 로 올라가 있었다(실험 중 바꾼 흔적). 세 번째 가입자(시뮬레이션용)는 PCC 규칙이 없다. 확인은 이렇게 한다.

```bash
docker exec mongo mongosh open5gs --quiet --eval \
  'db.subscribers.findOne({imsi:"<IMSI>"}).slice[0].session.map(s=>({dnn:s.name, qi:s.qos.index, pcc:(s.pcc_rule||[]).map(r=>r.qos.index)}))'
```

**`mysql` — IMS 가입자(PyHSS).** IMS 쪽 가입자(IMPI/IMPU, 전화번호, 인증 키)가 따로 있다. 5G 코어와 DB 가 둘이라 가입자를 추가할 때 양쪽에 넣어야 한다는 점은 5.5절에서 봤다.

**`smsc` 의 메시지 표.** SMSC 가 받아 둔 문자는 MySQL 의 SMSC 스키마(`smsc-create.sql`)에 쌓였다가 전달 뒤 지워진다. 전달이 멈추면 여기에 남아 있는 것이 증거다(13장).

DB 의 내용은 키를 포함하므로 **이 책과 저장소에는 넣지 않는다.** 백업이 필요하면 `docker exec mongo mongodump --archive > open5gs.archive` 처럼 받아 실험실 밖으로 내보내지 않는 곳에 둔다.

## C.5 런타임에만 존재하는 것

다음은 설정 파일이 아니라 기동 스크립트가 **매번 만드는** 상태다. 이상하면 파일이 아니라 만드는 스크립트를 본다.

| 상태 | 만드는 곳 | 확인 |
|---|---|---|
| `ogstun` 10.45.0.1/16, `ogstun2` 10.46.0.1/16 | `upf/tun_if.py` (env 의 UE 대역에서 파생) | `docker exec upf ip -br addr` |
| NAT `-s 10.45.0.0/16 ! -d <PCSCF_IP> ! -o ogstun -j MASQUERADE` | `upf/tun_if.py` | `docker exec upf iptables -t nat -S` |
| 도커 브리지 `br-<네트워크 ID>` | 도커(네트워크 생성 시) | `docker network ls` |
| 모뎀 `wwan0` 주소 | 우리가 QMI 로 받은 값을 손으로(11d) | `ip -br addr show wwan0` |

## C.6 백업 파일 읽는 법

`configs/_backup/` 의 파일 이름은 "무엇을 바꾸기 직전의 원본인가"를 꼬리표로 단다. `gnb.yml.noserial.bak` 은 `serial=` 을 넣기 전, `gnb.yml.gain65.bak`·`gain74.bak` 은 게인을 올리기 전, `env.ue192168.bak` 은 UE 대역을 바꾸기 전, `*.qosref.bak` 은 `qosReference` 를 지우기 전, `deploy-configs.sh.pre-dns.bak` 은 DNS 존을 매핑에 넣기 전이다. 되돌릴 때는 백업을 정본 자리에 복사하고 `deploy-configs.sh` 로 배포한 뒤 재기동한다. 클론 쪽으로 직접 복사하지 않는다.
