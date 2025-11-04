#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для загрузки изображений по ключевому слову "bear" с помощью icrawler.
Позволяет пользователю задать несколько диапазонов дат и количество изображений для каждого диапазона.
Создаёт CSV-аннотацию с абсолютными и относительными путями к скачанным изображениям.
"""

import argparse
from pathlib import Path
from csv import writer, reader
from icrawler.builtin import GoogleImageCrawler
from datetime import datetime
import sys

IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}


def parse_range(s: str):
    """
    Разбирает строку диапазона дат формата 'YYYY-MM-DD:YYYY-MM-DD'.
    """
    try:
        a, b = s.split(":")
        d1 = datetime.strptime(a, "%Y-%m-%d").date()
        d2 = datetime.strptime(b, "%Y-%m-%d").date()
        if d1 > d2:
            d1, d2 = d2, d1
        return (d1.year, d1.month, d1.day), (d2.year, d2.month, d2.day)
    except Exception:
        raise argparse.ArgumentTypeError(
            f"Неверный формат диапазона: {s}. Ожидается YYYY-MM-DD:YYYY-MM-DD"
        )


class PathIterator:
    """
    Итератор по путям к изображениям.

    Может работать в двух режимах:
      1. Если передан путь к папке — рекурсивно собирает все изображения.
      2. Если передан путь к CSV-файлу — читает пары путей (абсолютный;относительный).
    """

    def __init__(self, source: str, root: str | None = None):
        self.items = []
        p = Path(source)
        if p.is_file() and p.suffix.lower() == ".csv":
            with p.open("r", newline="") as f:
                r = reader(f, delimiter=";")
                for row in r:
                    if len(row) >= 2:
                        self.items.append([row[0], row[1]])
        else:
            base = Path(root) if root else p
            base = base.resolve()
            for fp in p.rglob("*"):
                if fp.is_file() and fp.suffix.lower() in IMG_EXTS:
                    abs_path = fp.resolve()
                    rel_path = abs_path.relative_to(base)
                    self.items.append([str(abs_path), str(rel_path)])
        self._i = 0

    def __iter__(self):
        """Возвращает итератор (самого себя)."""
        self._i = 0
        return self

    def __next__(self):
        """Возвращает следующий элемент итерации или вызывает StopIteration."""
        if self._i >= len(self.items):
            raise StopIteration
        val = self.items[self._i]
        self._i += 1
        return val


def crawl_range(keyword: str, out_dir: Path, date_range, max_num: int):
    """
    Загружает изображения из Google Images по заданному диапазону дат.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    google = GoogleImageCrawler(storage={"root_dir": str(out_dir)})
    google.crawl(
        keyword=keyword,
        filters={"date": date_range},
        max_num=max_num,
    )


def write_csv(csv_path: Path, pairs: list[list[str]]):
    """
    Записывает список пар [абсолютный путь, относительный путь] в CSV-файл.
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as f:
        w = writer(f, delimiter=";")
        for a, r in pairs:
            w.writerow([a, r])


def collect_pairs(root: Path) -> list[list[str]]:
    """
    Рекурсивно собирает все файлы изображений в папке и формирует список путей.
    """
    pairs = []
    root = root.resolve()
    for fp in root.rglob("*"):
        if fp.is_file() and fp.suffix.lower() in IMG_EXTS:
            abs_path = fp.resolve()
            rel_path = abs_path.relative_to(root)
            pairs.append([str(abs_path), str(rel_path)])
    return pairs


def main():
    """
    Парсит аргументы командной строки, скачивает изображения и создаёт аннотацию.
    """
    ap = argparse.ArgumentParser(
        description="Скачать изображения 'bear' по диапазонам дат и создать CSV-аннотацию."
    )
    ap.add_argument(
        "--out-dir", required=True, help="Папка для сохранения (корень датасета)."
    )
    ap.add_argument("--csv", required=True, help="Путь к итоговому CSV (abs;rel).")
    ap.add_argument(
        "--range",
        dest="ranges",
        action="append",
        type=parse_range,
        required=True,
        help="Диапазон дат YYYY-MM-DD:YYYY-MM-DD. Можно указывать несколько флагов --range.",
    )
    ap.add_argument(
        "--per-range",
        type=int,
        required=True,
        help="Сколько изображений скачивать на КАЖДЫЙ диапазон (одинаково для всех). 50..1000.",
    )
    ap.add_argument(
        "--keyword", default="bear", help='Ключевое слово (по умолчанию "bear").'
    )

    args = ap.parse_args()

    if not (50 <= args.per_range <= 1000):
        print(
            "Ошибка: --per-range должен быть в диапазоне [50, 1000].", file=sys.stderr
        )
        sys.exit(2)

    out_root = Path(args.out_dir)

    for idx, dr in enumerate(args.ranges):
        subdir = out_root / f"range_{idx}"
        crawl_range(args.keyword, subdir, dr, args.per_range)

    pairs = collect_pairs(out_root)
    write_csv(Path(args.csv), pairs)


if __name__ == "__main__":
    main()
