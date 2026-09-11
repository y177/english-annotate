# english-annotate

매일 아침 영어 뉴스 1건을 골라 **후치수식·시제·조동사·가정법** 4유형을 색으로 표시하고 한국어 주석을 붙인 학습 HTML을 만드는 도구. Claude 예약 작업(cron)이 매 실행마다 이 저장소를 `git clone` 해서 `ea.py`를 사용한다. 표준 라이브러리만 사용(검증 `check`만 Playwright 필요).

python3 ea.py extract input.txt \--title "제목" \--source "URL" \> scaffold.json

python3 ea.py build   data.json OUT.html DRIVE\_URL "2026-09-11 (금)" \[--note "문구"\] \[--folder DRIVE\_FOLDER\_ID\]

python3 ea.py check   OUT.html

- `extract`: 지문을 문단·문장으로 나눈 주석 scaffold(JSON) 생성  
- `build`: data.json 검증(span 존재·태그 짝·중첩 금지) → 뷰어 HTML(TTS·반복·한글가리기·인쇄) \+ Gmail용 `email.html` 생성  
- `check`: Playwright(Chromium)로 렌더 확인 — 카드/하이라이트 개수, 콘솔 에러 0

data.json 스키마: `{"meta":{"title","source","kind"},"paragraphs":[{"idx","summary","sentences":[{"en","kr"}],"notes":[{"type","span","ko"}]}]}` — `en` 안에 `<span class='hl TYPE'>…</span>`(TYPE ∈ mod|tense|modal|subj).

&nbsp;