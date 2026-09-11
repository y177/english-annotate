#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ea.py — english-annotate 단일 스크립트 (stdlib 전용).
  python3 ea.py extract  input.txt --title T --source URL > scaffold.json
  python3 ea.py build    data.json OUT.html DRIVE_URL "DATE" [--note "문구"]   # 검증 + 뷰어 HTML + email.html
  python3 ea.py check    OUT.html                                            # Playwright 렌더 검증
"""
import sys, re, json, os, html, argparse

TYPES = ("mod", "tense", "modal", "subj")
LBL = {"mod": "후치수식", "tense": "시제", "modal": "조동사", "subj": "가정법"}
COL = {"mod": "#0284c7", "tense": "#16a34a", "modal": "#7c3aed", "subj": "#ea580c"}
FOLDER = "https://drive.google.com/drive/folders/1vzqf9MGGTJPrxDwr4gWJUw10RcYLp5Kc"
_ABBREV = ["Mr", "Mrs", "Ms", "Dr", "Prof", "St", "vs", "etc", "e.g", "i.e", "cf", "Fig", "No", "Inc", "Ltd", "Co",
           "U.S", "U.K", "Ph.D", "M.D", "a.m", "p.m", "approx", "Rep", "Sen", "Gov", "Gen", "Col", "Lt", "Sgt", "Capt", "Jr", "Sr"]
MARK = "\x01"

# ---------- extract ----------
def split_paragraphs(text):
    text = re.sub(r"\n{3,}", "\n\n", text.replace("\r\n", "\n").replace("\r", "\n")).strip()
    blocks = re.split(r"\n\s*\n", text) if "\n\n" in text else text.split("\n")
    return [re.sub(r"[ \t]{2,}", " ", re.sub(r"\s*\n\s*", " ", b).strip()) for b in blocks if b.strip()]

def split_sentences(para):
    p = para
    for a in _ABBREV: p = re.sub(r"\b" + re.escape(a) + r"\.", a + MARK, p)
    parts = re.split(r'(?<=[.!?])["\')\]]?\s+(?=["\'(\[]?[A-Z0-9])', p)
    return [s.replace(MARK, ".").strip() for s in parts if s.strip()]

def cmd_extract(a):
    text = open(a.infile, "rb").read().decode("utf-8", errors="replace")
    paras = [{"idx": i, "summary": "", "sentences": [{"en": s, "kr": ""} for s in split_sentences(p)], "notes": []}
             for i, p in enumerate(split_paragraphs(text), 1)]
    out = {"meta": {"title": a.title, "source": a.source, "kind": "url"}, "paragraphs": paras}
    sys.stdout.buffer.write(json.dumps(out, ensure_ascii=False, indent=1).encode("utf-8"))

# ---------- validate ----------
def validate(data):
    errs = []
    for p in data["paragraphs"]:
        raw = " ".join(re.sub(r"<[^>]+>", "", s["en"]) for s in p["sentences"])
        for n in p.get("notes", []):
            if n["type"] not in TYPES: errs.append(f"P{p['idx']}: bad type {n['type']}")
            if n["span"] and n["span"] not in raw: errs.append(f"P{p['idx']}: span not found -> {n['span']!r}")
        for s in p["sentences"]:
            o = len(re.findall(r"<span class='hl ", s["en"])); c = len(re.findall(r"</span>", s["en"]))
            if o != c: errs.append(f"P{p['idx']}: span 태그 불일치 ({o}/{c}) -> {s['en'][:50]}")
            for cls in re.findall(r"<span class='hl (\w+)'>", s["en"]):
                if cls not in TYPES: errs.append(f"P{p['idx']}: bad hl class {cls}")
            if "<span" in re.sub(r"<span class='hl \w+'>[^<]*</span>", "", s["en"]): errs.append(f"P{p['idx']}: 중첩 span -> {s['en'][:50]}")
    return errs

# ---------- email ----------
def email_html(data, drive_url, date, note):
    m = data["meta"]; n_notes = sum(len(p.get("notes", [])) for p in data["paragraphs"])
    hl = lambda en: re.sub(r"<span class='hl (\w+)'>(.*?)</span>", lambda x: f"<b style='color:{COL[x.group(1)]}'>{x.group(2)}</b>", en)
    E = html.escape
    o = ["<div style='font-family:Malgun Gothic,Apple SD Gothic Neo,sans-serif;max-width:700px;color:#111;line-height:1.5'>",
         f"<h2 style='font-size:18px;margin:0 0 4px'>{E(m['title'])}</h2>",
         f"<p style='font-size:12px;color:#555;margin:0 0 8px'>출처: <a href='{E(m['source'])}'>{E(m['source'])}</a><br>{date} · 문단 {len(data['paragraphs'])} · 표시 구문 {n_notes}</p>",
         f"<p style='padding:8px 10px;background:#eff6ff;border-left:4px solid #0284c7;font-size:13px'>🎧 <b>듣기·반복·한글가리기 학습 파일</b>: <a href='{drive_url}'>구글 드라이브에서 열기</a> (다운로드 후 크롬/엣지로 열면 TTS 동작)</p>",
         "<p style='font-size:12px'>" + " &nbsp; ".join(f"<b style='color:{c}'>■ {LBL[k]}</b>" for k, c in COL.items()) + "</p>"]
    for p in data["paragraphs"]:
        o.append(f"<p style='margin:14px 0 4px'><b style='background:#0284c7;color:#fff;border-radius:5px;padding:0 7px'>{p['idx']}</b> <span style='color:#b45309;font-size:13px'>{E(p.get('summary',''))}</span></p>")
        for s in p["sentences"]:
            o.append(f"<p style='border:1px solid #ddd;border-radius:6px;padding:7px 9px;margin:5px 0'><b style='font-size:15px'>{hl(s['en'])}</b><br><span style='color:#b45309;font-size:13px'>{E(s.get('kr',''))}</span></p>")
        if p.get("notes"):
            o.append("<ul style='margin:2px 0;padding-left:18px;font-size:12.5px;color:#333'>" + "".join(
                f"<li><b style='color:{COL[n['type']]}'>[{LBL[n['type']]}] {E(n['span'])}</b> — {E(n['ko'])}</li>" for n in p["notes"]) + "</ul>")
    if note: o.append(f"<p style='font-size:12px;color:#555'>※ {E(note)}</p>")
    o.append(f"<p style='font-size:11px;color:#888;margin-top:16px'>english-annotate 자동 발송 · 후치수식·시제·조동사·가정법 4유형 · 보관함: <a href='{FOLDER}'>english-annotate-daily</a></p></div>")
    return "\n".join(o)

# ---------- build ----------
def cmd_build(a):
    data = json.load(open(a.data, encoding="utf-8"))
    errs = validate(data)
    if errs:
        print("VALIDATION FAILED:"); [print("  -", e) for e in errs]; sys.exit(1)
    n = sum(len(p.get("notes", [])) for p in data["paragraphs"])
    print(f"VALIDATION OK — 문단 {len(data['paragraphs'])}, 표시 구문 {n}")
    default = '/*__DATA__*/ {"meta":{"title":"","source":"","kind":"text"},"paragraphs":[]}'
    assert default in TPL
    page = TPL.replace(default, "/*__DATA__*/ " + json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    page = page.replace("__TITLE__", html.escape(data["meta"].get("title") or "영어 구문 주석", quote=False))
    open(a.out, "wb").write(page.encode("utf-8"))
    em = email_html(data, a.drive_url, a.date, a.note)
    open("email.html", "w", encoding="utf-8").write(em)
    sz = os.path.getsize(a.out)
    print(f"WROTE {a.out} ({sz} bytes) / email.html ({len(em.encode('utf-8'))} bytes)")
    if sz < 5000: print("WARN: too small"); sys.exit(2)

# ---------- check ----------
def cmd_check(a):
    import http.server, threading, socketserver
    from playwright.sync_api import sync_playwright
    d, f = os.path.split(os.path.abspath(a.out))
    H = lambda *x, **k: http.server.SimpleHTTPRequestHandler(*x, directory=d, **k)
    H.log_message = lambda *x: None
    srv = socketserver.TCPServer(("127.0.0.1", 0), H); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{port}/{f}"); pg.wait_for_timeout(600)
        cards, hls = pg.locator(".card").count(), pg.locator(".hl").count()
        b.close()
    srv.shutdown()
    ok = cards > 0 and hls > 0 and not errs
    print(f"CHECK {'OK' if ok else 'FAILED'} — cards {cards}, hl {hls}, console errors {errs}")
    sys.exit(0 if ok else 1)

def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    e = sp.add_parser("extract"); e.add_argument("infile"); e.add_argument("--title", default=""); e.add_argument("--source", default=""); e.set_defaults(fn=cmd_extract)
    b = sp.add_parser("build"); b.add_argument("data"); b.add_argument("out"); b.add_argument("drive_url"); b.add_argument("date"); b.add_argument("--note", default=""); b.set_defaults(fn=cmd_build)
    c = sp.add_parser("check"); c.add_argument("out"); c.set_defaults(fn=cmd_check)
    a = ap.parse_args(); a.fn(a)

TPL = r'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__ · 영어 구문 주석</title><style>:root{--bg:#0f172a;--card:#1e293b;--card2:#273449;--line:#334155;--text:#e2e8f0;--muted:#94a3b8;--accent:#38bdf8;--kr:#fbbf24;--shadow:0 4px 14px rgba(0,0,0,.35);--mod:#38bdf8;--tense:#22c55e;--modal:#a78bfa;--subj:#fb923c;}*{box-sizing:border-box;}body{margin:0;font-family:"Segoe UI","Malgun Gothic",system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;padding:0 0 80px;}header{background:linear-gradient(135deg,#0c4a6e,#155e75);padding:22px 20px 18px;box-shadow:var(--shadow);position:sticky;top:0;z-index:50;}header h1{margin:0 0 4px;font-size:1.2rem;}header p{margin:0;color:#bae6fd;font-size:.8rem;word-break:break-all;}.wrap{max-width:860px;margin:0 auto;padding:0 16px;}.legend{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap;}.lg{cursor:pointer;border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.06);color:#e0f2fe;border-radius:20px;padding:5px 13px;font-size:.82rem;font-weight:600;transition:.15s;display:flex;align-items:center;gap:7px;}.lg .dot{width:11px;height:11px;border-radius:50%;}.lg[data-t=mod] .dot{background:var(--mod);}.lg[data-t=tense] .dot{background:var(--tense);}.lg[data-t=modal] .dot{background:var(--modal);}.lg[data-t=subj] .dot{background:var(--subj);}.lg.off{opacity:.4;text-decoration:line-through;}.controls{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:18px auto;display:flex;flex-wrap:wrap;gap:14px 22px;align-items:center;box-shadow:var(--shadow);}.ctl{display:flex;align-items:center;gap:8px;font-size:.85rem;color:var(--muted);}.ctl input[type=range]{accent-color:var(--accent);}select.mini{background:var(--card2);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:5px 8px;font-size:.85rem;}.btn{cursor:pointer;border:none;border-radius:10px;padding:9px 16px;font-size:.9rem;font-weight:600;color:#0f172a;background:var(--accent);transition:.15s;white-space:nowrap;}.btn:hover{filter:brightness(1.08);}.btn.green{background:#22c55e;}.btn.stop{background:#ef4444;color:#fff;}.switch{display:flex;align-items:center;gap:7px;cursor:pointer;font-size:.85rem;color:var(--muted);}.switch input{width:16px;height:16px;accent-color:#22c55e;}.para{margin:22px 0;}.para-head{display:flex;align-items:center;gap:10px;margin:0 0 8px;}.para-head .num{background:var(--accent);color:#0f172a;font-weight:700;border-radius:8px;min-width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-size:.9rem;}.para-head .sum{color:var(--kr);font-size:.9rem;margin:0;}body.hide-kr .para-head .sum{filter:blur(5px);cursor:pointer;}body.hide-kr .para-head .sum:hover{filter:none;}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 15px;margin:8px 0;box-shadow:var(--shadow);transition:border-color .2s,transform .1s;}.card.active{border-color:var(--accent);transform:scale(1.005);}.card .en{font-size:1.1rem;font-weight:600;margin:0 0 4px;}.card .kr{color:var(--kr);font-size:.92rem;margin:0;}body.hide-kr .card .kr{filter:blur(5px);cursor:pointer;transition:filter .15s;}body.hide-kr .card .kr:hover{filter:none;}.card .row{display:flex;align-items:center;gap:10px;margin-top:9px;flex-wrap:wrap;}.card .row .play{cursor:pointer;border:none;background:#22c55e;color:#0f172a;border-radius:9px;padding:6px 13px;font-weight:600;font-size:.83rem;}.card .row .rep{display:flex;align-items:center;gap:6px;font-size:.78rem;color:var(--muted);}.hl{border-bottom:2px dotted currentColor;padding:0 1px;font-weight:700;}.hl.mod{color:var(--mod);}.hl.tense{color:var(--tense);}.hl.modal{color:var(--modal);}.hl.subj{color:var(--subj);}body.off-mod .hl.mod{color:inherit;border-bottom:none;font-weight:600;}body.off-tense .hl.tense{color:inherit;border-bottom:none;font-weight:600;}body.off-modal .hl.modal{color:inherit;border-bottom:none;font-weight:600;}body.off-subj .hl.subj{color:inherit;border-bottom:none;font-weight:600;}.notes{list-style:none;padding:0;margin:9px 0 0;border-top:1px dashed var(--line);padding-top:8px;}.notes li{display:flex;gap:8px;align-items:flex-start;font-size:.82rem;color:#cbd5e1;margin:5px 0;}.notes .dot{width:10px;height:10px;border-radius:50%;margin-top:5px;flex:none;}.notes li.t-mod .dot{background:var(--mod);}.notes li.t-tense .dot{background:var(--tense);}.notes li.t-modal .dot{background:var(--modal);}.notes li.t-subj .dot{background:var(--subj);}.notes .sp{font-weight:700;color:var(--text);}.notes .tag{font-size:.72rem;color:var(--muted);border:1px solid var(--line);border-radius:6px;padding:0 5px;margin-right:2px;}footer{color:var(--muted);font-size:.78rem;text-align:center;margin-top:36px;}.tip{background:var(--card2);border-left:3px solid var(--accent);border-radius:0 10px 10px 0;padding:10px 14px;font-size:.83rem;color:#cbd5e1;margin:18px 0;}@media print{@page{margin:14mm;}body{background:#fff;color:#000;padding:0;}header{position:static;background:#fff;color:#000;box-shadow:none;padding:0 0 6px;border-bottom:2px solid #000;}header h1{font-size:15pt;}header p{color:#444;}.legend,.controls,.tip,footer{display:none !important;}.wrap{max-width:none;padding:0;}.para{margin:10px 0;page-break-inside:avoid;}.para-head .num{background:#000;color:#fff;}.para-head .sum{color:#1d4ed8;}.card{background:#fff;border:1px solid #999;box-shadow:none;border-radius:6px;padding:6px 10px;margin:6px 0;page-break-inside:avoid;}.card .row{display:none;}.card .en{font-size:12pt;color:#000;}.hl{color:#000 !important;border-bottom:1px solid #000 !important;}.card .kr{color:#1d4ed8;font-size:10.5pt;}.notes{color:#333;}.notes .dot{border:1px solid #333;}body.hide-kr .kr,body.hide-kr .sum{filter:none;}}</style></head>
<body>
<header>
<div class="wrap">
<h1 id="docTitle">__TITLE__</h1>
<p id="docSource"></p>
<div class="legend" id="legend">
<span class="lg" data-t="mod"><span class="dot"></span>후치수식</span>
<span class="lg" data-t="tense"><span class="dot"></span>시제</span>
<span class="lg" data-t="modal"><span class="dot"></span>조동사</span>
<span class="lg" data-t="subj"><span class="dot"></span>가정법</span>
</div>
</div>
</header>
<div class="wrap">
<div class="tip">
<b>구문 주석 학습</b> — 문단마다 <b>후치수식·시제·조동사(느낌)·가정법</b> 4가지를 색으로 표시하고
아래에 한국어 주석을 달았습니다. 위 <b>범례</b>를 눌러 특정 유형 강조를 끄고 켤 수 있고,
각 문장의 <b>▶</b>로 원어민 발음을 반복해 들을 수 있습니다.
</div>
<div class="controls">
<button class="btn green" id="playAll">▶ 전체 듣기</button>
<button class="btn stop" id="stopBtn">■ 정지</button>
<button class="btn" id="printBtn">🖨 인쇄</button>
<div class="ctl">속도 <input type="range" id="rate" min="0.5" max="1.2" step="0.1" value="0.9"><span id="rateVal">0.9×</span></div>
<div class="ctl">기본 반복 <select id="defRep" class="mini"><option>1</option><option selected>2</option><option>3</option><option>5</option></select>회</div>
<div class="ctl">음성 <select id="voiceSel" class="mini"><option>로딩 중…</option></select></div>
<label class="switch"><input type="checkbox" id="hideKr">한글 가리기(셀프테스트)</label>
</div>
<div id="doc"></div>
<footer>
💡 범례로 유형별 강조를 토글하고, ▶로 문장별 반복 듣기가 됩니다. “인쇄”는 원문·해석·주석을 종이에 맞게 출력합니다.<br>
음성은 브라우저 내장 TTS(Web Speech API)를 사용합니다(크롬/엣지 권장).
</footer>
</div><script>
const DATA = /*__DATA__*/ {"meta":{"title":"","source":"","kind":"text"},"paragraphs":[]};
const TYPE_LABEL = {mod:"후치수식", tense:"시제", modal:"조동사", subj:"가정법"};
const STORE_OFF = "engAnno_off_v1";
const KIND_LABEL = {text:"텍스트", url:"기사", pdf:"PDF", "ko-text":"한국어 원문 번역", "ko-url":"한국어 기사 번역", "ko-pdf":"한국어 PDF 번역"};
document.getElementById('docTitle').textContent = DATA.meta.title || "영어 구문 주석";
(function(){
const s = DATA.meta.source ? `출처: ${DATA.meta.source}` : "";
const k = DATA.meta.kind ? ` (${KIND_LABEL[DATA.meta.kind]||DATA.meta.kind})` : "";
const ko = /^ko-/.test(DATA.meta.kind||"") ? " · 아래 노란 문장은 한국어 원문" : "";
document.getElementById('docSource').textContent = s ? s + k + ko : "";
})();
const docEl = document.getElementById('doc');
let cards = [];
function render(){
docEl.innerHTML=''; cards=[];
(DATA.paragraphs||[]).forEach(p=>{
const para=document.createElement('div'); para.className='para';
const head=document.createElement('div'); head.className='para-head';
head.innerHTML = `<span class="num">${p.idx}</span><p class="sum">${escapeHtml(p.summary||'')}</p>`;
para.appendChild(head);
(p.sentences||[]).forEach(s=>{
const c=document.createElement('div'); c.className='card';
const rep=`<select class="repSel mini"><option>1</option><option selected>2</option><option>3</option><option>5</option></select>`;
c.innerHTML = `<p class="en">${s.en||''}</p>`+`<p class="kr">${escapeHtml(s.kr||'')}</p>`+
`<div class="row"><button class="play">▶ 듣기</button>`+`<span class="rep">반복 ${rep}회</span></div>`;
const repSel=c.querySelector('.repSel'); const idx=cards.length;
c.querySelector('.play').addEventListener('click', ()=> playOne(idx));
cards.push({el:c, repSel, tts:(s.tts||stripTags(s.en||''))});
para.appendChild(c);
});
if((p.notes||[]).length){
const ul=document.createElement('ul'); ul.className='notes';
p.notes.forEach(n=>{
const li=document.createElement('li'); li.className='t-'+n.type;
li.innerHTML = `<span class="dot"></span><span><span class="tag">${TYPE_LABEL[n.type]||n.type}</span>`+
`<span class="sp">${escapeHtml(n.span||'')}</span> — ${escapeHtml(n.ko||'')}</span>`;
ul.appendChild(li);
});
para.appendChild(ul);
}
docEl.appendChild(para);
});
applyDefRep();
}
function escapeHtml(t){ return (t||'').replace(/[&<>]/g, m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m])); }
function stripTags(t){ const d=document.createElement('div'); d.innerHTML=t; return d.textContent||''; }
const legend=document.getElementById('legend');
function loadOff(){ try{ return JSON.parse(localStorage.getItem(STORE_OFF))||[]; }catch(e){ return []; } }
function applyOff(off){
['mod','tense','modal','subj'].forEach(t=>{
const on = !off.includes(t);
document.body.classList.toggle('off-'+t, !on);
const chip=legend.querySelector(`.lg[data-t=${t}]`);
if(chip) chip.classList.toggle('off', !on);
});
}
legend.addEventListener('click', e=>{
const chip=e.target.closest('.lg'); if(!chip) return;
const t=chip.dataset.t; let off=loadOff();
if(off.includes(t)) off=off.filter(x=>x!==t); else off.push(t);
try{ localStorage.setItem(STORE_OFF, JSON.stringify(off)); }catch(e){}
applyOff(off);
});
const synth=window.speechSynthesis;
let voices=[], enVoice=null;
const voiceSel=document.getElementById('voiceSel');
const rateInput=document.getElementById('rate');
const rateVal=document.getElementById('rateVal');
const defRep=document.getElementById('defRep');
function loadVoices(){
voices=synth.getVoices().filter(v=>/en[-_]/i.test(v.lang));
if(!voices.length) voices=synth.getVoices();
voiceSel.innerHTML='';
voices.forEach((v,i)=>{ const o=document.createElement('option'); o.value=i; o.textContent=`${v.name} (${v.lang})`; voiceSel.appendChild(o); });
let pick=voices.findIndex(v=>/en-US/i.test(v.lang)&&/female|google|samantha|zira|aria/i.test(v.name));
if(pick<0) pick=voices.findIndex(v=>/en-US/i.test(v.lang));
if(pick<0) pick=0;
voiceSel.value=pick; enVoice=voices[pick];
}
loadVoices();
if(synth.onvoiceschanged!==undefined) synth.onvoiceschanged=loadVoices;
voiceSel.addEventListener('change', ()=> enVoice=voices[voiceSel.value]);
rateInput.addEventListener('input', ()=> rateVal.textContent=rateInput.value+'×');
defRep.addEventListener('change', applyDefRep);
function applyDefRep(){ cards.forEach(c=> c.repSel.value=defRep.value); }
function speak(text){
return new Promise(res=>{
const u=new SpeechSynthesisUtterance(text);
if(enVoice) u.voice=enVoice;
u.lang=enVoice? enVoice.lang : 'en-US';
u.rate=parseFloat(rateInput.value);
u.onend=res; u.onerror=res;
synth.speak(u);
});
}
let stopFlag=false;
function highlight(i){ cards.forEach((c,j)=> c.el.classList.toggle('active', i===j)); }
async function playOne(i){
synth.cancel(); stopFlag=false;
const reps=parseInt(cards[i].repSel.value)||1;
highlight(i); cards[i].el.scrollIntoView({behavior:'smooth', block:'center'});
for(let r=0;r<reps;r++){ if(stopFlag)break; await speak(cards[i].tts); if(stopFlag)break; await new Promise(t=>setTimeout(t,250)); }
highlight(-1);
}
async function playAll(){
synth.cancel(); stopFlag=false;
for(let i=0;i<cards.length;i++){
if(stopFlag)break;
const reps=parseInt(cards[i].repSel.value)||1;
highlight(i); cards[i].el.scrollIntoView({behavior:'smooth', block:'center'});
for(let r=0;r<reps;r++){ if(stopFlag)break; await speak(cards[i].tts); if(stopFlag)break; await new Promise(t=>setTimeout(t,250)); }
await new Promise(t=>setTimeout(t,400));
}
highlight(-1);
}
document.getElementById('playAll').addEventListener('click', playAll);
document.getElementById('stopBtn').addEventListener('click', ()=>{ stopFlag=true; synth.cancel(); highlight(-1); });
document.getElementById('hideKr').addEventListener('change', e=>{ document.body.classList.toggle('hide-kr', e.target.checked); });
document.getElementById('printBtn').addEventListener('click', ()=>{ synth.cancel(); window.print(); });
render();
applyOff(loadOff());
</script></body>
</html>'''

if __name__ == "__main__":
    main()
