"""graphy: kleine Render-Schicht über pygame.

Fenster, Sprites, Zeichenschleife und Render-Klassen (Bild, Animation, Knopf, Text,
Eingabefeld, Schieberegler, Debug-Konsole). Der Zustand liegt bewusst auf Modulebene,
damit Projekte ihn wie bisher über ``graphy.screen``, ``graphy.running`` usw. lesen können.

Koordinaten der Render-Objekte sind in der nativen Auflösung (``nativeRes``) angegeben;
``rx`` und ``ry`` rechnen sie auf das Fenster um.
"""
from __future__ import annotations

import math
import os
import sys
import threading
import time
import warnings
from collections import deque
from typing import Any, Callable, Literal, Optional, TextIO, TypeVarTuple, Union

import pygame
from pygame.locals import DOUBLEBUF, FULLSCREEN, HWSURFACE
from screeninfo import get_monitors

T = TypeVarTuple("T")
T2 = TypeVarTuple("T2")
T3 = TypeVarTuple("T3")
T4 = TypeVarTuple("T4")

Color = tuple[int, int, int]
Resolution = tuple[int, int]
Point2 = tuple[float, float]
Rect4 = tuple[float, float, float, float]
FontSpec = Union[None, str, pygame.font.Font]
ImageSpec = Union[None, str, pygame.Surface]
Action = Union[Callable[..., Any], str, Literal[False], None]
DrawResult = Union[bool, Literal["quit"]]

HD: Resolution = (1920, 1080)
QHD: Resolution = (2560, 1440)
FOUR_K: Resolution = (3840, 2160)

RED: Color = (255, 0, 0)
GREEN: Color = (0, 255, 0)
BLUE: Color = (0, 0, 255)
WHITE: Color = (255, 255, 255)
BLACK: Color = (0, 0, 0)
COLORS: list[Color] = [RED, GREEN, BLUE, WHITE, BLACK]

_MISSING_SPRITE_COLOR: Color = (255, 0, 255)
_BACKGROUND: Color = (50, 50, 50)
_KEY_REPEAT_DELAY = 0.25
_SPRITE_PRESCALE = 4

# --- Zustand -----------------------------------------------------------------

activeInput: Optional[RenderInput] = None
running = False
clickEvent = False
unClickEvent = False
scrollEvent = 0
events: list[pygame.event.Event] = []
console: Optional[RenderConsole] = None
mouseButton = 1
defaultFont: Optional[str] = None
sprites: dict[str, tuple[pygame.Surface, str, bool]] = {}
keys: set[int] = set()
exeKeys: set[int] = set()
middle: Point2 = (0, 0)
displayResolution: Resolution = (0, 0)
nativeResolution: Resolution = HD
natY = False
mousePos: tuple[int, int] = (0, 0)
mouseMovement: tuple[int, int] = (0, 0)
cursorCaptured = False
tabbedIn = False
root = os.getcwd()
rx = 1.0
ry = 1.0
xMultiplier = 1.0
yMultiplier = 1.0
singleSize = False
FPS = 30
renders: list[RenderObject] = []
screen: Optional[pygame.Surface] = None
realScreen: Optional[pygame.Surface] = None
clock: Optional[pygame.time.Clock] = None
_keys_lock = threading.Lock()
_missing_sprites_warned: set[str] = set()


def getClipboard() -> str:
    """Text aus der Zwischenablage; vor paperclipInit() immer leer."""
    return ""


# --- Einrichtung -------------------------------------------------------------

def _main_file() -> str:
    main = sys.modules.get("__main__")
    main_file = getattr(main, "__file__", None)
    if isinstance(main_file, str):
        return main_file
    return os.path.join(os.getcwd(), "main.py")


def preload(file: str, nativeRes: Resolution = (1920, 1080), scale: float = 1,
            windowRes: Union[Literal[False], Resolution] = False) -> None:
    global root, displayResolution, nativeResolution, middle, rx, ry, xMultiplier, yMultiplier
    root = os.path.dirname(os.path.abspath(file))
    nativeResolution = nativeRes
    middle = (nativeResolution[0] / 2, nativeResolution[1] / 2)
    displayResolution = nativeResolution
    if windowRes is False:
        for monitor in get_monitors():
            if monitor.is_primary:
                displayResolution = (round(monitor.width * scale), round(monitor.height * scale))
                break
    else:
        displayResolution = (int(windowRes[0]), int(windowRes[1]))
    xMultiplier = displayResolution[0] / nativeResolution[0]
    yMultiplier = displayResolution[1] / nativeResolution[1]
    if singleSize:
        rx, ry = xMultiplier, yMultiplier
    else:
        rx, ry = 1.0, 1.0


def paperclipInit() -> None:
    """Richtet getClipboard() ein: unter Windows über die Win32-API, sonst über pygame.scrap."""
    global getClipboard
    if sys.platform == "win32":
        getClipboard = _windows_clipboard_reader()
    else:
        getClipboard = _pygame_clipboard


def _windows_clipboard_reader() -> Callable[[], str]:
    import ctypes
    from ctypes.wintypes import HANDLE, HGLOBAL, HWND, LPVOID, UINT

    windll = getattr(ctypes, "windll")
    open_clipboard = windll.user32.OpenClipboard
    open_clipboard.argtypes = (HWND,)
    open_clipboard.restype = ctypes.c_bool
    close_clipboard = windll.user32.CloseClipboard
    get_clipboard_data = windll.user32.GetClipboardData
    get_clipboard_data.argtypes = (UINT,)
    get_clipboard_data.restype = HANDLE
    global_lock = windll.kernel32.GlobalLock
    global_lock.argtypes = (HGLOBAL,)
    global_lock.restype = LPVOID
    global_unlock = windll.kernel32.GlobalUnlock
    global_unlock.argtypes = (HGLOBAL,)
    cf_unicodetext = 13

    def read() -> str:
        text = ""
        if open_clipboard(None):
            try:
                handle = get_clipboard_data(cf_unicodetext)
                if handle:
                    pointer = global_lock(handle)
                    if pointer:
                        text = ctypes.c_wchar_p(pointer).value or ""
                        global_unlock(handle)
            finally:
                close_clipboard()
        return text

    return read


def _pygame_clipboard() -> str:
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        data = pygame.scrap.get(pygame.SCRAP_TEXT)
    except pygame.error:
        return ""
    if not data:
        return ""
    return data.decode("utf-8", errors="ignore").rstrip("\x00")


def init(file: Union[None, str] = None, fps: int = 30, fontPath: Optional[str] = "Arial", fullscreen: bool = False,
         captureCursor: bool = False, naturalY: bool = False, singleSizeOn: bool = False,
         windowName: str = "GRAPHY!", spriteFolder: str = "assets", spriteExtension: str = ".png",
         scale: float = 1, nativeRes: Resolution = (1920, 1080), windowIcon: str = "icon",
         windowRes: Union[Literal[False], Resolution] = False, debugConsole: bool = False,
         copyToConsole: bool = False) -> None:
    """Öffnet das Fenster und lädt die Sprites.

    file bestimmt den Projektordner, relativ zu dem spriteFolder gesucht wird.
    Ohne file gilt das gestartete Hauptskript.
    """
    global natY, sprites, screen, realScreen, renders, clock, nativeResolution, singleSize, running
    global defaultFont, FPS, cursorCaptured, console, activeInput
    if file is None:
        file = _main_file()
    FPS = fps
    cursorCaptured = captureCursor
    natY = naturalY
    nativeResolution = nativeRes
    singleSize = singleSizeOn
    defaultFont = fontPath
    preload(file, nativeResolution, scale, windowRes)
    paperclipInit()
    pygame.init()
    pygame.display.set_caption(windowName)
    flags = HWSURFACE | DOUBLEBUF | (FULLSCREEN if fullscreen else 0)
    if not singleSize:
        screen = pygame.Surface(nativeResolution, flags)
        realScreen = pygame.display.set_mode(displayResolution, flags)
    else:
        screen = pygame.display.set_mode(displayResolution, flags)
        realScreen = None
    renders = []
    activeInput = None
    console = None
    sprites = {}
    _missing_sprites_warned.clear()
    scanDirectory(os.path.join(root, spriteFolder), spriteExtension)
    if windowIcon in sprites:
        pygame.display.set_icon(sprites[windowIcon][0])
    clock = pygame.time.Clock()
    if debugConsole:
        console = RenderConsole(priority=10)
        if copyToConsole:
            sys.stdout = DummyConsole()
    running = True


def classes() -> None:
    """Früher legte classes() die Render-Klassen an; sie stehen jetzt beim Import bereit."""
    return None


def _sprite_name(file: str, extension: str) -> str:
    name = file[: -len(extension)] if extension and file.endswith(extension) else file
    return name.rstrip(".")


def scanDirectory(directory: str, extension: str = ".png", extra: str = "") -> None:
    """Lädt alle Bilder mit dieser Endung, auch aus Unterordnern. Ein fehlender Ordner ist leer."""
    if not os.path.isdir(directory):
        return
    for file in sorted(os.listdir(directory)):
        path = os.path.join(directory, file)
        if os.path.isdir(path):
            scanDirectory(path, extension, f"{extra}/{file}")
        elif file.endswith(extension):
            image = pygame.image.load(path)
            has_alpha = image.get_alpha() is not None
            image = image.convert_alpha() if has_alpha else image.convert()
            size = (round(image.get_width() * rx * _SPRITE_PRESCALE), round(image.get_height() * ry * _SPRITE_PRESCALE))
            sprites[_sprite_name(file, extension)] = (pygame.transform.scale(image, size), extra, has_alpha)


def getScreen() -> pygame.Surface:
    if screen is None:
        raise RuntimeError("graphy.init() wurde noch nicht aufgerufen")
    return screen


def _missing_sprite(name: str, size: Point2 = (10, 10)) -> pygame.Surface:
    if name not in _missing_sprites_warned:
        _missing_sprites_warned.add(name)
        warnings.warn(f"graphy: Sprite {name!r} nicht gefunden, Platzhalter wird gezeigt", stacklevel=3)
    placeholder = pygame.Surface((max(1, round(size[0])), max(1, round(size[1]))))
    placeholder.fill(_MISSING_SPRITE_COLOR)
    return placeholder


def _resolve_image(image: Union[str, pygame.Surface], size: Point2 = (10, 10)) -> pygame.Surface:
    if isinstance(image, pygame.Surface):
        return image
    if image in sprites:
        return sprites[image][0]
    return _missing_sprite(image, size)


# --- Zeichnen ----------------------------------------------------------------

def drawNormal(surface: pygame.Surface, img: pygame.Surface, x: float = 0, y: float = 0, width: float = 1,
               height: float = 1, middle: bool = False) -> None:
    left, top = round(x * rx), round(y * ry)
    size = (max(0, round(width * rx)), max(0, round(height * ry)))
    if abs(img.get_width() - size[0]) > 1 or abs(img.get_height() - size[1]) > 1:
        img = pygame.transform.scale(img, size)
    if middle:
        surface.blit(img, (left - img.get_width() / 2, top - img.get_height() / 2))
    else:
        surface.blit(img, (left, top))


def drawRotated(surface: pygame.Surface, img: pygame.Surface, x: float = 0, y: float = 0, angle: float = 0,
                width: float = 1, height: float = 1, middle: bool = False, flipped: bool = False,
                stretch: float = 1) -> None:
    """Zeichnet img gedreht um seine Mitte. Ohne middle sind x, y die linke obere Ecke."""
    w, h = max(0, round(width * rx * stretch)), max(0, round(height * ry))
    img = pygame.transform.scale(img, (w, h))
    if flipped:
        img = pygame.transform.flip(img, False, True)
    rotated = pygame.transform.rotate(img, -angle)
    pivot = (x * rx, y * ry) if middle else (x * rx + w / 2, y * ry + h / 2)
    surface.blit(rotated, rotated.get_rect(center=(round(pivot[0]), round(pivot[1]))).topleft)


# --- Eingabe -----------------------------------------------------------------

def getMouse() -> Point2:
    """Mausposition in nativen Koordinaten."""
    x, y = pygame.mouse.get_pos()
    return (x / xMultiplier, y / yMultiplier)


def getHeldKeys() -> set[int]:
    """Gedrückte Tasten und Maustasten, vergleichbar mit pygame.K_* und pygame.BUTTON_*."""
    return keys


def getMousePosition() -> tuple[int, int]:
    """Letzte Mausposition aus MOUSEMOTION, in Fensterkoordinaten."""
    return mousePos


def getMouseMovement() -> tuple[int, int]:
    """Mausbewegung seit dem letzten draw(), in Fensterkoordinaten."""
    return mouseMovement


def click(button: int = 1) -> None:
    global clickEvent, mouseButton
    clickEvent = True
    mouseButton = button


def unclick() -> None:
    global unClickEvent
    unClickEvent = True


def scroll(direction: int) -> None:
    global scrollEvent
    scrollEvent = direction


def minMax(value: float, min: float, max: float) -> float:
    return max if value > max else min if value < min else value


def keyPress(key: int) -> None:
    if activeInput is None:
        return
    if key == pygame.K_SPACE:
        activeInput.text += " "
        activeInput.update()
    elif key == pygame.K_BACKSPACE:
        activeInput.text = activeInput.text[:-1]
        activeInput.update()


def pressDelay(key: int, delay: float = _KEY_REPEAT_DELAY) -> None:
    """Nach delay Sekunden wiederholt sich eine noch gedrückte Taste bei jedem draw()."""
    time.sleep(delay)
    with _keys_lock:
        if key in keys:
            exeKeys.add(key)


def setMouseCapture(capture: bool) -> None:
    global cursorCaptured
    cursorCaptured = capture
    pygame.event.set_grab(capture)
    pygame.mouse.set_visible(not capture)


def preDraw() -> None:
    """Zum Ersetzen: läuft in draw() nach dem Leeren und vor dem Zeichnen."""
    return None


def postDraw() -> None:
    """Zum Ersetzen: läuft in draw() nach dem Zeichnen und vor dem Anzeigen."""
    return None


def _handle_event(event: pygame.event.Event) -> bool:
    """Verarbeitet ein Ereignis. Gibt False zurück, wenn das Fenster geschlossen wurde."""
    global running, mousePos, mouseMovement, tabbedIn
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.ACTIVEEVENT:
        if event.gain == 1 and cursorCaptured:
            pygame.event.set_grab(True)
            pygame.mouse.set_visible(False)
            tabbedIn = True
        else:
            pygame.event.set_grab(False)
            pygame.mouse.set_visible(True)
            tabbedIn = False
    elif event.type == pygame.MOUSEMOTION:
        mousePos = event.pos
        mouseMovement = event.rel
        if cursorCaptured and tabbedIn:
            pygame.mouse.set_pos((displayResolution[0] // 2, displayResolution[1] // 2))
    elif event.type == pygame.MOUSEBUTTONDOWN:
        with _keys_lock:
            keys.add(event.button)
        click(event.button)
        if event.button == 4:
            scroll(1)
        elif event.button == 5:
            scroll(-1)
    elif event.type == pygame.MOUSEBUTTONUP:
        unclick()
        with _keys_lock:
            keys.discard(event.button)
            exeKeys.discard(event.button)
    elif event.type == pygame.KEYDOWN:
        if activeInput is not None:
            if event.key == pygame.K_v and pygame.key.get_mods() & pygame.KMOD_CTRL:
                activeInput.text += getClipboard()
                activeInput.update()
            elif event.unicode and event.key not in (pygame.K_BACKSPACE, pygame.K_SPACE, pygame.K_RETURN):
                activeInput.text += event.unicode
                activeInput.update()
        else:
            with _keys_lock:
                keys.add(event.key)
            threading.Thread(target=pressDelay, args=(event.key, _KEY_REPEAT_DELAY), daemon=True).start()
            keyPress(event.key)
    elif event.type == pygame.KEYUP:
        with _keys_lock:
            keys.discard(event.key)
            exeKeys.discard(event.key)
    return True


def draw() -> DrawResult:
    """Verarbeitet Ereignisse und zeichnet ein Bild.

    Gibt "quit" zurück, wenn das Fenster geschlossen wurde, sonst True, wenn in diesem Bild
    nicht geklickt wurde, und False nach einem Klick.
    """
    global events, clickEvent, unClickEvent, scrollEvent, running, mouseMovement
    if not running:
        raise Exception("Pygame not initialized\nPlease call graphy.init() before graphy.draw()")
    mouseMovement = (0, 0)
    events = pygame.event.get()
    for event in events:
        if not _handle_event(event):
            running = False
            pygame.quit()
            return "quit"
    with _keys_lock:
        repeating = list(exeKeys)
    for key in repeating:
        keyPress(key)

    target = getScreen()
    target.fill(_BACKGROUND)
    renders.sort(key=lambda render: render.priority + render.priorityOffset)
    preDraw()
    _dispatch_pointer()
    for render in list(renders):
        if render.enabled:
            render.draw()
    renders[:] = [render for render in renders if not render.temporary]

    clicked = not clickEvent
    clickEvent = False
    unClickEvent = False
    scrollEvent = 0
    postDraw()
    if realScreen is not None:
        realScreen.blit(pygame.transform.scale(target, displayResolution), (0, 0))
    pygame.display.flip()
    if clock is not None:
        clock.tick(FPS)
    return clicked


def _dispatch_pointer() -> None:
    """Hover und Klick gehen an das oberste Objekt unter der Maus."""
    hoverable = True
    mouse = getMouse()
    for render in renders[::-1]:
        if not render.enabled:
            continue
        if isinstance(render, (RenderButton, RenderInput)):
            if hoverable and pointInRect(mouse, (render.x, render.y, render.width, render.height), render.angle,
                                         render.middle):
                render.hover(True)
                if clickEvent:
                    render.click(True, mouseButton)
                hoverable = False
            else:
                render.hover(False)
                if clickEvent and isinstance(render, RenderInput):
                    render.click(False, mouseButton)
        elif isinstance(render, RenderSlider):
            if clickEvent:
                render.tryChange(mouse)
            if unClickEvent:
                render.endChange()
            if scrollEvent != 0:
                render.change(scrollEvent)


def renderThis(renderObject: RenderObject) -> None:
    """Platzhalter aus den alten Fassungen; Render-Objekte melden sich selbst an."""
    return None


def debug(text: object, color: Optional[Color] = None) -> None:
    """Schreibt eine Zeile in die Debug-Konsole (init(debugConsole=True))."""
    if console is None:
        raise RuntimeError("Keine Debug-Konsole: graphy.init(debugConsole=True) aufrufen")
    console.addLine(str(text), color)


def getLastChildren(object: Any) -> list[Any]:
    """Flacht verschachtelte Listen ab."""
    if not isinstance(object, list):
        return [object]
    children: list[Any] = []
    for element in object:
        children.extend(getLastChildren(element))
    return children


# --- Geometrie ---------------------------------------------------------------

def rectOverlap(rect1: Rect4, rect2: Rect4) -> bool:
    l1, r1 = Point(rect1[0], rect1[1]), Point(rect1[0] + rect1[2], rect1[1] + rect1[3])
    l2, r2 = Point(rect2[0], rect2[1]), Point(rect2[0] + rect2[2], rect2[1] + rect2[3])
    if l1.x == r1.x or l1.y == r1.y or r2.x == l2.x or l2.y == r2.y:
        return False
    if l1.x > r2.x or l2.x > r1.x:
        return False
    if r1.y < l2.y or r2.y < l1.y:
        return False
    return True


def markthis(size: float = 10) -> None:
    x, y = pygame.mouse.get_pos()
    RenderImage(imageName="mark", x=x / rx, y=y / ry, surface=None, priority=10, width=size, height=size, middle=True)


def rotate_point_around_center(point: Point2, center: Point2, angle_degrees: float) -> Point2:
    """Dreht point um center, gegen den Uhrzeigersinn in Bildschirmkoordinaten."""
    angle_radians = math.radians(-angle_degrees)
    px, py = point[0] - center[0], point[1] - center[1]
    x_new = px * math.cos(angle_radians) - py * math.sin(angle_radians)
    y_new = px * math.sin(angle_radians) + py * math.cos(angle_radians)
    return x_new + center[0], y_new + center[1]


def pointInRect(mouse_pos: Point2, rect: Rect4, angle_degrees: float = 0, middle: bool = False) -> bool:
    rect_x, rect_y, rect_w, rect_h = rect
    if middle:
        rect_x -= rect_w / 2
        rect_y -= rect_h / 2
    center = (rect_x + rect_w / 2, rect_y + rect_h / 2)
    x, y = rotate_point_around_center(mouse_pos, center, angle_degrees)
    return rect_x <= x <= rect_x + rect_w and rect_y <= y <= rect_y + rect_h


def hex(hexString: str) -> Color:
    """'#ff8000' oder 'ff8000' -> (255, 128, 0)."""
    value = hexString[1:] if hexString.startswith("#") else hexString
    if len(value) != 6:
        raise ValueError(f"Erwartet sechs Hexziffern: {hexString!r}")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


# --- Klassen -----------------------------------------------------------------

class Sprite(pygame.sprite.Sprite):
    def __init__(self, image: pygame.Surface, position: Point2) -> None:
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(topleft=position)


class DummyConsole:
    """Ersatz für sys.stdout: schreibt weiter in die Konsole und zusätzlich in die Debug-Konsole."""

    def __init__(self) -> None:
        self.original_stdout: TextIO = sys.stdout

    def write(self, message: str) -> int:
        written = self.original_stdout.write(message)
        if message.strip() and console is not None:
            console.addLine(message.strip())
        return written

    def flush(self) -> None:
        self.original_stdout.flush()


class Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def _resolve_action(owner: object, action: Action) -> Union[Callable[..., Any], Literal[False]]:
    """Aktionen dürfen als 'self.methode' angegeben werden; das zeigt auf eine Methode des Objekts."""
    if action is None or action is False:
        return False
    if isinstance(action, str):
        prefix = "self."
        if not action.startswith(prefix):
            raise ValueError(f"Aktion als Text muss 'self.<methode>' sein: {action!r}")
        attribute: object = getattr(owner, action[len(prefix):])
        if not callable(attribute):
            raise TypeError(f"{action!r} ist nicht aufrufbar")
        return attribute
    return action


class RenderObject:
    def __init__(self, surface: Optional[pygame.Surface] = None, temporary: bool = False, enabled: bool = True,
                 x: float = 0.0, xOffset: float = 0.0, y: float = 0.0, yOffset: float = 0.0, width: float = 10,
                 height: float = 10, priority: float = 2, angle: float = 0, stretch: float = 1) -> None:
        self.enabled = enabled
        self.temporary = temporary
        self.x = x
        self.y = 2 * middle[1] - y if natY else y
        self.xOffset = xOffset
        self.yOffset = yOffset
        self.width = width
        self.height = height
        self.sizeMulti: float = 1
        self.priority = priority
        self.priorityOffset: float = 0
        self.angle = angle
        self.stretch = stretch
        self.middle = getattr(self, "middle", False)
        self.surface: pygame.Surface = surface if surface is not None else getScreen()

    def show(self) -> None:
        self.enabled = True

    def hide(self) -> None:
        self.enabled = False

    def remove(self) -> None:
        if self in renders:
            renders.remove(self)

    def draw(self) -> None:
        return None

    def getRect(self) -> Rect4:
        return (self.x, self.y, self.width, self.height)

    def __str__(self) -> str:
        name = getattr(self, "strName", "-Unknown-")
        return (f"{self.__class__.__name__}({name}), x: {self.x}, y: {self.y}, width: {self.width}, "
                f"height: {self.height}, angle: {self.angle}, stretch: {self.stretch}, "
                f"priority: {self.priority + self.priorityOffset}")


class RenderImage(RenderObject):
    def __init__(self, strName: Optional[str] = None, surface: Optional[pygame.Surface] = None, temporary: bool = False,
                 enabled: bool = True, imageName: ImageSpec = None, x: float = 0, xOffset: float = 0, y: float = 0,
                 yOffset: float = 0, width: float = 10, height: float = 10, middle: bool = False, priority: float = 2,
                 angle: float = 0, flipped: bool = False, stretch: float = 1,
                 mapPosition: tuple[Optional[int], Optional[int]] = (None, None), gen: bool = True,
                 topStretchMultiplier: float = 1) -> None:
        self.strName = strName if strName is not None else imageName
        self.name = imageName
        self.middle = middle
        self.flipped = flipped
        self.topStretchMultiplier = topStretchMultiplier
        self.mapPosition = mapPosition
        if imageName is None:
            imageName = pygame.Surface((max(1, round(width)), max(1, round(height))))
            imageName.fill(RED)
        self.imageName: Union[str, pygame.Surface] = imageName
        self.image: pygame.Surface = _resolve_image(imageName, (width, height))
        super().__init__(surface=surface, temporary=temporary, enabled=enabled, x=x, xOffset=xOffset, y=y,
                         yOffset=yOffset, width=width, height=height, priority=priority, angle=angle, stretch=stretch)
        if type(self) is RenderImage and gen:
            renders.append(self)

    def offset(self, x: Optional[float] = None, y: Optional[float] = None, size: Optional[float] = None,
               priority: Optional[float] = None) -> None:
        if x is not None:
            self.xOffset = x
        if y is not None:
            self.yOffset = y
        if size is not None:
            self.sizeMulti = size
        if priority is not None:
            self.priorityOffset = priority

    def update(self) -> None:
        """Lädt das Bild neu aus sprites, etwa nachdem graphy.init() erneut lief."""
        self.image = _resolve_image(self.imageName, (self.width, self.height))

    def _scaled_size(self) -> tuple[int, int]:
        return (max(1, round(self.width * self.sizeMulti * rx)),
                max(1, round(self.height * self.sizeMulti * ry)))

    def _make_trapezoid_surface(self) -> pygame.Surface:
        img = pygame.transform.flip(self.image, True, False) if self.flipped else self.image
        base_w, h_px = self._scaled_size()
        img = pygame.transform.scale(img, (base_w, h_px))
        top_w = max(1, round(base_w * self.topStretchMultiplier))
        max_w = max(top_w, base_w)
        surf = pygame.Surface((max_w, h_px), pygame.SRCALPHA)
        for row in range(h_px):
            current_w = max(1, round(top_w + (base_w - top_w) * row / h_px))
            row_slice = pygame.transform.scale(img.subsurface((0, row, base_w, 1)), (current_w, 1))
            surf.blit(row_slice, ((max_w - current_w) // 2, row))
        return surf

    def draw(self) -> None:
        if not self.enabled:
            return
        if self.topStretchMultiplier != 1:
            texture = self._make_trapezoid_surface()
        else:
            texture = pygame.transform.flip(self.image, True, False) if self.flipped else self.image
            texture = pygame.transform.scale(texture, self._scaled_size())
        x_px = (self.x + self.xOffset) * rx
        y_px = (self.y + self.yOffset) * ry
        if self.middle:
            x_px -= texture.get_width() // 2
            y_px -= texture.get_height() // 2
        if self.angle != 0:
            center = texture.get_rect(topleft=(round(x_px), round(y_px))).center
            rotated = pygame.transform.rotate(texture, -self.angle)
            self.surface.blit(rotated, rotated.get_rect(center=center).topleft)
        else:
            self.surface.blit(texture, (x_px, y_px))

    def changeImage(self, image: Union[str, pygame.Surface]) -> None:
        self.image = _resolve_image(image, (self.width if hasattr(self, "width") else 10,
                                            self.height if hasattr(self, "height") else 10))


class RenderAnimation(RenderImage):
    def __init__(self, continuous: bool = True, slowdown: float = 1, rotation: Union[float, tuple[float, ...]] = 1,
                 strName: str = "animation", surface: Optional[pygame.Surface] = None, temporary: bool = False,
                 enabled: bool = True, imageNames: Optional[tuple[str, ...]] = None, x: float = 0, xOffset: float = 0,
                 y: float = 0, yOffset: float = 0, width: float = 10, height: float = 10, middle: bool = False,
                 priority: float = 2, angle: float = 0, stretch: float = 1,
                 mapPosition: tuple[Optional[int], Optional[int]] = (None, None), gen: bool = True,
                 topStretchMultiplier: float = 1) -> None:
        if not imageNames:
            raise ValueError("RenderAnimation braucht mindestens einen Bildnamen in imageNames")
        self.rotation = rotation
        self.continuous = continuous
        self.slowdown = slowdown
        self.imageNames = imageNames
        self.frame: float = 0
        super().__init__(strName=strName, surface=surface, temporary=temporary, enabled=enabled,
                         imageName=imageNames[0], x=x, xOffset=xOffset, y=y, yOffset=yOffset, width=width,
                         height=height, middle=middle, priority=priority, angle=angle, stretch=stretch,
                         mapPosition=mapPosition, gen=gen, topStretchMultiplier=topStretchMultiplier)
        if type(self) is RenderAnimation and gen:
            renders.append(self)

    def draw(self) -> None:
        if self.frame >= len(self.imageNames):
            if not self.continuous:
                self.remove()
                return
            self.frame = 0
        index = math.floor(self.frame)
        self.changeImage(self.imageNames[index])
        super().draw()
        if isinstance(self.rotation, tuple):
            self.angle += self.rotation[index % len(self.rotation)]
        else:
            self.angle += self.rotation
        self.frame += 1 / self.slowdown


class RenderButton(RenderImage):
    def __init__(self, imageName: ImageSpec = None, strName: str = "button",
                 clickAction: Union[Callable[[], None], Callable[[*T], None], str, Literal[False]] = False,
                 arguments: tuple[*T] = (),  # type: ignore[assignment]
                 rightClickAction: Union[Callable[[*T2], None], str, Literal[False]] = False,
                 rightArguments: tuple[*T2] = (),  # type: ignore[assignment]
                 middleClickAction: Union[Callable[[*T3], None], str, Literal[False]] = False,
                 middleArguments: tuple[*T3] = (),  # type: ignore[assignment]
                 hoverAction: Union[Callable[[], None], Callable[[*T4], None], str, Literal[False]] = False,
                 hoverArguments: tuple[*T4] = (),  # type: ignore[assignment]
                 unHoverAction: Union[Callable[..., None], str, Literal[False]] = False,
                 unHoverArguments: tuple[Any, ...] = (), surface: Optional[pygame.Surface] = None,
                 temporary: bool = False, enabled: bool = True, hoverImageName: Union[Literal[False], str, pygame.Surface] = False,
                 x: float = 0, xOffset: float = 0, y: float = 0, yOffset: float = 0, width: float = 10,
                 height: float = 10, priority: float = 2, angle: float = 0, stretch: float = 1, middle: bool = False,
                 gen: bool = True, topStretchMultiplier: float = 1) -> None:
        self.arguments: tuple[Any, ...] = arguments
        self.rightArguments: tuple[Any, ...] = rightArguments
        self.middleArguments: tuple[Any, ...] = middleArguments
        self.hoverArguments: tuple[Any, ...] = hoverArguments
        self.unHoverArguments: tuple[Any, ...] = unHoverArguments
        self.hoverImageName = hoverImageName
        self.hovered = False
        super().__init__(strName=strName, surface=surface, temporary=temporary, enabled=enabled, imageName=imageName,
                         x=x, xOffset=xOffset, y=y, yOffset=yOffset, width=width, height=height, priority=priority,
                         angle=angle, stretch=stretch, middle=middle, gen=gen,
                         topStretchMultiplier=topStretchMultiplier)
        self.clickAction = _resolve_action(self, clickAction)
        self.rightClickAction = _resolve_action(self, rightClickAction)
        self.middleClickAction = _resolve_action(self, middleClickAction)
        self.hoverAction = _resolve_action(self, hoverAction)
        self.unHoverAction = _resolve_action(self, unHoverAction)
        if type(self) is RenderButton and gen:
            renders.append(self)

    def click(self, me: bool, button: int = 1) -> None:
        if button == pygame.BUTTON_LEFT and self.clickAction is not False:
            self.clickAction(*self.arguments)
        elif button == pygame.BUTTON_RIGHT and self.rightClickAction is not False:
            self.rightClickAction(*self.rightArguments)
        elif button == pygame.BUTTON_MIDDLE and self.middleClickAction is not False:
            self.middleClickAction(*self.middleArguments)

    def hover(self, hover: bool = False) -> None:
        if hover:
            self.hovered = True
            if self.hoverImageName is not False:
                self.changeImage(self.hoverImageName)
            if self.hoverAction is not False:
                self.hoverAction(*self.hoverArguments)
        elif self.hovered:
            self.hovered = False
            if self.hoverImageName is not False:
                self.changeImage(self.imageName)
            if self.unHoverAction is not False:
                self.unHoverAction(*self.unHoverArguments)


class RenderSlider(RenderImage):
    def __init__(self, step: float = 10, sliderPos: float = 0, range: tuple[float, float] = (0, 100),
                 imageName: ImageSpec = None, strName: str = "slider", surface: Optional[pygame.Surface] = None,
                 temporary: bool = False, enabled: bool = True, sliderImageName: ImageSpec = None,
                 sliderHoverImageName: ImageSpec = None, x: float = 0, xOffset: float = 0, y: float = 0,
                 yOffset: float = 0, width: float = 10, height: float = 10, priority: float = 2, angle: float = 0,
                 updateAction: Optional[Callable[[float], None]] = None, stretch: float = 1, middle: bool = False,
                 gen: bool = True) -> None:
        if range[1] <= range[0]:
            raise ValueError(f"range muss aufsteigend sein: {range}")
        super().__init__(strName=strName, surface=surface, temporary=temporary, enabled=enabled, imageName=imageName,
                         x=x, xOffset=xOffset, y=y, yOffset=yOffset, width=width, height=height, priority=priority,
                         angle=angle, stretch=stretch, middle=middle, gen=False)
        self.updateAction = updateAction
        self.step = step
        self.range = range
        self.changing = False
        self.sliderImageName: Union[str, pygame.Surface] = sliderImageName if sliderImageName is not None else self.imageName
        self.sliderHoverImageName: Union[str, pygame.Surface] = (
            sliderHoverImageName if sliderHoverImageName is not None else self.sliderImageName)
        self.changeSliderImage(self.sliderImageName)
        self.sliderPos = minMax(sliderPos, -1, 1)
        self.value = self._value_from_position(self.sliderPos)
        self.sliderX, self.sliderY = self.x, self.y
        self.calcSliderXY()
        self.slider = RenderImage(strName="sliderSlider", surface=surface, temporary=temporary, enabled=enabled,
                                  imageName=self.sliderImageName, x=self.sliderX, xOffset=xOffset, y=self.sliderY,
                                  yOffset=yOffset, width=height, height=height, priority=priority, angle=angle,
                                  stretch=stretch, middle=middle, gen=False)
        if type(self) is RenderSlider and gen:
            renders.append(self)
        self.change(0)

    def _value_from_position(self, position: float) -> float:
        return self.range[0] + (position + 1) / 2 * (self.range[1] - self.range[0])

    def changeSliderImage(self, image: Union[str, pygame.Surface]) -> None:
        self.sliderImage = _resolve_image(image, (self.height, self.height))

    def calcSliderXY(self) -> None:
        distance = (self.sliderPos + (not self.middle) * (1 - self.height / self.width)) * self.width / 2
        self.sliderX = self.x + math.cos(math.radians(self.angle)) * distance
        self.sliderY = self.y + math.sin(math.radians(self.angle)) * distance

    def tryChange(self, mousePos: Point2) -> None:
        if pointInRect(mousePos, (self.x, self.y, self.width, self.height), self.angle, self.middle):
            self.changing = True
            self.slider.changeImage(self.sliderHoverImageName)

    def changeToMouse(self) -> None:
        mouse_x, _ = getMouse()
        cosine = math.cos(math.radians(self.angle))
        if abs(cosine) < 1e-9:
            return
        distance = (mouse_x - self.height / 2 - self.x) / cosine
        self.sliderPos = minMax(distance / (self.width / 2) + self.middle * (self.height / self.width)
                                - (not self.middle) * (1 - self.height / self.width), -1, 1)
        self.value = self._value_from_position(self.sliderPos) // self.step * self.step
        self._moved()

    def endChange(self) -> None:
        if self.changing:
            self.changing = False
            self.slider.changeImage(self.sliderImageName)

    def change(self, amount: float) -> None:
        self.value = minMax(self.value + amount * self.step, self.range[0], self.range[1])
        self.sliderPos = (self.value - self.range[0]) / (self.range[1] - self.range[0]) * 2 - 1
        self._moved()

    def _moved(self) -> None:
        if self.updateAction is not None:
            self.updateAction(self.value)
        self.calcSliderXY()
        self.slider.x, self.slider.y = self.sliderX, self.sliderY

    def draw(self) -> None:
        super().draw()
        if self.changing:
            self.changeToMouse()
        self.slider.draw()


def _load_font(font: FontSpec, size: float) -> pygame.font.Font:
    if isinstance(font, pygame.font.Font):
        return font
    if font is None:
        font = defaultFont
    pixel_size = max(1, round(size))
    if font is None:
        return pygame.font.Font(None, pixel_size)
    try:
        return pygame.font.Font(font, pixel_size)
    except (FileNotFoundError, OSError):
        return pygame.font.SysFont(font, pixel_size)


class RenderConsole(RenderObject):
    def __init__(self, surface: Optional[pygame.Surface] = None, enabled: bool = True, x: float = 0, y: float = 0,
                 maxLength: int = 10, removeDelay: float = -1, xOffset: float = 0, yOffset: float = 0,
                 font: FontSpec = None, size: int = 30, color: Color = (0, 0, 0), temporary: bool = False,
                 angle: float = 0, stretch: float = 1, middle: bool = False, priority: float = 2.1,
                 gen: bool = True) -> None:
        self.font = _load_font(font, size)
        self.size = size
        self.color = color
        self.maxLength = maxLength
        self.removeDelay = removeDelay
        self.history: deque[RenderText] = deque([], maxLength)
        self._created: deque[float] = deque([], maxLength)
        self.middle = middle
        self.updateQueued = False
        super().__init__(surface=surface, temporary=temporary, enabled=enabled, x=x, y=y, xOffset=xOffset,
                         yOffset=yOffset, width=0, height=0, priority=priority, angle=angle, stretch=stretch)
        if type(self) is RenderConsole and gen:
            renders.append(self)

    def addLine(self, Line: str, color: Optional[Color] = None) -> None:
        self.history.append(RenderText(text=Line, font=self.font, size=self.size, color=color or self.color,
                                       x=self.x + self.xOffset, y=self.y + self.yOffset, temporary=self.temporary,
                                       angle=self.angle, stretch=self.stretch, middle=self.middle,
                                       priority=self.priority, gen=False, surface=self.surface))
        self._created.append(time.time())
        self.updateQueued = True

    def draw(self) -> None:
        if self.removeDelay > 0:
            while self._created and time.time() - self._created[0] > self.removeDelay:
                self.history.popleft()
                self._created.popleft()
                self.updateQueued = True
        if self.updateQueued:
            for index, line in enumerate(self.history):
                line.yOffset = self.size * index
            self.height = self.size * len(self.history)
            self.width = max((line.width for line in self.history), default=0)
            self.updateQueued = False
        for line in self.history:
            line.draw()


class RenderText(RenderObject):
    def __init__(self, surface: Optional[pygame.Surface] = None, enabled: bool = True, x: float = 0, y: float = 0,
                 xOffset: float = 0, yOffset: float = 0, text: str = "example", font: FontSpec = None,
                 size: float = 30, color: Color = (0, 0, 0), temporary: bool = False, angle: float = 0,
                 stretch: float = 1, middle: bool = False, priority: float = 2, gen: bool = True,
                 strName: Optional[str] = None) -> None:
        self.strName = text if strName is None else strName
        self.font = _load_font(font, size)
        self.text = text
        self.color = color
        self.middle = middle
        self.renderSurface = self.font.render(text, True, color)
        super().__init__(surface=surface, temporary=temporary, enabled=enabled, x=x, y=y, xOffset=xOffset,
                         yOffset=yOffset, width=self.renderSurface.get_width(),
                         height=self.renderSurface.get_height(), priority=priority, angle=angle, stretch=stretch)
        if type(self) is RenderText and gen:
            renders.append(self)

    def updateText(self, newText: str) -> None:
        self.text = newText
        self.update()

    def update(self) -> None:
        self.renderSurface = self.font.render(self.text, True, self.color)
        self.height = self.renderSurface.get_height()
        self.width = self.renderSurface.get_width()

    def draw(self) -> None:
        drawRotated(surface=self.surface, img=self.renderSurface, x=self.x + self.xOffset, y=self.y + self.yOffset,
                    angle=self.angle, width=self.width * self.sizeMulti, height=self.height * self.sizeMulti,
                    stretch=self.stretch, middle=self.middle)


def _framed_surface(drawType: str, size: tuple[int, int], borderSize: float, fill: Color,
                    border: Color) -> pygame.Surface:
    if drawType == "rect":
        surface = pygame.Surface(size)
        surface.fill(border)
        inner = pygame.Rect(borderSize, borderSize, size[0] - borderSize * 2, size[1] - borderSize * 2)
        pygame.draw.rect(surface, fill, inner)
        return surface
    if drawType == "circ":
        surface = pygame.Surface(size, pygame.SRCALPHA)
        radius = size[1] / 2
        pygame.draw.circle(surface, border, (radius, radius), radius)
        pygame.draw.circle(surface, fill, (radius, radius), radius - borderSize)
        return surface
    raise ValueError(f"drawType muss 'rect' oder 'circ' sein, nicht {drawType!r}")


class RenderTextButton(RenderButton):
    def __init__(self, surface: Optional[pygame.Surface] = None, drawType: str = "rect", imageName: ImageSpec = None,
                 hoverImageName: ImageSpec = None, strName: str = "textButton", enabled: bool = True, x: float = 0,
                 y: float = 0, width: float = 30, height: float = 10, xOffset: float = 0, yOffset: float = 0,
                 clickAction: Action = False, rightClickAction: Action = False, middleClickAction: Action = False,
                 hoverAction: Action = False, unHoverAction: Action = False, arguments: tuple[Any, ...] = (),
                 rightArguments: tuple[Any, ...] = (), middleArguments: tuple[Any, ...] = (),
                 hoverArguments: tuple[Any, ...] = (), unHoverArguments: tuple[Any, ...] = (), text: str = "example",
                 font: FontSpec = None, size: Optional[float] = None, borderSize: float = 5, color: Color = (0, 0, 0),
                 activeColor: Optional[Color] = (100, 100, 100), textColor: Color = (200, 200, 200),
                 borderColor: Color = (200, 200, 200), temporary: bool = False, angle: float = 0, stretch: float = 1,
                 middle: bool = False, priority: float = 2, gen: bool = True) -> None:
        self.borderSize = borderSize
        self.middle = middle
        self.text = text
        self.size = size if size is not None else round(height)
        self.font = font
        self.textColor = textColor
        self.color = color
        self.activeColor = activeColor
        self.borderColor = borderColor
        self.textSurface = RenderText(surface=surface, x=x + borderSize - self.size / 10 * middle,
                                      y=y + borderSize - self.size / 15 * middle, xOffset=xOffset, yOffset=yOffset,
                                      text=text, font=font, size=self.size, color=textColor, temporary=temporary,
                                      angle=angle, stretch=stretch, middle=middle, priority=priority, gen=False)
        pixel_size = (max(1, round(width)), max(1, round(height)))
        self.renderSurface: Union[str, pygame.Surface] = (
            imageName if imageName is not None else _framed_surface(drawType, pixel_size, borderSize, color, borderColor))
        active: Union[Literal[False], str, pygame.Surface] = False
        if hoverImageName is not None:
            active = hoverImageName
        elif activeColor is not None:
            active = _framed_surface(drawType, pixel_size, borderSize, activeColor, borderColor)
        self.activeSurface = active
        super().__init__(imageName=self.renderSurface, strName=strName, clickAction=clickAction or False,
                         rightClickAction=rightClickAction or False, middleClickAction=middleClickAction or False,
                         hoverAction=hoverAction or False, unHoverAction=unHoverAction or False, arguments=arguments,
                         rightArguments=rightArguments, middleArguments=middleArguments,
                         hoverArguments=hoverArguments, unHoverArguments=unHoverArguments, surface=surface,
                         temporary=temporary, enabled=enabled, hoverImageName=self.activeSurface, x=x,
                         xOffset=xOffset, y=y, yOffset=yOffset, width=width, height=height, middle=middle,
                         priority=priority, angle=angle, stretch=stretch, gen=gen)
        if type(self) is RenderTextButton and gen:
            renders.append(self)

    def draw(self) -> None:
        super().draw()
        self.textSurface.draw()


class RenderInput(RenderObject):
    def __init__(self, surface: Optional[pygame.Surface] = None, enabled: bool = True, x: float = 0, y: float = 0,
                 xOffset: float = 0, yOffset: float = 0, text: str = "example", font: FontSpec = None,
                 size: float = 30, borderSize: float = 5, color: Color = (0, 0, 0),
                 activeColor: Color = (100, 100, 100), textColor: Color = (200, 200, 200),
                 borderColor: Color = (200, 200, 200), temporary: bool = False, angle: float = 0, stretch: float = 1,
                 middle: bool = False, priority: float = 2, gen: bool = True) -> None:
        self.strName = text
        self.borderSize = borderSize
        self.middle = middle
        self.text = text
        self.size = size
        self.font = font
        self.mainColor = color
        self.activeColor = activeColor
        self.color = color
        self.textColor = textColor
        self.borderColor = borderColor
        self.active = False
        self.hovered = False
        super().__init__(surface=surface, temporary=temporary, enabled=enabled, x=x, y=y, xOffset=xOffset,
                         yOffset=yOffset, width=0, height=0, priority=priority, angle=angle, stretch=stretch)
        self.textSurface: RenderText
        self.renderSurface: pygame.Surface
        self.update()
        if type(self) is RenderInput and gen:
            renders.append(self)

    def setOn(self, on: bool) -> None:
        global activeInput
        if on:
            activeInput = self
            self.color = self.activeColor
        else:
            if activeInput is self:
                activeInput = None
            self.color = self.mainColor
        self.update()

    def update(self) -> None:
        self.textSurface = RenderText(surface=self.surface, x=self.x + self.borderSize - self.size / 10 * self.middle,
                                      y=self.y + self.borderSize - self.size / 15 * self.middle, xOffset=self.xOffset,
                                      yOffset=self.yOffset, text=self.text, font=self.font, size=self.size,
                                      color=self.textColor, temporary=self.temporary, angle=self.angle,
                                      stretch=self.stretch, middle=self.middle, priority=self.priority, gen=False)
        self.width = self.textSurface.width + self.borderSize * 2
        self.height = self.textSurface.height + self.borderSize * 2
        self.renderSurface = _framed_surface("rect", (max(1, round(self.width)), max(1, round(self.height))),
                                             self.borderSize, self.color, self.borderColor)

    def click(self, me: bool, button: int = 1) -> None:
        self.active = me
        if not me:
            self.setOn(False)

    def hover(self, hover: bool = False) -> None:
        if hover:
            self.hovered = True
            self.setOn(True)
        elif self.hovered:
            self.hovered = False
            if not self.active:
                self.setOn(False)

    def draw(self) -> None:
        drawRotated(surface=self.surface, img=self.renderSurface, x=self.x + self.xOffset, y=self.y + self.yOffset,
                    angle=self.angle, width=self.width * self.sizeMulti, height=self.height * self.sizeMulti,
                    stretch=self.stretch, middle=self.middle)
        self.textSurface.draw()


class GameObject:
    def __init__(self, strName: Optional[str] = None, x: float = 0, y: float = 0,
                 renderObject: Optional[RenderObject] = None, enabled: bool = True, angle: float = 0,
                 priority: float = 2) -> None:
        if renderObject is None:
            raise ValueError("GameObject braucht ein renderObject")
        self.strName = strName if strName else getattr(renderObject, "strName", None)
        self.x = x
        self.y = y
        self.angle = angle
        self.enabled = enabled
        self.priority = priority
        self.renderObject = renderObject
        if strName:
            setattr(renderObject, "strName", strName)
        self.update()

    def update(self) -> None:
        self.renderObject.x = self.x
        self.renderObject.y = self.y
        self.renderObject.angle = self.angle
        self.renderObject.enabled = self.enabled
        self.renderObject.priority = self.priority


def example() -> None:
    init()
    RenderAnimation(imageNames=("image", "image2", "image2"), slowdown=10, rotation=1, height=200, width=200,
                    x=middle[0], y=middle[1])
    while running:
        draw()


if __name__ == "__main__":
    example()
