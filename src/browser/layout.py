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
    self.x = None
    self.y = None
    self.width = None
    self.height = None

  def __repr__(self):
    return "DocumentLayout()"

  def layout(self):
    self.width = WIDTH - 2 * HSTEP
    self.x = HSTEP
    self.y = VSTEP
    child = BlockLayout(self.node, self, None)
    self.children.append(child)
    child.layout()
    self.height = child.height + 2 * VSTEP

  def paint(self):
    return []

class BlockLayout:

  def __init__(self, node, parent, previous):
    self.node = node
    self.parent = parent
    self.previous = previous
    self.children = []
    self.x = None
    self.y = None
    self.width = None
    self.height = None

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
    self.x = self.parent.x
    self.width = self.parent.width
    if self.previous:
      self.y = self.previous.y + self.previous.height
    else:
      self.y = self.parent.y

    if isinstance(self.node, Element) and self.node.tag == "nav" and self.node.attributes.get("id") == "toc":
      tableOfContentsTitle = Element("div", { "class": "table-of-contents-title" }, self.node)
      tableOfContentsTitle.children.append(Text("Table of Contents", tableOfContentsTitle))
      self.node.children.insert(0, tableOfContentsTitle)

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

    if mode == "block":
      self.height = sum([child.height for child in self.children])
    else:
      self.height = self.cursor_y

  def layout_intermediate(self):
    previous = None
    for child in self.node.children:
      next = BlockLayout(child, self, previous)
      self.children.append(next)
      previous = next

  def paint(self):
    cmds = []
    if isinstance(self.node, Element) and self.node.tag == "pre":
      x2, y2 = self.x + self.width, self.y + self.height
      rect = DrawRect(self.x, self.y, x2, y2, "gray")
      cmds.append(rect)
    if isinstance(self.node, Element) and self.node.tag == "nav" and self.node.attributes.get("class") == "links":
      x2, y2 = self.x + self.width, self.y + self.height
      rect = DrawRect(self.x, self.y, x2, y2, "lightgray")
      cmds.append(rect)
    if isinstance(self.node, Element) and self.node.tag == "div" and self.node.attributes.get("class") == "table-of-contents-title":
      x2, y2 = self.x + self.width, self.y + self.height
      rect = DrawRect(self.x, self.y, x2, y2, "gray")
      cmds.append(rect)

    if self.layout_mode() == "inline":
      for x, y, word, font in self.display_list:
        cmds.append(DrawText(x, y, word, font))
    return cmds

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
    if self.cursor_x + w > self.width:
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
    for index, (rel_x, word, font) in enumerate(self.line):
      y = self.y + baseline - font.metrics("ascent")
      if self.centered:
        x = self.x + (self.width / 2 - line_width / 2) + rel_x
      else:
        x = self.x + rel_x
      self.display_list.append((x, y, word, font))
    max_descent = max(metric["descent"] for metric in metrics)
    self.cursor_y = baseline + 1.25 * max_descent
    self.cursor_x = 0
    self.line = []

class DrawText:
  def __init__(self, x1, y1, text, font):
    self.top = y1
    self.left = x1
    self.text = text
    self.font = font
    self.bottom = y1 + font.metrics("linespace")

  def execute(self, scroll, canvas):
    canvas.create_text(
        self.left, self.top - scroll,
        text=self.text,
        font=self.font,
        anchor='nw', fill="black"
    )

class DrawRect:
  def __init__(self, x1, y1, x2, y2, color):
    self.top = y1
    self.left = x1
    self.bottom = y2
    self.right = x2
    self.color = color

  def execute(self, scroll, canvas):
    canvas.create_rectangle(
        self.left, self.top - scroll,
        self.right, self.bottom - scroll,
        width=0,
        fill=self.color
    )

# layout.py 맨 끝부분
def paint_tree(layout_object, display_list):
    # 1. 현재 노드(layout_object)가 직접 그려야 할 명령들을 리스트에 추가
    display_list.extend(layout_object.paint())
    
    # 2. 모든 자식 노드들을 돌면서 재귀적으로 페인팅 명령 수집
    for child in layout_object.children:
        paint_tree(child, display_list)
