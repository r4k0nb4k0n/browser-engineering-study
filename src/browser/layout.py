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
    style_width = "auto"
    if (hasattr(self.node, "style")):
      style_width = self.node.style.get("width", "auto")
    if style_width.endswith("px"):
      self.width = int(style_width[:-2])
    else:
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
        if isinstance(child, Element) and (child.tag == "head" or child.tag in HTMLParser.HEAD_TAGS):
          continue
        next = BlockLayout(child, self, previous)
        self.children.append(next)
        previous = next
    else:
      self.display_list = []
      self.cursor_x = 0
      self.cursor_y = 0
      self.line = []
      self.recurse(self.node)
      self.flush()

    for child in self.children:
      child.layout()

    style_height = "auto"
    if hasattr(self.node, "style"):
      style_height = self.node.style.get("height", "auto")
    if style_height.endswith("px"):
      self.height = int(style_height[:-2])
    elif mode == "block":
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
    bgcolor = "transparent"
    if hasattr(self.node, "style"):
      bgcolor = self.node.style.get("background-color", "transparent")
    if bgcolor != "transparent":
      x2, y2 = self.x + self.width, self.y + self.height
      rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
      cmds.append(rect)
    elif isinstance(self.node, Element) and self.node.tag == "nav" and self.node.attributes.get("class") == "links":
      x2, y2 = self.x + self.width, self.y + self.height
      rect = DrawRect(self.x, self.y, x2, y2, "lightgray")
      cmds.append(rect)
    elif isinstance(self.node, Element) and self.node.tag == "div" and self.node.attributes.get("class") == "table-of-contents-title":
      x2, y2 = self.x + self.width, self.y + self.height
      rect = DrawRect(self.x, self.y, x2, y2, "gray")
      cmds.append(rect)

    if self.layout_mode() == "inline":
      for x, y, word, font, color in self.display_list:
        cmds.append(DrawText(x, y, word, font, color))
    return cmds

  def recurse(self, node):
    if isinstance(node, Text):
      for word in node.text.split():
        self.word(node, word)
    else:
      if isinstance(node, Element) and (node.tag == "head" or node.tag in HTMLParser.HEAD_TAGS):
        return
      if node.tag == "br":
        self.flush()
      for child in node.children:
        self.recurse(child)

  def word(self, node, word):
    if hasattr(node, "style"):
      weight = node.style["font-weight"]
      style = node.style["font-style"]
      if style == "normal": style = "roman"
      size = int(float(node.style["font-size"][:-2]) * .75)
      color = node.style["color"]
    else:
      weight = "normal"
      style = "roman"
      size = 12
      color = "black"
    font = get_font(size, weight, style)
    w = font.measure(word)
    if self.cursor_x + w > self.width:
      self.flush()
    self.line.append((self.cursor_x, word, font, color))
    self.cursor_x += w + font.measure(" ")

  def flush(self):
    if not self.line:
      return
    metrics = [font.metrics() for x, word, font, color in self.line]
    max_ascent = max([metric["ascent"] for metric in metrics])
    baseline = self.cursor_y + 1.25 * max_ascent
    for rel_x, word, font, color in self.line:
      x = self.x + rel_x
      y = self.y + baseline - font.metrics("ascent")
      self.display_list.append((x, y, word, font, color))
    max_descent = max([metric["descent"] for metric in metrics])
    self.cursor_y = baseline + 1.25 * max_descent
    self.cursor_x = 0
    self.line = []


class DrawText:
  def __init__(self, x1, y1, text, font, color):
    self.top = y1
    self.left = x1
    self.text = text
    self.font = font
    self.color = color
    self.bottom = y1 + font.metrics("linespace")

  def execute(self, scroll, canvas):
    canvas.create_text(
        self.left, self.top - scroll,
        text=self.text,
        font=self.font,
        anchor='nw',
        fill=self.color
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
