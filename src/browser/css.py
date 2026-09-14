from pathlib import Path

from browser.html import Element


class CSSParser:

  def __init__(self, s):
    self.s = s
    self.i = 0

  def whitespace(self):
    while self.i < len(self.s) and self.s[self.i].isspace():
      self.i += 1

  def word(self):
    start = self.i
    while self.i < len(self.s):
      if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
        self.i += 1
      else:
        break
    if not (self.i > start):
      raise Exception("Parsing error")
    return self.s[start:self.i]

  def literal(self, literal):
    if not (self.i < len(self.s) and self.s[self.i] == literal):
      raise Exception("Parsing error")
    self.i += 1

  def pair(self):
    prop = self.word()
    self.whitespace()
    self.literal(":")
    self.whitespace()
    val = self.word()
    return prop.casefold(), val

  def ignore_until(self, chars):
    while self.i < len(self.s):
      if self.s[self.i] in chars:
        return self.s[self.i]
      else:
        self.i += 1
    return None

  def simple_selector(self):
    tag = self.word().casefold()
    out = TagSelector(tag)
    while self.i < len(self.s) and self.s[self.i] == ":":
      if self.s[self.i:].startswith(":has("):
        self.i += len(":has(")
        self.whitespace()
        descendant = self.selector()
        self.whitespace()
        self.literal(")")
        out = HasSelector(out, descendant)
      else:
        break
    return out

  def selector(self):
    out = self.simple_selector()
    self.whitespace()
    while self.i < len(self.s) and self.s[self.i] not in "{)":
      descendant = self.simple_selector()
      out = DescendantSelector(out, descendant)
      self.whitespace()
    return out

  def body(self):
    pairs = {}
    while self.i < len(self.s) and self.s[self.i] != "}":
      try:
        prop, val = self.pair()
        pairs[prop] = val
        self.whitespace()
        self.literal(";")
        self.whitespace()
      except Exception:
        why = self.ignore_until([";", "}"])
        if why == ";":
          self.literal(";")
          self.whitespace()
        else:
          break
    return pairs

  def parse(self):
    rules = []
    while self.i < len(self.s):
      try:
        self.whitespace()
        selector = self.selector()
        self.literal("{")
        self.whitespace()
        body = self.body()
        self.literal("}")
        rules.append((selector, body))
      except Exception:
        why = self.ignore_until(["}"])
        if why == "}":
          self.literal("}")
          self.whitespace()
        else:
          break
    return rules


class TagSelector:

  def __init__(self, tag):
    self.tag = tag
    self.priority = 1

  def matches(self, node):
    return isinstance(node, Element) and self.tag == node.tag

  def __repr__(self):
    return f"TagSelector(tag={self.tag!r})"


class DescendantSelector:

  def __init__(self, ancestor, descendant):
    self.ancestor = ancestor
    self.descendant = descendant
    self.priority = ancestor.priority + descendant.priority

  def matches(self, node):
    if not self.descendant.matches(node):
      return False
    while node.parent:
      if self.ancestor.matches(node.parent):
        return True
      node = node.parent
    return False

  def __repr__(self):
    return f"DescendantSelector(ancestor={self.ancestor!r}, descendant={self.descendant!r})"

class HasSelector:

  def __init__(self, ancestor, descendant):
    self.ancestor = ancestor
    self.descendant = descendant
    self.priority = ancestor.priority + descendant.priority

  def matches(self, node):
    if not self.ancestor.matches(node):
      return False
    return self.has_descendant(node)

  def has_descendant(self, node):
    for child in node.children:
      if isinstance(child, Element):
        if self.descendant.matches(child):
          return True
        if self.has_descendant(child):
          return True
    return False

  def __repr__(self):
    return f"HasSelector(ancestor={self.ancestor!r}, descendant={self.descendant!r})"

def cascade_priority(rule):
  selector, body = rule
  return selector.priority


INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}


def style(node, rules):
  node.style = {}
  for property, default_value in INHERITED_PROPERTIES.items():
    if node.parent:
      node.style[property] = node.parent.style[property]
    else:
      node.style[property] = default_value
  for selector, body in rules:
    if not selector.matches(node): continue
    for property, value in body.items():
      node.style[property] = value
  if isinstance(node, Element) and "style" in node.attributes:
    pairs = CSSParser(node.attributes["style"]).body()
    for property, value in pairs.items():
      node.style[property] = value
  if node.style["font-size"].endswith("%"):
    if node.parent:
      parent_font_size = node.parent.style["font-size"]
    else:
      parent_font_size = INHERITED_PROPERTIES["font-size"]
    node_pct = float(node.style["font-size"][:-1]) / 100
    parent_px = float(parent_font_size[:-2])
    node.style["font-size"] = str(node_pct * parent_px) + "px"
  for child in node.children:
    style(child, rules)


DEFAULT_STYLE_SHEET = CSSParser(
    open(Path(__file__).parent / "browser.css").read()
).parse()

