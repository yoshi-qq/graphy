# graphy

Kleine Render-Schicht über pygame: Fenster, Sprites, Knöpfe, Text, Eingabefelder, Schieberegler, Debug-Konsole.

## Installation

graphy nutzt [pygame-ce](https://pyga.me), die gepflegte Abspaltung von pygame (`import pygame` bleibt gleich). Ist das alte pygame installiert, vorher entfernen:

```bash
pip uninstall pygame
```

```bash
pip install "graphy @ git+https://github.com/yoshi-qq/graphy.git"
```

Zum Mitentwickeln:

```bash
pip install -e ".[test]"
```

## Benutzung

```python
import graphy as g

g.init(file=__file__, fps=60, fontPath="font/fixed_sys.ttf", windowName="Spiel")
g.RenderText(text="Hallo", x=g.middle[0], y=g.middle[1], middle=True, size=40)
while g.running:
    if g.draw() == "quit":
        break
```

Sprites werden aus `spriteFolder` (Vorgabe `assets`, relativ zu `file`) geladen und über ihren Dateinamen ohne Endung angesprochen.

## Module

| Modul | Inhalt |
|---|---|
| `graphy` | Fenster, Zeichenschleife, Render-Klassen |
| `graphy.terminal` | `Console`: gebündelte Fehlermeldungen im Terminal (heißt nicht `graphy.console`, weil `graphy.console` die Debug-Konsole im Fenster ist) |
| `graphy.layout` | `distributeObjects`: Objekte in ein Raster verteilen |

## Herkunft

Zusammengeführt aus den Kopien in val2d, Poker, bruno, magico, calc und Game/graphics. Grundlage ist die Poker-Fassung; Schieberegler, Debug-Konsole, `scroll`/`unclick` und die Farbkonstanten stammen aus calc.

## Tests

```bash
pytest
```

Die Tests laufen ohne Fenster (`SDL_VIDEODRIVER=dummy`).
