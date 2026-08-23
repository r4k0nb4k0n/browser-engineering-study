import tkinter

from browser.html import HTMLParser, ViewSourceParser
from browser.layout import HEIGHT, WIDTH, DocumentLayout

SCROLL_STEP = 100


class Browser:

  def __init__(self):
    if tkinter._default_root:
      self.window = tkinter.Toplevel(tkinter._default_root)
    else:
      self.window = tkinter.Tk()
    self.canvas = tkinter.Canvas(
        self.window, width=WIDTH, height=HEIGHT, bg="white"
    )
    self.canvas.pack(fill="both", expand=True)
    self.scroll = 0
    self.window.bind("<Down>", self.scrolldown)

  def draw(self):
    self.canvas.delete("all")
    for x, y, word, font in self.display_list:
      self.canvas.create_text(
          x, y - self.scroll, text=word, font=font, anchor="nw", fill="black"
      )

  def load(self, url):
    body = url.request()
    if url.scheme == "view-source":
      self.nodes = ViewSourceParser(body).parse()
    else:
      self.nodes = HTMLParser(body).parse()
    self.document = DocumentLayout(self.nodes)
    self.document.layout()
    self.display_list = self.document.display_list
    self.draw()

  def scrolldown(self, e):
    self.scroll += SCROLL_STEP
    self.draw()
