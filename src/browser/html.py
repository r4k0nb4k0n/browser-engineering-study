class Text:

  def __init__(self, text, parent=None):
    self.text = text
    self.children = []
    self.parent = parent

  def __repr__(self):
    return repr(self.text)


class Element:

  def __init__(self, tag, attributes=None, parent=None):
    self.tag = tag
    self.attributes = attributes if attributes is not None else {}
    self.children = []
    self.parent = parent

  def __repr__(self):
    return "<" + self.tag + ">"


# 호환성을 위한 Tag 클래스
class Tag:

  def __init__(self, tag):
    self.tag = tag

  def __repr__(self):
    return f"Tag({self.tag!r})"


def print_tree(node, indent=0):
  print(" " * indent, node)
  for child in node.children:
    print_tree(child, indent + 2)


class HTMLParser:

  SELF_CLOSING_TAGS = [
      "area",
      "base",
      "br",
      "col",
      "embed",
      "hr",
      "img",
      "input",
      "link",
      "meta",
      "param",
      "source",
      "track",
      "wbr",
  ]

  def __init__(self, body):
    self.body = body
    self.unfinished = []

  def parse(self):
    text = ""
    in_tag = False
    for c in self.body:
      if c == "<":
        in_tag = True
        if text:
          self.add_text(text)
        text = ""
      elif c == ">":
        in_tag = False
        self.add_tag(text)
        text = ""
      else:
        text += c
    if not in_tag and text:
      self.add_text(text)
    return self.finish()

  def get_attributes(self, text):
    parts = text.split()
    tag = parts[0].casefold()
    attributes = {}
    for attrpair in parts[1:]:
      if "=" in attrpair:
        key, value = attrpair.split("=", 1)
        if len(value) > 2 and value[0] in ["'", '"'] and value[-1] == value[0]:
          value = value[1:-1]
        attributes[key.casefold()] = value
      else:
        attributes[attrpair.casefold()] = ""
    return tag, attributes

  def add_text(self, text):
    if text.isspace():
      return
    parent = self.unfinished[-1]
    node = Text(text, parent)
    parent.children.append(node)

  def add_tag(self, tag):
    tag, attributes = self.get_attributes(tag)
    if tag.startswith("!"):
      return

    if tag.startswith("/"):
      if len(self.unfinished) == 1:
        return
      node = self.unfinished.pop()
      parent = self.unfinished[-1]
      parent.children.append(node)
    elif tag in self.SELF_CLOSING_TAGS:
      parent = self.unfinished[-1]
      node = Element(tag, attributes, parent)
      parent.children.append(node)
    else:
      parent = self.unfinished[-1] if self.unfinished else None
      node = Element(tag, attributes, parent)
      self.unfinished.append(node)

  def finish(self):
    while len(self.unfinished) > 1:
      node = self.unfinished.pop()
      parent = self.unfinished[-1]
      parent.children.append(node)
    return self.unfinished.pop()


def lex(body, scheme=None):
  return HTMLParser(body).parse()
