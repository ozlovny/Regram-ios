#!/usr/bin/env python3
"""Облегчающие патчи Regram (v2): стекло без размытия, быстрые анимации, без предзагрузок, экономная сеть.
Запускается из корня репозитория перед сборкой. Обязательные патчи при неудаче валят шаг сразу (дёшево),
необязательные только печатают предупреждение."""
import re
import sys
from pathlib import Path

MARK = "// REGRAM-LITE patched"
ANIM_FACTOR = "0.2"  # во сколько раз укорачивать анимации (1.0 = без изменений, 0.1 = почти мгновенно)

errors = []


def rx(pattern, repl, flags=0):
    def fn(text):
        new, n = re.subn(pattern, repl, text, count=1, flags=flags)
        return new, n == 1
    return fn


def energy_default(text):
    m = re.search(r"static let `default`: EnergyUsageSettings = \{.*?\}\(\)", text, re.S)
    if not m:
        return text, False
    block, ok = m.group(0), True
    for key in ("autoplayVideo", "autoplayGif", "loopStickers", "extendBackgroundWork", "autodownloadInBackground"):
        block, n = re.subn(rf"({key}:\s*)true", r"\1false", block)
        ok = ok and n == 1
    for key in ("loopEmoji", "fullTranslucency"):
        block, n = re.subn(rf"({key}:\s*)isCapable", r"\1false && isCapable", block)
        ok = ok and n == 1
    block, n = re.subn(r"(activationThreshold:\s*)\d+", r"\g<1>100", block)
    ok = ok and n == 1
    return text.replace(m.group(0), block, 1), ok


def patch_file(path, patches):
    p = Path(path)
    if not p.exists():
        for name, _, required in patches:
            print(f"[lite] {'FAILED' if required else 'warn'}: {name} (file missing: {path})")
            if required:
                errors.append(name)
        return
    text = p.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[lite] already patched: {path}")
        return
    changed = False
    for name, fn, required in patches:
        text, ok = fn(text)
        if ok:
            changed = True
            print(f"[lite] ok: {name}")
        else:
            print(f"[lite] {'FAILED' if required else 'warn'}: {name}")
            if required:
                errors.append(name)
    if changed:
        p.write_text(MARK + "\n" + text, encoding="utf-8")


UI = "submodules/TelegramUI/"
# 1. Настройки энергии и сети по умолчанию
patch_file("submodules/TelegramUIPreferences/Sources/MediaAutoDownloadSettings.swift", [
    ("energy defaults off", energy_default, True),
    ("cellular preset -> low", rx(r"(cellular:\s*MediaAutoDownloadConnection\(enabled:\s*true,\s*preset:\s*)\.medium", r"\1.low"), True),
    ("wifi preset -> low", rx(r"(wifi:\s*MediaAutoDownloadConnection\(enabled:\s*true,\s*preset:\s*)\.high", r"\1.low"), True),
    ("downloadInBackground -> false", rx(r"(downloadInBackground:\s*)true(,\s*energyUsageSettings:)", r"\1false\2"), True),
    ("predownload -> false", rx(r"return category\.sizeLimit > 2 \* 1024 \* 1024 && category\.predownload", "return false"), True),
])

# 2. «Жидкое стекло» на iOS < 26: без живого размытия фона и без маски яркости (оба дорогие для GPU)
patch_file(UI + "Components/GlassBackgroundComponent/Sources/GlassBackgroundComponent.swift", [
    ("glass: backdrop blur off", rx(r"legacyView\.update\(size: size, shape: shape, style: style, transition: transition\)",
                                    "legacyView.isHidden = true // lite: no backdrop blur"), True),
    ("glass: luminance mask off", rx(r"foregroundView\.mask = self\.maskContainerView", "// lite: no luminance mask"), True),
])

# 3. Анимации: множитель длительности ComponentFlow (на устройстве по умолчанию 1.0)
patch_file("submodules/ComponentFlow/Source/Base/Transition.swift", [
    ("animations x%s faster (ComponentFlow)" % ANIM_FACTOR,
     rx(r"(static var animationDurationFactor: Double \{\s*#if targetEnvironment\(simulator\)\s*return Double\(UIAnimationDragCoefficient\(\)\)\s*#else\s*return\s+)1\.0",
        rf"\g<1>{ANIM_FACTOR}"), False),
])

# 4. Анимации: множитель Display (animationDurationFactorImpl), ищем определение сами
found = False
impl_rx = re.compile(r"(animationDurationFactorImpl\s*(?::[^=\n]*)?=\s*\{\s*(?:return\s+)?)1\.0")
for base in ("submodules/Display", "submodules/UIKitRuntimeUtils", "submodules/ComponentFlow"):
    for f in sorted(Path(base).rglob("*.swift")) if Path(base).exists() else []:
        t = f.read_text(encoding="utf-8", errors="ignore")
        if MARK not in t and impl_rx.search(t):
            f.write_text(MARK + "\n" + impl_rx.sub(rf"\g<1>{ANIM_FACTOR}", t, count=1), encoding="utf-8")
            print(f"[lite] ok: animations faster (Display impl in {f})")
            found = True
            break
    if found:
        break
if not found:
    print("[lite] warn: animationDurationFactorImpl definition not found or already patched")

# 5. Сеть: фоновые менеджеры предзагрузки отключены
patch_file("submodules/TelegramCore/Sources/State/ChatHistoryPreloadManager.swift", [
    ("history preload off", rx(r"(func start\(\)\s*\{)", "\\1\n        return // lite: preload off"), False),
])
patch_file(UI + "Sources/PrefetchManager.swift", [
    ("media prefetch off", rx(r"(private func updateOrderedPreloadMedia\([^\n{]*\)\s*\{)", "\\1\n        return // lite: prefetch off"), False),
])
patch_file(UI + "Sources/InChatPrefetchManager.swift", [
    ("in-chat prefetch off", rx(r"(private func update\(\)\s*\{)", "\\1\n        return // lite: prefetch off"), False),
])

if errors:
    sys.exit("[lite] required patches failed: " + ", ".join(errors))
print("[lite] done")
