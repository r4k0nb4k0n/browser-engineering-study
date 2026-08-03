import tkinter.font

from browser.html import Text

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18


class Layout:
  def __init__(self, tokens):
    self.display_list = []
    self.cursor_x = HSTEP
    self.cursor_y = VSTEP
    self.weight = "normal"
    self.style = "roman"
    self.size = 12
    for tok in tokens:
      self.token(tok)

  def token(self, tok):
    if isinstance(tok, Text):
      for word in tok.text.split():
        self.word(word)
    elif tok.tag == "i":
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

  def word(self, word):
    font = tkinter.font.Font(
        size=self.size,
        weight=self.weight,
        slant=self.style,
    )
    w = font.measure(word)
    if self.cursor_x + w > WIDTH - HSTEP:
      self.cursor_y += font.metrics("linespace") * 1.25
      self.cursor_x = HSTEP
    self.display_list.append((self.cursor_x, self.cursor_y, word, font))
    self.cursor_x += w + font.measure(" ")
