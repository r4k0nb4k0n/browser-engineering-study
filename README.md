# browser-engineering-study

[Web Browser Engineering](https://browser.engineering/) 스터디 저장소입니다.  
기존 OS 환경 제약(Python 3.9/3.10)에서 **Python 3.13 이상** 기준으로 최신화되었습니다.

## Requirements

- Python >= 3.13 (Tkinter 포함)

## Setup

### Windows

공식 설치 프로그램으로 Python 3.13을 설치한 뒤 (Tk 포함), `python3.13`이 PATH에 보이게 합니다.
Windows에는 `python3.13.exe`가 기본으로 없으므로, 설치 폴더에서 hardlink를 만듭니다.

```powershell
$pyDir = "$env:LOCALAPPDATA\Programs\Python\Python313"
New-Item -ItemType HardLink -Path "$pyDir\python3.13.exe" -Target "$pyDir\python.exe" -Force
# 새 터미널을 열거나, 현재 세션 PATH를 갱신
$env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")

python3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### macOS

Homebrew Python은 기본에 Tk가 포함되어 있지 않으므로 `python-tk`를 함께 설치합니다.  
`$(brew --prefix)`를 사용하여 Apple Silicon(`/opt/homebrew`)과 Intel Mac(`/usr/local`) 환경 모두 호환됩니다.

#### Option 1: venv / pip

```bash
brew install python@3.13 python-tk@3.13
$(brew --prefix)/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,macos]"
```

#### Option 2: uv

```bash
brew install python@3.13 python-tk@3.13
uv venv --python $(brew --prefix)/bin/python3.13 .venv
source .venv/bin/activate
uv pip install -e ".[dev,macos]"
```

> [!NOTE]
> `macos` extra는 macOS 환경에서 Jupyter Tk 창 스크린샷 캡처에 필요합니다. Windows는 별도 extra 없이 `display_tk_window`가 동작합니다.

노트북에서는 인터프리터/커널을 `.venv`로 선택한 뒤:

```python
from browser import URL

body = URL("https://browser.engineering/").request()
```

## Layout

```text
src/browser/   # import 가능한 패키지 (URL 등)
*.ipynb        # 장별 학습 노트북
```

