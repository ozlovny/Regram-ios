#!/usr/bin/env python3
"""Дополнительные патчи Regram (extra v1). Запускается после lite_patch.py."""
import re
import sys
from pathlib import Path

MARK = "// REGRAM-LITE-EXTRA patched"
ANIM_FACTOR = "0.5"  # множитель длительности анимаций Display (1.0 = без изменений, меньше = быстрее)
errors = []


def patch(path, name, pattern, repl, required=False, flags=0):
    p = Path(path)
    if not p.exists():
        print(f"[extra] {'FAILED' if required else 'warn'}: {name} (file missing: {path})")
        if required:
            errors.append(name)
        return
    text = p.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[extra] already patched: {path}")
        return
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    if n != 1:
        print(f"[extra] {'FAILED' if required else 'warn'}: {name}")
        if required:
            errors.append(name)
        return
    p.write_text(MARK + "\n" + new, encoding="utf-8")
    print(f"[extra] ok: {name}")


# 1. Display: общий множитель длительности для анимаций слоёв (переходы экранов, списки, пузыри сообщений)
patch("submodules/Display/Source/UIKitUtils.swift", f"Display animation duration x{ANIM_FACTOR}",
      r"return\s+animationDurationFactorImpl\(\)", f"return animationDurationFactorImpl() * {ANIM_FACTOR}", required=True)

if errors:
    sys.exit("[extra] required patches failed: " + ", ".join(errors))
print("[extra] done")
