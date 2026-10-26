import os
import dukpy
import tkinter
import urllib.parse

from browser.css import CSSParser, DEFAULT_STYLE_SHEET, cascade_priority, style
from browser.html import Element, HTMLParser, Text, ViewSourceParser, tree_to_list
from browser.layout import (
    HEIGHT,
    VSTEP,
    WIDTH,
    DocumentLayout,
    DrawLine,
    DrawOutline,
    DrawRect,
    DrawText,
    Rect,
    get_font,
    paint_tree,
)
from browser.url import URL

SCROLL_STEP = 100
VISITED_LINKS = set()

RUNTIME_JS = open(os.path.join(os.path.dirname(__file__), "runtime.js")).read()
EVENT_DISPATCH_JS = (
    "new Node(dukpy.handle).dispatchEvent(dukpy.type)"
)

class JSContext:
  def __init__(self, tab):
    self.tab = tab
    self.node_to_handle = {}
    self.handle_to_node = {}
    self.interp = dukpy.JSInterpreter()
    self.interp.export_function("log", print)
    self.interp.export_function("querySelectorAll", self.querySelectorAll)
    self.interp.export_function("getAttribute", self.getAttribute)
    self.interp.export_function("innerHTML_set", self.innerHTML_set)
    self.interp.evaljs(RUNTIME_JS)

  def run(self, script, code):
    try:
      return self.interp.evaljs(code)
    except dukpy.JSRuntimeError as e:
      print("Script", script, "crashed", e)

  def dispatch_event(self, type, elt):
    handle = self.node_to_handle.get(elt, -1)
    self.interp.evaljs(
        EVENT_DISPATCH_JS, type=type, handle=handle
    )

  def get_handle(self, elt):
    if elt not in self.node_to_handle:
      handle = len(self.node_to_handle)
      self.node_to_handle[elt] = handle
      self.handle_to_node[handle] = elt
    else:
      handle = self.node_to_handle[elt]
    return handle

  def querySelectorAll(self, selector_text):
    selector = CSSParser(selector_text).selector()
    nodes = [
        node
        for node in tree_to_list(self.tab.nodes, [])
        if selector.matches(node)
    ]
    return [self.get_handle(node) for node in nodes]

  def getAttribute(self, handle, attr):
    elt = self.handle_to_node[handle]
    attr = elt.attributes.get(attr, None)
    return attr if attr else ""

  def innerHTML_set(self, handle, s):
    doc = HTMLParser("<html><body>" + s + "</body></html>").parse()
    new_nodes = doc.children[0].children
    elt = self.handle_to_node[handle]
    elt.children = new_nodes
    for child in elt.children:
      child.parent = elt
    self.tab.render()

class Tab:

  def __init__(self, tab_height):
    self.url = None
    self.history = []
    self.history_pointer = -1
    self.scroll = 0
    self.tab_height = tab_height
    self.focus = None
    self.js = None

  def load(self, url, payload=None, update_history=True):
    if update_history:
      self.history = self.history[: self.history_pointer + 1]
      self.history.append(url)
      self.history_pointer = len(self.history) - 1
    self.url = url
    if url.scheme != "view-source":
      VISITED_LINKS.add(str(url))
    self.scroll = 0
    body = url.request(payload)
    if url.scheme == "view-source":
      self.nodes = ViewSourceParser(body).parse()
    else:
      self.nodes = HTMLParser(body).parse()

    for node in tree_to_list(self.nodes, []):
      if (
          isinstance(node, Element)
          and node.tag == "a"
          and "href" in node.attributes
          and str(self.url.resolve(node.attributes["href"])) in VISITED_LINKS
      ):
        node.is_visited_link = True

    scripts = [
        node.attributes["src"]
        for node in tree_to_list(self.nodes, [])
        if isinstance(node, Element)
        and node.tag == "script"
        and "src" in node.attributes
    ]
    self.js = JSContext(self)
    for script in scripts:
      script_url = url.resolve(script)
      try:
        body = script_url.request()
      except Exception:
        continue
      self.js.run(script, body)

    self.rules = DEFAULT_STYLE_SHEET.copy()
    links = [
        node.attributes["href"]
        for node in tree_to_list(self.nodes, [])
        if isinstance(node, Element)
        and node.tag == "link"
        and node.attributes.get("rel") == "stylesheet"
        and "href" in node.attributes
    ]
    for link in links:
      style_url = url.resolve(link)
      try:
        body = style_url.request()
      except Exception:
        continue
      self.rules.extend(CSSParser(body).parse())

    style_tags = [
        node
        for node in tree_to_list(self.nodes, [])
        if isinstance(node, Element) and node.tag == "style"
    ]
    for style_tag in style_tags:
      css_text = "".join(
          [child.text for child in style_tag.children if isinstance(child, Text)]
      )
      self.rules.extend(CSSParser(css_text).parse())
    
    self.render()

  def render(self):
    style(self.nodes, sorted(self.rules, key=cascade_priority))
    self.document = DocumentLayout(self.nodes)
    self.document.layout()
    self.display_list = []
    paint_tree(self.document, self.display_list)

  def draw(self, canvas, offset):
    for cmd in self.display_list:
      if cmd.rect.top > self.scroll + self.tab_height:
        continue
      if cmd.rect.bottom < self.scroll:
        continue
      cmd.execute(self.scroll - offset, canvas)

  def scrolldown(self):
    max_y = max(self.document.height + 2 * VSTEP - self.tab_height, 0)
    self.scroll = min(self.scroll + SCROLL_STEP, max_y)

  def click(self, x, y):
    if self.focus:
      self.focus.is_focused = False
    self.focus = None
    y += self.scroll

    objs = [
        obj
        for obj in tree_to_list(self.document, [])
        if obj.x <= x < obj.x + obj.width and obj.y <= y < obj.y + obj.height
    ]
    if not objs:
      return self.render()
    elt = objs[-1].node

    while elt:
      if isinstance(elt, Text):
        pass
      elif elt.tag == "a" and "href" in elt.attributes:
        if self.js:
          self.js.dispatch_event("click", elt)
        url = self.url.resolve(elt.attributes["href"])
        return self.load(url)
      elif elt.tag == "input":
        if self.js:
          self.js.dispatch_event("click", elt)
        elt.attributes["value"] = ""
        self.focus = elt
        elt.is_focused = True
        return self.render()
      elif elt.tag == "button":
        if self.js:
          self.js.dispatch_event("click", elt)
        form = elt
        while form:
          if form.tag == "form" and "action" in form.attributes:
            return self.submit_form(form)
          form = form.parent
      elt = elt.parent
    self.render()

  def enter(self):
    if self.focus and self.focus.tag == "input":
      elt = self.focus
      while elt:
        if elt.tag == "form" and "action" in elt.attributes:
          return self.submit_form(elt)
        elt = elt.parent

  def submit_form(self, elt):
    if self.js:
      self.js.dispatch_event("submit", elt)
    inputs = [
        node
        for node in tree_to_list(elt, [])
        if isinstance(node, Element)
        and node.tag == "input"
        and "name" in node.attributes
    ]
    body = ""
    for input in inputs:
      name = input.attributes["name"]
      value = input.attributes.get("value", "")
      name = urllib.parse.quote(name)
      value = urllib.parse.quote(value)
      body += "&" + name + "=" + value
    body = body[1:]
    url = self.url.resolve(elt.attributes["action"])
    self.load(url, body)

  def keypress(self, char):
    if self.focus:
      if self.js:
        self.js.dispatch_event("keydown", self.focus)
      self.focus.attributes["value"] += char
      self.render()

  def go_back(self):
    if self.history_pointer > 0:
      self.history_pointer -= 1
      self.load(self.history[self.history_pointer], update_history=False)

  def go_forward(self):
    if self.history_pointer < len(self.history) - 1:
      self.history_pointer += 1
      self.load(self.history[self.history_pointer], update_history=False)


class Chrome:

  def __init__(self, browser):
    self.browser = browser
    self.focus = None
    self.address_bar = ""
    self.address_bar_cursor_index = 0
    self.document = None
    self.display_list = []
    self.bottom = 60
    self.render()

  def html(self):
    active_tab = self.browser.active_tab
    lines = ['<div class="chrome">']

    # 1. 탭 바: 새 탭 버튼(+) 및 열려 있는 탭 목록(<a>)
    lines.append('<button class="newtab" style="width:30px;">+</button>')
    for i, tab in enumerate(self.browser.tabs):
      if tab == active_tab:
        lines.append(f' <a href="tab:{i}"><b>Tab {i}</b></a>')
      else:
        lines.append(f' <a href="tab:{i}">Tab {i}</a>')
    lines.append("<br>")

    # 2. 내비게이션 바: 뒤로가기(◀), 앞으로가기(▶), 주소창(<input>)
    can_back = active_tab and active_tab.history_pointer > 0
    can_forward = (
        active_tab and active_tab.history_pointer < len(active_tab.history) - 1
    )
    back_style = "width:30px;" if can_back else "width:30px;color:gray;"
    fwd_style = "width:30px;" if can_forward else "width:30px;color:gray;"

    lines.append(f'<button class="back" style="{back_style}">◀</button>')
    lines.append(f'<button class="forward" style="{fwd_style}">▶</button>')
    lines.append(' <input class="address" style="width:680px;">')
    lines.append("</div>")
    return "".join(lines)

  def render(self):
    active_tab = self.browser.active_tab
    current_url = str(active_tab.url) if (active_tab and active_tab.url) else ""
    val = self.address_bar if self.focus == "address bar" else current_url

    tree = HTMLParser(self.html()).parse()
    style(tree, sorted(DEFAULT_STYLE_SHEET, key=cascade_priority))

    for node in tree_to_list(tree, []):
      if isinstance(node, Element) and node.tag == "input":
        node.attributes["value"] = val
        if self.focus == "address bar":
          node.is_focused = True
          node.cursor_index = self.address_bar_cursor_index

    self.document = DocumentLayout(tree)
    self.document.layout()
    self.bottom = self.document.height + 2 * VSTEP
    self.display_list = []
    paint_tree(self.document, self.display_list)

  def paint(self):
    self.render()
    cmds = [
        DrawRect(Rect(0, 0, WIDTH, self.bottom), "white"),
        DrawLine(0, self.bottom, WIDTH, self.bottom, "black", 1),
    ]
    cmds.extend(self.display_list)
    return cmds

  def click(self, x, y):
    self.render()
    objs = [
        obj
        for obj in tree_to_list(self.document, [])
        if obj.x <= x < obj.x + obj.width and obj.y <= y < obj.y + obj.height
    ]
    if not objs:
      self.focus = None
      return

    elt = objs[-1].node
    while elt:
      if isinstance(elt, Text):
        pass
      elif elt.tag == "button":
        self.focus = None
        cls = elt.attributes.get("class", "")
        if "newtab" in cls:
          self.browser.new_tab(URL("https://browser.engineering/"))
        elif "back" in cls and self.browser.active_tab:
          self.browser.active_tab.go_back()
        elif "forward" in cls and self.browser.active_tab:
          self.browser.active_tab.go_forward()
        return
      elif elt.tag == "a" and "href" in elt.attributes:
        self.focus = None
        href = elt.attributes["href"]
        if href.startswith("tab:"):
          tab_idx = int(href[4:])
          if 0 <= tab_idx < len(self.browser.tabs):
            self.browser.active_tab = self.browser.tabs[tab_idx]
        return
      elif elt.tag == "input":
        self.focus = "address bar"
        if self.browser.active_tab and self.browser.active_tab.url:
          self.address_bar = str(self.browser.active_tab.url)
        else:
          self.address_bar = ""
        self.address_bar_cursor_index = len(self.address_bar)
        return
      elt = elt.parent
    self.focus = None

  def blur(self):
    self.focus = None

  def keypress(self, char):
    if self.focus == "address bar":
      self.address_bar = (
          self.address_bar[:self.address_bar_cursor_index]
          + char
          + self.address_bar[self.address_bar_cursor_index:]
      )
      self.address_bar_cursor_index += 1
      return True
    return False

  def backspace(self):
    if (
        self.focus == "address bar"
        and self.address_bar != ""
        and self.address_bar_cursor_index > 0
    ):
      self.address_bar = (
          self.address_bar[:self.address_bar_cursor_index - 1]
          + self.address_bar[self.address_bar_cursor_index:]
      )
      self.address_bar_cursor_index -= 1

  def enter(self):
    if self.focus == "address bar" and self.address_bar != "":
      self.browser.active_tab.load(URL(self.address_bar))
      self.address_bar_cursor_index = len(self.address_bar)
      self.focus = None

  def arrow_left(self):
    if self.focus == "address bar":
      self.address_bar_cursor_index = max(self.address_bar_cursor_index - 1, 0)

  def arrow_right(self):
    if self.focus == "address bar":
      self.address_bar_cursor_index = min(
          self.address_bar_cursor_index + 1, len(self.address_bar)
      )


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
    self.window.bind("<Down>", self.handle_down)
    self.window.bind("<Button-1>", self.handle_click)
    self.window.bind("<Key>", self.handle_key)
    self.window.bind("<BackSpace>", self.handle_backspace)
    self.window.bind("<Return>", self.handle_enter)
    self.window.bind("<Left>", self.handle_left)
    self.window.bind("<Right>", self.handle_right)

    self.tabs = []
    self.active_tab = None
    self.focus = None
    self.chrome = Chrome(self)

  def draw(self):
    self.canvas.delete("all")
    self.active_tab.draw(self.canvas, self.chrome.bottom)
    for cmd in self.chrome.paint():
      cmd.execute(0, self.canvas)
    self.canvas.update_idletasks()

  def handle_down(self, e):
    self.active_tab.scrolldown()
    self.draw()

  def handle_click(self, e):
    if e.y < self.chrome.bottom:
      self.focus = None
      self.chrome.click(e.x, e.y)
    else:
      self.focus = "content"
      self.chrome.blur()
      tab_y = e.y - self.chrome.bottom
      self.active_tab.click(e.x, tab_y)
    self.draw()

  def handle_key(self, e):
    if len(e.char) == 0:
      return
    if not (0x20 <= ord(e.char) < 0x7F):
      return
    if self.chrome.keypress(e.char):
      self.draw()
    elif self.focus == "content":
      self.active_tab.keypress(e.char)
      self.draw()

  def handle_backspace(self, e):
    self.chrome.backspace()
    self.draw()

  def handle_enter(self, e):
    if self.focus == "content":
      self.active_tab.enter()
    else:
      self.chrome.enter()
    self.draw()

  def handle_left(self, e):
    self.chrome.arrow_left()
    self.draw()

  def handle_right(self, e):
    self.chrome.arrow_right()
    self.draw()

  def new_tab(self, url):
    new_tab = Tab(HEIGHT - self.chrome.bottom)
    new_tab.load(url)
    self.active_tab = new_tab
    self.tabs.append(new_tab)
    self.draw()