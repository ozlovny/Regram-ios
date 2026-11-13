#!/usr/bin/env python3
"""Выписывает ключевые куски кода в reports/lite-dump.txt (v2). Ничего не меняет."""
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


def outline(path, cap=220):
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


def grep(regex, ctx, cap, label, only=None):
    rx = re.compile(regex)
    out(f"## GREP {label}")
    n = 0
    for root, dirs, fs in os.walk(only or "."):
        dirs[:] = [d for d in dirs if d not in {".git", "build", "build-input", "third-party", "Tests"}]
        for f in sorted(fs):
            if not f.endswith((".swift", ".m", ".h", ".mm")):
                continue
            path = os.path.join(root, f)
            path = path[2:] if path.startswith("./") else path
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


# 1. Как приложение классифицирует мощность устройства
grep(r"var isGraphicallyCapable|isGraphicallyCapable\s*:|static (var|let) performance", 10, 12, "device performance classes")
# 2. Где создаются тяжёлые Metal-слои и «линза»
grep(r"LiquidGlassShapesLayer\(", 3, 15, "LiquidGlassShapesLayer creation")
grep(r"LiquidLensView\(", 3, 15, "LiquidLensView creation")
grep(r"MetalEngine\.shared|MetalEngine\(", 2, 10, "MetalEngine")
outline("submodules/TelegramUI/Components/LiquidLens/Sources/LiquidLensView.swift")
# 3. Где реально используется множитель анимаций Display
grep(r"animationDurationFactor\(\)", 1, 40, "Display animationDurationFactor use", only="submodules/Display")
# 4. Переходы навигации
outline("submodules/Display/Source/NavigationController.swift")
grep(r"animated\(duration:\s*0\.[3-9]", 1, 25, "navigation durations", only="submodules/Display/Source")
# 5. Запуск приложения
outline("submodules/TelegramUI/Sources/AppDelegate.swift")
grep(r"asyncAfter|Timer\.scheduledTimer|\.after\(", 2, 25, "startup delays/timers", only="submodules/TelegramUI/Sources")
# 6. Истории и сервисы Regram
full("build-system/check-regram-story-flags.py", 120)
grep(r"URLSession|URLRequest\(", 1, 40, "Regram network calls", only="Regram")
out("## Regram/RGAppUpdate files")
for f in sorted(Path("Regram/RGAppUpdate").rglob("*.swift"))[:30] if Path("Regram/RGAppUpdate").exists() else []:
    out(f"{len(f.read_text(errors='ignore').splitlines())}  {f}")
out()

OUT.write_text("\n".join(buf), encoding="utf-8")
print(f"written {OUT}, {len(buf)} lines")
