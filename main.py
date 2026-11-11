"""Mizuyori — точка входа."""

import sys

# Русский в консоли Windows: печатаем в UTF-8 независимо от кодовой страницы
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def main() -> int:
    print("Mizuyori запущен.")
    print(f"Python {sys.version.split()[0]}: {sys.executable}")
    try:
        input("Нажми Enter, чтобы выйти...")
    except EOFError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
