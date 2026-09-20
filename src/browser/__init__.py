from browser.css import (
    CSSParser,
    DEFAULT_STYLE_SHEET,
    INHERITED_PROPERTIES,
    DescendantSelector,
    TagSelector,
    cascade_priority,
    style,
)
from browser.html import Element, HTMLParser, Tag, Text, lex, print_tree, tree_to_list
from browser.url import URL, load

try:
  from browser.browser import SCROLL_STEP, Browser, Chrome, Tab
  from browser.layout import (
      FONTS,
      HEIGHT,
      HSTEP,
      BlockLayout,
      LineLayout,
      TextLayout,
      DrawLine,
      DrawOutline,
      DrawRect,
      DrawText,
      Rect,
      VSTEP,
      WIDTH,
      get_font,
      paint_tree,
  )
  from browser.tk_capture import capture_tk_window, display_tk_window
except ImportError:
  # Tk / pyobjc가 없는 환경에서도 CSS·HTML·URL·lex는 import 가능하게 둔다.
  SCROLL_STEP, Browser, Chrome, Tab = None, None, None, None
  FONTS = None
  HEIGHT, WIDTH = 600, 800
  HSTEP, VSTEP = 13, 18
  BlockLayout = None
  LineLayout = None
  TextLayout = None
  DrawRect, DrawText, DrawOutline, DrawLine, paint_tree = (
      None,
      None,
      None,
      None,
      None,
  )
  Rect = None
  get_font = None
  capture_tk_window = None
  display_tk_window = None

__all__ = [
    "URL",
    "Text",
    "Element",
    "Tag",
    "lex",
    "HTMLParser",
    "print_tree",
    "tree_to_list",
    "load",
    "FONTS",
    "get_font",
    "WIDTH",
    "HEIGHT",
    "HSTEP",
    "VSTEP",
    "BlockLayout",
    "LineLayout",
    "TextLayout",
    "DrawText",
    "DrawRect",
    "DrawOutline",
    "DrawLine",
    "Rect",
    "paint_tree",
    "SCROLL_STEP",
    "Browser",
    "Chrome",
    "Tab",
    "capture_tk_window",
    "display_tk_window",
    "CSSParser",
    "TagSelector",
    "DescendantSelector",
    "cascade_priority",
    "style",
    "DEFAULT_STYLE_SHEET",
    "INHERITED_PROPERTIES",
]
