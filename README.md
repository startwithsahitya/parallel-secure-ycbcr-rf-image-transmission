# Parallel YCbCr Image Transmission over RF

A research prototype for transmitting a 1024×1024 RGB image over three parallel RF channels by converting the image to YCbCr, applying 2×2 block-average downsampling, adding a security layer, packetizing the data, and transmitting Y, Cb, and Cr simultaneously.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Main Research Question](#2-main-research-question)
3. [Core Architecture](#3-core-architecture)
4. [Design Decisions](#4-design-decisions)
5. [Image Processing](#5-image-processing)
6. [Data Size](#6-data-size)
7. [Security Layer](#7-security-layer)
8. [Packetization](#8-packetization)
9. [Parallel RF Architecture](#9-parallel-rf-architecture)
10. [RF Hardware Direction](#10-rf-hardware-direction)
11. [RF Frequency](#11-rf-frequency)
12. [Why Data Rate Is Not Fixed Yet](#12-why-data-rate-is-not-fixed-yet)
13. [Example Theoretical Timing](#13-example-theoretical-timing)
14. [Compression](#14-compression)
15. [Simulation](#15-simulation)
16. [Channel Simulation](#16-channel-simulation)
17. [Simulation vs Hardware](#17-simulation-vs-hardware)
18. [Communication Metrics](#18-metrics)
19. [Image Quality Metrics](#19-image-quality-metrics)
20. [Main Experiments](#20-main-experiments)
21. [Important Constraints](#21-important-constraints)
22. [Future Work](#22-future-work)
23. [Final Project Goal](#23-final-project-goal)
24. [License](#license)

---

## 1. Project Overview

This project investigates whether an image can be transmitted **faster through parallel RF communication** by separating its YCbCr components and transmitting them simultaneously over independent RF channels.

The system takes a **1024×1024 RGB image**, converts it to **YCbCr**, and performs **2×2 block-average downsampling** independently on Y, Cb, and Cr.

Each component is reduced from:

```
1024 × 1024
     ↓
 2×2 averaging
     ↓
512 × 512
```

The three resulting components are then processed through a **security layer**, packetized, and transmitted simultaneously:

```
                    1024×1024 RGB
                          │
                          ▼
                       YCbCr
                          │
                          ▼
                  2×2 Downsampling
                          │
               ┌──────────┼──────────┐
               ▼          ▼          ▼
               Y         Cb         Cr
           512×512    512×512    512×512
               │          │          │
               └──────────┼──────────┘
                          ▼
                   Security Layer
                          │
                          ▼
                    Packetization
                          │
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
     RF Channel 1   RF Channel 2   RF Channel 3
          Y              Cb              Cr
         TX/RX          TX/RX          TX/RX
           └──────────────┼──────────────┘
                          ▼
                  Packet Reassembly
                          │
                          ▼
                   Security Layer
                     / Decryption
                          │
                          ▼
                    Y / Cb / Cr
                          │
                          ▼
                      Upsample
                          │
                          ▼
                     YCbCr → RGB
                          │
                          ▼
                Reconstructed Image
```

The project will be implemented in **both simulation and physical hardware** so that the performance of the simulated communication system can be compared with the real RF implementation.

---

## 2. Main Research Question

> **Can parallel transmission of Y, Cb, and Cr over independent RF channels reduce image transmission time while maintaining acceptable image quality, communication reliability, and security?**

The project therefore compares:

**Sequential transmission**

```
Y → Cb → Cr
```

with:

**Parallel transmission**

```
Y  ─────────→ RF Channel 1
Cb ─────────→ RF Channel 2
Cr ─────────→ RF Channel 3

         simultaneously
```

The expected speed improvement will **not be assumed to be exactly 3×**. It will be measured experimentally because RF overhead, packet losses, retransmissions, synchronization, protocol overhead, and hardware limitations affect the actual result.

---

## 3. Core Architecture

The system is divided into five major layers:

```
┌─────────────────────────────────────┐
│         1. IMAGE PROCESSING          │
│   RGB → YCbCr → 2×2 Downsampling     │
└───────────────────┬───────────────────┘
                    │
┌───────────────────▼───────────────────┐
│           2. SECURITY LAYER          │
│         Encryption / Protection      │
└───────────────────┬───────────────────┘
                    │
┌───────────────────▼───────────────────┐
│           3. DATA PROTOCOL           │
│  Packetization / IDs / CRC / etc.    │
└───────────────────┬───────────────────┘
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
   ┌───────────┐ ┌───────────┐ ┌───────────┐
   │  RF CH. 1  │ │  RF CH. 2  │ │  RF CH. 3  │
   │      Y     │ │     Cb     │ │     Cr     │
   └───────────┘ └───────────┘ └───────────┘
          │         │         │
          └─────────┼─────────┘
                    ▼
┌─────────────────────────────────────┐
│      4. RECEIVER / REASSEMBLY        │
│   Packets → Security → Y/Cb/Cr       │
└───────────────────┬───────────────────┘
                    │
┌───────────────────▼───────────────────┐
│      5. IMAGE RECONSTRUCTION         │
│    Upsampling → YCbCr → RGB          │
└─────────────────────────────────────┘
```

---

## 4. Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Input image | 1024×1024 RGB | Fixed experimental input |
| Color space | YCbCr | Separates image information into three components |
| Downsampling | 2×2 block average | Simple, deterministic, easy to implement in hardware/software |
| Downsampled size | 512×512 per component | Each dimension is reduced by 2 |
| RF architecture | 3 parallel channels | Core research objective |
| Channel assignment | Y / Cb / Cr | One image component per RF path |
| Security | Security layer before RF transmission | Protect transmitted image data |
| Initial security prototype | XOR + key | Simple proof-of-concept implementation |
| Strong cryptography | Future work | Can replace prototype security without changing RF architecture |
| Packetization | Required | Enables framing, identification, reassembly, and error handling |
| Compression | Not part of baseline | Keeps the parallel-RF experiment independent from compression |
| Simulation | Developed alongside hardware | Allows controlled experiments and comparison |
| Main comparison | Sequential vs parallel | Measures actual benefit of parallel communication |

---

## 5. Image Processing

### 5.1 RGB → YCbCr

The input image is converted from RGB into three components:

```
RGB
 │
 ├── Y
 ├── Cb
 └── Cr
```

YCbCr is useful for this architecture because the image can naturally be separated into three independent data streams.

### 5.2 2×2 Block-Average Downsampling

For every 2×2 block:

```
P1  P2
P3  P4
```

the output pixel is:

```
Output = (P1 + P2 + P3 + P4) / 4
```

This operation is applied independently to **Y, Cb, and Cr**.

Therefore:

```
1024 × 1024
     ↓
2×2 average
     ↓
512 × 512
```

for each component.

> **Note:** This is **not standard 4:2:0 chroma subsampling**, because Y is also downsampled.

---

## 6. Data Size

Each downsampled component contains:

```
512 × 512 = 262,144 samples
```

Assuming 8-bit samples:

| Component | Size |
|---|---|
| Y | 262,144 bytes |
| Cb | 262,144 bytes |
| Cr | 262,144 bytes |
| **Total** | **786,432 bytes** |

Approximately:

```
768 KiB ≈ 0.786 MB
```

The original raw RGB image contains:

```
1024 × 1024 × 3 = 3,145,728 bytes ≈ 3.15 MB
```

Therefore, the proposed image-processing stage reduces the raw pixel-data volume by approximately **75%**.

---

## 7. Security Layer

Security is a **core architectural layer** of the system, applied before the data is transmitted over RF.

Conceptually:

```
Image Data → YCbCr → Downsampling → Security Layer → Packetization → RF Transmission
```

At the receiver:

```
RF Reception → Packet Reassembly → Security Layer / Decryption → YCbCr Reconstruction
```

### Initial Prototype

The first implementation will use a lightweight **XOR-based encryption mechanism with a shared key**.

Conceptually:

```
Ciphertext = Data XOR Key
Data       = Ciphertext XOR Key
```

This is intended as a **prototype security mechanism**, not as a claim of modern cryptographic security.

For a production-quality security implementation, the project can later use authenticated encryption such as:

- AES-GCM
- ChaCha20-Poly1305

The security layer will remain modular so that the underlying encryption method can be changed without redesigning the RF architecture.

---

## 8. Packetization

The image components cannot simply be treated as one continuous RF stream — the data will be divided into packets.

A conceptual packet format:

```
┌──────────┬────────────┬────────────┬────────┬─────────┐
│ Frame ID │ Channel ID │ Packet No. │ Length │ Payload │
└──────────┴────────────┴────────────┴────────┴─────────┘
```

Possible channel identifiers:

| ID | Component |
|---|---|
| 0 | Y |
| 1 | Cb |
| 2 | Cr |

Packetization allows the receiver to determine:

- which image/frame the packet belongs to
- which component it belongs to
- packet ordering
- payload size
- missing packets
- duplicate packets
- corrupted packets

Future protocol features may include:

- CRC
- Acknowledgements
- Retransmission
- Sequence numbers
- Timeout handling
- Synchronization
- Forward error correction

---

## 9. Parallel RF Architecture

The key idea of this project is **true parallel transmission**.

The baseline architecture is:

```
              ┌─────────────── RF Channel 1 ───────────────┐
Y  ──────────►│                                             │
              └─────────────────────────────────────────────┘

              ┌─────────────── RF Channel 2 ───────────────┐
Cb ──────────►│                                             │
              └─────────────────────────────────────────────┘

              ┌─────────────── RF Channel 3 ───────────────┐
Cr ──────────►│                                             │
              └─────────────────────────────────────────────┘
```

All three channels operate at the same time. This requires either:

- three independent RF transceiver paths, **or**
- an equivalent multi-channel/wideband architecture capable of supporting the three simultaneous streams.

> Using one radio and switching between Y, Cb, and Cr would be **time-multiplexing**, not true parallel transmission.

---

## 10. RF Hardware Direction

The initial hardware investigation is focused on **sub-GHz RF transceiver modules**, with **SX1262-based hardware** being one candidate.

The SX1262 family is attractive for investigation because it supports sub-GHz operation and provides both LoRa and FSK modes.

The final radio configuration has not yet been fixed because the project needs to experimentally determine the appropriate trade-off between:

- Data rate
- Range
- Packet reliability
- Bandwidth
- Modulation
- Power consumption
- Antenna performance
- Interference
- Latency

The hardware architecture will therefore be parameterized rather than assuming a particular RF configuration from the beginning.

---

## 11. RF Frequency

The project is being developed with the **865–868 MHz region in India** as a potential operating region.

India's Department of Telecommunications (DoT) has rules covering low-power short-range devices in the 865–868 MHz band. The 2021 rules specify operation on a non-interference, non-protection, shared, and non-exclusive basis, subject to the applicable technical requirements.

The exact RF configuration is **not fixed yet**. Frequency selection must consider the applicable requirements for:

- Operating frequency
- Occupied bandwidth
- Transmit power
- Duty cycle
- Modulation
- Channel configuration
- Antenna/system characteristics

The project will not assume that arbitrary frequencies inside 865–868 MHz can simply be used as independent 1 MHz channels.

For hardware deployment, applicable WPC/DoT requirements must be checked for the specific equipment and configuration. DoT also provides an Equipment Type Approval (ETA) process for applicable wireless equipment operating in licence-exempt bands.

---

## 12. Why Data Rate Is Not Fixed Yet

The amount of data is known:

```
Total data ≈ 6.29 million bits
```

But the final transmission time depends strongly on the effective application throughput.

For a single component:

```
512 × 512 × 8 = 2,097,152 bits
```

For three components:

```
2,097,152 × 3 = 6,291,456 bits
```

The ideal transmission time for the complete image over one sequential channel is:

```
T = Total Bits / Data Rate
```

For true parallel transmission:

```
T_parallel ≈ max(T_Y, T_Cb, T_Cr)
```

plus protocol, synchronization, retransmission, and other overhead. The actual improvement will therefore be measured experimentally.

---

## 13. Example Theoretical Timing

*For illustration only*, assuming an effective 100 kbps rate:

### Sequential

```
6,291,456 / 100,000 ≈ 62.9 seconds
```

### Parallel

Each channel carries:

```
2,097,152 bits
```

Therefore:

```
2,097,152 / 100,000 ≈ 21.0 seconds
```

**Ideal improvement ≈ 3×**

However, this is only a theoretical upper-bound-style calculation. Real performance will be affected by:

```
Packet overhead
+ RF protocol
+ Synchronization
+ Packet loss
+ Retransmission
+ FEC
+ Processing time
+ RF channel conditions
```

---

## 14. Compression

Compression is intentionally **not included in the baseline architecture** — the purpose is to isolate the effect of parallel RF transmission.

The baseline experiment therefore measures:

```
Image processing + Security + Packetization + RF transmission
```

without introducing an additional compression variable.

Compression can later be evaluated as a separate experiment using techniques such as:

- JPEG
- JPEG2000
- WebP
- Predictive coding
- Entropy coding
- Custom image compression

If compression is introduced, the intended order is:

```
Image → Compression → Encryption → Packetization → RF
```

rather than compressing encrypted data.

---

## 15. Simulation

Simulation will be developed **alongside the physical implementation**. It is not intended to replace the hardware — instead, it provides a controlled environment for studying the system before and during hardware testing.

```
                SIMULATION
                    │
   Image ──► Processing
                    │
                Security
                    │
               Packetization
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
      Channel 1  Channel 2  Channel 3
         │          │          │
         └──────────┼──────────┘
                    │
                RF Model
                    │
               Reassembly
                    │
                Security
                    │
             Reconstruction
                    │
                 Metrics
```

---

## 16. Channel Simulation

The simulated RF channels can introduce controlled communication impairments such as:

- Noise
- Bit errors
- Packet loss
- Delay
- Channel imbalance
- Retransmissions
- Different SNR conditions

The simulation distinguishes between:

**Bit-level errors**

```
Transmitted bit → Channel → Received bit
```

**Packet-level loss**

```
Packet → Channel → Packet received / lost
```

This makes it possible to evaluate both communication-layer and application-layer behavior.

---

## 17. Simulation vs Hardware

One of the main goals is to use the **same logical architecture** in both environments.

| Parameter | Simulation | Hardware |
|---|---|---|
| Input image | Same | Same |
| Image processing | Same | Same |
| Security layer | Same logic | Same logic |
| Packet structure | Same | Same |
| Channel assignment | Same | Same |
| Number of channels | 3 | 3 |
| Receiver reconstruction | Same | Same |
| Metrics | Same | Same |

This makes it possible to answer questions such as:

> How closely does the simulated system represent the physical RF system?

---

## 18. Metrics

The project will evaluate both **communication performance** and **image quality**.

### Communication Metrics

**Transmission Time** — total time required to successfully transmit and reconstruct one image.

```
T = End Time - Start Time
```

**Throughput**

```
Throughput = Successfully Received Payload Bits / Total Transmission Time
```

Application throughput will be distinguished from the radio's nominal/raw bit rate.

**BER (Bit Error Rate)**

```
BER = Number of Incorrect Bits / Total Received Bits
```

**PER (Packet Error Rate)**

```
PER = Number of Failed Packets / Total Transmitted Packets
```

**Additional metrics:**

- Packet Loss — percentage of packets that do not arrive successfully
- Retransmissions — number of packets that must be sent again
- SNR — signal-to-noise ratio during transmission
- RSSI — received signal strength indicator, where supported by the radio
- Range — maximum tested distance under defined experimental conditions

---

## 19. Image Quality Metrics

The reconstructed image will be compared with the original/reference image.

**MSE (Mean Squared Error)**

```
MSE = mean((Original - Reconstructed)²)
```

**PSNR (Peak Signal-to-Noise Ratio)**

```
PSNR = 10 · log10(MAX² / MSE)
```

**SSIM (Structural Similarity Index)** — used to evaluate perceptual/structural similarity.

Visual comparisons will additionally be stored for qualitative evaluation.

---

## 20. Main Experiments

### Experiment 1 — Image Processing

```
RGB → YCbCr → 2×2 Downsampling → Upsampling → YCbCr → RGB
```

Measure: PSNR, SSIM, MSE, visual quality.

This establishes the image-quality cost of the downsampling operation before RF communication is introduced.

### Experiment 2 — Single RF Link

Test one RF channel with one image component.

Measure: range, throughput, packet loss, BER/PER, retransmissions, transmission time.

### Experiment 3 — Three Parallel RF Links

Transmit Y → RF1, Cb → RF2, Cr → RF3 simultaneously. Measure the same parameters as Experiment 2.

### Experiment 4 — Sequential vs Parallel

Run both systems under comparable conditions (`Y → Cb → Cr` vs. simultaneous `Y/Cb/Cr → RF1/RF2/RF3`).

Compare: total transmission time, effective throughput, packet loss, retransmissions, image quality, reliability.

### Experiment 5 — Simulation vs Hardware

Use the same logical configuration in simulation and physical hardware.

Compare: transmission time, throughput, packet loss, BER/PER, image quality, RF conditions.

### Experiment 6 — Compression *(optional, future)*

```
Without Compression  vs.  With Compression
```

while keeping the parallel RF architecture unchanged.

---

## 21. Important Constraints

1. **Parallelism requires independent RF paths** — three streams cannot be considered truly parallel if a single radio simply switches between them.

2. **Three channels do not automatically provide 3× speed** — the theoretical maximum improvement assumes balanced channels and negligible overhead. Real performance depends on RF data rate, packet overhead, synchronization, packet loss, retransmissions, FEC, processing, and channel conditions.

3. **Downsampling affects image quality** — the reduction from 1024×1024 to 512×512 introduces information loss. PSNR, SSIM, and visual comparison will quantify this effect.

4. **XOR is not the final security solution** — the XOR implementation is intended for the prototype architecture only and should not be treated as equivalent to modern authenticated encryption.

5. **RF operation must follow applicable regulations** — the exact frequency, bandwidth, power, duty cycle, and equipment requirements must be verified against the applicable Indian WPC/DoT rules before physical deployment. The 865–868 MHz SRD framework is subject to technical conditions rather than being a blanket authorization for arbitrary configurations.

---

## 22. Future Work

- AES-GCM / ChaCha20-Poly1305
- Forward Error Correction
- Adaptive data rate
- Adaptive modulation
- Better packet recovery
- Image compression
- Unequal protection for Y/Cb/Cr
- Dynamic channel selection
- SDR implementation
- Larger images
- Video transmission
- Multi-image/frame transmission
- Power-consumption analysis
- Optimization of RF channel allocation
- Simulation-to-hardware parameter calibration

---

## 23. Final Project Goal

The final system aims to demonstrate a complete secure image communication pipeline:

```
                  ┌────────────────────┐
                  │    1024×1024 RGB    │
                  └──────────┬──────────┘
                             ↓
                       YCbCr Convert
                             ↓
                    2×2 Downsampling
                             ↓
                ┌────────────┼────────────┐
                ↓            ↓            ↓
                Y           Cb           Cr
                └────────────┼────────────┘
                             ↓
                      Security Layer
                             ↓
                       Packetization
                             ↓
                ┌────────────┼────────────┐
                ↓            ↓            ↓
               RF1          RF2          RF3
                ↓            ↓            ↓
                └────────────┼────────────┘
                             ↓
                    Packet Reassembly
                             ↓
                       Decryption
                             ↓
                       Y / Cb / Cr
                             ↓
                        Upsampling
                             ↓
                       YCbCr → RGB
                             ↓
                   Reconstructed Image
```

The project will ultimately answer, through **simulation and physical measurement**, whether separating an image into YCbCr components and transmitting those components over **parallel RF channels** can provide a meaningful reduction in transmission time while maintaining acceptable **image quality, communication reliability, and security**.

---

## License

This project is intended as a research/engineering prototype. Add the project's chosen open-source license here once the licensing decision is finalized.
