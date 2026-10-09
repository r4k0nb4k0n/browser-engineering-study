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

INPUT_WIDTH_PX = 200

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

  def should_paint(self):
    return True

  def paint(self):
    return []

class LineLayout:
  def __init__(self, node, parent, previous):
    self.node = node
    self.parent = parent
    self.previous = previous
    self.children = []

  def layout(self):
    self.width = self.parent.width
    self.x = self.parent.x

    if self.previous:
      self.y = self.previous.y + self.previous.height
    else:
      self.y = self.parent.y

    if not self.children:
      self.height = 0
      return

    for word in self.children:
      word.layout()
    max_ascent = max([word.font.metrics("ascent") for word in self.children])
    baseline = self.y + 1.25 * max_ascent
    for word in self.children:
      word.y = baseline - word.font.metrics("ascent")
    max_descent = max([word.font.metrics("descent") for word in self.children])
    
    self.height = 1.25 * (max_ascent + max_descent)

  def should_paint(self):
    return True

  def paint(self):
    return []


class TextLayout:
  def __init__(self, node, word, parent, previous):
    self.node = node
    self.word = word
    self.children = []
    self.parent = parent
    self.previous = previous

  def layout(self):
    if hasattr(self.node, "style"):
      weight = self.node.style["font-weight"]
      style = self.node.style["font-style"]
      if style == "normal": style = "roman"
      size = int(float(self.node.style["font-size"][:-2]) * .75)
    else:
      weight = "normal"
      style = "roman"
      size = 12
    self.font = get_font(size, weight, style)
    self.width = self.font.measure(self.word)

    if self.previous:
      space = self.previous.font.measure(" ")
      self.x = self.previous.x + space + self.previous.width
    else:
      self.x = self.parent.x

    self.height = self.font.metrics("linespace")

  def should_paint(self):
    return True

  def paint(self):
    color = "black"
    if hasattr(self.node, "style"):
      color = self.node.style["color"]
    return [DrawText(self.x, self.y, self.word, self.font, color)]

class InputLayout:
  def __init__(self, node, parent, previous):
    self.node = node
    self.children = []
    self.parent = parent
    self.previous = previous

  def layout(self):
    if hasattr(self.node, "style"):
      weight = self.node.style["font-weight"]
      style = self.node.style["font-style"]
      if style == "normal": style = "roman"
      size = int(float(self.node.style["font-size"][:-2]) * .75)
    else:
      weight = "normal"
      style = "roman"
      size = 12
    self.font = get_font(size, weight, style)
    self.width = INPUT_WIDTH_PX

    if self.previous:
      space = self.previous.font.measure(" ")
      self.x = self.previous.x + space + self.previous.width
    else:
      self.x = self.parent.x

    self.height = self.font.metrics("linespace")

  def should_paint(self):
    return True

  def self_rect(self):
    return Rect(self.x, self.y, self.x + self.width, self.y + self.height)

  def paint(self):
    cmds = []
    bgcolor = self.node.style.get("background-color", "transparent")
    if bgcolor != "transparent":
      rect = DrawRect(self.self_rect(), bgcolor)
      cmds.append(rect)
    if self.node.tag == "input":
      text = self.node.attributes.get("value", "")
    elif self.node.tag == "button":
      if len(self.node.children) == 1 and isinstance(self.node.children[0], Text):
        text = self.node.children[0].text
      else:
        print("Ignoring HTML contents inside button")
        text = ""
    color = self.node.style["color"]
    cmds.append(DrawText(self.x, self.y, text, self.font, color))
    return cmds


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
    elif self.node.children or self.node.tag == "input":
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
      if not (self.node.children and isinstance(self.node.children[0], Element) and self.node.children[0].attributes.get("class") == "table-of-contents-title"):
        tableOfContentsTitle = Element("div", { "class": "table-of-contents-title" }, self.node)
        tableOfContentsTitle.style = { "font-size": "16px", "font-style": "normal", "font-weight": "normal", "color": "black" }
        toc_text = Text("Table of Contents", tableOfContentsTitle)
        toc_text.style = tableOfContentsTitle.style.copy()
        tableOfContentsTitle.children.append(toc_text)
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
      self.new_line()
      self.recurse(self.node)

    for child in self.children:
      child.layout()

    style_height = "auto"
    if hasattr(self.node, "style"):
      style_height = self.node.style.get("height", "auto")
    if style_height.endswith("px"):
      self.height = int(style_height[:-2])
    else:
      self.height = sum([child.height for child in self.children])

  def layout_intermediate(self):
    previous = None
    for child in self.node.children:
      next = BlockLayout(child, self, previous)
      self.children.append(next)
      previous = next

  def self_rect(self):
    return Rect(self.x, self.y, self.x + self.width, self.y + self.height)

  def should_paint(self):
    return isinstance(self.node, Text) or \
        (self.node.tag != "input" and self.node.tag != "button")

  def paint(self):
    cmds = []
    bgcolor = "transparent"
    if hasattr(self.node, "style"):
      bgcolor = self.node.style.get("background-color", "transparent")
    if bgcolor != "transparent":
      rect = DrawRect(self.self_rect(), bgcolor)
      cmds.append(rect)
    elif isinstance(self.node, Element) and self.node.tag == "nav" and self.node.attributes.get("class") == "links":
      rect = DrawRect(self.self_rect(), "lightgray")
      cmds.append(rect)
    elif isinstance(self.node, Element) and self.node.tag == "div" and self.node.attributes.get("class") == "table-of-contents-title":
      rect = DrawRect(self.self_rect(), "gray")
      cmds.append(rect)

    return cmds

  def recurse(self, node):
    if isinstance(node, Text):
      for word in node.text.split():
        self.word(node, word)
    else:
      if isinstance(node, Element) and (node.tag == "head" or node.tag in HTMLParser.HEAD_TAGS):
        return
      if node.tag == "br":
        self.new_line()
      elif node.tag == "input" or node.tag == "button":
        self.input(node)
      else:
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
      self.new_line()
    line = self.children[-1]
    previous_word = line.children[-1] if line.children else None
    text = TextLayout(node, word, line, previous_word)
    line.children.append(text)
    self.cursor_x += w + font.measure(" ")

  def new_line(self):
    self.cursor_x = 0
    last_line = self.children[-1] if self.children else None
    new_line = LineLayout(self.node, self, last_line)
    self.children.append(new_line)

  def input(self, node):
    w = INPUT_WIDTH_PX
    if self.cursor_x + w > self.width:
      self.new_line()
    line = self.children[-1]
    previous_word = line.children[-1] if line.children else None
    input = InputLayout(node, line, previous_word)
    line.children.append(input)

    weight = node.style["font-weight"]
    style = node.style["font-style"]
    if style == "normal": style = "roman"
    size = int(float(node.style["font-size"][:-2]) * .75)
    font = get_font(size, weight, style)

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


class Rect:
  def __init__(self, left, top, right, bottom):
    self.left = left
    self.top = top
    self.right = right
    self.bottom = bottom

  def contains_point(self, x, y):
    return x >= self.left and x < self.right and y >= self.top and y < self.bottom


class DrawText:
  def __init__(self, x1, y1, text, font, color):
    self.rect = Rect(x1, y1, x1 + font.measure(text), y1 + font.metrics("linespace"))
    self.text = text
    self.font = font
    self.color = color

  def execute(self, scroll, canvas):
    canvas.create_text(
        self.rect.left, self.rect.top - scroll,
        text=self.text,
        font=self.font,
        anchor='nw',
        fill=self.color
    )


class DrawRect:
  def __init__(self, rect, color):
    self.rect = rect
    self.color = color

  def execute(self, scroll, canvas):
    canvas.create_rectangle(
        self.rect.left, self.rect.top - scroll,
        self.rect.right, self.rect.bottom - scroll,
        width=0,
        fill=self.color
    )


class DrawOutline:
  def __init__(self, rect, color, thickness):
    self.rect = rect
    self.color = color
    self.thickness = thickness

  def execute(self, scroll, canvas):
    canvas.create_rectangle(
        self.rect.left, self.rect.top - scroll,
        self.rect.right, self.rect.bottom - scroll,
        width=self.thickness,
        outline=self.color
    )


class DrawLine:
  def __init__(self, x1, y1, x2, y2, color, thickness):
    self.rect = Rect(x1, y1, x2, y2)
    self.color = color
    self.thickness = thickness

  def execute(self, scroll, canvas):
    canvas.create_line(
        self.rect.left, self.rect.top - scroll,
        self.rect.right, self.rect.bottom - scroll,
        fill=self.color, width=self.thickness
    )

# layout.py 맨 끝부분
def paint_tree(layout_object, display_list):
    # 1. 현재 노드(layout_object)가 직접 그려야 할 명령들을 리스트에 추가
    if layout_object.should_paint():
      display_list.extend(layout_object.paint())
    
    # 2. 모든 자식 노드들을 돌면서 재귀적으로 페인팅 명령 수집
    for child in layout_object.children:
        paint_tree(child, display_list)
