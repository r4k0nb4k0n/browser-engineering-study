import socket
import ssl

from browser.html import Text, Tag, lex


class URL:
  def __init__(self, url):
    # split by the first ':' to get the scheme
    self.scheme, remainder = url.split(":", 1)
    assert self.scheme in ["http", "https", "file", "data", "view-source"]

    self.host = None
    self.port = None
    self.path = None
    self.data = None

    if self.scheme == "view-source":
      self.inner_url = URL(remainder)
    elif self.scheme == "data":
      if "," not in remainder:
          raise ValueError(f"Invalid data URL: {url} - missing comma.")
      _, data_content = remainder.split(",", 1)
      self.data = data_content
    else:
      if remainder.startswith("//"):
        remainder = remainder[2:]
      if "/" not in remainder:
        remainder = remainder + "/"
      self.host, remainder = remainder.split("/", 1)
      self.path = "/" + remainder

      if self.scheme == "http":
        self.port = 80
      elif self.scheme == "https":
        self.port = 443

      if ":" in self.host:
        self.host, port = self.host.split(":", 1)
        self.port = int(port)

  def resolve(self, url):
    if "://" in url: return URL(url)
    if not url.startswith("/"):
      dir, _ = self.path.rsplit("/", 1)
      while url.startswith("../"):
        _, url = url.split("/", 1)
        if "/" in dir:
          dir, _ = dir.rsplit("/", 1)
      url = dir + "/" + url
    if url.startswith("//"):
      return URL(self.scheme + ":" + url)
    elif self.scheme == "file":
      return URL("file://" + url)
    else:
      return URL(self.scheme + "://" + self.host + ":" + str(self.port) + url)

  def request(self, headers=None):
    if self.scheme == "view-source":
      return self.inner_url.request(headers)

    if self.scheme == "data":
      return self.data

    if self.scheme == "file":
      file_path = self.path
      with open(file_path, "r") as f:
        return f.read()

    s = socket.socket(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP
    )
    if self.scheme == "https":
      ctx = ssl.create_default_context()
      s = ctx.wrap_socket(s, server_hostname=self.host)
    s.connect((self.host, self.port))

    default_headers = {
        "Host": self.host,
        "Connection": "close",
        "User-Agent": "Shenanigan"
    }
    if headers:
        default_headers.update(headers)
    request_lines = [f"GET {self.path} HTTP/1.1\r\n"]
    for header_name, header_value in default_headers.items():
        request_lines.append(f"{header_name}: {header_value}\r\n")
    request_lines.append("\r\n")

    request_data = "".join(request_lines).encode("utf8")
    s.send(request_data)

    response = s.makefile("r", encoding="utf8", newline="\r\n")
    statusline = response.readline()
    version, status, explanation = statusline.split(" ", 2)
    response_headers = {}
    while True:
      line = response.readline()
      if line == "\r\n": break
      header, value = line.split(":", 1)
      response_headers[header.casefold()] = value.strip()
    assert "transfer-encoding" not in response_headers
    assert "content-encoding" not in response_headers
    body = response.read()
    s.close()
    return body


def load(url, headers=None):
  body = url.request(headers=headers)
  for tok in lex(body, url.scheme):
    if isinstance(tok, Text):
      print(tok.text, end="")


if __name__ == "__main__":
  load(URL("https://browser.engineering/"))
