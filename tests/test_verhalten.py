from pathlib import Path

import pygame
import pytest

import graphy
from graphy import terminal as console_module
from graphy import layout

from conftest import NATIVE


def _post_click(button: int = 1) -> None:
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=(0, 0)))


# --- reine Hilfsfunktionen ---------------------------------------------------

def test_min_max() -> None:
    assert graphy.minMax(5, 0, 3) == 3
    assert graphy.minMax(-1, 0, 3) == 0
    assert graphy.minMax(2, 0, 3) == 2


def test_get_last_children_flattens() -> None:
    assert graphy.getLastChildren([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]
    assert graphy.getLastChildren(7) == [7]


def test_rotate_point_around_center() -> None:
    x, y = graphy.rotate_point_around_center((1, 0), (0, 0), 90)
    assert x == pytest.approx(0, abs=1e-9)
    assert y == pytest.approx(-1)


@pytest.mark.parametrize("point,angle,middle,expected", [
    ((15, 15), 0, False, True),
    ((35, 15), 0, False, False),
    ((10, 10), 0, True, True),
    ((25, 12), 45, False, False),
])
def test_point_in_rect(point: tuple[float, float], angle: float, middle: bool, expected: bool) -> None:
    assert graphy.pointInRect(point, (10, 10, 20, 10), angle, middle) is expected


def test_rect_overlap() -> None:
    assert graphy.rectOverlap((0, 0, 10, 10), (5, 5, 10, 10)) is True
    assert graphy.rectOverlap((0, 0, 10, 10), (20, 20, 5, 5)) is False
    assert graphy.rectOverlap((0, 0, 0, 10), (0, 0, 10, 10)) is False


@pytest.mark.xfail(strict=True, raises=TypeError, reason="Fehler aus allen Kopien übernommen: tuple() mit drei Argumenten")
def test_hex() -> None:
    assert graphy.hex("#ff8000") == (255, 128, 0)


def test_classes_is_noop() -> None:
    assert graphy.classes() is None


def test_colors() -> None:
    assert graphy.COLORS == [graphy.RED, graphy.GREEN, graphy.BLUE, graphy.WHITE, graphy.BLACK]
    assert graphy.HD == (1920, 1080)


def test_distribute_objects() -> None:
    assert layout.distributeObjects(list(range(5)), 2.0) == [[0, 1, 2], [3, 4]]
    assert layout.distributeObjects([], 1.0) == []


def test_console_counts_repeats(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(console_module.os, "system", lambda command: 0)
    log = console_module.Console()
    log.log(2, "!", "Fehler")
    log.log(2, "!", "Fehler")
    assert log.messages["Fehler"][1] == 2
    assert log.messages["Fehler"][0] == "! |Fehler"
    assert "Fehler" in capsys.readouterr().out


# --- Fenster und Sprites ------------------------------------------------------

def test_draw_requires_init(shutdown) -> None:
    shutdown()
    with pytest.raises(Exception, match="not initialized"):
        graphy.draw()


def test_init_sets_up_window(window: Path) -> None:
    assert graphy.running is True
    assert graphy.getScreen().get_size() == NATIVE
    assert graphy.middle == (960, 540)
    assert graphy.defaultFont == "Arial"
    assert graphy.console is None


def test_scan_directory_names(window: Path) -> None:
    assert set(graphy.sprites) == {"icon", "rot", "gruen"}
    image, folder, has_alpha = graphy.sprites["gruen"]
    assert folder == "/sub"
    assert has_alpha is True
    assert graphy.sprites["rot"][2] is False
    assert image.get_size() == (16, 16)


def test_scan_directory_strips_trailing_dot(asset_root: Path, shutdown) -> None:
    graphy.init(file=str(asset_root / "main.py"), windowRes=NATIVE, singleSizeOn=True, spriteExtension="png")
    assert "rot" in graphy.sprites
    assert "rot." not in graphy.sprites
    shutdown()


def test_draw_return_values(window: Path) -> None:
    assert graphy.draw() is True
    _post_click()
    assert graphy.draw() is False
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    assert graphy.draw() == "quit"
    assert graphy.running is False


def test_draw_exposes_events_and_scroll(window: Path) -> None:
    seen: list[int] = []
    graphy.preDraw = lambda: seen.append(graphy.scrollEvent)
    try:
        _post_click(4)
        graphy.draw()
        assert any(e.type == pygame.MOUSEBUTTONDOWN for e in graphy.events)
        assert seen == [1]
        assert graphy.scrollEvent == 0
        assert graphy.mouseButton == 4
    finally:
        graphy.preDraw = lambda: None


def test_click_unclick_scroll_flags() -> None:
    graphy.click(3)
    graphy.unclick()
    graphy.scroll(-1)
    assert (graphy.clickEvent, graphy.mouseButton, graphy.unClickEvent, graphy.scrollEvent) == (True, 3, True, -1)
    graphy.clickEvent = graphy.unClickEvent = False
    graphy.scrollEvent = 0


def test_held_keys(window: Path) -> None:
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="a", mod=0))
    graphy.draw()
    assert pygame.K_a in graphy.getHeldKeys()
    pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_a, mod=0))
    graphy.draw()
    assert pygame.K_a not in graphy.getHeldKeys()


# --- Zeichnen -----------------------------------------------------------------

def _red(size: tuple[int, int] = (10, 10)) -> pygame.Surface:
    surface = pygame.Surface(size)
    surface.fill((255, 0, 0))
    return surface


def test_draw_normal_positions(window: Path) -> None:
    target = pygame.Surface((100, 100))
    graphy.drawNormal(target, _red(), 20, 30, 10, 10)
    assert target.get_at((25, 35))[:3] == (255, 0, 0)
    assert target.get_at((15, 35))[:3] == (0, 0, 0)


@pytest.mark.parametrize("middle,inside,outside", [
    (False, (25, 35), (15, 25)),
    (True, (20, 30), (27, 37)),
])
def test_draw_rotated_positions(window: Path, middle: bool, inside: tuple[int, int], outside: tuple[int, int]) -> None:
    target = pygame.Surface((100, 100))
    graphy.drawRotated(target, _red(), 20, 30, 0, 10, 10, middle=middle)
    assert target.get_at(inside)[:3] == (255, 0, 0)
    assert target.get_at(outside)[:3] == (0, 0, 0)


def test_draw_rotated_scaled_resolution(asset_root: Path, shutdown) -> None:
    graphy.init(file=str(asset_root / "main.py"), windowRes=(960, 540), nativeRes=NATIVE, singleSizeOn=True)
    target = pygame.Surface((200, 200), pygame.SRCALPHA)
    graphy.drawRotated(target, _red(), 100, 100, 0, 20, 20)
    bounds = target.get_bounding_rect()
    assert (bounds.x, bounds.y, bounds.width, bounds.height) == (50, 50, 10, 10)
    shutdown()


# --- Render-Klassen -----------------------------------------------------------

def test_render_image_registers_and_offsets(window: Path) -> None:
    image = graphy.RenderImage(imageName="rot", x=5, y=6, width=10, height=10)
    assert image in graphy.renders
    assert image.strName == "rot"
    image.offset(x=1, y=2, size=3, priority=4)
    assert (image.xOffset, image.yOffset, image.sizeMulti, image.priorityOffset) == (1, 2, 3, 4)
    assert image.getRect() == (5, 6, 10, 10)
    image.hide()
    assert image.enabled is False
    image.remove()
    assert image not in graphy.renders


def test_render_image_without_sprite_is_red(window: Path) -> None:
    image = graphy.RenderImage(width=4, height=4, gen=False)
    assert image.image.get_at((0, 0))[:3] == (255, 0, 0)


def test_render_image_draws(window: Path) -> None:
    graphy.RenderImage(imageName="rot", x=100, y=100, width=10, height=10)
    graphy.draw()
    assert graphy.getScreen().get_at((105, 105))[:3] == (255, 0, 0)


def test_natural_y_flips(asset_root: Path, shutdown) -> None:
    graphy.init(file=str(asset_root / "main.py"), windowRes=NATIVE, singleSizeOn=True, naturalY=True)
    assert graphy.RenderObject(y=0).y == 1080
    shutdown()


def test_animation_rotation(window: Path) -> None:
    single = graphy.RenderAnimation(imageNames=("rot", "icon"), rotation=2, gen=False)
    single.draw()
    assert single.angle == 2
    stepped = graphy.RenderAnimation(imageNames=("rot", "icon"), rotation=(1, 5), slowdown=1, gen=False)
    stepped.draw()
    stepped.draw()
    assert stepped.angle == 6


def test_button_dispatches_by_mouse_button(window: Path) -> None:
    calls: list[str] = []
    button = graphy.RenderButton(
        imageName="rot", x=0, y=0, width=50, height=50,
        clickAction=lambda tag: calls.append(tag), arguments=("links",),
        rightClickAction=lambda tag: calls.append(tag), rightArguments=("rechts",),
        middleClickAction=lambda tag: calls.append(tag), middleArguments=("mitte",),
    )
    for mouse_button in (pygame.BUTTON_LEFT, pygame.BUTTON_RIGHT, pygame.BUTTON_MIDDLE):
        button.click(True, mouse_button)
    assert calls == ["links", "rechts", "mitte"]


def test_button_hover_swaps_image(window: Path) -> None:
    hovered: list[bool] = []
    button = graphy.RenderButton(imageName="rot", hoverImageName="icon", hoverAction=lambda: hovered.append(True),
                                 unHoverAction=lambda: hovered.append(False))
    button.hover(True)
    assert button.image is graphy.sprites["icon"][0]
    button.hover(False)
    assert button.image is graphy.sprites["rot"][0]
    assert hovered == [True, False]


def test_text_uses_font_from_init(asset_root: Path, shutdown, monkeypatch: pytest.MonkeyPatch) -> None:
    requested: list[object] = []
    original = pygame.font.Font

    def spy(font, size):
        requested.append(font)
        return original(None, size)

    graphy.init(file=str(asset_root / "main.py"), windowRes=NATIVE, singleSizeOn=True, fontPath="eigene.ttf")
    monkeypatch.setattr(pygame.font, "Font", spy)
    graphy.RenderText(text="a", gen=False)
    graphy.RenderText(text="b", font="andere.ttf", gen=False)
    assert requested == ["eigene.ttf", "andere.ttf"]
    shutdown()


def test_text_update(window: Path) -> None:
    text = graphy.RenderText(text="a", size=20, strName="titel")
    assert text.strName == "titel"
    narrow = text.width
    text.updateText("aaaaaa")
    assert text.width > narrow
    assert graphy.RenderText(text="ohne", gen=False).strName == "ohne"


def test_text_button_builds_surfaces(window: Path) -> None:
    button = graphy.RenderTextButton(text="ok", width=40, height=20, color=(0, 0, 0), activeColor=(10, 10, 10))
    assert button.renderSurface.get_size() == (40, 20)
    assert button.activeSurface.get_at((10, 10))[:3] == (10, 10, 10)
    assert button.strName == "textButton"


def test_input_receives_typing(window: Path) -> None:
    field = graphy.RenderInput(text="", x=0, y=0, size=20)
    field.setOn(True)
    assert graphy.activeInput is field
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h, unicode="h", mod=0))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i, unicode="i", mod=0))
    graphy.draw()
    graphy.keyPress(pygame.K_SPACE)
    assert field.text == "hi "
    graphy.keyPress(pygame.K_BACKSPACE)
    assert field.text == "hi"
    field.setOn(False)
    assert graphy.activeInput is None


def test_slider_changes_value(window: Path) -> None:
    values: list[float] = []
    slider = graphy.RenderSlider(step=10, range=(0, 100), imageName="rot", sliderImageName="icon",
                                 width=200, height=20, updateAction=values.append)
    assert slider in graphy.renders
    slider.change(3)
    assert slider.value == pytest.approx(30.5)
    slider.change(100)
    assert slider.value == 100
    assert values[-1] == 100


def test_debug_console(asset_root: Path, shutdown) -> None:
    graphy.init(file=str(asset_root / "main.py"), windowRes=NATIVE, singleSizeOn=True, debugConsole=True)
    graphy.debug("hallo", (1, 2, 3))
    assert len(graphy.console.history) == 1
    assert graphy.console.history[0].text == "hallo"
    graphy.draw()
    assert graphy.console.height == graphy.console.size
    shutdown()


def test_debug_without_console(window: Path) -> None:
    with pytest.raises(RuntimeError):
        graphy.debug("x")


def test_game_object_syncs(window: Path) -> None:
    image = graphy.RenderImage(imageName="rot", gen=False)
    game_object = graphy.GameObject(strName="spieler", x=3, y=4, renderObject=image)
    game_object.x = 9
    game_object.update()
    assert (image.x, image.y, image.strName) == (9, 4, "spieler")
