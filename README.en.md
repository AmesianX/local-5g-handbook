# Building a Local 5G Network — A Hacker's Field Guide to Mobile Networks

[한국어](README.md) · **English**

> **📕 [Download the PDF (A4, 181 pages, Korean)](https://github.com/AmesianX/local-5g-handbook/releases/latest/download/local-5g-handbook-ko.pdf)** · [All editions](https://github.com/AmesianX/local-5g-handbook/releases)

One Linux box, one software-defined radio, one 5G modem and a SIM card whose secret key we wrote ourselves. This is the record of how we built a complete 5G mobile network in a single room, from the radio up through the core and the phone system, until a real Galaxy phone rang with a number issued by our own network.

> **Phreaking was the hacker's playground of the 1970s. Today, it's building your own local 5G network.**

*The book is written in Korean. This page introduces it in English.*

---

## A carrier of your own, in your own room

Most of us grew up believing that a mobile network is something only a handful of licensed carriers are allowed to run. That isn't wrong, but it helps to ask *why* spectrum has owners in the first place. Radio waves radiated into the open interfere with one another, degrade public services and trample on the carriers' business, so the airwaves can't be a free-for-all. Which raises an interesting question: what about a closed space from which not a single milliwatt escapes? If there is no one to interfere with, could we stand up a base station of our own and start signing up subscribers?

Picture it. We flash a blank SIM with a 128-bit key of our choosing, add one line with an IMSI and a phone number to our subscriber database, and slide the card into a Galaxy phone. The status bar lights up with `5G` and `HD`. We dial the number and the phone rings; we send a text and the bubble appears. And everything in between — the cryptographic handshake in which the phone proves who it is, the message that hands it an IP address, the SIP that sets up the call, the RTP packets carrying a voice — flows through our own Linux box, so we can follow, in Wireshark, a conversation the carriers have never once let us see.

Push the idea a little further. The network's only way out to the internet is the Linux box's default route. Carry that box and the radio to a mountain hut, a ship at sea, or a village whose towers have fallen in an earthquake, plug a satellite terminal into that route, and *our* cell comes alive right there: people take the phones out of their pockets, insert a SIM we burned for them, and call each other and get online. A network that does everything a carrier does, without a carrier, that we can carry in our hands. This is not just a daydream, either. Japan has licensed exactly this kind of network to non-carriers since 2019 under the name **Local 5G**, Korea since 2021 as **e-Um 5G**, and those networks are built from the very same pieces this book assembles.

## It started at 2600 Hz

In the 1970s there were people in the United States who called themselves **phone phreaks**. Long-distance switches of the day signalled to one another over the very same line that carried your voice, so if you blew a 2600 Hz tone into the handset, the switch concluded the line was idle and sat waiting for its next command. A toy whistle given away in boxes of breakfast cereal produced exactly that pitch, and a device that generated the whole set of tones at the push of a button became known as the **blue box**. A college student named Steve Wozniak redesigned the blue box with digital circuitry, and his friend Steve Jobs sold them. Jobs later said that without the blue box there would have been no Apple — that it was where they first learned a giant system could be moved by a box that fit in your palm.

For the half-century that followed, mobile networks became the most closed territory a hacker could face. The baseband runs its own firmware beneath the operating system, base stations sit on rooftops, and the core lives in refrigerator-sized racks inside the carrier's exchange; all we ever got to see were a few signal bars on the status bar. Then, quietly, the work inside those refrigerators turned into Linux processes calling one another over HTTP/2. Open-source cores and base stations matured to the point where real phones can attach to them, and programmable SIM cards became something an individual can simply order.

The phreaks found ways to fool the switch. **Now we get to own the switch.** Just as hackers back then were hooked on peering into the guts of a continent-spanning network with nothing but a whistle, the engineer of our era has inherited that same thrill, and it takes the form of **building a 5G network in your own room.** The difference is that this time we aren't fooling anyone's network — we are building our own from end to end. Which is exactly why there is no need to hide it, and why we can publish it as a book and enjoy it together.

## But what about the radio? Experiments A and B

The dream is big, but the first step has to be careful. A radio experiment carries risk in two directions: outward, we must never disturb anyone else's communications; inward, we must not burn our own equipment. The whole book is built on two experiments that avoid both.

**Experiment A — anyone, right now.** Instead of antennas, connect the software radio playing the base station (a B210) and the 5G modem module playing the phone **directly with coaxial cable, with an attenuator in between.** The signal travels only inside a metal tube instead of through the air, so nothing is radiated, and you can start on your desk without an expensive shielded enclosure. Registration and authentication, data and throughput, and even calls and texts placed by our own test tools — nearly the whole network is built and measured with this one setup. It is the idea this book cherishes most: rather than trapping radio waves, we never create them in the first place, and the modem under test doubles as the instrument that measures the network.

**Experiment B — with a real phone.** What goes inside the shield box — a metal enclosure radio waves cannot escape — is **the phone, not the B210.** The B210 stays outside and its signal is fed through the wall of the box over coax, becoming radio only at a small antenna on the inside. The phone is the side whose antenna can't be removed, so the phone is what we enclose. Do it the other way round and the phone, left outside, hears a commercial cell thousands of times stronger and never even sees ours. You need to get hold of a shield box, so the bar is higher, but in return you get to experiment with the very phone in your pocket.

> ⚠️ **Connect without an attenuator and you will burn your gear.** When a phone first raises its hand to the network it can shout at up to +23 dBm, while the B210's receiver is only good for about 0 dBm. A 40 dB attenuator brings that shout down to −17 dBm. And don't drop the attenuator just because you're inside the shield box: a hand's width of air barely takes anything off the signal. Section 0.7 has the full rules.

## What we actually achieved

Every number in this book was measured in our own lab. Throughout the text, calculated values are marked **[estimate]**, measured values **[measured]**, and anything still unconfirmed **[needs verification]**.

| | |
|---|---|
| Radio | 5G NR SA, band n78 TDD, centre 3350.01 MHz (40 MHz clear of commercial allocations), 20 MHz |
| RAN · Core | srsRAN Project + B210 · Open5GS 5GC + Kamailio IMS + PyHSS |
| Experiment A | Quectel RM520N-GL modem + self-programmed sysmoISIM-SJA5, direct coax + 40 dB attenuator |
| Experiment B | Real Galaxy S22+ handset inside a TOJOIN MS3020-A shield box |
| Throughput (A) | 55 Mbps down / 11 Mbps up |
| Round-trip latency | A: 38 ms, B: 25–31 ms (UE → UPF) |
| Calls & messaging | VoNR voice calls, SMS, MMS, video call setup (on a real phone in experiment B) |
| Shield-box leakage | Below detection limit |

## Why we are sharing this

The phreaks traded what they discovered through newsletters and magazines, and we are doing the same with the road we stumbled along. Mobile networking has long been locked behind thousands of pages of standards and the doors of the carriers, and a curious engineer diving in alone can easily be worn out by decibels, channel numbers and SIM keys before ever bringing up a first cell. That was us, too. We lost half a day to a single USB 2.0 cable, chased 30 dB around the wrong corner of the system because we misread one number on an engineering screen, and watched a call setup that had worked between our scripts for four months get rejected by a real phone on its very first try.

So this book does not lay out theory first, textbook-style. Knowledge appears exactly where building experiment A gets stuck, as the answer to that particular block, and the twenty-four times we actually got stuck are preserved in a casebook — the symptom, the wrong hypotheses, the one decisive log line, and the fix. We want the next person not to lose the same hours in the same places. By the time you close the book, you should be able to explain what happens behind those signal bars not from someone else's diagram but from the logs of a network you brought up with your own hands.

## Who it's for

Hackers and engineers who are at home with networking and Linux but have never studied electronics or mobile communications. If you can open a capture in Wireshark and spin up a container, you are ready; it's fine if you've never heard of a decibel or OFDM. Unfamiliar ideas are explained through things you already know — port numbers, relative paths, floating-point epsilon.

## Contents

| | | |
|---|---|---|
| | **Preface · Ch. 0** | A network of your own: why build it, experiments A and B, the rules that keep your gear alive |
| **Part I** | Before the gear arrives | 1 Radio waves and frequency · 2 SDR and the B210 · 3 Mobile networks at a glance |
| **Part II** | First signal | 4 Building the lab · 5 OFDM and the 5G NR physical layer · 6 The base station |
| **Part III** | First subscriber | 7 What a SIM really is · 8 Modems and AT commands · 9 The 5G core and SBI · 10 Identity and authentication |
| **Part IV** | The network walks | 11 Sessions and IP · 12 QMI and the data path · 13 Voice and text (IMS) · 14 The engineering screen, dissected · 15 Test procedure and measurement |
| **Part V** | Experiment B | 16 A real phone inside the shield box |
| **Part VI** | When you fall | 17 Casebook: the twenty-four times we got stuck |
| **Part VII** | Going deeper | 18 History of the modem and dial-up, dissected · 19 The entire AT command system · 20 Attack surface and trust boundaries |
| **Appendices** | | A Glossary · B Command reference · C Configuration file map · D Radio and legal notice |

## Safety and the law

Every experiment in this book assumes **nothing is radiated into the open air**: in experiment A the signal stays inside coaxial cable, in experiment B inside a shield box. Mobile spectrum requires a licence in every country, so transmitting over the air without one is against the law — and the 3.6 GHz values common in example configs sit right in the middle of commercial allocations, so never copy them as-is. PLMN 001/01 is the code the international standards set aside for testing. Appendix D collects where the law draws its lines; please read it before you power anything on.

Real values for subscriber keys (Ki, OPc), card admin keys (ADM) and PIN/PUK never appear in the book; they are all replaced by placeholders such as `<KI>`, `<OPC>` and `<ADM1>`.

## Repository layout

| Path | Contents |
|---|---|
| `00-머리말.md`, `00a-…`, `01-…` – `20-…`, `부록A–D` | The book, in Markdown |
| `reader.html` | Single-page reader with contents, search and reading position; download and open in a browser |
| `images/` | Figures and real-phone screenshots |
| `tools/make_pdf.py`, `tools/build_reader.py` | Build the PDF and the reader; the PDF build verifies every table-of-contents page number against the printed pages |
| `tools/edit_guard.py` | Checks that an edited manuscript left code, numbers and cross-references untouched |
| `tools/acronym_audit.py`, `tools/gloss_audit.py`, `tools/landing_audit.py` | Acronym, term-definition and section-ending audits |
| `tools/ims_call.py`, `tools/milenage.py` | Test tools used in the book (keys are placeholders) |

```bash
python3 tools/build_reader.py   # reader.html
python3 tools/make_pdf.py       # 로컬5G망구축하기.pdf (needs Playwright Chromium and poppler-utils)
```

## License

MIT License. © AmesianX. All measurements and logs in the text come from this lab.
