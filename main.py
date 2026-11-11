"""Mizuyori — точка входа."""

import sys


def main() -> int:
    print("Mizuyori запущен.")
    print(f"Python {sys.version.split()[0]}")
    input("Нажми Enter, чтобы выйти...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
