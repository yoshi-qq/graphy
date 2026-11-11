"""Hält Namen und Parameterreihenfolge der öffentlichen Schnittstelle fest.

Ändert sich hier etwas, brechen Aufrufer, die Werte nach Position übergeben.
"""
import inspect
from typing import Callable

import pytest

import graphy
from graphy import layout, terminal

PUBLIC_NAMES = [
    # Konstanten
    "HD", "QHD", "FOUR_K", "RED", "GREEN", "BLUE", "WHITE", "BLACK", "COLORS", "T", "T2", "T3", "T4",
    # Zustand
    "activeInput", "running", "clickEvent", "unClickEvent", "scrollEvent", "events", "console",
    "mouseButton", "defaultFont", "sprites", "keys", "exeKeys", "middle", "displayResolution",
    "natY", "mousePos", "mouseMovement", "cursorCaptured", "tabbedIn",
    # Funktionen
    "preload", "paperclipInit", "init", "classes", "scanDirectory", "drawNormal", "drawRotated",
    "getMouse", "getHeldKeys", "getMousePosition", "getMouseMovement", "click", "unclick", "scroll",
    "minMax", "keyPress", "pressDelay", "preDraw", "postDraw", "draw", "renderThis", "debug",
    "getLastChildren", "setMouseCapture", "rectOverlap", "markthis", "rotate_point_around_center",
    "pointInRect", "hex", "getScreen", "example",
    # Klassen
    "Sprite", "DummyConsole", "Point", "RenderObject", "RenderImage", "RenderAnimation", "RenderButton",
    "RenderSlider", "RenderConsole", "RenderText", "RenderTextButton", "RenderInput", "GameObject",
]


@pytest.mark.parametrize("name", PUBLIC_NAMES)
def test_public_name_exists(name: str) -> None:
    assert hasattr(graphy, name)


def _params(func: Callable) -> list[str]:
    return [p for p in inspect.signature(func).parameters if p != "self"]


SIGNATURES: dict[str, list[str]] = {
    "init": ["file", "fps", "fontPath", "fullscreen", "captureCursor", "naturalY", "singleSizeOn", "windowName",
             "spriteFolder", "spriteExtension", "scale", "nativeRes", "windowIcon", "windowRes",
             "debugConsole", "copyToConsole"],
    "preload": ["file", "nativeRes", "scale", "windowRes"],
    "scanDirectory": ["directory", "extension", "extra"],
    "drawNormal": ["surface", "img", "x", "y", "width", "height", "middle"],
    "drawRotated": ["surface", "img", "x", "y", "angle", "width", "height", "middle", "flipped", "stretch"],
    "click": ["button"],
    "scroll": ["direction"],
    "minMax": ["value", "min", "max"],
    "keyPress": ["key"],
    "pressDelay": ["key", "delay"],
    "debug": ["text", "color"],
    "pointInRect": ["mouse_pos", "rect", "angle_degrees", "middle"],
    "rotate_point_around_center": ["point", "center", "angle_degrees"],
    "rectOverlap": ["rect1", "rect2"],
    "markthis": ["size"],
    "setMouseCapture": ["capture"],
    "getLastChildren": ["object"],
    "hex": ["hexString"],
}


@pytest.mark.parametrize("name,expected", SIGNATURES.items())
def test_function_signature(name: str, expected: list[str]) -> None:
    assert _params(getattr(graphy, name)) == expected


CLASS_SIGNATURES: dict[str, list[str]] = {
    "RenderObject": ["surface", "temporary", "enabled", "x", "xOffset", "y", "yOffset", "width", "height",
                     "priority", "angle", "stretch"],
    "RenderImage": ["strName", "surface", "temporary", "enabled", "imageName", "x", "xOffset", "y", "yOffset",
                    "width", "height", "middle", "priority", "angle", "flipped", "stretch", "mapPosition", "gen",
                    "topStretchMultiplier"],
    "RenderAnimation": ["continuous", "slowdown", "rotation", "strName", "surface", "temporary", "enabled",
                        "imageNames", "x", "xOffset", "y", "yOffset", "width", "height", "middle", "priority",
                        "angle", "stretch", "mapPosition", "gen", "topStretchMultiplier"],
    "RenderButton": ["imageName", "strName", "clickAction", "arguments", "rightClickAction", "rightArguments",
                     "middleClickAction", "middleArguments", "hoverAction", "hoverArguments", "unHoverAction",
                     "unHoverArguments", "surface", "temporary", "enabled", "hoverImageName", "x", "xOffset", "y",
                     "yOffset", "width", "height", "priority", "angle", "stretch", "middle", "gen",
                     "topStretchMultiplier"],
    "RenderSlider": ["step", "sliderPos", "range", "imageName", "strName", "surface", "temporary", "enabled",
                     "sliderImageName", "sliderHoverImageName", "x", "xOffset", "y", "yOffset", "width", "height",
                     "priority", "angle", "updateAction", "stretch", "middle", "gen"],
    "RenderText": ["surface", "enabled", "x", "y", "xOffset", "yOffset", "text", "font", "size", "color",
                   "temporary", "angle", "stretch", "middle", "priority", "gen", "strName"],
    "RenderConsole": ["surface", "enabled", "x", "y", "maxLength", "removeDelay", "xOffset", "yOffset", "font",
                      "size", "color", "temporary", "angle", "stretch", "middle", "priority", "gen"],
    "RenderTextButton": ["surface", "drawType", "imageName", "hoverImageName", "strName", "enabled", "x", "y",
                         "width", "height", "xOffset", "yOffset", "clickAction", "rightClickAction",
                         "middleClickAction", "hoverAction", "unHoverAction", "arguments", "rightArguments",
                         "middleArguments", "hoverArguments", "unHoverArguments", "text", "font", "size",
                         "borderSize", "color", "activeColor", "textColor", "borderColor", "temporary", "angle",
                         "stretch", "middle", "priority", "gen"],
    "RenderInput": ["surface", "enabled", "x", "y", "xOffset", "yOffset", "text", "font", "size", "borderSize",
                    "color", "activeColor", "textColor", "borderColor", "temporary", "angle", "stretch", "middle",
                    "priority", "gen"],
    "GameObject": ["strName", "x", "y", "renderObject", "enabled", "angle", "priority"],
}


@pytest.mark.parametrize("name,expected", CLASS_SIGNATURES.items())
def test_class_signature(name: str, expected: list[str]) -> None:
    assert _params(getattr(graphy, name).__init__) == expected


@pytest.mark.parametrize("cls,method,expected", [
    ("RenderButton", "click", ["me", "button"]),
    ("RenderInput", "click", ["me", "button"]),
    ("RenderImage", "offset", ["x", "y", "size", "priority"]),
    ("RenderText", "updateText", ["newText"]),
    ("RenderConsole", "addLine", ["Line", "color"]),
    ("RenderSlider", "change", ["amount"]),
])
def test_method_signature(cls: str, method: str, expected: list[str]) -> None:
    assert _params(getattr(getattr(graphy, cls), method)) == expected


def test_submodules() -> None:
    assert _params(terminal.Console.log) == ["_case", "symbol", "problem", "reason", "detailsSymbol", "details", "obj"]
    assert _params(layout.distributeObjects) == ["objects", "aspect_ratio"]
