import tkinter
import tkinter.font

from browser.html import Element, HTMLParser, Text

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

FONTS = {}


def get_font(size, weight, style):
  key = (size, weight, style)
  if key not in FONTS:
    try:
      font = tkinter.font.Font(size=size, weight=weight, slant=style)
      label = tkinter.Label(font=font)
    except RuntimeError:
      # Tk 루트 창이 없을 경우 자동 생성하여 폰트 런타임 에러 방지
      tkinter.Tk()
      font = tkinter.font.Font(size=size, weight=weight, slant=style)
      label = tkinter.Label(font=font)
    FONTS[key] = (font, label)
  return FONTS[key][0]


class Layout:

  def __init__(self, tree):
    if isinstance(tree, str):
      tree = HTMLParser(tree).parse()

    self.display_list = []
    self.cursor_x = HSTEP
    self.cursor_y = VSTEP
    self.weight = "normal"
    self.style = "roman"
    self.size = 12
    self.line = []
    self.centered = False

    self.recurse(tree)
    self.flush()

  def open_tag(self, tag):
    if tag == "i":
      self.style = "italic"
    elif tag == "b":
      self.weight = "bold"
    elif tag == "small":
      self.size -= 2
    elif tag == "big":
      self.size += 4
    elif tag == "br":
      self.flush()
    elif tag == "p":
      self.flush()
      self.cursor_y += VSTEP
    elif tag == "h1":
      self.size += 6
      self.flush()
      self.cursor_y += VSTEP
      self.centered = True

  def close_tag(self, tag):
    if tag == "i":
      self.style = "roman"
    elif tag == "b":
      self.weight = "normal"
    elif tag == "small":
      self.size += 2
    elif tag == "big":
      self.size -= 4
    elif tag == "p":
      self.flush()
      self.cursor_y += VSTEP
    elif tag == "h1":
      self.size -= 6
      self.flush()
      self.cursor_y += VSTEP
      self.centered = False

  def recurse(self, tree):
    if isinstance(tree, Text):
      for word in tree.text.split():
        self.word(word)
    else:
      self.open_tag(tree.tag)
      for child in tree.children:
        self.recurse(child)
      self.close_tag(tree.tag)

  def word(self, word):
    font = get_font(self.size, self.weight, self.style)
    w = font.measure(word)
    if self.cursor_x + w > WIDTH - HSTEP:
      self.flush()
    self.line.append((self.cursor_x, word, font))
    self.cursor_x += w + font.measure(" ")

  def flush(self):
    if not self.line:
      return
    metrics = [font.metrics() for x, word, font in self.line]
    max_ascent = max(metric["ascent"] for metric in metrics)
    baseline = self.cursor_y + 1.25 * max_ascent
    line_width = sum(font.measure(word) for x, word, font in self.line)
    for index, (x, word, font) in enumerate(self.line):
      y = baseline - font.metrics("ascent")
      if self.centered:
        x += WIDTH / 2 - line_width / 2
      else:
        x = x
      self.display_list.append((x, y, word, font))
    max_descent = max(metric["descent"] for metric in metrics)
    self.cursor_y = baseline + 1.25 * max_descent
    self.cursor_x = HSTEP
    self.line = []
