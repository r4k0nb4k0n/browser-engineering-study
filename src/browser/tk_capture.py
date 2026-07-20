import os
import subprocess
import sys
import tempfile
import textwrap
import time
import tkinter


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


def capture_tk_window(window, settle_seconds=0.5):
  """Capture a native Tk window as PNG bytes (macOS).

  Jupyter does not auto-capture OS windows, so notebooks should call this
  (preferably via display_tk_window) and show the result with IPython.display.

  Does not change the window title or other learning-facing window state.
  """
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


def _capture_tk_in_subprocess(setup_code="", settle_seconds=0.5):
  """Create/capture/destroy Tk in a child process that then exits.

  Opening Tk inside the Jupyter kernel leaves a macOS GUI app attached to the
  kernel PID. A short-lived subprocess avoids that.
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

  캡처 후 window는 닫히지만, 노트북 커널 프로세스에 macOS GUI가 붙을 수
  있다. Dock에 Python이 남으면 커널을 재시작하면 된다.

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
