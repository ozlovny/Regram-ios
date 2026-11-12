б#!/usr/bin/env python3
"""Выписывает ключевые куски кода в reports/lite-dump.txt. Ничего не меняет."""
import os
import re
from pathlib import Path

OUT = Path("reports/lite-dump.txt")
OUT.parent.mkdir(exist_ok=True)
buf = []

STRUCT = re.compile(
    r"^\s*((public|private|fileprivate|internal|final|open|static|override|@objc|@MainActor)\s+)*"
    r"(class|struct|enum|protocol|extension|func|init)\b|#available|#if|@available"
)


def out(s=""):
    buf.append(s)


def read(path):
    p = Path(path)
    if not p.exists():
        out(f"## {path}\n(MISSING)\n")
        return None
    return p.read_text(encoding="utf-8", errors="ignore").splitlines()


def full(path, cap):
    lines = read(path)
    if lines is None:
        return
    out(f"## FULL {path} ({len(lines)} lines, showing {min(cap, len(lines))})")
    for i, l in enumerate(lines[:cap], 1):
        out(f"{i}: {l[:170]}")
    out()


def outline(path, cap=260):
    lines = read(path)
    if lines is None:
        return
    out(f"## OUTLINE {path} ({len(lines)} lines)")
    n = 0
    for i, l in enumerate(lines, 1):
        if STRUCT.search(l):
            out(f"{i}: {l.strip()[:150]}")
            n += 1
            if n >= cap:
                out("...cut")
                break
    out()


def rng(path, a, b):
    lines = read(path)
    if lines is None:
        return
    out(f"## RANGE {path} {a}-{b}")
    for i in range(a, min(b, len(lines)) + 1):
        out(f"{i}: {lines[i - 1][:170]}")
    out()


def grep(regex, ctx, cap, label):
    rx = re.compile(regex)
    out(f"## GREP {label}")
    n = 0
    for root, dirs, fs in os.walk("."):
        dirs[:] = [d for d in dirs if d not in {".git", "build", "build-input", "third-party"}]
        for f in fs:
            if not f.endswith((".swift", ".m", ".h", ".mm")):
                continue
            path = os.path.join(root, f)[2:]
            try:
                lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            for i, l in enumerate(lines):
                if rx.search(l):
                    out(f"-- {path}:{i + 1}")
                    for j in range(max(0, i - 1), min(len(lines), i + ctx)):
                        out(f"   {lines[j][:150]}")
                    n += 1
                    if n >= cap:
                        out("...cut\n")
                        return
    out()


G = "submodules/TelegramUI/Components/"
full(G + "GlassBackgroundComponent/Sources/GlassBackgroundComponent.swift", 900)
outline(G + "GlassBackgroundComponent/Sources/LegacyGlassView.swift")
outline(G + "StaticGlassBackground/Sources/StaticGlassBackgroundView.swift")
outline(G + "StaticGlassBackground/Sources/StaticGlassBackground.swift")
outline(G + "LiquidGlassShapes/Sources/LiquidGlassShapesLayer.swift")
outline(G + "LiquidGlassShapes/Sources/LiquidGlassBackdropLayers.swift")
outline(G + "NavigationBarComponent/Sources/NavigationBarPlatterTransitionView.swift")
outline("submodules/TelegramCore/Sources/State/ChatHistoryPreloadManager.swift")
outline("submodules/TelegramUI/Sources/PrefetchManager.swift")
outline("submodules/TelegramUI/Sources/InChatPrefetchManager.swift")
outline("submodules/MediaPlayer/Sources/TimeBasedVideoPreload.swift")
rng("submodules/TelegramPresentationData/Sources/PresentationData.swift", 540, 600)
grep(r"func animationDurationFactor|static var animationDurationFactor|animationDurationFactor\(\)\s*(->|\{)", 8, 30,
     "animationDurationFactor definitions")

# Собственные функции Regram
out("## Regram/ top-level folders (name: swift files)")
for d in sorted(Path("Regram").iterdir()) if Path("Regram").exists() else []:
    if d.is_dir():
        out(f"{d.name}: {len(list(d.rglob('*.swift')))}")
out()
full("build-system/check-regram-features.py", 120)
outline("Regram/RGInputToolbar/Sources/RGInputToolbar.swift")

OUT.write_text("\n".join(buf), encoding="utf-8")
print(f"written {OUT}, {len(buf)} lines")
