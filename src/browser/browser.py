import tkinter

from browser.css import style
from browser.html import HTMLParser, ViewSourceParser
from browser.layout import HEIGHT, VSTEP, WIDTH, DocumentLayout, paint_tree

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
    for cmd in self.display_list:
      if cmd.top > self.scroll + HEIGHT: continue
      if cmd.bottom < self.scroll: continue
      cmd.execute(self.scroll, self.canvas)
    self.canvas.update_idletasks()

  def load(self, url):
    body = url.request()
    if url.scheme == "view-source":
      self.nodes = ViewSourceParser(body).parse()
    else:
      self.nodes = HTMLParser(body).parse()
    style(self.nodes)
    self.document = DocumentLayout(self.nodes)
    self.document.layout()
    self.display_list = []
    paint_tree(self.document, self.display_list)
    self.draw()

  def scrolldown(self, e):
    max_y = max(self.document.height + 2 * VSTEP - HEIGHT, 0)
    self.scroll = min(self.scroll + SCROLL_STEP, max_y)
    self.draw()
