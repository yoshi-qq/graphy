# Changelog

Versionen nach [SemVer](https://semver.org/lang/de/). Datum TT.MM.JJJJ.

## 1.2.0 – 11.11.2026

Schneller, Verhalten unverändert.

### Neu
- `clearCache()` leert die Zwischenspeicher für skalierte und gedrehte Bilder.
- `bench/bench_draw.py` misst die Zeit pro Bild.

### Schneller
- Skalierte, gespiegelte und gedrehte Bilder werden zwischengespeichert (begrenzt auf 4096 Einträge und 16 Mio. Pixel je Speicher). Gleiche Bilder in gleicher Größe kosten nur noch einen Dictionary-Zugriff.
- Drehung um 0° kopiert nicht mehr.
- Trapez-Verzerrung (`topStretchMultiplier`) wird je Objekt zwischengespeichert statt jedes Bild zeilenweise neu gebaut.
- Text liegt im Pixelformat des Fensters vor; Blits sind schneller.
- Skaliertes Fenster (`singleSizeOn=False`) schreibt direkt in die Fensterfläche statt über eine Zwischenfläche.
- Tastenwiederholung ohne einen Thread je Tastendruck.

Messung (ohne Fenster, 300 Bilder, 383 Objekte, Median):

| Szene | 1.1.0 | 1.2.0 |
|---|---|---|
| 1920×1080, singleSize | 10,3–10,9 ms | 5,3–6,5 ms |
| 960×540, singleSize | 3,5–3,8 ms | 1,9–2,2 ms |
| 960×540, skaliert | 10,7–11,2 ms | 6,8 ms |
| 1920×1080 + 40 temporäre je Bild | 11,1–12,5 ms | 6,3–6,6 ms |

## 1.1.0 – 11.11.2026

Vollständig typisiert (`mypy --strict`), bekannte Fehler behoben.

### Behoben
- `hex()` lieferte einen Fehler statt der Farbe.
- Fehlende Sprites ließen das Programm abstürzen; jetzt Platzhalter und Warnung.
- Temporäre Objekte wurden nur teilweise entfernt.
- Tastenwiederholung konnte `draw()` aus einem anderen Thread stören.
- Aktionen als Text liefen über `eval`; jetzt nur `"self.<methode>"`.
- `RenderTextButton` mit eigenem Bild stürzte ab.
- Schieberegler: Startwert und Bereiche, die nicht bei 0 beginnen.
- Eingefangene Maus wurde in die Mitte der Spielfläche statt des Fensters gesetzt.
- Klare Fehler bei Render-Objekten vor `init()`, Animation ohne Bilder, `GameObject` ohne Objekt.
- `init()` ohne `file` sucht Sprites neben dem gestarteten Skript; fehlender Sprite-Ordner ist kein Fehler.
- Dateiendung wird nur am Ende des Namens entfernt.
- Zwischenablage auch außerhalb von Windows.
- `terminal.Console` zeigt einzelne Meldungen formatiert.

## 1.0.0 – 11.11.2026

Erste Fassung als Paket, zusammengeführt aus den Projektkopien (Poker als Basis, Zusätze aus calc).
