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


def tree_to_list(tree, list):
  list.append(tree)
  for child in tree.children:
    tree_to_list(child, list)
  return list


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

  HEAD_TAGS = [
      "base",
      "basefont",
      "bgsound",
      "noscript",
      "link",
      "meta",
      "title",
      "style",
      "script",
  ]

  def __init__(self, body):
    self.body = body
    self.unfinished = []

  def parse(self):
    text = ""
    in_tag = False
    in_comment = False
    i = 0
    while i < len(self.body):
      c = self.body[i]
      if in_comment:
        if self.body[i:].startswith("-->"):
          in_comment = False
          i += 3
        else:
          i += 1
      elif self.body[i:].startswith("<!--"):
        in_comment = True
        if text:
          self.add_text(text)
        text = ""
        i += 4
      elif c == "<":
        in_tag = True
        if text:
          self.add_text(text)
        text = ""
        i += 1
      elif c == ">" and in_tag:
        in_tag = False
        self.add_tag(text)
        text = ""
        i += 1
      else:
        text += c
        i += 1
    if not in_tag and not in_comment and text:
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

  def implicit_tags(self, tag):
    while True:
      open_tags = [node.tag for node in self.unfinished]
      if open_tags == [] and tag != "html":
        self.add_tag("html")
      elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
        if tag in self.HEAD_TAGS:
          self.add_tag("head")
        else:
          self.add_tag("body")
      elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
        self.add_tag("/head")
      else:
        break

  def add_text(self, text):
    if text.isspace():
      return
    self.implicit_tags(None)
    parent = self.unfinished[-1]
    node = Text(text, parent)
    parent.children.append(node)

  def add_tag(self, tag):
    tag, attributes = self.get_attributes(tag)
    if tag.startswith("!"):
      return

    self.implicit_tags(tag)

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
    if not self.unfinished:
      self.implicit_tags(None)
    while len(self.unfinished) > 1:
      node = self.unfinished.pop()
      parent = self.unfinished[-1]
      parent.children.append(node)
    return self.unfinished.pop()


class ViewSourceParser(HTMLParser):

  def parse(self):
    self.unfinished = [Element("pre", {}, None)]
    text = ""
    in_tag = False
    i = 0
    while i < len(self.body):
      c = self.body[i]
      if c == "<":
        in_tag = True
        if text:
          # 인덴트 성격의 공백은 일반 폰트
          if text.isspace():
            parent = self.unfinished[-1]
            parent.children.append(Text(text, parent))
          # but make text contents bold.
          else:
            b_node = Element("b", {}, self.unfinished[-1])
            self.unfinished[-1].children.append(b_node)
            b_node.children.append(Text(text, b_node))
        text = "<"
        i += 1
      elif c == ">":
        in_tag = False
        text += ">"
        # Keep source code for HTML tags in a normal font,
        parent = self.unfinished[-1]
        parent.children.append(Text(text, parent))
        text = ""
        i += 1
      else:
        text += c
        i += 1
    if text:
      # Keep source code for HTML tags in a normal font,
      if in_tag or text.isspace():
        parent = self.unfinished[-1]
        parent.children.append(Text(text, parent))
      # but make text contents bold.
      else:
        b_node = Element("b", {}, self.unfinished[-1])
        self.unfinished[-1].children.append(b_node)
        b_node.children.append(Text(text, b_node))
    return self.unfinished[0]


def lex(body, scheme=None):
  if scheme == "view-source":
    return ViewSourceParser(body).parse()
  return HTMLParser(body).parse()
