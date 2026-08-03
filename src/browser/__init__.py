from browser.html import Text, Tag, lex
from browser.url import URL, load

try:
  from browser.tk_capture import capture_tk_window, display_tk_window
except ImportError:
  # Tk / pyobjc가 없는 환경에서도 URL·lex는 import 가능하게 둔다.
  capture_tk_window = None
  display_tk_window = None

__all__ = [
    "URL",
    "Text",
    "Tag",
    "lex",
    "load",
    "capture_tk_window",
    "display_tk_window",
]
