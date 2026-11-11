import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path
from typing import Iterator

import pygame
import pytest

import graphy


NATIVE = (1920, 1080)


def _write_png(path: Path, size: tuple[int, int], color: tuple[int, int, int], alpha: bool) -> None:
    flags = pygame.SRCALPHA if alpha else 0
    surface = pygame.Surface(size, flags)
    surface.fill((*color, 255) if alpha else color)
    pygame.image.save(surface, str(path))


@pytest.fixture
def asset_root(tmp_path: Path) -> Path:
    """Projektordner mit assets/: icon.png, rot.png (ohne Alpha), sub/gruen.png (mit Alpha)."""
    pygame.init()
    assets = tmp_path / "assets"
    (assets / "sub").mkdir(parents=True)
    _write_png(assets / "icon.png", (4, 4), (0, 0, 255), alpha=False)
    _write_png(assets / "rot.png", (4, 4), (255, 0, 0), alpha=False)
    _write_png(assets / "sub" / "gruen.png", (4, 4), (0, 255, 0), alpha=True)
    (tmp_path / "main.py").write_text("")
    return tmp_path


@pytest.fixture
def window(asset_root: Path) -> Iterator[Path]:
    """graphy.init mit 1:1-Auflösung, damit rx = ry = 1."""
    graphy.init(file=str(asset_root / "main.py"), fps=1000, windowRes=NATIVE, nativeRes=NATIVE, singleSizeOn=True)
    yield asset_root
    _shutdown()


def _shutdown() -> None:
    graphy.running = False
    graphy.renders = []
    graphy.activeInput = None
    graphy.console = None
    graphy.keys.clear()
    graphy.exeKeys.clear()
    graphy.clickEvent = False
    graphy.unClickEvent = False
    graphy.scrollEvent = 0
    pygame.quit()


@pytest.fixture
def shutdown():
    return _shutdown
