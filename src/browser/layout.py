import tkinter
import tkinter.font

from browser.html import Element, HTMLParser, Text

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

FONTS = {}

BLOCK_ELEMENTS = [
  "html", "body", "article", "section", "nav", "aside",
  "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
  "footer", "address", "p", "hr", "pre", "blockquote",
  "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
  "figcaption", "main", "div", "table", "form", "fieldset",
  "legend", "details", "summary"
]


def get_font(size, weight, style, family="Times New Roman"):
  key = (size, weight, style, family)
  if key not in FONTS:
    try:
      font = tkinter.font.Font(
          family=family, size=size, weight=weight, slant=style
      )
      label = tkinter.Label(font=font)
    except RuntimeError:
      # Tk 루트 창이 없을 경우 자동 생성하여 폰트 런타임 에러 방지
      tkinter.Tk()
      font = tkinter.font.Font(
          family=family, size=size, weight=weight, slant=style
      )
      label = tkinter.Label(font=font)
    FONTS[key] = (font, label)
  return FONTS[key][0]


class DocumentLayout:
  def __init__(self, node):
    self.node = node
    self.parent = None
    self.children = []
    self.display_list = []

  def __repr__(self):
    return "DocumentLayout()"

  def layout(self):
    child = BlockLayout(self.node, self, None)
    self.children.append(child)
    child.layout()

class BlockLayout:

  def __init__(self, node, parent, previous):
    self.node = node
    self.parent = parent
    self.previous = previous
    self.children = []
  
  def __repr__(self):
    return "BlockLayout({})".format(self.node)
  
  def layout_mode(self):
    if isinstance(self.node, Text):
      return "inline"
    elif any([isinstance(child, Element) and \
              child.tag in BLOCK_ELEMENTS
              for child in self.node.children]):
      return "block"
    elif self.node.children:
      return "inline"
    else:
      return "block"

  def layout(self):
    mode = self.layout_mode()
    if mode == "block":
      previous = None
      for child in self.node.children:
        next = BlockLayout(child, self, previous)
        self.children.append(next)
        previous = next
    else:
      self.display_list = []
      self.cursor_x = 0
      self.cursor_y = 0
      self.weight = "normal"
      self.style = "roman"
      self.size = 12

      self.line = []
      self.centered = False
      self.in_pre = False

      self.recurse(self.node)
      self.flush()

    for child in self.children:
      child.layout()

  def layout_intermediate(self):
    previous = None
    for child in self.node.children:
      next = BlockLayout(child, self, previous)
      self.children.append(next)
      previous = next

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
    elif tag == "pre":
      self.in_pre = True
      self.flush()
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
    elif tag == "pre":
      self.in_pre = False
      self.flush()
      self.cursor_y += VSTEP
    elif tag == "h1":
      self.size -= 6
      self.flush()
      self.cursor_y += VSTEP
      self.centered = False

  def recurse(self, tree):
    if isinstance(tree, Text):
      lines = tree.text.split("\n")
      for i, line in enumerate(lines):
        if i > 0:
          self.flush()
        if self.in_pre:
          if line:
            self.word(line, add_space=False)
        else:
          words = line.split()
          for j, word in enumerate(words):
            self.word(word, add_space=(j < len(words) - 1))
    else:
      self.open_tag(tree.tag)
      for child in tree.children:
        self.recurse(child)
      self.close_tag(tree.tag)

  def word(self, word, add_space=True):
    family = "Courier New" if self.in_pre else "Times New Roman"
    font = get_font(self.size, self.weight, self.style, family=family)
    w = font.measure(word)
    if self.cursor_x + w > WIDTH - HSTEP:
      self.flush()
    self.line.append((self.cursor_x, word, font))
    self.cursor_x += w + (font.measure(" ") if add_space else 0)

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
