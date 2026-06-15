# Lync 6 / Lync 12 Serial Protocol Specification

Source: Lync Serial Commands Version 1.1 (`Lync_V2_Serial_Protocol.pdf`)

---

## 1. Serial Port Settings

| Parameter    | Value   |
|-------------|---------|
| Baud rate   | 38400   |
| Data bits   | 8       |
| Stop bits   | 1       |
| Parity      | None    |
| Flow control| None    |

**Connector:** RS-232 DB-9. PC pin 2 (RxD) ← Lync pin 2 (TxD); PC pin 3 (TxD) → Lync pin 3 (RxD); Pin 5 = GND.

---

## 2. Zone Addressing

| Zone Address | Meaning              |
|-------------|----------------------|
| 0           | Broadcast (all zones)|
| 1–6         | Zones 1–6 (Lync6 and Lync12) |
| 7–12        | Zones 7–12 (Lync12 only) |

---

## 3. Checksum Calculation

Checksum is the **8-bit sum** (mod 256) of all preceding bytes in the frame.

```
checksum = (HEAD + RESERVED + ZONE + COMMAND + DATA_BYTES...) & 0xFF
```

Example — Zone 1 Power On: `0x02 + 0x00 + 0x01 + 0x04 + 0x57` → checksum = `0x5E`

---

## 4. Commands: PC → Lync

### Frame Format

```
[HEAD] [RESERVED] [ZONE] [CMD] [DATA...] [CHECKSUM]
  0x02    0x00     1byte  1byte  1–13 bytes  1byte
```

Most commands have 1 data byte (6 bytes total). Multi-byte commands (name setting) have up to 13 data bytes.

---

### 4.1 MP3 Repeat Loop — CMD `0x01`

| Action          | Data  |
|----------------|-------|
| Repeat Loop ON  | 0xFF  |
| Repeat Loop OFF | 0x00  |

Zone address: `0` (broadcast).

---

### 4.2 Common Command — CMD `0x04`

Zone address: `0` for broadcast, `1–12` for specific zone.

#### Power

| Action       | Data  | Notes |
|-------------|-------|-------|
| All Power ON | 0x55  | Zone addr = 0 or 1–12 |
| All Power OFF| 0x56  | Zone addr = 0 or 1–12 |
| Zone Power ON| 0x57  | Use specific zone addr |
| Zone Power OFF| 0x58 | Use specific zone addr |

> If zone address is 0 (broadcast), `0x57`/`0x58` behaves like All ON/OFF.
> **No response** is sent if the zone is already at the requested power state.

#### Mute

| Action     | Data  |
|-----------|-------|
| Mute ON    | 0x1E  |
| Mute OFF   | 0x1F  |

#### Do Not Disturb (DND)

| Action   | Data  |
|---------|-------|
| DND ON   | 0x59  |
| DND OFF  | 0x5A  |

#### MP3 Transport

| Action    | Data  |
|----------|-------|
| Fast Fwd  | 0x0A  |
| Play/Pause| 0x0B  |
| Fast Back | 0x0C  |
| Stop      | 0x0D  |

#### Input Source Select

Selecting an input also **powers the zone ON** if it was off.
**No response** if the zone is already on that source.

| Data  | Input # | Compatible  |
|-------|---------|-------------|
| 0x10  | 1       | Lync6 & 12  |
| 0x11  | 2       | Lync6 & 12  |
| 0x12  | 3       | Lync6 & 12  |
| 0x13  | 4       | Lync6 & 12  |
| 0x14  | 5       | Lync6 & 12  |
| 0x15  | 6       | Lync6 & 12  |
| 0x16  | 7       | Lync6 & 12  |
| 0x17  | 8       | Lync6 & 12  |
| 0x18  | 9       | Lync6 & 12  |
| 0x19  | 10      | Lync6 & 12  |
| 0x1A  | 11      | Lync6 & 12  |
| 0x1B  | 12      | Lync6 & 12  |
| 0x63  | 13      | Lync12 only |
| 0x64  | 14      | Lync12 only |
| 0x65  | 15      | Lync12 only |
| 0x66  | 16      | Lync12 only |
| 0x67  | 17      | Lync12 only |
| 0x68  | 18      | Lync12 only |

#### Party Mode Input Source Select

| Data  | Party Mode Input # |
|-------|-------------------|
| 0x36  | 1                 |
| 0x37  | 2                 |
| 0x38  | 3                 |
| 0x39  | 4                 |
| 0x3A  | 5                 |
| 0x3B  | 6                 |
| 0x3C  | 7                 |
| 0x3D  | 8                 |
| 0x3E  | 9                 |
| 0x3F  | 10                |
| 0x40  | 11                |
| 0x41  | 12                |
| 0x69  | 13                |
| 0x6A  | 14                |
| 0x6B  | 15                |
| 0x6C  | 16                |
| 0x6D  | 17                |
| 0x6E  | 18                |

---

### 4.3 Query All Zone Status — CMD `0x05`

```
[0x02][0x00][0x00][0x05][0x00][checksum]
```

Zone addr = 0. Reply: one `0x05` Zone Internal Status response per zone.

---

### 4.4 Zone Name Setting — CMD `0x06`

```
[0x02][0x00][zone][0x06][0x00][c1][c2]...[c10][0x00][checksum]
```

- Zone: 1–12
- Data: 0x00, then up to 10 ASCII chars, padded with 0x00 to total 13 data bytes

---

### 4.5 Source Name Setting — CMD `0x07`

```
[0x02][0x00][zone][0x07][src_num][c1][c2]...[c10][0x00][checksum]
```

- Zone: 1–12 (each zone has its own source name table)
- Data1: source number 1–18
- Data2–12: up to 10 ASCII chars, null-padded to 13 data bytes total

---

### 4.6 Query ID — CMD `0x08`

```
[0x02][0x00][0x00][0x08][0x00][checksum]
```

Reply: ASCII string `"Lync6"` or `"Lync12"`.

---

### 4.7 Recall File — CMD `0x0A`

```
[0x02][0x00][0x00][0x0A][file_num][checksum]
```

`file_num`: 1–4.

---

### 4.8 Save File — CMD `0x0B`

```
[0x02][0x00][0x00][0x0B][file_num][checksum]
```

`file_num`: 1–4.

---

### 4.9 Query Zone Status (Full) — CMD `0x0C`

```
[0x02][0x00][zone][0x0C][0x00][checksum]
```

Zone: 1–12. Triggers replies: Zone Internal Status, Zone Name, all Source Names, MP3 on/off, MP3 file/artist names.

---

### 4.10 Query Zone Name — CMD `0x0D`

```
[0x02][0x00][zone][0x0D][0x00][checksum]
```

Reply: Zone Name response (cmd `0x0D`).

---

### 4.11 Query Zone Source Name — CMD `0x0E`

```
[0x02][0x00][zone][0x0E][0x00][checksum]
```

Reply: Zone Source Name response (cmd `0x0C`).

---

### 4.12 Volume — CMD `0x15`

Zone: 0–12.

| dB   | TX Data | | dB   | TX Data |
|------|---------|---|------|---------|
|  0   | 0x80    | | -31  | 0x61    |
| -1   | 0x7F    | | -32  | 0x60    |
| -2   | 0x7E    | | -33  | 0x5F    |
| -3   | 0x7D    | | -34  | 0x5E    |
| -4   | 0x7C    | | -35  | 0x5D    |
| -5   | 0x7B    | | -36  | 0x5C    |
| -6   | 0x7A    | | -37  | 0x5B    |
| -7   | 0x79    | | -38  | 0x5A    |
| -8   | 0x78    | | -39  | 0x59    |
| -9   | 0x77    | | -40  | 0x58    |
| -10  | 0x76    | | -41  | 0x57    |
| -11  | 0x75    | | -42  | 0x56    |
| -12  | 0x74    | | -43  | 0x55    |
| -13  | 0x73    | | -44  | 0x54    |
| -14  | 0x72    | | -45  | 0x53    |
| -15  | 0x71    | | -46  | 0x52    |
| -16  | 0x70    | | -47  | 0x51    |
| -17  | 0x6F    | | -48  | 0x50    |
| -18  | 0x6E    | | -49  | 0x4F    |
| -19  | 0x6D    | | -50  | 0x4E    |
| -20  | 0x6C    | | -51  | 0x4D    |
| -21  | 0x6B    | | -52  | 0x4C    |
| -22  | 0x6A    | | -53  | 0x4B    |
| -23  | 0x69    | | -54  | 0x4A    |
| -24  | 0x68    | | -55  | 0x49    |
| -25  | 0x67    | | -56  | 0x48    |
| -26  | 0x66    | | -57  | 0x47    |
| -27  | 0x65    | | -58  | 0x46    |
| -28  | 0x64    | | -59  | 0x45    |
| -29  | 0x63    | | -60  | 0x44    |
| -30  | 0x62    | | -61  | 0x43    |

**Formula:** `tx_byte = 0x80 - abs(db_value)` for dB 0 to -61; valid range `0x43`–`0x80`.

---

### 4.13 Balance — CMD `0x16`

Zone: 0–12.

| dB  | TX Data | | dB  | TX Data |
|-----|---------|---|-----|---------|
| +18 | 0x92    | |  0  | 0x80    |
| +17 | 0x91    | | -1  | 0x7F    |
| +16 | 0x90    | | -2  | 0x7E    |
| +15 | 0x8F    | | -3  | 0x7D    |
| +14 | 0x8E    | | -4  | 0x7C    |
| +13 | 0x8D    | | -5  | 0x7B    |
| +12 | 0x8C    | | -6  | 0x7A    |
| +11 | 0x8B    | | -7  | 0x79    |
| +10 | 0x8A    | | -8  | 0x78    |
| +9  | 0x89    | | -9  | 0x77    |
| +8  | 0x88    | | -10 | 0x76    |
| +7  | 0x87    | | -11 | 0x75    |
| +6  | 0x86    | | -12 | 0x74    |
| +5  | 0x85    | | -13 | 0x73    |
| +4  | 0x84    | | -14 | 0x72    |
| +3  | 0x83    | | -15 | 0x71    |
| +2  | 0x82    | | -16 | 0x70    |
| +1  | 0x81    | | -17 | 0x6F    |
|     |         | | -18 | 0x6E    |

**Formula:** `tx_byte = (0x80 + db_value) & 0xFF`; valid range `0x6E`–`0x92`.

> **Note:** The PDF examples for Balance accidentally show `CMD=0x04` — this is a copy-paste error. The correct command byte is `0x16` as stated in the command table.

---

### 4.14 Treble — CMD `0x17`

Zone: 0–12.

| dB  | TX Data | | dB  | TX Data |
|-----|---------|---|-----|---------|
| +10 | 0x8A    | |  0  | 0x80    |
| +9  | 0x89    | | -1  | 0x7F    |
| +8  | 0x88    | | -2  | 0x7E    |
| +7  | 0x87    | | -3  | 0x7D    |
| +6  | 0x86    | | -4  | 0x7C    |
| +5  | 0x85    | | -5  | 0x7B    |
| +4  | 0x84    | | -6  | 0x7A    |
| +3  | 0x83    | | -7  | 0x79    |
| +2  | 0x82    | | -8  | 0x78    |
| +1  | 0x81    | | -9  | 0x77    |
|     |         | | -10 | 0x76    |

**Formula:** `tx_byte = (0x80 + db_value) & 0xFF`; valid range `0x76`–`0x8A`.

---

### 4.15 Bass — CMD `0x18`

Zone: 0–12. Same encoding as Treble.

| dB  | TX Data |
|-----|---------|
| +10 | 0x8A    |
| 0   | 0x80    |
| -10 | 0x76    |

**Formula:** `tx_byte = (0x80 + db_value) & 0xFF`; valid range `0x76`–`0x8A`.

---

### 4.16 Set Echo Mode — CMD `0x19`

```
[0x02][0x00][0x00][0x19][data][checksum]
```

| Action      | Data  |
|------------|-------|
| Echo ON     | 0xFF  |
| Echo OFF    | 0x00  |

When Echo is OFF the device suppresses all responses to PC commands.

---

### 4.17 Set Zone/Source Names to Default — CMD `0x1C`

```
[0x02][0x00][0x00][0x1C][0x00][checksum]
```

Resets all zone names and source names to factory defaults (see tables below).

**Default Zone Names:** Zone 1 through Zone 12 (literal "Zone N").

**Default Source Names:** Source 1 through Source 18 (literal "Source N"). Lync6 only supports Sources 1–6.

---

### 4.18 Set Audio to Default — CMD `0x1E`

```
[0x02][0x00][zone][0x1E][0x00][checksum]
```

Zone: 0–12 (0 = all zones).

Resets audio settings to:

| Setting      | Default  |
|-------------|----------|
| Input Source | Input 1  |
| Volume       | −40 dB   |
| Treble       | 0 dB     |
| Bass         | 0 dB     |
| Balance      | 0 (center)|

---

## 5. Responses: Lync → PC

### Frame Format

```
[HEAD][RESERVED][ZONE][CMD][DATA_1]...[DATA_9][CHECKSUM]
  0x02   0x00    1byte 1byte                    1byte
```

Total length = 14 bytes for fixed-length responses (4 header + 9 data + 1 checksum).

Checksum = `(HEAD + RESERVED + ZONE + CMD + DATA_1 + ... + DATA_N) & 0xFF`

### Response Type Summary

| CMD  | Name                      | Total Bytes | Zone Addr |
|------|--------------------------|-------------|-----------|
| 0x05 | Zone Internal Status      | 14          | 1–12      |
| 0x06 | Audio & Keypad Exist      | 14          | 0         |
| 0x09 | MP3 Play End/Stop         | 6           | 0         |
| 0x0C | Zone Source Name          | 17          | zone      |
| 0x0D | Zone Name                 | 17          | zone      |
| 0x11 | MP3 File Name             | variable ≤70| 0         |
| 0x12 | MP3 Artist Name           | variable ≤70| 0         |
| 0x13 | MP3 ON                    | 6           | 0         |
| 0x14 | MP3 OFF                   | 22          | 0         |
| 0x1B | Echo Error Status         | 14          | 0         |

---

### 5.1 Zone Internal Status — Response CMD `0x05`

14 bytes. Only sent when a zone **actually changes state** (e.g. issuing "all power on" to a Lync6 where 1 zone was already on produces 5 responses, not 6).

```
[0x02][0x00][zone][0x05][D1][D2][D3][D4][D5][D6][D7][D8][D9][checksum]
```

#### Data1 — Zone Flags

| Bit | Function | Values       |
|-----|---------|--------------|
| 0   | Power   | 0=OFF, 1=ON  |
| 1   | Mute    | 0=OFF, 1=ON  |
| 2   | DND     | 0=OFF, 1=ON  |
| 3–7 | (reserved) |           |

#### Data2 — Global Flags

| Bit | Function   | Values       |
|-----|-----------|--------------|
| 7   | All ON    | 0=NO, 1=YES  |
| 6   | All OFF   | 0=NO, 1=YES  |
| 5   | Party Mode| 0=OFF, 1=ON  |
| 0–4 | (reserved)|              |

#### Data3 — MP3 Status

| Bits | Function         | Values       |
|------|-----------------|--------------|
| 0–3  | MP3 Repeat Loop | 0=OFF, 1=ON  |
| 4–7  | (reserved)      |              |

#### Data4 — Party Mode MP3

| Bits | Function         | Values       |
|------|-----------------|--------------|
| 0–3  | MP3 Repeat Loop | 0=OFF, 1=ON  |
| 4–7  | (reserved)      |              |

#### Data5 — Input Port

| Value | Input   |
|-------|---------|
| 0x01  | Input 1 |
| 0x02  | Input 2 |
| ...   | ...     |
| 0x0C  | Input 12|

> **Note:** Response uses input numbers 1–12 (inputs 13–18 not represented in this response byte).

#### Data6 — Volume (response encoding, different from TX)

| dB   | RX Data | | dB   | RX Data |
|------|---------|---|------|---------|
|  0   | 0x00    | | -31  | 0xE1    |
| -1   | 0xFF    | | -32  | 0xE0    |
| -2   | 0xFE    | | -33  | 0xDF    |
| -3   | 0xFD    | | -34  | 0xDE    |
| -4   | 0xFC    | | -35  | 0xDD    |
| -5   | 0xFB    | | -36  | 0xDC    |
| -6   | 0xFA    | | -37  | 0xDB    |
| -7   | 0xF9    | | -38  | 0xDA    |
| -8   | 0xF8    | | -39  | 0xD9    |
| -9   | 0xF7    | | -40  | 0xD8    |
| -10  | 0xF6    | | -41  | 0xD7    |
| -11  | 0xF5    | | -42  | 0xD6    |
| -12  | 0xF4    | | -43  | 0xD5    |
| -13  | 0xF3    | | -44  | 0xD4    |
| -14  | 0xF2    | | -45  | 0xD3    |
| -15  | 0xF1    | | -46  | 0xD2    |
| -16  | 0xF0    | | -47  | 0xD1    |
| -17  | 0xEF    | | -48  | 0xD0    |
| -18  | 0xEE    | | -49  | 0xCF    |
| -19  | 0xED    | | -50  | 0xCE    |
| -20  | 0xEC    | | -51  | 0xCD    |
| -21  | 0xEB    | | -52  | 0xCC    |
| -22  | 0xEA    | | -53  | 0xCB    |
| -23  | 0xE9    | | -54  | 0xCA    |
| -24  | 0xE8    | | -55  | 0xC9    |
| -25  | 0xE7    | | -56  | 0xC8    |
| -26  | 0xE6    | | -57  | 0xC7    |
| -27  | 0xE5    | | -58  | 0xC6    |
| -28  | 0xE4    | | -59  | 0xC5    |
| -29  | 0xE3    | | -60  | 0xC4    |
| -30  | 0xE2    | | -61  | 0xC3    |

**Formula:** `db_value = -(rx_byte if rx_byte <= 0x7F else 0x100 - rx_byte)` — equivalently, interpret as signed two's complement where 0x00=0, 0xFF=-1, 0xC3=-61.

> **Important:** TX (command) volume encoding and RX (response) volume encoding are **different**. TX uses 0x80=0dB; RX uses 0x00=0dB.

#### Data7 — Treble (response encoding)

| dB  | RX Data |
|-----|---------|
| +10 | 0x0A    |
| +9  | 0x09    |
| ... | ...     |
|  0  | 0x00    |
| -1  | 0xFF    |
| ... | ...     |
| -10 | 0xF6    |

**Formula:** Signed byte — `db_value = rx_byte if rx_byte <= 0x7F else rx_byte - 0x100`.

#### Data8 — Bass (response encoding)

Same encoding as Treble (Data7). 0x0A=+10, 0x00=0, 0xF6=-10.

#### Data9 — Balance (response encoding)

| dB  | RX Data |
|-----|---------|
| +18 | 0x12    |
| +17 | 0x11    |
| ... | ...     |
|  0  | 0x00    |
| -1  | 0xFF    |
| ... | ...     |
| -18 | 0xEE    |

**Formula:** Same signed-byte pattern as Treble/Bass.

---

### 5.2 Audio & Keypad Exist — Response CMD `0x06`

14 bytes. Zone address = 0.

```
[0x02][0x00][0x00][0x06][D1][D2][D3][D4][D5][0x00][0x00][0x00][0x00][checksum]
```

- **D1:** 0x00
- **D2:** Audio exist, zones 1–8 (bit 0 = zone 1, bit 7 = zone 8)
- **D3:** Keypad exist, zones 1–8 (same bit layout)
- **D4:** Audio exist, zones 9–12 (bit 0 = zone 9, bits 4–7 unused)
- **D5:** Keypad exist, zones 9–12 (same bit layout)
- **D6–D9:** 0x00

---

### 5.3 MP3 Play End/Stop — Response CMD `0x09`

6 bytes:
```
[0x02][0x00][0x00][0x09][0x00][checksum]
```

---

### 5.4 Zone Source Name — Response CMD `0x0C`

17 bytes:
```
[0x02][0x00][zone][0x0C][name_1]...[name_11][input_ch][checksum]
```

- Bytes 4–14: 11-byte null-padded ASCII source name string
- Byte 15: input channel number (1-based)

---

### 5.5 Zone Name — Response CMD `0x0D`

17 bytes:
```
[0x02][0x00][zone][0x0D][name_1]...[name_11][zone_addr][checksum]
```

- Bytes 4–14: 11-byte null-padded ASCII zone name string
- Byte 15: zone address (1-based)

---

### 5.6 MP3 File Name — Response CMD `0x11`

Variable length (up to 70 bytes):
```
[0x02][0x00][0x00][0x11][filename_chars...][0x00][checksum]
```

- Data: null-terminated ASCII string, max 64 chars

---

### 5.7 MP3 Artist Name — Response CMD `0x12`

Same structure as MP3 File Name, CMD = `0x12`.

---

### 5.8 MP3 ON — Response CMD `0x13`

6 bytes:
```
[0x02][0x00][0x00][0x13][0x00][checksum]
```

---

### 5.9 MP3 OFF — Response CMD `0x14`

22 bytes:
```
[0x02][0x00][0x00][0x14]["Device Not Found"][checksum]
```

Data is the ASCII string `"Device Not Found"` (17 bytes, no null terminator).

---

### 5.10 Echo Error Status — Response CMD `0x1B`

14 bytes:
```
[0x02][0x00][0x00][0x1B][error_no][0x00][0x00][0x00][0x00][0x00][0x00][0x00][0x00][checksum]
```

| Error No. | Meaning                    |
|-----------|---------------------------|
| 1         | Volume setting range error |
| 2         | Balance setting range error|
| 3         | Treble setting range error |
| 4         | Bass setting range error   |

---

## 6. Encoding Formulas Summary

### TX (PC → Lync)

| Parameter | Formula                             | Range (bytes) |
|-----------|-------------------------------------|---------------|
| Volume    | `0x80 + db` (db is 0 to -61)        | 0x43–0x80     |
| Balance   | `(0x80 + db) & 0xFF`                | 0x6E–0x92     |
| Treble    | `(0x80 + db) & 0xFF`                | 0x76–0x8A     |
| Bass      | `(0x80 + db) & 0xFF`                | 0x76–0x8A     |

### RX (Lync → PC, inside Zone Internal Status response)

| Parameter | Formula                             | Range (bytes) |
|-----------|-------------------------------------|---------------|
| Volume    | signed 8-bit: `0x00`=0dB, `0xFF`=-1dB | 0xC3–0x00  |
| Balance   | signed 8-bit: `0x00`=0, `0x12`=+18, `0xEE`=-18 | 0xEE–0x12 |
| Treble    | signed 8-bit: `0x00`=0, `0x0A`=+10, `0xF6`=-10 | 0xF6–0x0A |
| Bass      | signed 8-bit: same as Treble        | 0xF6–0x0A     |

---

## 7. Known PDF Errata

1. **Balance examples** show `CMD=0x04` — should be `0x16` per the command table header.
2. **Volume data range** in CMD 0x15 header says "0x00–0x43" — actual range is 0x43–0x80 per examples and table.
3. **Query Source Name** (§4.11) example shows `0x0C` as command — should be `0x0E`.
4. **Command table** header lists "Set Audio To Default: 0x1C" and "Set Name To Default: 0x1E" — the section bodies have them swapped; use the section body definitions (0x1C = names reset, 0x1E = audio reset).
5. **Volume table in response** (Data6) is missing -30 dB (0xE2) — it jumps from -29 to -31 in the PDF. The value 0xE2 = -30 dB by formula and is assumed correct.

---

## 8. Behavioral Rules for Emulator

1. Respond with `0x05` Zone Internal Status **only if a zone changed state**.
2. Input Select implicitly **powers the zone ON** — update power state and emit `0x05`.
3. Power command with **broadcast zone (0)** affects all zones; response is one `0x05` per zone that changed.
4. When **Echo Mode is OFF** (`CMD 0x19`, data `0x00`), suppress all responses.
5. Out-of-range audio values should trigger an **Echo Error Status** (`0x1B`) response.
6. `CMD 0x0C` (Query Zone Status Full) triggers: `0x05` + `0x0D` (zone name) + `0x0C` (all source names) + `0x13`/`0x14` (MP3 state) + `0x11`/`0x12` (MP3 file/artist if playing).
7. `CMD 0x05` (Query All Zone Status) emits one `0x05` per active zone.
