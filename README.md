# browser-engineering-study

[Web Browser Engineering](https://browser.engineering/) 스터디 저장소입니다.

## Setup

macOS Homebrew Python은 기본에 Tk가 없어서 `python-tk`를 같이 설치합니다.

```bash
brew install python@3.13 python-tk@3.13
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,macos]"
```

`macos` extra는 Jupyter에서 Tk 창 스크린샷을 셀 출력으로 붙일 때 필요합니다.

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
