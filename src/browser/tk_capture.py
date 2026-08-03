import contextlib
import io
import os
import struct
import subprocess
import sys
import tempfile
import textwrap
import time
import tkinter
import zlib


def _close_tk_window(window):
  """Force-close a Tk window so it does not linger."""
  for action in (
      lambda: window.attributes("-topmost", False),
      window.withdraw,
      window.quit,
      window.destroy,
  ):
    try:
      action()
    except tkinter.TclError:
      pass

  # Clear leftover default root from earlier runs.
  root = getattr(tkinter, "_default_root", None)
  if root is not None:
    try:
      root.quit()
    except tkinter.TclError:
      pass
    try:
      root.destroy()
    except tkinter.TclError:
      pass
  tkinter._default_root = None


@contextlib.contextmanager
def _suppress_stderr():
  """Hide OS GUI noise (e.g. macOS mach-port messages) during capture."""
  try:
    devnull = open(os.devnull, "w")
    stderr_fd = sys.stderr.fileno()
    saved = os.dup(stderr_fd)
  except (OSError, AttributeError, io.UnsupportedOperation):
    yield
    return

  try:
    os.dup2(devnull.fileno(), stderr_fd)
    yield
  finally:
    os.dup2(saved, stderr_fd)
    os.close(saved)
    devnull.close()


def _prepare_tk_window(window, settle_seconds=0.5):
  """Bring a Tk window on-screen long enough to capture."""
  window.update_idletasks()
  window.update()
  try:
    window.deiconify()
    window.lift()
    window.attributes("-topmost", True)
  except tkinter.TclError as exc:
    raise RuntimeError(
        "Tk 창이 이미 파괴된 상태입니다. Jupyter 커널을 재시작한 뒤 다시 실행하세요."
    ) from exc
  window.update()
  time.sleep(settle_seconds)
  try:
    window.attributes("-topmost", False)
  except tkinter.TclError:
    pass
  window.update()


def _png_chunk(tag, data):
  return (
      struct.pack(">I", len(data))
      + tag
      + data
      + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
  )


def _bgra_to_png(width, height, bgra):
  """Encode a bottom-up or top-down BGRA buffer as PNG bytes."""
  row_bytes = width * 4
  expected = row_bytes * height
  if len(bgra) < expected:
    raise RuntimeError("윈도우 비트맵 데이터가 불완전합니다.")

  raw = bytearray()
  # GetDIBits with positive biHeight returns bottom-up rows; flip while converting.
  for y in range(height - 1, -1, -1):
    raw.append(0)  # filter: None
    row = memoryview(bgra)[y * row_bytes : (y + 1) * row_bytes]
    for i in range(0, row_bytes, 4):
      b, g, r, a = row[i : i + 4]
      raw.extend((r, g, b, a))

  return b"".join(
      (
          b"\x89PNG\r\n\x1a\n",
          _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)),
          _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9)),
          _png_chunk(b"IEND", b""),
      )
  )


def _capture_macos(window):
  try:
    from Quartz import (
        CGRectNull,
        CGWindowListCopyWindowInfo,
        CGWindowListCreateImage,
        kCGNullWindowID,
        kCGWindowImageBoundsIgnoreFraming,
        kCGWindowListOptionIncludingWindow,
        kCGWindowListOptionOnScreenOnly,
    )
    from Cocoa import NSBitmapImageRep, NSPNGFileType
  except ImportError as exc:
    raise ImportError(
        "macOS window capture requires: pip install -e '.[macos]'"
    ) from exc

  pid = os.getpid()
  windows = CGWindowListCopyWindowInfo(
      kCGWindowListOptionOnScreenOnly, kCGNullWindowID
  )
  matches = [w for w in windows if w.get("kCGWindowOwnerPID") == pid]
  if not matches:
    raise RuntimeError("캡처할 Tk 창을 찾지 못했습니다.")

  matches.sort(
      key=lambda w: (w.get("kCGWindowBounds") or {}).get("Width", 0)
      * (w.get("kCGWindowBounds") or {}).get("Height", 0),
      reverse=True,
  )
  window_id = matches[0]["kCGWindowNumber"]
  cg_image = CGWindowListCreateImage(
      CGRectNull,
      kCGWindowListOptionIncludingWindow,
      window_id,
      kCGWindowImageBoundsIgnoreFraming,
  )
  if cg_image is None:
    raise RuntimeError("창 이미지 생성에 실패했습니다.")

  bitmap = NSBitmapImageRep.alloc().initWithCGImage_(cg_image)
  png_data = bitmap.representationUsingType_properties_(NSPNGFileType, None)
  return bytes(png_data)


def _capture_windows(window):
  import ctypes
  from ctypes import wintypes

  user32 = ctypes.windll.user32
  gdi32 = ctypes.windll.gdi32

  hwnd = int(window.winfo_id())
  GA_ROOT = 2
  root = user32.GetAncestor(hwnd, GA_ROOT)
  if root:
    hwnd = root

  rect = wintypes.RECT()
  if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
    raise RuntimeError("윈도우 영역을 가져오지 못했습니다.")
  width = rect.right - rect.left
  height = rect.bottom - rect.top
  if width <= 0 or height <= 0:
    raise RuntimeError(f"유효하지 않은 윈도우 크기: {width}x{height}")

  hwnd_dc = user32.GetWindowDC(hwnd)
  if not hwnd_dc:
    raise RuntimeError("윈도우 DC를 가져오지 못했습니다.")
  mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
  bmp = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
  old = gdi32.SelectObject(mem_dc, bmp)

  # PW_RENDERFULLCONTENT helps with DWM-composited window contents.
  PW_RENDERFULLCONTENT = 2
  printed = user32.PrintWindow(hwnd, mem_dc, PW_RENDERFULLCONTENT)
  if not printed:
    printed = user32.PrintWindow(hwnd, mem_dc, 0)
  if not printed:
    # Fallback: copy from screen DC at the window rect.
    screen_dc = user32.GetDC(0)
    try:
      gdi32.BitBlt(
          mem_dc, 0, 0, width, height, screen_dc, rect.left, rect.top, 0x00CC0020
      )  # SRCCOPY
    finally:
      user32.ReleaseDC(0, screen_dc)

  class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]

  bmi = BITMAPINFOHEADER()
  bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
  bmi.biWidth = width
  bmi.biHeight = height  # positive => bottom-up
  bmi.biPlanes = 1
  bmi.biBitCount = 32
  bmi.biCompression = 0  # BI_RGB

  buf_size = width * height * 4
  buf = (ctypes.c_ubyte * buf_size)()
  got = gdi32.GetDIBits(mem_dc, bmp, 0, height, buf, ctypes.byref(bmi), 0)
  gdi32.SelectObject(mem_dc, old)
  gdi32.DeleteObject(bmp)
  gdi32.DeleteDC(mem_dc)
  user32.ReleaseDC(hwnd, hwnd_dc)

  if got != height:
    raise RuntimeError("윈도우 픽셀을 읽지 못했습니다.")

  return _bgra_to_png(width, height, bytes(buf))


def capture_tk_window(window, settle_seconds=0.5):
  """Capture a native Tk window as PNG bytes (macOS / Windows).

  Jupyter does not auto-capture OS windows, so notebooks should call this
  (preferably via display_tk_window) and show the result with IPython.display.

  Does not change the window title or other learning-facing window state.
  """
  _prepare_tk_window(window, settle_seconds=settle_seconds)
  with _suppress_stderr():
    if sys.platform == "darwin":
      return _capture_macos(window)
    if sys.platform == "win32":
      return _capture_windows(window)
  raise RuntimeError(
      f"Tk 창 캡처는 macOS/Windows만 지원합니다 (현재: {sys.platform})"
  )


def _capture_tk_in_subprocess(setup_code="", settle_seconds=0.5):
  """Create/capture/destroy Tk in a child process that then exits.

  Opening Tk inside the Jupyter kernel can leave a GUI app attached to the
  kernel PID (notably on macOS). A short-lived subprocess avoids that.
  """
  setup_code = textwrap.dedent(setup_code).strip()
  with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
    png_path = tmp.name

  script = textwrap.dedent(
      f"""
      import tkinter
      from browser.tk_capture import capture_tk_window, _close_tk_window

      window = tkinter.Tk()
      {setup_code}
      try:
        png = capture_tk_window(window, settle_seconds={settle_seconds!r})
        with open({png_path!r}, "wb") as f:
          f.write(png)
      finally:
        _close_tk_window(window)
      """
  )

  env = os.environ.copy()
  # Prefer the same interpreter / editable install as the notebook kernel.
  result = subprocess.run(
      [sys.executable, "-c", script],
      capture_output=True,
      env=env,
  )
  if result.returncode != 0:
    err = result.stderr.decode("utf-8", errors="replace").strip()
    raise RuntimeError(
        "Tk 캡처 subprocess가 실패했습니다"
        + (f":\n{err}" if err else f" (exit {result.returncode})")
    )

  try:
    with open(png_path, "rb") as f:
      png = f.read()
  finally:
    try:
      os.unlink(png_path)
    except OSError:
      pass

  if not png:
    raise RuntimeError("Tk 캡처 subprocess가 빈 PNG를 반환했습니다.")
  return png


def display_tk_window(
    window=None,
    settle_seconds=0.5,
    destroy=True,
    setup_code="",
):
  """Capture a Tk window and show it as Jupyter cell output.

  학습용(권장): 책 코드처럼 window를 직접 만든 뒤 넘긴다::

      window = tkinter.Tk()
      # ... canvas 등 학습 코드 ...
      display_tk_window(window)

  캡처 후 window는 닫힌다. macOS에서는 커널 프로세스에 GUI가 붙을 수 있어
  Dock에 Python이 남으면 커널을 재시작하면 된다.

  커널에 GUI를 남기지 않으려면 window 없이 호출한다(자식 프로세스 캡처)::

      display_tk_window()
      display_tk_window(setup_code="canvas = tkinter.Canvas(window); canvas.pack()")

  캡처 헬퍼는 window.title() 등 창 타이틀을 바꾸지 않는다.
  """
  from IPython.display import Image, display

  if window is None:
    png = _capture_tk_in_subprocess(
        setup_code=setup_code, settle_seconds=settle_seconds
    )
  else:
    if setup_code:
      raise ValueError("setup_code는 window=None(subprocess)일 때만 사용할 수 있습니다.")
    try:
      png = capture_tk_window(window, settle_seconds=settle_seconds)
    finally:
      if destroy:
        _close_tk_window(window)

  display(Image(data=png))
  # None을 반환해 노트북 Out에 PNG 바이트가 덤프되지 않게 한다.
  return None
