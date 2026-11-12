#!/usr/bin/env python3
"""Сканер кода: ищет места, которые нагружают CPU/GPU/сеть. Ничего не меняет, печатает отчёт."""
import os
import re
from collections import defaultdict

SKIP_DIRS = {".git", "node_modules", "build-input", "bazel-out", "build"}
SRC_EXT = (".swift", ".m", ".mm", ".h", ".plist")

NAME_RX = re.compile(r"Glass|AppDelegate|SharedAccountContext|Preload|PowerSaving|EnergySaving|Regram|Liquid", re.I)

COUNT_PATTERNS = {
    "blur/visual effect": r"UIVisualEffectView|UIBlurEffect|CIGaussianBlur|BackdropView|blurRadius|CAFilter|backdropLayer",
    "glass": r"Glass",
    "display link": r"CADisplayLink|displayLink",
    "timers": r"Timer\.scheduledTimer|SwiftSignalKit\.Timer|DispatchSource\.makeTimerSource|\bTimer\(",
    "lottie/stickers": r"AnimatedStickerNode|RLottie|LottieView|AnimatedStickerFrameSource|MultiAnimationRenderer",
    "preload": r"[Pp]reload|[Pp]refetch|[Pp]redownload",
    "shadow/mask (offscreen)": r"shadowRadius|shadowPath|layer\.mask\b|cornerRadius.*masksToBounds|allowsGroupOpacity",
    "energy flags": r"fullTranslucency|energyUsageSettings|automaticEnergyUsageShouldBeOn",
}
COUNT_RX = {k: re.compile(v) for k, v in COUNT_PATTERNS.items()}

CONTEXT_PATTERNS = [
    ("fullTranslucency usage", r"fullTranslucency", 60),
    ("automaticEnergyUsageShouldBeOn", r"automaticEnergyUsageShouldBeOn", 30),
    ("UIBackgroundModes", r"UIBackgroundModes|BGTaskScheduler|BGAppRefresh", 30),
    ("global animation switches", r"setAnimationsEnabled|animationDurationFactor|layer\.speed\s*=", 30),
    ("glass types", r"(class|struct|final class)\s+\w*Glass\w*", 40),
]
CONTEXT_RX = [(t, re.compile(p), cap) for t, p, cap in CONTEXT_PATTERNS]

names, plists = [], []
counts = defaultdict(dict)
context = defaultdict(list)
nfiles = nsrc = 0

for root, dirs, fs in os.walk("."):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for f in fs:
        path = os.path.join(root, f)[2:]
        nfiles += 1
        if NAME_RX.search(f):
            names.append(path)
        if f == "Info.plist":
            plists.append(path)
        if not f.endswith(SRC_EXT):
            continue
        try:
            if os.path.getsize(path) > 2_000_000:
                continue
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        nsrc += 1
        for label, rx in COUNT_RX.items():
            n = len(rx.findall(text))
            if n:
                counts[label][path] = n
        for title, rx, cap in CONTEXT_RX:
            if len(context[title]) >= cap or not rx.search(text):
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line) and len(context[title]) < cap:
                    context[title].append(f"{path}:{i}: {line.strip()[:150]}")

print(f"# files: {nfiles}, source files scanned: {nsrc}\n")
print("## Files by name (Glass/AppDelegate/SharedAccountContext/Preload/Regram...)")
for p in sorted(names)[:150]:
    print(p)
print(f"({len(names)} total)\n")
print("## Info.plist files")
for p in sorted(plists)[:40]:
    print(p)
print()
for label, d in counts.items():
    print(f"## Top files: {label} (total {sum(d.values())} in {len(d)} files)")
    for p, n in sorted(d.items(), key=lambda x: -x[1])[:15]:
        print(f"{n:5d}  {p}")
    print()
for title, lines in context.items():
    print(f"## {title}")
    for l in lines:
        print(l)
    print()
