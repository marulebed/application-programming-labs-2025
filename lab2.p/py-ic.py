#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Лабораторная работа №2:
Загрузка изображений 'bear' по диапазонам дат с помощью icrawler и создание CSV-аннотации.
"""

import argparse
from pathlib import Path
from csv import writer, reader
from typing import Iterable
from icrawler.builtin import GoogleImageCrawler
import sys
from datetime import datetime

IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}


def parse_range(s: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Преобразует 'YYYY-MM-DD:YYYY-MM-DD' в кортеж ((Y, M, D), (Y, M, D))."""
    a, b = s.split(":")
    d1 = datetime.strptime(a, "%Y-%m-%d").date()
    d2 = datetime.strptime(b, "%Y-%m-%d").date()
    if d1 > d2:
        d1, d2 = d2, d1
    return (d1.year, d1.month, d1.day), (d2.year, d2.month, d2.day)


def parse_args() -> argparse.Namespace:
    """Разбор аргументов командной строки."""
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
        "--keyword",
        default="bear",
        help='Ключевое слово (по умолчанию "bear").',
    )
    return ap.parse_args()
    args = ap.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """Проверяет корректность введённых аргументов."""
    if not (50 <= args.per_range <= 1000):
        print(
            "Ошибка: --per-range должен быть в диапазоне [50, 1000].", file=sys.stderr
        )
        sys.exit(2)


def crawl_range(
    keyword: str,
    out_dir: Path,
    date_range: tuple[tuple[int, int, int], tuple[int, int, int]],
    max_num: int,
) -> None:
    """Скачивает изображения для одного диапазона дат в указанную папку."""
    out_dir.mkdir(parents=True, exist_ok=True)
    google = GoogleImageCrawler(storage={"root_dir": str(out_dir)})
    google.crawl(keyword=keyword, filters={"date": date_range}, max_num=max_num)


def collect_pairs(root: Path) -> list[list[str]]:
    """Собирает все изображения в формате [абсолютный путь, относительный путь]."""
    pairs: list[list[str]] = []
    root = root.resolve()
    for fp in root.rglob("*"):
        if fp.is_file() and fp.suffix.lower() in IMG_EXTS:
            abs_path = fp.resolve()
            rel_path = abs_path.relative_to(root)
            pairs.append([str(abs_path), str(rel_path)])
    return pairs


def write_csv(csv_path: Path, pairs: Iterable[Iterable[str]]) -> None:
    """Записывает аннотацию в CSV-файл с разделителем ';'."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as f:
        w = writer(f, delimiter=";")
        for row in pairs:
            w.writerow(list(row))


class PathIterator:
    """Итератор по изображениям из папки или CSV (возвращает [abs, rel])."""

    def __init__(self, source: str, root: str | None = None) -> None:
        self.items: list[list[str]] = []
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

    def __iter__(self) -> "PathIterator":
        """Возвращает сам итератор."""
        self._i = 0
        return self

    def __next__(self) -> list[str]:
        """Возвращает следующую пару [abs, rel] или завершает итерацию."""
        if self._i >= len(self.items):
            raise StopIteration
        val = self.items[self._i]
        self._i += 1
        return val


def run_downloads(args: argparse.Namespace) -> None:
    """Запускает скачивание по всем диапазонам и формирует CSV-аннотацию."""
    out_root = Path(args.out_dir)
    for idx, dr in enumerate(args.ranges):
        subdir = out_root / f"range_{idx}"
        crawl_range(args.keyword, subdir, dr, args.per_range)

    pairs = collect_pairs(out_root)
    write_csv(Path(args.csv), pairs)


def main() -> None:
    """Точка входа: вызывает функции разбора, проверки и скачивания."""
    args = parse_args()
    validate_args(args)
    run_downloads(args)


if __name__ == "__main__":
    main()
