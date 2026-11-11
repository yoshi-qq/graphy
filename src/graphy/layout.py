"""Hilfen zur Anordnung von Objekten."""
from __future__ import annotations

import math
from typing import TypeVar

T = TypeVar("T")


def distributeObjects(objects: list[T], aspect_ratio: float) -> list[list[T]]:
    """Verteilt objects zeilenweise auf ein Raster, dessen Breite zu Höhe etwa aspect_ratio entspricht."""
    if aspect_ratio <= 0:
        raise ValueError(f"aspect_ratio muss positiv sein: {aspect_ratio}")
    count = len(objects)
    height = int(math.sqrt(count / aspect_ratio))
    width = int(aspect_ratio * height)
    while width * height < count:
        if width <= height * aspect_ratio:
            width += 1
        else:
            height += 1
    return [row for row in (objects[start:start + width] for start in range(0, count, width or 1)) if row][:height]
