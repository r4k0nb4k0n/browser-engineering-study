class Text:
  def __init__(self, text):
    self.text = text

  def __repr__(self):
    return f"Text({self.text!r})"


class Tag:
  def __init__(self, tag):
    self.tag = tag

  def __repr__(self):
    return f"Tag({self.tag!r})"


def _decode_entity(name):
  if name == "lt":
    return "<"
  if name == "gt":
    return ">"
  return f"&{name};"


def lex(body, scheme=None):
  """HTML body → Text/Tag 토큰 리스트 (3.4 Styling Text)."""
  if scheme == "view-source":
    return [Text(body)]

  out = []
  buffer = ""
  in_tag = False
  in_html_entity = False
  html_entity = ""
  for c in body:
    if in_html_entity:
      if c == ";":
        in_html_entity = False
        buffer += _decode_entity(html_entity)
        html_entity = ""
      else:
        html_entity += c
    elif c == "<":
      in_tag = True
      if buffer:
        out.append(Text(buffer))
      buffer = ""
    elif c == ">":
      in_tag = False
      out.append(Tag(buffer))
      buffer = ""
    elif c == "&" and not in_tag:
      in_html_entity = True
      html_entity = ""
    else:
      buffer += c
  if not in_tag and buffer:
    out.append(Text(buffer))
  return out
