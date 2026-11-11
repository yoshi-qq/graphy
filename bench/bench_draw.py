"""Misst die Zeit pro Bild von graphy.draw() ohne Fenster und ohne FPS-Grenze.

Aufruf: python bench/bench_draw.py
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import statistics
import sys
import tempfile
import time
from pathlib import Path

import pygame

import graphy

FRAMES = 300
WARMUP = 20


def _make_assets(root: Path) -> None:
    pygame.init()
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for index in range(5):
        surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        surface.fill((40 * index, 200, 100, 255))
        pygame.image.save(surface, str(assets / f"kachel{index}.png"))
    (root / "main.py").write_text("")


def _scene() -> None:
    for index in range(300):
        graphy.RenderImage(imageName=f"kachel{index % 5}", x=(index * 37) % 1800, y=(index * 53) % 1000,
                           width=64, height=64, angle=(index % 4) * 15)
    for index in range(60):
        graphy.RenderText(text=f"Zeile {index}", x=20, y=index * 16, size=18, color=(255, 255, 255))
    for index in range(20):
        graphy.RenderTextButton(text=f"Knopf {index}", x=1500, y=index * 50, width=200, height=40)
    graphy.RenderAnimation(imageNames=("kachel0", "kachel1"), x=900, y=500, width=128, height=128, rotation=3)
    graphy.RenderImage(imageName="kachel2", x=600, y=600, width=200, height=120, topStretchMultiplier=0.5)


def _temporary_scene() -> None:
    """Wie Val2d: Figuren werden jedes Bild als temporäre, gedrehte und gespiegelte Bilder neu angelegt."""
    for index in range(40):
        graphy.RenderImage(temporary=True, imageName=f"kachel{index % 5}", x=(index * 47) % 1800,
                           y=(index * 29) % 1000, width=48, height=96, angle=index * 9, flipped=index % 2 == 0)


def run(label: str, single_size: bool, window: tuple[int, int], per_frame: bool = False) -> float:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        _make_assets(root)
        graphy.init(file=str(root / "main.py"), fps=0, singleSizeOn=single_size, windowRes=window)
        _scene()
        times: list[float] = []
        for frame in range(FRAMES + WARMUP):
            start = time.perf_counter()
            if per_frame:
                _temporary_scene()
            graphy.draw()
            if frame >= WARMUP:
                times.append(time.perf_counter() - start)
        pygame.quit()
    median_ms = statistics.median(times) * 1000
    print(f"{label:<34} {median_ms:7.2f} ms/Bild  ({1000 / median_ms:6.0f} FPS)")
    return median_ms


def main() -> None:
    print(f"graphy {graphy.__file__}  Python {sys.version.split()[0]}")
    run("Fenster 1920x1080, singleSize", True, (1920, 1080))
    run("Fenster 960x540, singleSize", True, (960, 540))
    run("Fenster 960x540, skaliert", False, (960, 540))
    run("1920x1080, + 40 temporäre je Bild", True, (1920, 1080), per_frame=True)


if __name__ == "__main__":
    main()
