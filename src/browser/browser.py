import tkinter

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

class Tab:

  def __init__(self, tab_height):
    self.url = None
    self.history = []
    self.history_pointer = -1
    self.scroll = 0
    self.tab_height = tab_height
    self.focus = None

  def load(self, url, update_history=True):
    if update_history:
      self.history = self.history[: self.history_pointer + 1]
      self.history.append(url)
      self.history_pointer = len(self.history) - 1
    self.url = url
    if url.scheme != "view-source":
      VISITED_LINKS.add(str(url))
    self.scroll = 0
    body = url.request()
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
        url = self.url.resolve(elt.attributes["href"])
        return self.load(url)
      elif elt.tag == "input":
        elt.attributes["value"] = ""
        self.focus = elt
        elt.is_focused = True
        return self.render()
      elt = elt.parent
    self.render()

  def keypress(self, char):
    if self.focus:
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
    self.font = get_font(20, "normal", "roman")
    self.font_height = self.font.metrics("linespace")
    self.padding = 5
    self.tabbar_top = 0
    self.tabbar_bottom = self.font_height + 2 * self.padding
    plus_width = self.font.measure("+") + 2 * self.padding
    self.newtab_rect = Rect(
        self.padding,
        self.padding,
        self.padding + plus_width,
        self.padding + self.font_height,
    )
    self.urlbar_top = self.tabbar_bottom
    self.urlbar_bottom = (
        self.urlbar_top + self.font_height + 2 * self.padding
    )
    self.bottom = self.urlbar_bottom

    back_width = self.font.measure("<") + 2 * self.padding
    self.back_rect = Rect(
        self.padding,
        self.urlbar_top + self.padding,
        self.padding + back_width,
        self.urlbar_bottom - self.padding,
    )

    forward_width = self.font.measure(">") + 2 * self.padding
    self.forward_rect = Rect(
        self.back_rect.right + self.padding,
        self.urlbar_top + self.padding,
        self.back_rect.right + self.padding + forward_width,
        self.urlbar_bottom - self.padding,
    )

    self.address_rect = Rect(
        self.forward_rect.right + self.padding,
        self.urlbar_top + self.padding,
        WIDTH - self.padding,
        self.urlbar_bottom - self.padding,
    )
    self.focus = None
    self.address_bar = ""
    self.address_bar_cursor_index = 0

  def tab_rect(self, i):
    tabs_start = self.newtab_rect.right + self.padding
    tab_width = self.font.measure("Tab X") + 2 * self.padding
    return Rect(
        tabs_start + tab_width * i,
        self.tabbar_top,
        tabs_start + tab_width * (i + 1),
        self.tabbar_bottom,
    )

  def paint(self):
    cmds = []
    # Chrome background & bottom separator line
    cmds.append(DrawRect(Rect(0, 0, WIDTH, self.bottom), "white"))
    cmds.append(DrawLine(0, self.bottom, WIDTH, self.bottom, "black", 1))

    # New tab (+) button
    cmds.append(DrawOutline(self.newtab_rect, "black", 1))
    cmds.append(
        DrawText(
            self.newtab_rect.left + self.padding,
            self.newtab_rect.top,
            "+",
            self.font,
            "black",
        )
    )

    # Tabs
    for i, tab in enumerate(self.browser.tabs):
      bounds = self.tab_rect(i)
      cmds.append(DrawLine(bounds.left, 0, bounds.left, bounds.bottom, "black", 1))
      cmds.append(DrawLine(bounds.right, 0, bounds.right, bounds.bottom, "black", 1))
      cmds.append(
          DrawText(
              bounds.left + self.padding,
              bounds.top + self.padding,
              f"Tab {i}",
              self.font,
              "black",
          )
      )
      if tab == self.browser.active_tab:
        cmds.append(DrawLine(0, bounds.bottom, bounds.left, bounds.bottom, "black", 1))
        cmds.append(
            DrawLine(bounds.right, bounds.bottom, WIDTH, bounds.bottom, "black", 1)
        )

    tab = self.browser.active_tab
    back_color = "black" if tab and tab.history_pointer > 0 else "gray"
    forward_color = (
        "black"
        if tab and tab.history_pointer < len(tab.history) - 1
        else "gray"
    )

    # Back (<) button
    cmds.append(DrawOutline(self.back_rect, back_color, 1))
    cmds.append(
        DrawText(
            self.back_rect.left + self.padding,
            self.back_rect.top,
            "<",
            self.font,
            back_color,
        )
    )

    # Forward (>) button
    cmds.append(DrawOutline(self.forward_rect, forward_color, 1))
    cmds.append(
        DrawText(
            self.forward_rect.left + self.padding,
            self.forward_rect.top,
            ">",
            self.font,
            forward_color,
        )
    )

    # Address bar
    cmds.append(DrawOutline(self.address_rect, "black", 1))
    if self.focus == "address bar":
      text = self.address_bar.replace("\n", "").replace("\r", "")
      cmds.append(
          DrawText(
              self.address_rect.left + self.padding,
              self.address_rect.top,
              text,
              self.font,
              "black",
          )
      )
      w = self.font.measure(text[:self.address_bar_cursor_index])
      cmds.append(
          DrawLine(
              self.address_rect.left + self.padding + w,
              self.address_rect.top,
              self.address_rect.left + self.padding + w,
              self.address_rect.bottom,
              "red",
              1,
          )
      )
    else:
      if self.browser.active_tab:
        url = str(self.browser.active_tab.url).replace("\n", "").replace("\r", "")
        cmds.append(
            DrawText(
                self.address_rect.left + self.padding,
                self.address_rect.top,
                url,
                self.font,
                "black",
            )
        )

    return cmds

  def click(self, x, y):
    self.focus = None
    if self.newtab_rect.contains_point(x, y):
      self.browser.new_tab(URL("https://browser.engineering/"))
    elif self.back_rect.contains_point(x, y):
      self.browser.active_tab.go_back()
    elif self.forward_rect.contains_point(x, y):
      self.browser.active_tab.go_forward()
    elif self.address_rect.contains_point(x, y):
      self.focus = "address bar"
      if self.browser.active_tab and self.browser.active_tab.url:
        self.address_bar = str(self.browser.active_tab.url)
      else:
        self.address_bar = ""
      self.address_bar_cursor_index = len(self.address_bar)
    else:
      for i, tab in enumerate(self.browser.tabs):
        if self.tab_rect(i).contains_point(x, y):
          self.browser.active_tab = tab
          break

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