#!/usr/bin/env python3
"""Дополнительные патчи Regram (extra v2). Запускается после lite_patch.py."""
import re
import sys
from pathlib import Path

MARK = "// REGRAM-LITE-EXTRA patched"
ANIM_FACTOR = "0.6"  # множитель длительности анимаций Display (1.0 = без изменений, меньше = быстрее)
errors = []
# Условие всегда истинно, но компилятор этого не видит: нет предупреждения «недостижимый код» (здесь оно = ошибка).
EARLY_RETURN = "\\1\n        if CommandLine.arguments.count >= 0 { return } // lite"


def patch_file(path, patches):
    """patches: список (имя, регулярка, замена, обязательный)."""
    p = Path(path)
    if not p.exists():
        for name, _, _, required in patches:
            print(f"[extra] {'FAILED' if required else 'warn'}: {name} (file missing: {path})")
            if required:
                errors.append(name)
        return
    text = p.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[extra] already patched: {path}")
        return
    changed = False
    for name, pattern, repl, required in patches:
        text, n = re.subn(pattern, repl, text, count=1)
        if n == 1:
            changed = True
            print(f"[extra] ok: {name}")
        else:
            print(f"[extra] {'FAILED' if required else 'warn'}: {name}")
            if required:
                errors.append(name)
    if changed:
        p.write_text(MARK + "\n" + text, encoding="utf-8")


# 1. Display: общий множитель длительности для анимаций слоёв (переходы экранов, списки, пузыри сообщений)
patch_file("submodules/Display/Source/UIKitUtils.swift", [
    (f"Display animation duration x{ANIM_FACTOR}", r"return\s+animationDurationFactorImpl\(\)",
     f"return animationDurationFactorImpl() * {ANIM_FACTOR}", True),
])

# 2. iPhone 7 имеет 4 ядра и считался «мощным»: приложение включало тяжёлые эффекты. Считаем устройство слабым.
patch_file("submodules/Display/Source/DeviceMetrics.swift", [
    ("device classified as low-performance", r"(self\.isGraphicallyCapable\s*=\s*)cpuCount >= 4",
     r"\g<1>false && cpuCount >= 4", True),
])

# 3-4. Запуск и постоянная работа
patch_file("submodules/TelegramUI/Sources/AppDelegate.swift", [
    ("launch update check off", r"(private func maybeCheckForUpdates\(\)\s*\{)", EARLY_RETURN, False),
    ("memory timer 0.5s -> 30s",
     r"(Foundation\.Timer\.scheduledTimer\(withTimeInterval:\s*)0\.5(,\s*repeats:\s*true,\s*block:\s*\{\s*_ in\s*let value = getMemoryConsumption\(\))",
     r"\g<1>30.0\g<2>", False),
])

if errors:
    sys.exit("[extra] required patches failed: " + ", ".join(errors))
print("[extra] done")
