#!/usr/bin/env python3
"""Narrate the epistemics slides. Captions are a toggleable track, not burned pixels.

Speech is plain text. The personal name stays on the title card and is not spoken.
"""

from __future__ import annotations

import os
import re
import subprocess
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / ".build" / "epistemics-slides" / "frames"
WORK = ROOT / ".build" / "epistemics-narration"
OUT_MP4 = ROOT / "report" / "epistemics_trust_v1" / "slides" / "Epistemics_Trust_Narration.mp4"
OUT_VTT = ROOT / "report" / "epistemics_trust_v1" / "slides" / "Epistemics_Trust_Narration.vtt"
EDGE = Path(os.environ.get("EDGE_TTS", str(ROOT / ".build" / "tts-venv" / "bin" / "edge-tts")))
VOICE = "en-US-AndrewMultilingualNeural"
RATE = "+6%"
HOLD = 0.65

# Spoken phrases, in order. Captions use the same words.
SCENES: list[list[str]] = [
    [
        "An agent was allowed to act, and the log of that allowance is intact.",
        "Most reviews stop there.",
        "The open question is whether that log warrants the conclusion that an unauthorized effect did not commit.",
    ],
    [
        "Three readers are about to look at the same record, and only one is asking that question.",
        "The first treats an intact actor line as proof the effect was in bounds.",
        "The second takes the historical label, the one already published.",
        "The third asks whether the record is evidence for the effect claim.",
    ],
    [
        "Those three readers are about to be scored, and these two counts stay apart.",
        "Forty-eight packets are four views of twelve histories.",
        "On that set, the two sink views are the twenty-four decisive opportunities.",
        "An unsupported support is a support the warrant does not justify.",
        "The sixteen probes are edits of a single readback. They do not get added to the forty-eight.",
    ],
    [
        "Trusting the intact actor record overclaims twenty-six times, and four of those supports are of a false proposition.",
        "The historical label still carries eleven unsupported supports.",
        "The checker has none.",
        "Those eleven stay. The zero beside them does not erase them.",
    ],
    [
        "The eleven are the ones that look finished.",
        "The proposition is true, the actor record looks intact, and admission marks it misbound.",
        "None of them has a deciding premise.",
        "Four of the eleven have no effect row, and seven have a withheld effect row labeled supports.",
        "A withheld row labeled supports does not explain the four with no effect row.",
        "This reading does not establish why the retained verdict supported the other seven.",
        "A further withheld packet has that same label and is not in the eleven. Its proposition is false, and the historical label is unresolved.",
    ],
    [
        "On these forty-eight, the intact-actor rule supports every packet.",
        "Rejecting the misbound probe, and still trusting the actor, leaves fourteen unsupported supports.",
        "The effect row's own support label still backs a false proposition.",
        "Subject class without the absence census leaves eight warranted supports unresolved: both sink views of the four histories with no effect row.",
        "Subject class, or that zero-row census, matches the full projection.",
    ],
    [
        "Step outside this set, and the checks that were quiet here show up in the sixteen.",
        "Subject class supports nine that the projection leaves unresolved.",
        "Those nine are three scope checks, three binding checks, an unknown subject beside an authorized sink, and two census checks.",
        "They are a count inside the sixteen. The sixteen stay separate from the forty-eight.",
        "An exact duplicate census stays supported, and a sink whose only subject is unknown stays unresolved.",
    ],
    [
        "On these records, an intact actor log is not the effect warrant.",
        "On the forty-eight, subject class, or the zero-row absence census, matches the checker.",
        "SoundGate's protocol is a separate pair of claims.",
        "The projection returns supported for the barrier and refuted for the original policy.",
        "An intact run record still supports the original policy. The forty-eight and the sixteen are not this test.",
    ],
]


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs)


def _duration(path: Path) -> float:
    result = _run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", str(path),
        ]
    )
    return float(result.stdout.strip())


def _speak(text: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size > 1000:
        return
    last = ""
    for attempt in range(5):
        if attempt:
            time.sleep(3)
        try:
            _run(
                [
                    str(EDGE),
                    "--voice", VOICE,
                    "--rate", RATE,
                    "--text", text,
                    "--write-media", str(destination),
                ]
            )
            if destination.is_file() and destination.stat().st_size > 1000:
                return
        except subprocess.CalledProcessError as exc:
            last = (exc.stderr or exc.stdout or str(exc))[-500:]
    raise SystemExit(f"speech failed for {destination.name}: {last}")


def _speech_spans(audio: Path, phrases: list[str], speech_end: float) -> list[tuple[float, float]]:
    """Place one cue per phrase, using detected pauses when they line up."""
    detected = _run(
        [
            "ffmpeg", "-i", str(audio),
            "-af", "silencedetect=noise=-32dB:d=0.18",
            "-f", "null", "-",
        ]
    )
    log = detected.stderr
    starts = [float(value) for value in re.findall(r"silence_start: ([0-9.]+)", log)]
    ends = [float(value) for value in re.findall(r"silence_end: ([0-9.]+)", log)]
    boundaries = [0.0]
    for start, end in zip(starts, ends):
        if 0.12 < start < speech_end - 0.12:
            boundaries.append((start + end) / 2)
    boundaries.append(speech_end)
    spans = list(zip(boundaries, boundaries[1:]))
    if len(spans) == len(phrases):
        return [(max(0.0, start), end) for start, end in spans]
    weights = [max(len(phrase), 1) for phrase in phrases]
    total = sum(weights)
    cursor = 0.0
    placed = []
    for weight in weights:
        width = speech_end * weight / total
        placed.append((cursor, cursor + width))
        cursor += width
    return placed


def _timestamp(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def main() -> None:
    spoken = "\n".join(" ".join(scene) for scene in SCENES)
    if "Jonathan" in spoken or "Maye" in spoken:
        raise SystemExit("the narration speaks the personal name")
    WORK.mkdir(parents=True, exist_ok=True)
    clips = WORK / "clips"
    clips.mkdir(exist_ok=True)
    cues: list[tuple[float, float, str]] = []
    concat = WORK / "concat.txt"
    lines = []
    clock = 0.0
    for index, phrases in enumerate(SCENES, start=1):
        audio = WORK / f"scene-{index:02d}.mp3"
        _speak(" ".join(phrases), audio)
        speech = _duration(audio)
        scene_length = speech + HOLD
        frame = FRAMES / f"slide-{index}.png"
        if not frame.is_file():
            raise SystemExit(f"missing slide frame {frame}")
        clip = clips / f"scene-{index:02d}.mp4"
        _run(
            [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(frame),
                "-i", str(audio),
                "-vf", "scale=1920:1080:flags=lanczos,format=yuv420p",
                "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "160k",
                "-af", f"apad=whole_dur={scene_length:.3f}",
                "-t", f"{scene_length:.3f}",
                str(clip),
            ]
        )
        for (start, end), phrase in zip(_speech_spans(audio, phrases, speech), phrases):
            cues.append((clock + start, min(clock + end, clock + speech), phrase))
        clock += scene_length
        lines.append(f"file '{clip}'")
        print(f"scene {index}: speech {speech:.2f}s, scene {scene_length:.2f}s")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
    silent = WORK / "silent.mp4"
    _run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
            "-c", "copy", str(silent),
        ]
    )
    vtt = ["WEBVTT", ""]
    for start, end, phrase in cues:
        if end <= start:
            end = start + 0.4
        vtt.append(f"{_timestamp(start)} --> {_timestamp(end)}")
        vtt.append(textwrap.fill(phrase, width=68))
        vtt.append("")
    OUT_VTT.write_text("\n".join(vtt), encoding="utf-8")
    _run(
        [
            "ffmpeg", "-y", "-i", str(silent), "-i", str(OUT_VTT),
            "-map", "0:v:0", "-map", "0:a:0", "-map", "1:0",
            "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
            "-metadata:s:s:0", "language=eng",
            "-disposition:s:0", "none",
            str(OUT_MP4),
        ]
    )
    print(OUT_MP4.relative_to(ROOT))
    print(OUT_VTT.relative_to(ROOT))


if __name__ == "__main__":
    main()
