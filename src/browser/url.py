import socket
import ssl


class URL:
  def __init__(self, url):
    # split by the first ':' to get the scheme
    self.scheme, remainder = url.split(":", 1)
    assert self.scheme in ["http", "https", "file", "data", "view-source"]

    self.host = None
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
    if self.scheme == "http":
      self.port = 80
    elif self.scheme == "https":
      self.port = 443
    if self.scheme == "https":
      ctx = ssl.create_default_context()
      s = ctx.wrap_socket(s, server_hostname=self.host)
    if ":" in self.host:
      self.host, port = self.host.split(":", 1)
      self.port = int(port)
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


def lex(body, scheme=None):
  if scheme == "view-source":
    return body

  text = ""
  in_tag = False
  in_html_entity = False
  html_entity = ""
  for c in body:
    if c == "<":
      in_tag = True
    elif c == ">":
      in_tag = False
    elif c == "&":
      in_html_entity = True
    elif in_html_entity:
      if c == ";":
        in_html_entity = False
        if html_entity == "lt":
          text += "<"
        elif html_entity == "gt":
          text += ">"
        else:
          text += f"&{html_entity};"
        html_entity = ""
      else:
        html_entity += c
    elif not in_tag:
      text += c
  return text


def load(url, headers=None):
  body = url.request(headers=headers)
  print(lex(body, url.scheme), end="")


if __name__ == "__main__":
  load(URL("https://browser.engineering/"))
