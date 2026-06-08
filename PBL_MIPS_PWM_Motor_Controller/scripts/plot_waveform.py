#!/usr/bin/env python3
"""Plot key PWM/MMIO signals from an Icarus Verilog VCD file.

This script intentionally uses only the Python standard library plus
matplotlib. If automatic signal detection picks the wrong hierarchy, edit
SIGNAL_OVERRIDES below and set the exact full signal name from the VCD.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


SIGNAL_OVERRIDES = {
    "pwm_out": None,
    "switches": None,
    "pwm_duty": None,
    "pwm_en": None,
}

DEFAULT_SIGNAL_KEYWORDS = {
    "pwm_out": ("pwm_out",),
    "switches": ("switch",),
    "pwm_duty": ("pwm_duty", "duty"),
    "pwm_en": ("pwm_en", "enable", "en"),
}

BAD_ENABLE_WORDS = (
    "addr",
    "clk",
    "mem_write_en",
    "rst",
    "stall",
    "write_en",
)

BAD_DUTY_WORDS = ("addr",)


@dataclass
class VcdSignal:
    identifier: str
    size: int
    vtype: str
    name: str


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Plot PWM signals from wave.vcd")
    parser.add_argument(
        "--vcd",
        default=str(project_root / "wave.vcd"),
        help="VCD file path, default: wave.vcd in the project root",
    )
    parser.add_argument(
        "--out",
        default=str(project_root / "docs" / "waveform_profile.png"),
        help="PNG output path, default: docs/waveform_profile.png",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show the matplotlib window after saving the PNG",
    )
    return parser.parse_args()


def parse_timescale(line: str) -> Optional[float]:
    match = re.search(r"\$timescale\s+(\d+)\s*([a-zA-Z]+)\s+\$end", line)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).lower()
    units = {
        "s": 1.0,
        "ms": 1e-3,
        "us": 1e-6,
        "ns": 1e-9,
        "ps": 1e-12,
        "fs": 1e-15,
    }
    return amount * units.get(unit, 1.0)


def read_vcd_header(vcd_path: Path) -> Tuple[List[VcdSignal], float, int]:
    signals: List[VcdSignal] = []
    scope: List[str] = []
    tick_seconds = 1e-9
    header_end_line = 0

    with vcd_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            parsed_timescale = parse_timescale(stripped)
            if parsed_timescale is not None:
                tick_seconds = parsed_timescale

            if stripped.startswith("$scope"):
                parts = stripped.split()
                if len(parts) >= 3:
                    scope.append(parts[2])
            elif stripped.startswith("$upscope"):
                if scope:
                    scope.pop()
            elif stripped.startswith("$var"):
                parts = stripped.split()
                if len(parts) >= 5:
                    vtype = parts[1]
                    size = int(parts[2])
                    identifier = parts[3]
                    end_index = parts.index("$end") if "$end" in parts else len(parts)
                    reference = " ".join(parts[4:end_index])
                    full_name = ".".join(scope + [reference])
                    signals.append(VcdSignal(identifier, size, vtype, full_name))
            elif stripped == "$enddefinitions $end":
                header_end_line = line_number
                break

    if not signals:
        raise RuntimeError(f"No signals found in VCD header: {vcd_path}")
    return signals, tick_seconds, header_end_line


def leaf_name(full_name: str) -> str:
    return full_name.split(".")[-1].split()[0]


def related_candidates(signals: Sequence[VcdSignal]) -> List[str]:
    words = ("pwm_out", "switch", "duty", "pwm_en", "enable", "en")
    matches = []
    for signal in signals:
        lowered = signal.name.lower()
        if any(word in lowered for word in words):
            matches.append(signal.name)
    return matches


def score_signal(key: str, signal: VcdSignal) -> int:
    name = signal.name.lower()
    leaf = leaf_name(name)
    score = 0

    if key == "pwm_out":
        if leaf == "pwm_out":
            score += 100
        if "pwm_out" in name:
            score += 50
    elif key == "switches":
        if leaf == "switches":
            score += 100
        if "switch" in name:
            score += 50
        if "mips_tb" in name:
            score += 10
    elif key == "pwm_duty":
        if leaf == "pwm_duty":
            score += 150
        if "pwm_duty" in name:
            score += 100
        elif "duty" in name:
            score += 40
        if any(word in name for word in BAD_DUTY_WORDS):
            score -= 200
    elif key == "pwm_en":
        if leaf == "pwm_en":
            score += 160
        if "pwm_en" in name:
            score += 120
        elif "enable" in leaf:
            score += 50
        elif leaf == "en":
            score += 40
        if any(word in name for word in BAD_ENABLE_WORDS):
            score -= 200

    score -= len(signal.name) // 20
    return score


def choose_signal(key: str, signals: Sequence[VcdSignal]) -> Optional[VcdSignal]:
    override = SIGNAL_OVERRIDES.get(key)
    if override:
        for signal in signals:
            if signal.name == override:
                return signal
        return None

    keywords = DEFAULT_SIGNAL_KEYWORDS[key]
    candidates = [
        signal
        for signal in signals
        if any(keyword in signal.name.lower() for keyword in keywords)
    ]
    if not candidates:
        return None

    candidates.sort(key=lambda signal: (score_signal(key, signal), -len(signal.name)), reverse=True)
    best = candidates[0]
    return best if score_signal(key, best) > 0 else None


def decode_value(raw: str, size: int) -> Optional[int]:
    raw = raw.strip().lower()
    if not raw:
        return None
    if any(char in raw for char in "xz"):
        return None
    if raw[0] == "b":
        bits = raw[1:]
        return int(bits, 2) if bits else None
    if raw[0] in "01":
        return int(raw[0])
    if raw[0] == "r":
        try:
            return int(float(raw[1:]))
        except ValueError:
            return None
    return None


def parse_signal_values(
    vcd_path: Path,
    selected: Dict[str, VcdSignal],
    tick_seconds: float,
) -> Dict[str, List[Tuple[float, Optional[int]]]]:
    id_to_key: Dict[str, str] = {
        signal.identifier: key for key, signal in selected.items()
    }
    values: Dict[str, List[Tuple[float, Optional[int]]]] = {
        key: [] for key in selected
    }
    current_time = 0

    with vcd_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                current_time = int(stripped[1:])
                continue

            if stripped[0] in "01xz":
                identifier = stripped[1:]
                key = id_to_key.get(identifier)
                if key is not None:
                    value = decode_value(stripped[0], selected[key].size)
                    values[key].append((current_time * tick_seconds * 1e6, value))
            elif stripped[0] in "br":
                parts = stripped.split()
                if len(parts) != 2:
                    continue
                raw_value, identifier = parts
                key = id_to_key.get(identifier)
                if key is not None:
                    value = decode_value(raw_value, selected[key].size)
                    values[key].append((current_time * tick_seconds * 1e6, value))

    return values


def prepare_step(events: Sequence[Tuple[float, Optional[int]]], end_time: float) -> Tuple[List[float], List[Optional[int]]]:
    if not events:
        return [0.0, end_time], [None, None]

    times = [events[0][0]]
    vals = [events[0][1]]
    for time_value, value in events[1:]:
        times.append(time_value)
        vals.append(value)

    if times[-1] < end_time:
        times.append(end_time)
        vals.append(vals[-1])
    return times, vals


def print_available(signals: Sequence[VcdSignal], limit: int = 80) -> None:
    print("\nRelated signal candidates:")
    candidates = related_candidates(signals)
    if candidates:
        for name in candidates[:limit]:
            print(f"  {name}")
    else:
        print("  No related candidates found.")

    print("\nAvailable signals sample:")
    for signal in signals[:limit]:
        print(f"  {signal.name}")


def plot_values(
    values: Dict[str, List[Tuple[float, Optional[int]]]],
    selected: Dict[str, VcdSignal],
    output_path: Path,
    show: bool,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "matplotlib is not installed. Run: python -m pip install matplotlib"
        ) from exc

    end_time = 0.0
    for events in values.values():
        if events:
            end_time = max(end_time, events[-1][0])

    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(12, 8))
    fig.suptitle("PBL MIPS PWM Motor Controller - Waveform Profile")

    plot_specs = [
        ("switches", "switches", 0, 255),
        ("pwm_duty", "PWM duty register", 0, 255),
        ("pwm_en", "PWM enable", -0.1, 1.1),
        ("pwm_out", "pwm_out", -0.1, 1.1),
    ]

    for axis, (key, label, ymin, ymax) in zip(axes, plot_specs):
        times, samples = prepare_step(values[key], end_time)
        axis.step(times, samples, where="post", linewidth=1.4)
        axis.set_ylabel(label)
        axis.set_ylim(ymin, ymax)
        axis.grid(True, alpha=0.35)
        axis.set_title(selected[key].name, fontsize=9, loc="left")

    axes[-1].set_xlabel("time (us)")
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    print(f"Saved plot: {output_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def main() -> int:
    args = parse_args()
    vcd_path = Path(args.vcd).resolve()
    output_path = Path(args.out).resolve()

    if not vcd_path.exists():
        print(f"VCD file not found: {vcd_path}", file=sys.stderr)
        return 1

    signals, tick_seconds, _ = read_vcd_header(vcd_path)

    selected: Dict[str, VcdSignal] = {}
    missing: List[str] = []
    for key in ("pwm_out", "switches", "pwm_duty", "pwm_en"):
        signal = choose_signal(key, signals)
        if signal is None:
            missing.append(key)
        else:
            selected[key] = signal

    if missing:
        print(f"Could not find required signal(s): {', '.join(missing)}", file=sys.stderr)
        print_available(signals)
        return 2

    print("Selected signals:")
    for key, signal in selected.items():
        print(f"  {key}: {signal.name}")

    values = parse_signal_values(vcd_path, selected, tick_seconds)
    empty = [key for key, events in values.items() if not events]
    if empty:
        print(f"No value changes found for: {', '.join(empty)}", file=sys.stderr)
        print_available(signals)
        return 3

    plot_values(values, selected, output_path, args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
