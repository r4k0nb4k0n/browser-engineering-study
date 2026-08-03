# browser-engineering-study

[Web Browser Engineering](https://browser.engineering/) 스터디 저장소입니다.

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

Homebrew Python은 기본에 Tk가 없어서 `python-tk`를 같이 설치합니다.

```bash
brew install python@3.13 python-tk@3.13
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,macos]"
```

`macos` extra는 macOS에서 Jupyter Tk 창 스크린샷에 필요합니다. Windows는 추가 패키지 없이 `display_tk_window`가 동작합니다.

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
