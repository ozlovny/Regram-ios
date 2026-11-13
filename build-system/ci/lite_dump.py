#!/usr/bin/env python3
"""Выписывает ключевые куски кода в reports/lite-dump.txt (v3). Ничего не меняет."""
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


# 1. Где ещё включаются «мощные» ветки кода
grep(r"isGraphicallyCapable", 2, 40, "isGraphicallyCapable uses")
# 2. Нижняя панель и линза: самые тяжёлые элементы на главном экране
full("submodules/TelegramUI/Components/LiquidLens/Sources/LiquidLensView.swift", 820)
grep(r"UIVisualEffectView|liquidLensView|GlassBackground", 2, 25, "TabBar glass/lens", only="submodules/TelegramUI/Components/TabBarComponent")
outline("submodules/TelegramUI/Components/GlassBarButtonComponent/Sources/GlassBarButtonComponent.swift")
# 3. Переходы навигационной панели
full("submodules/TelegramUI/Components/NavigationBarComponent/Sources/NavigationBarPlatterTransitionView.swift", 380)
# 4. Истории в списке чатов
grep(r"StoryPeerListComponent\(", 3, 10, "story list creation", only="submodules/ChatListUI")
grep(r"hideStories|isStoryListHidden|storiesHidden|hiddenStories|storyListHidden", 2, 20, "story hiding flags")
# 5. Обновления Regram: откуда вызывается
grep(r"RGAppUpdater", 3, 20, "RGAppUpdater call sites", only="submodules/TelegramUI")

OUT.write_text("\n".join(buf), encoding="utf-8")
print(f"written {OUT}, {len(buf)} lines")
