#!/usr/bin/env python3
"""
Lync12 serial protocol emulator.

Exposes a PTY (pseudo-terminal) that app.py can connect to without physical
hardware. Set SERIAL_PORT to the slave path printed at startup.

Usage:
    python3 emulator.py            # Lync12 (12 zones)
    python3 emulator.py --zones 6  # Lync6 (6 zones)
    python3 emulator.py --log-level DEBUG

Implementation notes:
  - Volume, treble, bass, balance are stored in RX/response encoding (signed-byte,
    0x00-centered) because app.py sends commands using that same encoding, not the
    TX encoding described in PROTOCOL_SPEC.md §4.
  - Input (D5 in zone status) is sent 0-based; app.py adds 1 to get 1-based input.
  - Zone/source name responses use CMD 0x0E, not 0x0C as the spec states (the spec
    has a copy-paste error; the real device and app.py both use 0x0E).
  - Zone/source name frames are 18 bytes (4 header + 13 data + 1 checksum); the
    extra 13th data byte is padding to match what app.py expects (i += 18).
  - 0x05 status frames are only emitted when zone state actually changes.
"""
import argparse
import logging
import os
import pty
import select
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_HEAD = 0x02
_RESERVED = 0x00
NUM_SOURCES = 18

# Default audio state (RX/response encoding; 0xD8 = signed -40 = -40 dB)
_DEFAULT_VOLUME = 0xD8
_DEFAULT_TREBLE = 0x00
_DEFAULT_BASS = 0x00
_DEFAULT_BALANCE = 0x00
_DEFAULT_INPUT = 1


@dataclass
class ZoneState:
    zone: int
    power: bool = False
    mute: bool = False
    dnd: bool = False
    input: int = _DEFAULT_INPUT       # 1-based
    volume: int = _DEFAULT_VOLUME     # RX encoding; 0x00=0dB, 0xC3=-61dB
    treble: int = _DEFAULT_TREBLE     # signed byte; 0x00=0dB, 0x0A=+10, 0xF6=-10
    bass: int = _DEFAULT_BASS
    balance: int = _DEFAULT_BALANCE   # signed byte; 0x00=center, 0x12=+18, 0xEE=-18
    party: bool = False
    allon: bool = False
    alloff: bool = False
    mp3_repeat: bool = False
    party_repeat: bool = False
    name: str = ""
    source_names: Dict[int, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name:
            self.name = f"Zone {self.zone}"
        if not self.source_names:
            self.source_names = {i: f"Source {i}" for i in range(1, NUM_SOURCES + 1)}


class Lync12Emulator:
    """
    Software emulator of a Lync 6 / Lync 12 whole-home audio controller.

    Creates a PTY pair. The slave path is passed to SERIAL_PORT so app.py
    connects as if talking to real hardware. The emulator owns the master FD
    and processes incoming frames on a background thread.
    """

    def __init__(self, num_zones: int = 12):
        if num_zones not in (6, 12):
            raise ValueError("num_zones must be 6 or 12")
        self.num_zones = num_zones
        self._zones: Dict[int, ZoneState] = {
            i: ZoneState(zone=i) for i in range(1, num_zones + 1)
        }
        self._echo_mode = True
        self._lock = threading.Lock()
        self._master_fd: Optional[int] = None
        self._slave_fd: Optional[int] = None   # kept open to prevent PTY HUP
        self._slave_path: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._buf = bytearray()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> str:
        """Open a PTY and start the reader thread. Returns the slave device path."""
        master_fd, slave_fd = pty.openpty()
        self._master_fd = master_fd
        self._slave_fd = slave_fd   # kept open; closing it causes PTY HUP before app connects
        self._slave_path = os.ttyname(slave_fd)
        self._running = True
        self._thread = threading.Thread(target=self._reader_loop, daemon=True, name="lync12-emu")
        self._thread.start()
        logger.info("Emulator started — slave path: %s", self._slave_path)
        return self._slave_path

    def stop(self):
        """Stop the emulator and close the PTY master."""
        self._running = False
        for fd_attr in ('_master_fd', '_slave_fd'):
            fd = getattr(self, fd_attr)
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
                setattr(self, fd_attr, None)

    @property
    def slave_path(self) -> Optional[str]:
        return self._slave_path

    # ------------------------------------------------------------------
    # State access (for test setup and assertions)
    # ------------------------------------------------------------------

    def get_zone(self, zone: int) -> Optional[ZoneState]:
        """Return a copy of zone state (thread-safe)."""
        import copy
        with self._lock:
            z = self._zones.get(zone)
            return copy.copy(z) if z else None

    def preset_zone(self, zone: int, **kwargs):
        """Directly set zone state fields for test setup."""
        with self._lock:
            z = self._zones.get(zone)
            if z is None:
                raise ValueError(f"Zone {zone} not found")
            for k, v in kwargs.items():
                setattr(z, k, v)

    def snapshot(self) -> Dict[int, dict]:
        """Return all zone state as plain dicts (thread-safe)."""
        with self._lock:
            return {
                z.zone: {
                    "power": z.power, "mute": z.mute, "dnd": z.dnd,
                    "input": z.input, "volume": z.volume,
                    "treble": z.treble, "bass": z.bass, "balance": z.balance,
                    "name": z.name,
                }
                for z in self._zones.values()
            }

    # ------------------------------------------------------------------
    # PTY I/O
    # ------------------------------------------------------------------

    def _reader_loop(self):
        while self._running:
            try:
                r, _, _ = select.select([self._master_fd], [], [], 0.05)
                if r:
                    data = os.read(self._master_fd, 256)
                    self._buf.extend(data)
                    self._process_buffer()
            except OSError:
                break

    def _send(self, data: bytes):
        if self._echo_mode and self._master_fd is not None:
            try:
                os.write(self._master_fd, data)
            except OSError as e:
                logger.warning("PTY write failed: %s", e)

    # ------------------------------------------------------------------
    # Frame parsing
    # ------------------------------------------------------------------

    def _process_buffer(self):
        while len(self._buf) >= 6:
            if self._buf[0] != _HEAD:
                self._buf = self._buf[1:]
                continue

            cmd = self._buf[3]

            # Name-setting commands carry 13 data bytes → 18-byte frame
            frame_len = 18 if cmd in (0x06, 0x07) else 6
            if len(self._buf) < frame_len:
                break

            frame = bytes(self._buf[:frame_len])
            self._buf = self._buf[frame_len:]

            zone = frame[2]
            if cmd in (0x06, 0x07):
                self._handle_name_cmd(zone, cmd, frame[4:17])
            else:
                self._dispatch(zone, cmd, frame[4])

    @staticmethod
    def _checksum(frame: bytearray) -> int:
        return sum(frame) & 0xFF

    def _make_frame(self, zone: int, cmd: int, data: bytes) -> bytes:
        f = bytearray([_HEAD, _RESERVED, zone, cmd]) + bytearray(data)
        f.append(self._checksum(f))
        return bytes(f)

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, zone: int, cmd: int, data: int):
        logger.debug("RX zone=%-2d cmd=0x%02X data=0x%02X", zone, cmd, data)
        {
            0x01: lambda: self._do_mp3_repeat(data),
            0x04: lambda: self._do_common(zone, data),
            0x05: lambda: self._do_query_all_status(),
            0x08: lambda: self._do_query_id(),
            0x0A: lambda: None,   # Recall file — no persistent state to emulate
            0x0B: lambda: None,   # Save file — no persistent state to emulate
            0x0C: lambda: self._do_query_zone_full(zone),
            0x0D: lambda: self._do_query_zone_name(zone),
            0x0E: lambda: self._do_query_source_name(zone),
            0x15: lambda: self._do_set_audio(zone, data, "volume", 1, -61, 0),
            0x16: lambda: self._do_set_audio(zone, data, "balance", 2, -18, 18),
            0x17: lambda: self._do_set_audio(zone, data, "treble", 3, -10, 10),
            0x18: lambda: self._do_set_audio(zone, data, "bass", 4, -10, 10),
            0x19: lambda: self._do_set_echo(data),
            0x1C: lambda: self._do_reset_names(),
            0x1E: lambda: self._do_reset_audio(zone),
        }.get(cmd, lambda: logger.warning("Unhandled CMD 0x%02X", cmd))()

    def _handle_name_cmd(self, zone: int, cmd: int, data: bytes):
        # data[0]=padding/source_num, data[1:12]=name (11 bytes), data[12]=0x00
        name = data[1:12].rstrip(b'\x00').decode('ascii', errors='replace')
        with self._lock:
            if cmd == 0x06 and zone in self._zones:
                self._zones[zone].name = name
                logger.debug("Zone %d name → %r", zone, name)
            elif cmd == 0x07:
                src = data[0]
                if zone in self._zones and 1 <= src <= NUM_SOURCES:
                    self._zones[zone].source_names[src] = name
                    logger.debug("Zone %d source %d name → %r", zone, src, name)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    def _do_mp3_repeat(self, data: int):
        on = (data == 0xFF)
        with self._lock:
            for z in self._zones.values():
                z.mp3_repeat = on

    def _do_common(self, zone: int, data: int):
        frames = []
        with self._lock:
            targets = self._targets(zone)

            if data == 0x55:    # All power ON
                for z in targets:
                    if not z.power:
                        z.power, z.allon, z.alloff = True, True, False
                        frames.append(self._build_status(z.zone))

            elif data == 0x56:  # All power OFF
                for z in targets:
                    if z.power:
                        z.power, z.allon, z.alloff = False, False, True
                        frames.append(self._build_status(z.zone))

            elif data == 0x57:  # Zone power ON
                for z in targets:
                    if not z.power:
                        z.power = True
                        frames.append(self._build_status(z.zone))

            elif data == 0x58:  # Zone power OFF
                for z in targets:
                    if z.power:
                        z.power = False
                        frames.append(self._build_status(z.zone))

            elif data == 0x1E:  # Mute ON
                for z in targets:
                    if not z.mute:
                        z.mute = True
                        frames.append(self._build_status(z.zone))

            elif data == 0x1F:  # Mute OFF
                for z in targets:
                    if z.mute:
                        z.mute = False
                        frames.append(self._build_status(z.zone))

            elif data == 0x59:  # DND ON
                for z in targets:
                    if not z.dnd:
                        z.dnd = True
                        frames.append(self._build_status(z.zone))

            elif data == 0x5A:  # DND OFF
                for z in targets:
                    if z.dnd:
                        z.dnd = False
                        frames.append(self._build_status(z.zone))

            elif data in (0x0A, 0x0B, 0x0C, 0x0D):
                logger.debug("MP3 transport 0x%02X — no state change", data)

            elif 0x10 <= data <= 0x1B or 0x63 <= data <= 0x68:
                inp = self._data_to_input(data)
                for z in targets:
                    was_on, was_inp = z.power, z.input
                    z.input, z.power = inp, True
                    if not was_on or was_inp != inp:
                        frames.append(self._build_status(z.zone))

            elif 0x36 <= data <= 0x41 or 0x69 <= data <= 0x6E:
                inp = self._party_data_to_input(data)
                for z in targets:
                    z.party, z.input = True, inp
                    frames.append(self._build_status(z.zone))

            else:
                logger.warning("Unknown common data 0x%02X zone %d", data, zone)

        for f in frames:
            self._send(f)

    def _do_query_all_status(self):
        with self._lock:
            frames = [self._build_status(zn) for zn in sorted(self._zones)]
        for f in frames:
            self._send(f)

    def _do_query_id(self):
        self._send(f"Lync{self.num_zones}".encode('ascii'))

    def _do_query_zone_full(self, zone: int):
        # Order: all 0x05 statuses first (builds zone_states list in parser),
        # then zone names, then source names (18 per zone), then MP3 state.
        with self._lock:
            zone_nums = sorted(z.zone for z in self._targets(zone))
            status_frames = [self._build_status(zn) for zn in zone_nums]
            name_frames = [self._build_zone_name(zn) for zn in zone_nums]
            src_frames = [
                self._build_source_name(zn, src)
                for zn in zone_nums
                for src in range(1, NUM_SOURCES + 1)
            ]

        for f in status_frames:
            self._send(f)
        for f in name_frames:
            self._send(f)
        for f in src_frames:
            self._send(f)
        self._send(self._build_mp3_off())

    def _do_query_zone_name(self, zone: int):
        with self._lock:
            frames = [self._build_zone_name(z.zone) for z in self._targets(zone)]
        for f in frames:
            self._send(f)

    def _do_query_source_name(self, zone: int):
        with self._lock:
            frames = [
                self._build_source_name(z.zone, src)
                for z in self._targets(zone)
                for src in range(1, NUM_SOURCES + 1)
            ]
        for f in frames:
            self._send(f)

    def _do_set_audio(self, zone: int, data: int, field: str, err_code: int,
                      db_min: int, db_max: int):
        db = _signed_byte(data)
        if not (db_min <= db <= db_max):
            self._send(self._build_error(err_code))
            return
        frames = []
        with self._lock:
            for z in self._targets(zone):
                if getattr(z, field) != data:
                    setattr(z, field, data)
                    frames.append(self._build_status(z.zone))
        for f in frames:
            self._send(f)

    def _do_set_echo(self, data: int):
        self._echo_mode = (data == 0xFF)
        logger.debug("Echo mode: %s", "ON" if self._echo_mode else "OFF")

    def _do_reset_names(self):
        with self._lock:
            for z in self._zones.values():
                z.name = f"Zone {z.zone}"
                z.source_names = {i: f"Source {i}" for i in range(1, NUM_SOURCES + 1)}

    def _do_reset_audio(self, zone: int):
        frames = []
        with self._lock:
            for z in self._targets(zone):
                z.input = _DEFAULT_INPUT
                z.volume = _DEFAULT_VOLUME
                z.treble = _DEFAULT_TREBLE
                z.bass = _DEFAULT_BASS
                z.balance = _DEFAULT_BALANCE
                frames.append(self._build_status(z.zone))
        for f in frames:
            self._send(f)

    # ------------------------------------------------------------------
    # Frame builders — must be called with _lock held
    # ------------------------------------------------------------------

    def _build_status(self, zone_num: int) -> bytes:
        z = self._zones[zone_num]
        d1 = (0x01 if z.power else 0) | (0x02 if z.mute else 0) | (0x04 if z.dnd else 0)
        d2 = (0x80 if z.allon else 0) | (0x40 if z.alloff else 0) | (0x20 if z.party else 0)
        d3 = 0x10 if z.mp3_repeat else 0x00   # bit 4 = what app.py actually checks
        d4 = 0x10 if z.party_repeat else 0x00
        d5 = (z.input - 1) & 0xFF             # 0-based; app.py adds 1 to restore
        return self._make_frame(zone_num, 0x05, bytes([
            d1, d2, d3, d4, d5,
            z.volume & 0xFF, z.treble & 0xFF, z.bass & 0xFF, z.balance & 0xFF,
        ]))

    def _build_zone_name(self, zone_num: int) -> bytes:
        z = self._zones[zone_num]
        # 11-byte name + zone addr + 1 padding = 13 data bytes → 18-byte frame
        name_b = z.name.encode('ascii')[:10].ljust(11, b'\x00')
        return self._make_frame(zone_num, 0x0D, name_b + bytes([zone_num, 0x00]))

    def _build_source_name(self, zone_num: int, src_num: int) -> bytes:
        z = self._zones[zone_num]
        name = z.source_names.get(src_num, f"Source {src_num}")
        # 11-byte name + src num + 1 padding = 13 data bytes → 18-byte frame
        name_b = name.encode('ascii')[:10].ljust(11, b'\x00')
        return self._make_frame(zone_num, 0x0E, name_b + bytes([src_num, 0x00]))

    def _build_mp3_off(self) -> bytes:
        return self._make_frame(0, 0x14, b"Device Not Found")

    def _build_error(self, error_num: int) -> bytes:
        return self._make_frame(0, 0x1B, bytes([error_num]) + bytes(8))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _targets(self, zone: int) -> List[ZoneState]:
        """Zones to act on. Must be called with _lock held."""
        if zone == 0:
            return list(self._zones.values())
        z = self._zones.get(zone)
        return [z] if z else []

    @staticmethod
    def _data_to_input(data: int) -> int:
        if 0x10 <= data <= 0x1B:
            return data - 0x10 + 1
        if 0x63 <= data <= 0x68:
            return data - 0x63 + 13
        return 1

    @staticmethod
    def _party_data_to_input(data: int) -> int:
        if 0x36 <= data <= 0x41:
            return data - 0x36 + 1
        if 0x69 <= data <= 0x6E:
            return data - 0x69 + 13
        return 1


def _signed_byte(b: int) -> int:
    return b if b <= 127 else b - 256


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Lync12 serial protocol emulator")
    parser.add_argument("--zones", type=int, choices=[6, 12], default=12,
                        help="Number of zones (default: 12)")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    emu = Lync12Emulator(num_zones=args.zones)
    slave = emu.start()

    print(f"Lync{args.zones} emulator running")
    print(f"  export SERIAL_PORT={slave}")
    print(f"  Press Ctrl+C to stop\n")

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        emu.stop()
        print("\nEmulator stopped.")


if __name__ == "__main__":
    main()
