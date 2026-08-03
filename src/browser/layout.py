import tkinter
import tkinter.font

from browser.html import Text, Tag, lex

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

FONTS = {}


def get_font(size, weight, style):
  key = (size, weight, style)
  if key not in FONTS:
    font = tkinter.font.Font(size=size, weight=weight, slant=style)
    label = tkinter.Label(font=font)
    FONTS[key] = (font, label)
  return FONTS[key][0]


class Layout:
  def __init__(self, tokens):
    # 예전 lex(문자열 반환)나 HTML 문자열이 그대로 들어오면 토큰으로 맞춘다.
    if isinstance(tokens, str):
      tokens = lex(tokens)
      if isinstance(tokens, str):
        tokens = [Text(tokens)]

    self.display_list = []
    self.cursor_x = HSTEP
    self.cursor_y = VSTEP
    self.weight = "normal"
    self.style = "roman"
    self.size = 12
    self.line = []
    self.centered = False
    for tok in tokens:
      self.token(tok)
    self.flush()

  def token(self, tok):
    if isinstance(tok, Text):
      for word in tok.text.split():
        self.word(word)
    elif isinstance(tok, Tag):
      if tok.tag == "i":
        self.style = "italic"
      elif tok.tag == "/i":
        self.style = "roman"
      elif tok.tag == "b":
        self.weight = "bold"
      elif tok.tag == "/b":
        self.weight = "normal"
      elif tok.tag == "small":
        self.size -= 2
      elif tok.tag == "/small":
        self.size += 2
      elif tok.tag == "big":
        self.size += 4
      elif tok.tag == "/big":
        self.size -= 4
      elif tok.tag == "br":
        self.flush()
      elif tok.tag == "/p":
        self.flush()
        self.cursor_y += VSTEP
      elif tok.tag == "h1 class=\"title\"":
        self.size += 6
        self.flush()
        self.cursor_y += VSTEP
        self.centered = True
      elif tok.tag == "/h1":
        self.size -= 6
        self.flush()
        self.cursor_y += VSTEP
        self.centered = False

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
