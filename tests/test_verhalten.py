import sys
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


def test_hex() -> None:
    assert graphy.hex("#ff8000") == (255, 128, 0)
    assert graphy.hex("00ff10") == (0, 255, 16)
    with pytest.raises(ValueError):
        graphy.hex("#fff")


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
    assert capsys.readouterr().out.splitlines() == ["! |Fehler"]


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

    class SpyFont(original):  # type: ignore[misc, valid-type]
        def __init__(self, font: object, size: int) -> None:
            requested.append(font)
            super().__init__(None, size)

    graphy.init(file=str(asset_root / "main.py"), windowRes=NATIVE, singleSizeOn=True, fontPath="eigene.ttf")
    monkeypatch.setattr(pygame.font, "Font", SpyFont)
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
    assert slider.value == 50
    slider.change(3)
    assert slider.value == 80
    assert slider.sliderPos == pytest.approx(0.6)
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


# --- behobene Fehler ------------------------------------------------------------

def test_missing_sprite_shows_placeholder(window: Path) -> None:
    with pytest.warns(UserWarning, match="fehlt_noch"):
        image = graphy.RenderImage(imageName="fehlt_noch", width=8, height=8)
    graphy.draw()
    assert image.image.get_at((0, 0))[:3] == (255, 0, 255)


def test_missing_sprite_folder_is_empty(tmp_path: Path, shutdown) -> None:
    graphy.init(file=str(tmp_path / "main.py"), windowRes=NATIVE, singleSizeOn=True)
    assert graphy.sprites == {}
    shutdown()


def test_init_without_file_uses_main_script(monkeypatch: pytest.MonkeyPatch, asset_root: Path, shutdown) -> None:
    import types
    fake_main = types.ModuleType("__main__")
    fake_main.__file__ = str(asset_root / "main.py")
    monkeypatch.setitem(sys.modules, "__main__", fake_main)
    graphy.init(windowRes=NATIVE, singleSizeOn=True)
    assert "rot" in graphy.sprites
    shutdown()


def test_sprite_name_only_strips_suffix(asset_root: Path, shutdown) -> None:
    pygame.image.save(pygame.Surface((2, 2)), str(asset_root / "assets" / "png_rahmen.png"))
    graphy.init(file=str(asset_root / "main.py"), windowRes=NATIVE, singleSizeOn=True, spriteExtension="png")
    assert "png_rahmen" in graphy.sprites
    shutdown()


def test_temporary_renders_are_all_removed(window: Path) -> None:
    kept = graphy.RenderImage(imageName="rot")
    for _ in range(3):
        graphy.RenderImage(imageName="rot", temporary=True)
    graphy.draw()
    assert graphy.renders == [kept]


def test_string_action_resolves_method(window: Path) -> None:
    button = graphy.RenderButton(imageName="rot", clickAction="self.hide")
    button.click(True, pygame.BUTTON_LEFT)
    assert button.enabled is False
    with pytest.raises(ValueError):
        graphy.RenderButton(imageName="rot", clickAction="print('x')")


def test_text_button_with_image_and_default_hover(window: Path) -> None:
    button = graphy.RenderTextButton(imageName="rot", text="ok", width=20, height=10)
    assert isinstance(button.activeSurface, pygame.Surface)
    with pytest.raises(ValueError):
        graphy.RenderTextButton(drawType="stern")


def test_animation_needs_images(window: Path) -> None:
    with pytest.raises(ValueError):
        graphy.RenderAnimation()


def test_game_object_needs_render_object() -> None:
    with pytest.raises(ValueError):
        graphy.GameObject()


def test_render_before_init_has_clear_error(shutdown) -> None:
    shutdown()
    graphy.screen = None
    with pytest.raises(RuntimeError, match="init"):
        graphy.RenderText(text="x")


def test_image_update_reloads_sprite(window: Path) -> None:
    image = graphy.RenderImage(imageName="rot", gen=False)
    graphy.sprites["rot"] = (_red((3, 3)), "", False)
    image.update()
    assert image.image.get_size() == (3, 3)


def test_clipboard_paste(window: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    field = graphy.RenderInput(text="", size=20)
    field.setOn(True)
    monkeypatch.setattr(graphy, "getClipboard", lambda: "eingefügt")
    monkeypatch.setattr(pygame.key, "get_mods", lambda: pygame.KMOD_CTRL)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v, unicode="v", mod=pygame.KMOD_CTRL))
    graphy.draw()
    assert field.text == "eingefügt"


def test_layout_rejects_bad_ratio() -> None:
    with pytest.raises(ValueError):
        layout.distributeObjects([1], 0)


# --- Zwischenspeicher ---------------------------------------------------------------

def test_scaled_is_cached_and_matches_transform(window: Path) -> None:
    graphy.clearCache()
    source = _red((8, 4))
    source.set_at((0, 0), (0, 255, 0))
    first = graphy._scaled(source, (16, 8), True, False)
    assert graphy._scaled(source, (16, 8), True, False) is first
    expected = pygame.transform.scale(pygame.transform.flip(source, True, False), (16, 8))
    assert pygame.image.tobytes(first, "RGB") == pygame.image.tobytes(expected, "RGB")


def test_rotated_is_cached_and_zero_is_identity(window: Path) -> None:
    graphy.clearCache()
    source = _red((8, 4))
    assert graphy._rotated(source, 0) is source
    assert graphy._rotated(source, 360) is source
    turned = graphy._rotated(source, 90)
    assert graphy._rotated(source, 90) is turned
    assert turned.get_size() == (4, 8)


def test_cache_respects_pixel_budget(window: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    graphy.clearCache()
    monkeypatch.setattr(graphy, "_CACHE_PIXEL_LIMIT", 1000)
    source = _red((4, 4))
    for size in range(10, 20):
        graphy._scaled(source, (size, size))
    assert sum(w * h for _, s in graphy._scale_cache.values() for w, h in [s.get_size()]) <= 1000
    graphy.clearCache()


def test_key_repeat_after_delay(window: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [100.0]
    monkeypatch.setattr(graphy.time, "monotonic", lambda: clock[0])
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w, unicode="w", mod=0))
    graphy.draw()
    assert pygame.K_w not in graphy.exeKeys
    clock[0] += 0.3
    graphy.draw()
    assert pygame.K_w in graphy.exeKeys
    pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_w, mod=0))
    graphy.draw()
    assert pygame.K_w not in graphy.exeKeys


def test_scaled_window_output_matches(asset_root: Path, shutdown) -> None:
    graphy.init(file=str(asset_root / "main.py"), windowRes=(960, 540), nativeRes=NATIVE, singleSizeOn=False)
    graphy.RenderImage(imageName="rot", x=0, y=0, width=200, height=200)
    graphy.draw()
    assert graphy.realScreen is not None
    assert graphy.realScreen.get_at((50, 50))[:3] == (255, 0, 0)
    assert graphy.realScreen.get_at((150, 150))[:3] == (50, 50, 50)
    shutdown()


def test_window_size_differs_from_resolution(asset_root: Path, shutdown, monkeypatch: pytest.MonkeyPatch) -> None:
    graphy.init(file=str(asset_root / "main.py"), windowRes=(960, 540), nativeRes=NATIVE, singleSizeOn=False)
    graphy.realScreen = pygame.Surface((800, 600))
    graphy.draw()
    shutdown()


# --- Unsichtbares überspringen --------------------------------------------------

@pytest.mark.parametrize("x,y,angle,middle,outside", [
    (50, 50, 0, False, False),
    (-10, 50, 0, False, True),       # genau links daneben
    (-9, 50, 0, False, False),       # ragt 1 px hinein
    (100, 50, 0, False, True),
    (50, 100, 0, False, True),
    (104, 50, 0, True, False),       # Mitte knapp rechts, Hälfte ragt hinein
    (105, 50, 0, True, True),
    (-12, 50, 45, False, False),     # gedreht ragt die Ecke hinein
    (-30, 50, 45, False, True),
])
def test_outside_detection(window: Path, x: float, y: float, angle: float, middle: bool, outside: bool) -> None:
    target = pygame.Surface((100, 100))
    image = graphy.RenderImage(surface=target, imageName=_red(), x=x, y=y, width=10, height=10, angle=angle,
                               middle=middle, gen=False)
    assert image._outside() is outside


def test_offscreen_image_is_not_scaled(window: Path) -> None:
    graphy.clearCache()
    target = pygame.Surface((100, 100))
    image = graphy.RenderImage(surface=target, imageName=_red(), x=500, y=500, width=30, height=30, gen=False)
    image.draw()
    assert len(graphy._scale_cache) == 0
    image.x, image.y = 10, 10
    image.draw()
    assert len(graphy._scale_cache) == 1
    assert target.get_at((20, 20))[:3] == (255, 0, 0)
    graphy.clearCache()


def test_offscreen_animation_still_advances(window: Path) -> None:
    target = pygame.Surface((100, 100))
    animation = graphy.RenderAnimation(surface=target, imageNames=("rot", "rot"), x=500, y=500, width=10,
                                       height=10, gen=False)
    animation.draw()
    assert animation.frame == 1
