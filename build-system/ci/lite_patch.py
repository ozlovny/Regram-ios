#!/usr/bin/env python3
"""Облегчающие патчи Regram: меньше анимаций, фоновой работы и сети.
Запускается из корня репозитория перед сборкой. Если какой-то патч не применился,
завершается с ошибкой сразу (дёшево), а не после многочасовой сборки."""
import re
import sys
from pathlib import Path

FILE = Path("submodules/TelegramUIPreferences/Sources/MediaAutoDownloadSettings.swift")
MARK = "// REGRAM-LITE patched"

failed = []


def sub_once(text, pattern, repl, what, flags=0):
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    if n != 1:
        failed.append(what)
        print(f"[lite] FAILED: {what}")
        return text
    print(f"[lite] ok: {what}")
    return new


if not FILE.exists():
    sys.exit(f"[lite] file not found: {FILE}")

text = FILE.read_text(encoding="utf-8")
if MARK in text:
    print("[lite] already patched, nothing to do")
    sys.exit(0)

# 1. Энергопотребление: всё тяжёлое выключено по умолчанию, режим энергосбережения всегда включён
m = re.search(r"static let `default`: EnergyUsageSettings = \{.*?\}\(\)", text, re.S)
if not m:
    failed.append("EnergyUsageSettings.default block")
    print("[lite] FAILED: EnergyUsageSettings.default block")
else:
    block = m.group(0)
    for key in ("autoplayVideo", "autoplayGif", "loopStickers", "extendBackgroundWork", "autodownloadInBackground"):
        block, n = re.subn(rf"({key}:\s*)true", r"\1false", block)
        print(f"[lite] {'ok' if n == 1 else 'FAILED'}: energy {key} -> false")
        if n != 1:
            failed.append(key)
    for key in ("loopEmoji", "fullTranslucency"):
        block, n = re.subn(rf"({key}:\s*)isCapable", r"\1false && isCapable", block)
        print(f"[lite] {'ok' if n == 1 else 'FAILED'}: energy {key} -> false")
        if n != 1:
            failed.append(key)
    block, n = re.subn(r"(activationThreshold:\s*)\d+", r"\g<1>100", block)
    print(f"[lite] {'ok' if n == 1 else 'FAILED'}: activationThreshold -> 100")
    if n != 1:
        failed.append("activationThreshold")
    text = text.replace(m.group(0), block, 1)

# 2. Сеть: самые экономные пресеты автозагрузки и без загрузки в фоне
text = sub_once(text, r"(cellular:\s*MediaAutoDownloadConnection\(enabled:\s*true,\s*preset:\s*)\.medium",
                r"\1.low", "cellular preset -> low")
text = sub_once(text, r"(wifi:\s*MediaAutoDownloadConnection\(enabled:\s*true,\s*preset:\s*)\.high",
                r"\1.low", "wifi preset -> low")
text = sub_once(text, r"(downloadInBackground:\s*)true(,\s*energyUsageSettings:)",
                r"\1false\2", "downloadInBackground -> false")

# 3. Сеть: предзагрузка видео выключена
text = sub_once(text, r"return category\.sizeLimit > 2 \* 1024 \* 1024 && category\.predownload",
                "return false", "predownload -> false")

if failed:
    sys.exit("[lite] patches failed: " + ", ".join(failed))

FILE.write_text(MARK + "\n" + text, encoding="utf-8")
print("[lite] done")
