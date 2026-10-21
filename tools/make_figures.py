# -*- coding: utf-8 -*-
"""1~3 장의 그림을 책의 실제 수치로 그린다.  사용: python3 tools/make_figures.py

그림도 재현 가능해야 한다. 숫자를 바꾸려면 이 파일의 상수를 고치고 다시 돌린다.
출력은 images/fig-*.png.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np, pathlib

FP = fm.FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
plt.rcParams['font.family'] = FP.get_name()
plt.rcParams['axes.unicode_minus'] = False
OUT = pathlib.Path(__file__).resolve().parent.parent / 'images'
INK, SUB, HI, OK = '#1a1a1a', '#6b6b6b', '#c23b22', '#2e6f40'


def save(fig, name):
    fig.savefig(OUT / name, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('  ', name)


# ── 그림 1-1  dB 눈금자 ────────────────────────────────────────────────
def db_ruler():
    """배수와 dB 를 나란히 놓는다. 0 근처는 라벨이 겹치므로 위아래로 엇갈려 찍는다."""
    pts = [(-40, '1/10000', 1, '감쇠기 40 dB'), (-20, '1/100', 0, ''),
           (-10, '1/10', 1, ''), (-3, '1/2', 0, ''), (0, '×1', 1, '기준 = 1 mW'),
           (3, '×2', 0, ''), (10, '×10', 1, ''), (20, '×100', 0, ''),
           (40, '×10000', 1, '')]
    fig, ax = plt.subplots(figsize=(9.6, 2.6))
    ax.axhline(0, color=INK, lw=1.5, zorder=1)
    for db, mul, up, note in pts:
        acc = bool(note)
        ax.plot([db], [0], 'o', ms=7.5, color=HI if acc else INK, zorder=3)
        lab = '0 dB' if db == 0 else ('\u2212%d dB' % -db if db < 0 else '+%d dB' % db)
        y1, y2 = (0.40, 0.72) if up else (-0.42, -0.74)
        va1, va2 = ('bottom', 'bottom') if up else ('top', 'top')
        ax.plot([db, db], [0, y1 * .72], color='#bdbdbd', lw=.9, zorder=2)
        ax.text(db, y1, lab, ha='center', va=va1, fontsize=10.5,
                color=HI if acc else INK, fontweight='bold' if acc else 'normal')
        ax.text(db, y2, mul, ha='center', va=va2, fontsize=10, color=SUB)
        if note:
            ax.text(db, -1.30 if up else 1.20, note, ha='center',
                    va='top' if up else 'bottom', fontsize=9.5, color=HI)
    ax.set_title('배수를 더하기로 바꾼 눈금 — 10 배마다 10 dB, 2 배는 약 3 dB',
                 fontsize=11.5, pad=16)
    ax.set_xlim(-48, 48); ax.set_ylim(-1.75, 1.55); ax.axis('off')
    save(fig, 'fig-1-1-db-ruler.png')


# ── 그림 1-2  링크 예산 폭포도 ─────────────────────────────────────────
def link_budget():
    """1.8 의 링크 예산. 왼쪽부터 깎여 내려가고, 마지막에 실측과의 차이를 보인다."""
    labels = ['B210 송신\n(tx_gain 80)', '동축·커넥터', '감쇠기\n40 dB',
              '모뎀 입력\n총전력', '부반송파\n612 개로', '예상 RSRP']
    fig, ax = plt.subplots(figsize=(9.6, 5.0))
    cur, xs = 0.0, range(6)
    deltas = [None, -2.5, -40.0, 'sum', -27.9, 'sum']
    for x, d in zip(xs, deltas):
        if d is None:
            ax.bar(x, 1.6, .6, bottom=-0.8, color='#ccd7e4', ec=INK, lw=1.1, zorder=3)
            ax.text(x, 5, '0 dBm', ha='center', fontsize=11, fontweight='bold', color=INK)
        elif d == 'sum':
            ax.bar(x, cur, .6, color='#ccd7e4', ec=INK, lw=1.1, zorder=3)
            # 책 본문과 같은 반올림 값을 쓴다 (1.8 의 −43 / −71)
            shown = -43 if cur > -50 else -71
            ax.text(x, cur - 5, f'\u2212{abs(shown)} dBm', ha='center', va='top',
                    fontsize=11, fontweight='bold', color=INK)
        else:
            ax.bar(x, -d, .6, bottom=cur + d, color='#f6dcd6', ec=HI, lw=1.1, zorder=3)
            txt = f'\u2212{abs(d):.1f} dB'
            if -d < 8:      # 막대가 얇으면 글자를 위로 뺀다
                ax.text(x, cur + d - 3.4, txt, ha='center', va='top', fontsize=10, color=HI)
            else:
                ax.text(x, cur + d / 2, txt, ha='center', va='center', fontsize=10, color=HI)
            cur += d
    ax.set_xticks(list(xs)); ax.set_xticklabels(labels, fontsize=9.5, color=SUB)
    ax.tick_params(axis='x', length=0, pad=8)

    for y, lab in [(-103, '실측 DRX (ANT2)  −103'), (-112, '실측 PRX (ANT1)  −112')]:
        ax.axhline(y, color=OK, lw=1.3, ls=(0, (6, 4)), zorder=1)
        ax.text(-0.75, y, lab, va='center', ha='left', fontsize=9.5,
                color=OK, backgroundcolor='white', zorder=4)
    ax.annotate('', xy=(5.62, -71), xytext=(5.62, -107),
                arrowprops=dict(arrowstyle='<->', color=HI, lw=1.6))
    ax.text(5.78, -89, '30~40 dB\n설명 안 됨', va='center', ha='left',
            fontsize=10.5, color=HI, fontweight='bold')

    ax.set_ylim(-124, 14); ax.set_xlim(-0.85, 7.1)
    ax.set_ylabel('dBm', fontsize=10)
    ax.set_yticks([0, -20, -40, -60, -80, -100, -120])
    for sp in ('top', 'right', 'bottom'): ax.spines[sp].set_visible(False)
    ax.grid(axis='y', color='#e8e8e8', lw=.8, zorder=0)
    ax.set_title('tx_gain 80 에서 모뎀 입력까지 — 예산과 실측이 갈리는 곳',
                 fontsize=12, pad=14)
    save(fig, 'fig-1-2-link-budget.png')


# ── 그림 2-1  I/Q 평면과 성상도 ────────────────────────────────────────
def constellation():
    """같은 잡음을 세 변조에 똑같이 뿌린다. QPSK 는 멀쩡하고 256QAM 은 뭉개진다."""
    SIGMA = 0.042                      # 세 그림에 동일하게 적용되는 잡음
    rng = np.random.default_rng(11)
    specs = [('QPSK — 한 칸에 2 비트', 2), ('16QAM — 4 비트', 4), ('256QAM — 8 비트', 16)]
    fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.9))
    for ax, (title, n) in zip(axes, specs):
        lv = (np.arange(n) - (n - 1) / 2) / ((n - 1) / 2)
        I, Q = (a.ravel() for a in np.meshgrid(lv, lv))
        rep = 40 if n <= 4 else 6
        ax.scatter(np.repeat(I, rep) + rng.normal(0, SIGMA, I.size * rep),
                   np.repeat(Q, rep) + rng.normal(0, SIGMA, Q.size * rep),
                   s=2.0, color='#8aa0bd', alpha=.55, linewidths=0, zorder=2)
        ax.scatter(I, Q, s=18 if n <= 4 else 5, color=INK, zorder=3, linewidths=0)
        ax.set_title(title, fontsize=10.5, pad=8)
        ax.set_xlim(-1.38, 1.38); ax.set_ylim(-1.38, 1.38); ax.set_aspect('equal')
        ax.axhline(0, color='#cfcfcf', lw=.8, zorder=1)
        ax.axvline(0, color='#cfcfcf', lw=.8, zorder=1)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values(): sp.set_color('#bdbdbd')
        d = abs(lv[1] - lv[0])
        ax.text(0, -1.30, f'점 사이 거리 {d:.2f}', ha='center', fontsize=9, color=SUB)
    axes[0].set_xlabel('I  (실수부)', fontsize=9.5)
    axes[0].set_ylabel('Q  (허수부)', fontsize=9.5)
    axes[0].annotate('점 하나 = 샘플 하나\n= 복소수 하나\n\n파란 구름 = 잡음이\n흩어 놓은 자리',
                     xy=(0.86, 0.86), xytext=(-0.08, 0.12), fontsize=8.8, color=HI,
                     ha='center', va='center',
                     arrowprops=dict(arrowstyle='->', color=HI, lw=1,
                                     connectionstyle='arc3,rad=-0.2'))
    fig.text(.5, -.04,
             '세 그림에 **같은 크기의 잡음**을 뿌렸다. QPSK 는 멀쩡하고, 256QAM 은 이웃 점과 구름이 겹치기 시작한다 — '
             'SINR 이 속도를 정하는 이유가 이 그림이다.'.replace('**', ''),
             ha='center', fontsize=9.5, color=SUB)
    save(fig, 'fig-2-1-constellation.png')


# ── 그림 3-1  시간·주파수 격자 ─────────────────────────────────────────
def grid():
    """자원 블록 하나(부반송파 12 × 심볼 14)와, 그것이 51 개 쌓인 우리 셀."""
    NS, NP = 14, 12
    fig, ax = plt.subplots(figsize=(9.0, 4.6))
    for sx in range(NS):
        for k in range(NP):
            ax.add_patch(plt.Rectangle((sx, k), 1, 1, fc='#eef2f7', ec='white', lw=1.1))
    ax.add_patch(plt.Rectangle((0, 0), NS, NP, fc='none', ec=INK, lw=1.8))
    ax.add_patch(plt.Rectangle((4, 7), 1, 1, fc=HI, ec='white', lw=1.1, zorder=3))
    ax.annotate('자원 요소(RE) 하나\n= 부반송파 1 × 심볼 1\n= 복소수 하나 (2 장의 I/Q)',
                xy=(5.0, 7.5), xytext=(16.4, 9.6), fontsize=9.5, color=HI, va='center',
                arrowprops=dict(arrowstyle='->', color=HI, lw=1.1))
    # 51 개 쌓인 모습
    for n, yb in enumerate([13.4, 14.6, 15.8]):
        ax.add_patch(plt.Rectangle((0, yb), NS, 0.9, fc='#dde5ef', ec=SUB, lw=.8))
    ax.text(NS / 2, 17.15, '. . .', ha='center', fontsize=12, color=SUB, rotation=90)
    ax.annotate('', xy=(NS + .6, 12.0), xytext=(NS + .6, 17.0),
                arrowprops=dict(arrowstyle='<->', color=SUB, lw=1.2))
    ax.text(NS + 1.0, 14.6, '자원 블록이 세로로 **51 개**\n= 부반송파 612 개\n= 우리 20 MHz 셀'.replace('**', ''),
            fontsize=9.5, color=INK, va='center')
    ax.text(NS / 2, 12.55, '← 자원 블록(RB) 하나 →', ha='center', fontsize=10, color=INK)
    ax.text(NS / 2, -1.45, '심볼 14 개  =  슬롯 하나  =  0.5 ms   (SCS 30 kHz)',
            ha='center', fontsize=10.5, color=INK)
    ax.text(-1.1, NP / 2, '부반송파 12 개\n= 360 kHz', va='center', ha='center',
            fontsize=10.5, color=INK, rotation=90)
    ax.set_xlim(-2.6, NS + 9.2); ax.set_ylim(-2.3, 18.1)
    ax.set_aspect('equal'); ax.axis('off')
    save(fig, 'fig-3-1-grid.png')


# ── 그림 3-2  TDD 패턴 ────────────────────────────────────────────────
def tdd():
    fig, ax = plt.subplots(figsize=(9.4, 2.6))
    pat = ['D'] * 6 + ['S'] + ['U'] * 3
    col = {'D': '#2e6f40', 'S': '#b9a24a', 'U': '#c23b22'}
    for i, p in enumerate(pat):
        ax.add_patch(plt.Rectangle((i, 0), .92, 1, fc=col[p], alpha=.82, ec='white'))
        ax.text(i + .46, .5, p, ha='center', va='center', color='white',
                fontsize=13, fontweight='bold')
        ax.text(i + .46, -.28, f'{i}', ha='center', fontsize=8.5, color=SUB)
    ax.text(3, 1.42, '하향 6 슬롯', ha='center', fontsize=10, color=col['D'])
    ax.text(6.46, 1.42, '전환', ha='center', fontsize=10, color=col['S'])
    ax.text(8.5, 1.42, '상향 3', ha='center', fontsize=10, color=col['U'])
    ax.annotate('', xy=(0, -.72), xytext=(10, -.72),
                arrowprops=dict(arrowstyle='<->', color=INK, lw=1.1))
    ax.text(5, -1.05, '10 슬롯 = 5 ms 주기로 되풀이',
            ha='center', fontsize=10, color=INK)
    ax.text(5, -1.62, 'TCP 의 ACK 는 상향 슬롯을 타야 한다 — 차례가 10 번 중 3 번뿐이라 하향도 같이 묶인다',
            ha='center', fontsize=9.5, color=HI)
    ax.set_xlim(-.5, 10.6); ax.set_ylim(-2.0, 1.95); ax.axis('off')
    save(fig, 'fig-3-2-tdd.png')


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    print('그림 생성:')
    db_ruler(); link_budget(); constellation(); grid(); tdd()
