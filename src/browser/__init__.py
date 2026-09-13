from browser.css import CSSParser, DescendantSelector, TagSelector, style
from browser.html import Element, HTMLParser, Tag, Text, lex, print_tree
from browser.url import URL, load

try:
  from browser.browser import SCROLL_STEP, Browser
  from browser.layout import FONTS, HEIGHT, HSTEP, BlockLayout, VSTEP, WIDTH, get_font
  from browser.tk_capture import capture_tk_window, display_tk_window
except ImportError:
  # Tk / pyobjc가 없는 환경에서도 CSS·HTML·URL·lex는 import 가능하게 둔다.
  SCROLL_STEP, Browser = None, None
  FONTS = None
  HEIGHT, WIDTH = 600, 800
  HSTEP, VSTEP = 13, 18
  BlockLayout = None
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
    "load",
    "FONTS",
    "get_font",
    "WIDTH",
    "HEIGHT",
    "HSTEP",
    "VSTEP",
    "Layout",
    "SCROLL_STEP",
    "Browser",
    "capture_tk_window",
    "display_tk_window",
    "CSSParser",
    "TagSelector",
    "DescendantSelector",
    "style",
]
