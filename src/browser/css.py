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

  def selector(self):
    out = TagSelector(self.word().casefold())
    self.whitespace()
    while self.i < len(self.s) and self.s[self.i] != "{":
      tag = self.word()
      descendant = TagSelector(tag.casefold())
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

  def matches(self, node):
    return isinstance(node, Element) and self.tag == node.tag

  def __repr__(self):
    return f"TagSelector(tag={self.tag!r})"


class DescendantSelector:

  def __init__(self, ancestor, descendant):
    self.ancestor = ancestor
    self.descendant = descendant

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


def style(node, rules):
  node.style = {}
  for selector, body in rules:
    if not selector.matches(node): continue
    for property, value in body.items():
      node.style[property] = value
  if isinstance(node, Element) and "style" in node.attributes:
    pairs = CSSParser(node.attributes["style"]).body()
    for property, value in pairs.items():
      node.style[property] = value
  for child in node.children:
    style(child, rules)


DEFAULT_STYLE_SHEET = CSSParser(
    open(Path(__file__).parent / "browser.css").read()
).parse()

