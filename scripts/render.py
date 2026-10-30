#!/usr/bin/env python3
"""Рендер наставнического разбора MR из JSON разбора в одну самодостаточную HTML-страницу.

Без внешних зависимостей, CSS и JS — внутри файла: страница открывается офлайн и пересылается одним файлом.

    python3 render.py result/shop-42/shop-42.json   # → shop-42.html рядом

Формат JSON — references/schema.md: render валидирует JSON, проецирует факты и рисует страницы ревью и обучения.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

CSS = r"""
:root{--bg:#fff;--fg:#1f2328;--muted:#656d76;--line:#d0d7de;--soft:#f6f8fa;--accent:#0969da;
--add:#e6ffec;--add-fg:#1a7f37;--del:#ffebe9;--del-fg:#cf222e;--gl-add:#ecfdf0;--gl-add-ln:#d2f4dc;--gl-add-ln-fg:#24663b;--gl-del:#fbe9eb;--gl-del-ln:#f6d1d6;--gl-del-ln-fg:#8d1c2b;--gl-hunk:#f0f0f7;--tk-k:#cf222e;--tk-s:#0a3069;--tk-c:#6e7781;--tk-n:#0550ae;--tk-a:#8250df;--tk-t:#953800;--info:#ddf4ff;--warn:#fff8c5;--lesson:#fbefff;--risk:#ffebe9;--analyst:#dafbe1}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--muted:#8d96a0;--line:#30363d;--soft:#161b22;--accent:#4493f8;
--add:#12261e;--add-fg:#3fb950;--del:#25171c;--del-fg:#f85149;--gl-add:#122b1c;--gl-add-ln:#1a3d27;--gl-add-ln-fg:#7ee29b;--gl-del:#2d171b;--gl-del-ln:#432027;--gl-del-ln-fg:#ff9aa5;--gl-hunk:#1c2230;--tk-k:#ff7b72;--tk-s:#a5d6ff;--tk-c:#8b949e;--tk-n:#79c0ff;--tk-a:#d2a8ff;--tk-t:#ffa657;--info:#0c2d4b;--warn:#2e2a12;--lesson:#271a33;--risk:#3a1418;--analyst:#0f2a1b}}
*{box-sizing:border-box}
[hidden]{display:none!important}
a{color:var(--accent)}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
:root{--navw:380px;--tbh:46px}
.layout{display:grid;grid-template-columns:var(--navw) minmax(0,1fr);max-width:none;margin:0 auto}
body:not(.hasgraph) .layout{grid-template-columns:280px minmax(0,1fr);max-width:1680px}
.layout{transition:grid-template-columns .25s ease}
body.dragging .layout{transition:none}
nav{border-right:0!important}
body.navfolded .layout{grid-template-columns:0 minmax(0,1fr)}
body.navfolded nav{overflow:hidden;padding:0}
#navgrip{position:fixed;top:var(--tbh);bottom:0;width:13px;left:calc(var(--navw) - 6px);cursor:col-resize;z-index:25;transition:left .25s ease}
#navgrip::before{content:"";position:absolute;top:0;bottom:0;left:6px;width:1px;background:var(--line);transition:background .15s,width .15s}
#navgrip:hover::before{background:var(--accent);width:3px;left:5px}
#navgrip span{position:absolute;top:50%;left:-3px;width:19px;height:19px;margin-top:-10px;border-radius:50%;background:var(--bg);border:1px solid var(--line);
color:var(--muted);font-size:13px;line-height:17px;text-align:center;opacity:0;transition:opacity .15s,transform .25s}
#navgrip:hover span{opacity:1;border-color:var(--accent);color:var(--accent)}
body.dragging #navgrip{transition:none}
body.navfolded #navgrip{left:0;cursor:pointer}
body.navfolded #navgrip span{opacity:1;transform:rotate(180deg)}
.cg-pointer{display:none}
body.hasgraph .cg-inline{display:none} body.hasgraph .cg-pointer{display:block;color:var(--muted)}
.cg-nav{margin-top:6px} .cg-nav .cnode{font-size:13px;max-width:none} .cg-nav li{padding:3px 0 3px 16px} .cg-nav ul{padding-left:18px}
.cg-nav a.cnode.cur{background:var(--info);box-shadow:0 0 0 3px var(--accent)}
@media (max-width:900px),print{body.hasgraph .cg-inline{display:block} body.hasgraph .cg-pointer{display:none} #navgrip{display:none}}
nav{position:sticky;top:var(--tbh);align-self:start;height:calc(100vh - var(--tbh));overflow:auto;padding:24px 16px;border-right:1px solid var(--line);font-size:14px}
nav a{display:block;color:var(--fg);text-decoration:none;padding:4px 8px;border-radius:6px}
nav a:hover{background:var(--soft)}
nav .n{display:inline-block;min-width:22px;color:var(--muted)}
/* граф в колонке: карточки узлов, как в полном графе, но плотнее; ветки сворачиваются, узлы уровня на одной линии */
ul.gtree,ul.gtree ul{list-style:none;margin:0;padding:0}
ul.gtree{margin-top:8px}
ul.gtree ul{margin-left:9px;padding-left:9px;border-left:1px solid var(--line)}
ul.gtree li{margin:6px 0 0}
ul.gtree details>summary{list-style:none;cursor:pointer}
ul.gtree details>summary::-webkit-details-marker{display:none}
.grow{position:relative;display:flex;align-items:flex-start;gap:4px}
.tg{flex:none;width:16px;height:22px;margin-top:6px;font-size:13px;line-height:22px;text-align:center;color:var(--muted);border-radius:4px}
summary:hover .tg{background:var(--soft);color:var(--accent)}
.tg::before{content:"▾"} details:not([open])>summary .tg::before{content:"▸";color:var(--accent);font-weight:700}
.tg.leaf::before{content:""}
nav ul.gtree .gn{flex:1;min-width:0;display:block;padding:5px 9px;border:1px solid var(--line);border-radius:8px;background:var(--soft);
color:var(--fg);text-decoration:none;line-height:1.35}
nav ul.gtree a.gn{border-color:var(--accent)}
nav ul.gtree a.gn:hover{background:var(--info)}
nav ul.gtree .gn.error{background:var(--risk);border-color:transparent} nav ul.gtree .gn.result{background:var(--add);border-color:transparent}
nav ul.gtree .gn.store{background:none;border-style:dashed}
nav ul.gtree a.gn.cur{background:var(--info);box-shadow:0 0 0 2px var(--accent)}
nav ul.gtree a.gn.curin{box-shadow:0 0 0 2px var(--accent);border-style:dashed}
.cond{display:inline-block;max-width:calc(100% - 20px);margin:0 0 3px 20px;padding:0 8px;border:1px solid var(--line);border-radius:10px;
font-size:11.5px;line-height:1.5;color:var(--muted);background:var(--bg);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cond code{background:none;border:0;padding:0;font-size:11px}
.l2{display:block;font-size:11px;line-height:1.35;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.l2 .rl{text-transform:uppercase;letter-spacing:.04em;font-size:10.5px}
.l1{display:flex;align-items:center;gap:5px;min-width:0}
.l1 code{font-size:13px;background:none;border:0;padding:0;color:inherit;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
a.gn .l1 code{font-weight:600}
.gn.error .l1 code{color:var(--del-fg)} .gn.result .l1 code{color:var(--add-fg)}
.nt{display:block;margin-top:1px;font-size:11.5px;line-height:1.35;color:var(--muted)}
.hn{display:none} details:not([open])>summary .hn{display:inline;font-size:11px;font-weight:600;color:var(--accent)}
.gb{position:absolute;top:5px;right:7px;display:flex;align-items:center;gap:3px}
.grow:has(.gb) .l2{padding-right:var(--gbw,62px)}
.gb .gl{margin:0;padding:0 3px;font-size:10.5px}
.gtools{display:flex;gap:6px;margin:4px 8px 0} .gtools button{font:12px/1.4 inherit;color:var(--fg);background:var(--soft);border:1px solid var(--line);border-radius:6px;padding:1px 8px;cursor:pointer}
nav .navhint{font-size:12px;color:var(--muted);margin-top:10px}
.printonly{display:none} @media print{.printonly{display:block}}
.nb.chunk .lbl{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-right:4px}
details.ol.done2>summary a::after{content:" ✓";color:var(--add-fg)}
[id]{scroll-margin-top:60px}
ol.trace{list-style:none;padding:0;margin:12px 0;counter-reset:none}
ol.trace li.tstep{position:relative;margin:0 0 10px 14px;padding:10px 14px;border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;background:var(--soft)}
ol.trace li.tstep::before{content:"";position:absolute;left:-15px;top:-10px;bottom:-10px;border-left:1px dashed var(--line)}
.tsh{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:4px}
.tsn{display:inline-block;width:20px;height:20px;border-radius:50%;background:var(--accent);color:var(--bg);font-size:12px;line-height:20px;text-align:center;flex:none}
.tsr{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.03em} .tsf{font-size:12px;color:var(--muted);font-family:ui-monospace,Menlo,monospace}
.tsrow{display:grid;grid-template-columns:120px minmax(0,1fr);gap:8px;margin-top:3px;font-size:14.5px}
.tsrow .lbl,.ba .lbl{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.03em;padding-top:2px}
pre.tsc{margin:0;padding:6px 10px;font-size:12.5px;background:var(--bg);border:1px solid var(--line);border-radius:6px;overflow-x:auto}
.chlearn{margin:6px 0 10px;padding:8px 12px;border-left:3px solid var(--add-fg);background:var(--analyst);border-radius:6px}
.chcheck{margin:14px 0 6px;padding:10px 14px;border:1px dashed var(--accent);border-radius:8px}
.chcheck details.q{margin:6px 0 0}
.ba{margin:14px 0;padding:10px 14px;border:1px solid var(--line);border-radius:8px}
.ba h3{margin:0 0 8px}
.bagrid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px} .bagrid>div,.tsv{min-width:0} .bagrid pre{overflow-x:auto}
section.q5{margin:18px 0;padding:14px 18px;border:1px solid var(--line);border-radius:10px}
section.q5>h3{margin:0 0 6px;display:flex;gap:10px;align-items:baseline}
section.q5 .qn{display:inline-block;flex:none;width:24px;height:24px;border-radius:50%;background:var(--accent);color:var(--bg);font-size:13px;line-height:24px;text-align:center}
section.q5 p.qthink{margin:4px 0 8px;color:var(--muted)} section.q5 p.qthink b{color:var(--fg)}
details.ans>summary{cursor:pointer;display:inline-block;padding:4px 12px;border:1px solid var(--accent);border-radius:999px;color:var(--accent);font-weight:600}
details.ans[open]>summary{margin-bottom:8px}
details.ans .isec h3{font-size:15px;margin:14px 0 6px}
.part{margin:8px 0 10px;padding:12px 18px;border-radius:10px;background:var(--info)} .part h2{margin:0 0 4px} .part p{margin:0}
@media print{details.ans>*{display:block}}
.ba .lbl.was{color:var(--del-fg)} .ba .lbl.now{color:var(--add-fg)}
@media (max-width:1000px){.bagrid{grid-template-columns:1fr}.tsrow{grid-template-columns:1fr}}
.crossbar{margin:6px 0 18px;padding:8px 14px;border:1px solid var(--line);border-radius:8px;background:var(--soft);font-weight:600}
.crossbar a{margin-left:4px}
main.single{max-width:1100px;margin:0 auto;padding:32px 48px 96px}
nav .progress{margin:12px 8px;color:var(--muted);font-size:13px}
main{padding:32px 48px 96px;min-width:0}
header h1{margin:0 0 4px;font-size:30px;line-height:1.25}
header .sub{color:var(--muted);margin:0 0 16px}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:24px}
.chip{background:var(--soft);border:1px solid var(--line);border-radius:999px;padding:2px 10px;font-size:13px}
.chip a{color:var(--accent)}
section.step{border-top:1px solid var(--line);padding-top:24px;margin-top:32px}
section.step h2{font-size:22px;margin:0 0 4px}
section.step h2 .n{color:var(--accent);margin-right:8px}
.part{margin:56px 0 0;padding:16px 20px;border-radius:10px;background:var(--soft);border:1px solid var(--line)}
.part h2{margin:0;font-size:24px}
.part p{margin:6px 0 0;color:var(--muted)}
nav .part-n{margin:14px 8px 2px;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
nav .part-g{margin:10px 8px 2px;font-size:12.5px;font-weight:600;color:var(--muted)}
.chapter{margin:56px 0 0}
.chapter>h2{margin:0 0 10px;font-size:26px}
.chapter>h2 .n{color:var(--accent);margin-right:8px}
.decision{margin:18px 0 0;padding:0 0 4px 16px;border-left:3px solid var(--line)}
.decision>h3{margin:0 0 10px;font-size:18px}
.step .kindtag,.decision .kindtag{font-size:12px;border-radius:4px;padding:1px 6px;margin-right:8px;vertical-align:middle;background:var(--lesson);color:#8250df;font-weight:600}
details.anatomy{border:1px solid var(--line);border-radius:8px;padding:6px 14px;margin:12px 0}
details.anatomy>summary{cursor:pointer;font-weight:600}
details.anatomy[open]>summary{margin-bottom:6px}
details.anatomy table{margin:6px 0 10px}
details.anatomy td.ln{white-space:nowrap;width:1%;font-family:ui-monospace,Menlo,monospace;font-size:12.5px;color:var(--muted)}
details.anatomy td.st{white-space:nowrap;width:1%}
.pgroup{margin:0;border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:8px;overflow:hidden}
.pgroup h3{margin:0;padding:10px 14px;font-size:19px;background:var(--soft)}
.pgroup .row{display:grid;grid-template-columns:150px minmax(0,1fr);border-top:1px solid var(--line)}
.pgroup .lbl{padding:8px 12px;color:var(--muted);font-size:13px;font-weight:600;background:var(--soft)}
.pgroup .val{padding:8px 12px}
.pgroup .val ol{margin:0;padding-left:20px}
@media (max-width:900px){.pgroup .row{grid-template-columns:1fr}}
.stepfiles{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 16px}
.stepfiles code{font-size:12px}
.done{float:right;font-size:13px;color:var(--muted);cursor:pointer;user-select:none}
.done input{vertical-align:middle}
h3{font-size:17px;margin:20px 0 8px}
p{margin:8px 0}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.88em;background:var(--soft);border:1px solid var(--line);border-radius:4px;padding:0 4px}
pre{background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:0;overflow:auto;margin:12px 0}
pre code{display:block;border:0;background:none;padding:12px 16px;font-size:13px;line-height:1.5}
pre .cap{display:block;font:12px ui-monospace,Menlo,monospace;color:var(--muted);border-bottom:1px solid var(--line);padding:6px 16px}
pre .cap code{display:inline;padding:0 4px;font-size:12px;border:1px solid var(--line);background:var(--bg)}
.l-add{display:block;background:var(--add);color:var(--add-fg)}
.l-del{display:block;background:var(--del);color:var(--del-fg)}
.l-hunk{display:block;color:var(--muted)}
.hl{display:block;background:var(--warn)}
table{border-collapse:collapse;margin:12px 0;width:100%;font-size:14px}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}
th{background:var(--soft)}
.callout{border-left:4px solid var(--accent);background:var(--info);border-radius:6px;padding:10px 14px;margin:14px 0}
.callout.warn{border-color:#bf8700;background:var(--warn)}
.callout.lesson{border-color:#8250df;background:var(--lesson)}
.callout.risk{border-color:var(--del-fg);background:var(--risk)}
.callout.analyst{border-color:var(--add-fg);background:var(--analyst)}
.callout.try{border-color:#8250df;background:var(--lesson)}
.plan .pk{margin:6px 0}
.plan td.no{white-space:nowrap;width:1%;color:var(--muted)}
.plan td.pf a{display:inline-block;margin:0 6px 2px 0}
.plan .kind{margin-left:3px}
.fromplan{color:var(--muted);font-size:13.5px;margin:-4px 0 8px}
.think .row.r .val ul{margin:0;padding-left:18px}
.callout b.t{display:block;margin-bottom:2px}
table.anno{font-size:13px;table-layout:fixed}
table.anno td.c{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:var(--soft);width:58%;font-size:12.5px}
table.anno td.c.add{background:var(--gl-add)}
table.anno td.x{font-size:14px}
table.anno .cap{font:12px ui-monospace,Menlo,monospace;color:var(--muted)}
.think{border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:8px;margin:14px 0;overflow:hidden}
.think .row{display:grid;grid-template-columns:150px minmax(0,1fr);border-top:1px solid var(--line)}
.think .row:first-child{border-top:0}
.think .lbl{padding:8px 12px;color:var(--muted);font-size:13px;font-weight:600;background:var(--soft)}
.think .val{padding:8px 12px}
.think .val pre{margin:6px 0 0}
.think .row.q .val{font-weight:600}
.think .row.d .val{font-weight:600;color:var(--add-fg)}
.think .trace{padding:5px 12px;font-size:12px;color:var(--muted);border-top:1px solid var(--line);background:var(--soft)}
.think .trace.recon{color:#bf8700}
@media (max-width:900px){.think .row{grid-template-columns:1fr}}
.ex{border:1px solid var(--line);border-left:4px solid #bf8700;border-radius:8px;padding:10px 14px;margin:12px 0;background:var(--soft)}
.ex-kind{font-size:12px;text-transform:uppercase;letter-spacing:.04em;font-weight:700;color:#9a6700;margin-right:4px}
.ex textarea{display:block;width:100%;box-sizing:border-box;margin:8px 0 4px;font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
.ex details.ex-a>summary{cursor:pointer;color:var(--accent);font-weight:600}
.ex pre{margin:8px 0}
.pic-why{font-size:17px;margin:8px 0 14px}
.pic-why .lbl,.pic-ba .lbl{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-bottom:2px}
.pic-ba{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0}
.pic-b,.pic-a{border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.pic-b{background:var(--soft)} .pic-a{border-color:#1a7f37;border-width:2px}
.pic-key{margin:8px 0 16px}
table.pic-map{width:100%} table.pic-map th{text-align:left;white-space:nowrap;vertical-align:top;width:1%;padding-right:16px;font-weight:600}
table.pic-map ul{list-style:none;margin:0;padding:0} table.pic-map li{padding:2px 0}
table.pic-map li.heart code{font-weight:700} .pic-heart{font-size:12px;color:#fff;background:#8250df;border-radius:4px;padding:0 5px}
.pic-same{font-size:13px;color:var(--muted)}
@media (max-width:700px){.pic-ba{grid-template-columns:1fr}}
.tb-lvl{display:flex;gap:0;border:1px solid var(--line);border-radius:6px;overflow:hidden}
.tb-lvl button{border:0;background:none;padding:3px 10px;cursor:pointer;font:inherit;font-size:13px;color:var(--muted)}
.tb-lvl button[aria-pressed=true]{background:var(--accent);color:#fff}
.filecard{border:1px solid var(--line);border-left:4px solid #8250df;border-radius:8px;padding:10px 14px;margin:10px 0}
.filecard .fc-role{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.filecard .fc-lead{margin:4px 0}
.filecard .fc-list{list-style:none;padding:0;margin:6px 0 0}
.filecard .fc-list li{padding:6px 0;border-top:1px solid var(--line)}
.filecard .fc-list li:first-child{border-top:0}
.filecard .fc-m{text-decoration:none} .filecard .fc-sig{white-space:pre-wrap;word-break:break-word}
.filecard .fc-tag{font-size:12px;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:0 4px}
.filecard .fc-p{margin-top:2px}
details.lvl2{margin:10px 0}
details.lvl2>summary{cursor:pointer;color:var(--muted);font-weight:600}
details.lvl2>summary .add{color:#1a7f37} details.lvl2>summary .del{color:#cf222e}
.samecard{border:1px dashed var(--line);border-radius:8px;padding:8px 14px;margin:14px 0}
.samecard table{width:100%;font-size:13px}
details.more{border:1px dashed var(--line);border-radius:8px;padding:6px 14px;margin:14px 0}
details.more>summary{cursor:pointer;color:var(--muted);font-weight:600}
details.more[open]>summary{margin-bottom:6px}
.files{width:100%}
.files td.num{text-align:right;font-family:ui-monospace,Menlo,monospace;white-space:nowrap}
.files .add{color:var(--add-fg)} .files .del{color:var(--del-fg)}
.kind{font-size:12px;border-radius:4px;padding:1px 6px;background:var(--soft);border:1px solid var(--line);white-space:nowrap}
details.q{border:1px solid var(--line);border-radius:8px;padding:8px 14px;margin:8px 0}
details.q summary{cursor:pointer;font-weight:600}
details.q[open] summary{margin-bottom:6px}
code.term,span.term{cursor:help;position:relative;text-decoration:underline dotted var(--muted);text-underline-offset:3px}
.term:hover::after,.term:focus::after{content:attr(data-tip);position:absolute;left:0;top:100%;z-index:20;margin-top:4px;
width:max-content;max-width:min(340px,80vw);white-space:normal;background:var(--fg);color:var(--bg);border-radius:6px;
padding:6px 10px;font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;text-decoration:none;box-shadow:0 4px 12px rgba(0,0,0,.2)}
dl.gloss dt{font-weight:600;margin-top:10px} dl.gloss dd{margin:2px 0 0 0;color:var(--fg)}
.flow{display:flex;flex-wrap:wrap;align-items:stretch;gap:6px;margin:14px 0}
.flow .arr{align-self:center;color:var(--muted);font-size:18px}
.fnode{display:flex;flex-direction:column;border:1px solid var(--line);border-radius:8px;padding:8px 12px;background:var(--soft);
color:var(--fg);text-decoration:none;min-width:120px;max-width:220px;font-size:14px;line-height:1.35}
.fnode.changed{border:2px solid var(--accent)}
.fnode code{word-break:break-all}
.fnode .fnote{color:var(--muted);font-size:12px;margin-top:2px}
.fnode .fstep{color:var(--accent);font-size:12px;margin-top:4px;font-weight:600}
a.fnode:hover{background:var(--info)}
.cg{margin:14px 0;overflow-x:auto}
.cg ul{list-style:none;margin:0;padding-left:26px}
.cg>ul{padding-left:0}
.cg li{position:relative;padding:5px 0 5px 18px}
.cg>ul>li{padding-left:0}
.cg li li::before{content:"";position:absolute;left:0;top:0;bottom:0;border-left:1px solid var(--muted)}
.cg li li:last-child::before{bottom:auto;height:22px}
.cg li li::after{content:"";position:absolute;left:0;top:22px;width:14px;border-top:1px solid var(--muted)}
.cg .cnode{display:inline-flex;flex-direction:column;border:1px solid var(--line);border-radius:8px;padding:6px 10px;
background:var(--soft);color:var(--fg);text-decoration:none;max-width:460px;font-size:14px;line-height:1.35;vertical-align:top}
.cg .cnode.changed{border:2px solid var(--accent)}
.cg .cnode.error{background:var(--risk)}
.cg .cnode.store{border-style:dashed}
.cg .cnode.result{background:var(--add)}
.cg .cnode .fnote{color:var(--muted);font-size:12px;margin-top:2px}
.cg .cnode .fstep{color:var(--accent);font-size:12px;margin-top:3px;font-weight:600}
.cg a.cnode:hover{background:var(--info)}
.specdiff{margin:10px 0 4px;padding:8px 14px;border:1px solid var(--line);border-left:4px solid #1a7f37;border-radius:8px;background:var(--analyst)}
.specdiff ul{margin:6px 0 0;padding-left:20px} .specdiff li{margin:3px 0} .specdiff .todo{color:var(--muted)}
nav a.navq{font-size:13px;color:var(--muted)}
.cg a.cnode.active,a.fnode.active{box-shadow:0 0 0 3px var(--accent)}
.nb.chunk.flash,.nb.chunk:target{box-shadow:0 0 0 3px var(--accent)}
.cg .cnode .crole{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-bottom:2px}
.cg .edge{display:block;width:max-content;font-size:12px;color:var(--muted);margin:0 0 3px;padding:1px 8px;border:1px solid var(--line);
border-radius:10px;background:var(--bg)}
.verdict{border:2px solid var(--line);border-radius:12px;padding:18px 22px;margin:8px 0 28px}
.verdict.ok,.verdict.wait,.verdict.ask,.verdict.merged{border-color:var(--add-fg)} .verdict.fix,.verdict.askmerge{border-color:#bf8700} .verdict.rework{border-color:var(--del-fg)}
.verdict .vh{font-size:22px;font-weight:700;margin:0 0 4px}
.verdict h3{margin:18px 0 6px}
.verdict table{margin:6px 0}
.verdict td.st,.verdict td.go{white-space:nowrap;width:1%}
.verdict ol{margin:6px 0;padding-left:22px}
.verdict table.vlist td{vertical-align:top}
.verdict .fact{color:var(--muted);font-size:13.5px;margin-top:2px}
.verdict .todo{margin-top:4px;font-weight:600}
.verdict .rwhy{margin-top:2px;font-weight:400}
.verdict p.tally{margin:6px 0 0;color:var(--muted);font-size:14px}
.verdict details.review{margin-top:12px}
.verdict details.review>summary{cursor:pointer;font-weight:600;color:var(--accent)}
.verdict p.rk{margin:12px 0 2px;font-weight:700;color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.04em}
.lvl{font-size:12px;border-radius:4px;padding:1px 6px;white-space:nowrap;font-weight:600}
.lvl.blocker{background:var(--risk);color:var(--del-fg)} .lvl.fix{background:var(--warn);color:#9a6700} .lvl.note{background:var(--soft);color:var(--muted)}
.think details{border-top:1px solid var(--line)}
.think details>summary{cursor:pointer;padding:6px 12px;font-size:13px;color:var(--muted);background:var(--soft)}
.dfile{border:1px solid var(--line);border-radius:8px;margin:14px 0;overflow:hidden}
.dhead{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:8px 12px;background:var(--soft);border-bottom:1px solid var(--line);font-size:13px}
.dhead code{font-weight:600;background:none;border:0;font-size:13px}
.dhead .add{color:var(--add-fg);font-weight:600} .dhead .del{color:var(--del-fg);font-weight:600}
table.gd{margin:0;border:0;font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;table-layout:fixed}
table.gd td{border:0;padding:0 8px;vertical-align:top}
table.gd td.ln{width:46px;text-align:right;color:var(--muted);user-select:none;border-right:1px solid var(--line)}
table.gd td.cd{white-space:pre-wrap;overflow-wrap:anywhere}
table.gd col.cm{width:40%}
table.gd td.cm{vertical-align:top;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;white-space:normal;padding:2px 10px;border-left:1px solid var(--line);background:var(--bg)}
table.gd tr.add td.cm,table.gd tr.del td.cm{background:var(--bg)}
table.gd td.cm .nb{margin:2px 0}
.nb.part{border-left-color:#8250df;background:var(--lesson)}
table.gd td.cm.rng{box-shadow:inset 3px 0 0 #8250df}
table.gd td.cm .nb{position:sticky;top:8px}
.nb .ref{display:block;font-size:11.5px;color:var(--muted);margin-bottom:1px}
.nb.note{border-left-color:var(--muted)}
table.gd td.cd{color:var(--fg)}
table.gd td.cd .sg{display:inline-block;width:1.4em;margin-left:-4px;user-select:none;color:var(--muted)}
table.gd tr.add td{background:var(--gl-add)} table.gd tr.add td.ln{background:var(--gl-add-ln);color:var(--gl-add-ln-fg);border-right-color:var(--gl-add-ln)}
table.gd tr.add td.cd .sg{color:var(--add-fg)}
table.gd tr.del td{background:var(--gl-del)} table.gd tr.del td.ln{background:var(--gl-del-ln);color:var(--gl-del-ln-fg);border-right-color:var(--gl-del-ln)}
table.gd tr.del td.cd .sg{color:var(--del-fg)}
table.gd tr.hunk td{background:var(--gl-hunk);color:var(--muted)}
.tk-k{color:var(--tk-k)} .tk-s{color:var(--tk-s)} .tk-c{color:var(--tk-c);font-style:italic} .tk-n{color:var(--tk-n)}
.tk-a{color:var(--tk-a)} .tk-t{color:var(--tk-t)}
table.gd tr.hid{display:none}
table.gd tr.exp td{background:var(--soft);color:var(--accent);cursor:pointer;text-align:center;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
table.gd tr.note td{background:var(--soft);padding:6px 14px 6px 104px;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;white-space:normal;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
table.gd tr.note .nb{max-width:860px;margin:4px 0;background:var(--bg)}
table.gd tr.note .nb.part,table.gd tr.note .nb.chunk{background:var(--lesson)}
.nb.chunk{border-left-color:#8250df}
.nb.chunk .cwhyrole{margin-top:6px} .nb.chunk .clinks{margin-top:4px;font-size:13px}
.nb.chunk .cwhyrole .lbl,.nb.chunk .clinks .lbl{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-right:4px}
.nb.chunk .chow{margin-top:6px} .nb.chunk .chow .lbl{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.nb.chunk ol{margin:2px 0 0;padding-left:20px} .nb.chunk li{margin:1px 0}
.nb.chunk .cw{margin-top:6px;padding:5px 9px;border-radius:6px;border-left:3px solid var(--muted);background:var(--bg)}
.nb.chunk .cw.risk{border-left-color:var(--del-fg);background:var(--risk)} .nb.chunk .cw.warn{border-left-color:#bf8700;background:var(--warn)}
.nb.chunk .cwhy{color:var(--muted);font-size:13px;margin-top:2px} table.gd tr.note .nb.risk{background:var(--risk)} table.gd tr.note .nb.warn{background:var(--warn)}
.nb{border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:6px;padding:6px 10px;background:var(--soft)}
.nb.risk{border-left-color:var(--del-fg);background:var(--risk)} .nb.warn{border-left-color:#bf8700;background:var(--warn)}
.nb b.t{margin-right:6px}
@media (max-width:900px){table.gd tr.note td{padding-left:10px}table.gd col.cm{width:45%}}
footer{margin-top:48px;color:var(--muted);font-size:13px}
/* шапка: где я, куда дальше — одна на обе страницы */
html{scroll-padding-top:calc(var(--tbh) + 12px)}
.tb{position:sticky;top:0;z-index:40;display:flex;align-items:center;gap:12px;height:var(--tbh);padding:0 16px;background:var(--bg);
border-bottom:1px solid var(--line);font-size:14px;white-space:nowrap}
.tb a{text-decoration:none}
.tb-mr{font-weight:700;color:var(--fg);flex:none}
.tb-tabs{display:flex;border:1px solid var(--line);border-radius:8px;overflow:hidden;flex:none}
.tb-tabs a{padding:4px 12px;color:var(--fg)}
.tb-tabs a+a{border-left:1px solid var(--line)}
.tb-tabs a:hover{background:var(--soft)}
.tb-tabs a[aria-current]{background:var(--accent);color:var(--bg);font-weight:600}
.tb-v{padding:2px 10px;border-radius:999px;border:1px solid var(--line);color:var(--fg)!important;font-size:13px;flex:none}
.tb-v.ok,.tb-v.ask,.tb-v.wait,.tb-v.merged{border-color:var(--add-fg)} .tb-v.fix,.tb-v.askmerge{border-color:#bf8700} .tb-v.rework{border-color:var(--del-fg)}
.tb-crumb{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;color:var(--muted);font-size:13px}
.tb-jump{flex:1;min-width:0;overflow:hidden;display:flex;gap:2px}
.tb-jump a{padding:3px 8px;border-radius:6px;color:var(--fg);font-size:13px}
.tb-jump a:hover{background:var(--soft)}
.tb-prog{display:flex;align-items:center;gap:6px;color:var(--muted);font-size:12.5px;flex:none}
.tb-prog .bar{width:80px;height:6px;border-radius:3px;background:var(--soft);border:1px solid var(--line);overflow:hidden}
.tb-prog .bar i{display:block;height:100%;width:0;background:var(--add-fg)}
.tb-cont{flex:none;max-width:340px;overflow:hidden;text-overflow:ellipsis;padding:4px 12px;border-radius:8px;background:var(--accent);color:var(--bg)!important;font-weight:600}
a:focus-visible,button:focus-visible,summary:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (max-width:1200px){.tb-v{display:none}}
/* левая колонка: граф и главы одновременно, без вкладок */
.nsec{margin:0 0 12px}
.nsec>summary{cursor:pointer;list-style:none;padding:4px 8px;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.nsec>summary::-webkit-details-marker,details.ol>summary::-webkit-details-marker{display:none}
.nsec>summary::before{content:"▸ "} .nsec[open]>summary::before{content:"▾ "}
.gl{font-size:11px;font-weight:400;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:0 4px;margin-left:4px;white-space:nowrap}
.wk{display:inline-block;flex:none;width:15px;height:15px;border-radius:50%;font:700 10px/15px -apple-system,sans-serif;text-align:center;color:#fff}
nav a.wk{display:inline-block;padding:0;border-radius:50%;text-decoration:none;color:#fff} nav a.wk.note{color:var(--muted)} nav a.wk:hover{box-shadow:0 0 0 2px var(--accent)}
.wk.risk{background:var(--del-fg)} .wk.warn{background:#bf8700} .wk.note{background:none;color:var(--muted);border:1px solid var(--line);width:15px;height:15px;line-height:13px}
nav ul.gtree a.gn.done .l1 code::after{content:" ✓";color:var(--add-fg)}
.glegend{margin:8px 8px 0;font-size:11.5px;line-height:1.5;color:var(--muted)}
details.ol{margin:1px 0}
details.ol>summary{cursor:pointer;list-style:none;display:flex;gap:6px;align-items:baseline;padding:3px 8px;border-radius:6px;font-size:13.5px;font-weight:600}
details.ol>summary::before{content:"▸";flex:none;color:var(--muted)} details.ol[open]>summary::before{content:"▾"}
nav details.ol>summary a{display:inline;flex:1;padding:0;border-radius:0}
details.ol>summary:hover{background:var(--soft)}
details.ol.cur>summary{background:var(--soft)}
details.ol .cnt{flex:none;font-size:11.5px;font-weight:400;color:var(--muted)} details.ol .cnt.full{color:var(--add-fg)}
nav a.oli{padding:2px 8px 2px 24px;font-size:13px}
nav a.oli.sub{padding-left:38px;font-size:12.5px;color:var(--muted)}
nav a.oli.sub code{font-size:11.5px}
nav a.oli.cur{background:var(--info);color:var(--fg);font-weight:600}
nav a.oli.done::after{content:" ✓";color:var(--add-fg)}
nav a.oli.q{color:var(--muted)}
/* основная колонка: глава вместо сквозных номеров, «Дальше» в конце файла */
.kick{display:block;font-size:13px;font-weight:400;color:var(--muted);margin-bottom:2px}
a.next{display:block;width:max-content;max-width:100%;margin:24px 0 0 auto;padding:6px 14px;border:1px solid var(--line);border-radius:8px;
background:var(--soft);text-decoration:none;font-size:14px;overflow:hidden;text-overflow:ellipsis}
a.next:hover{border-color:var(--accent)}
a.tocode{white-space:nowrap}
a.rvref{display:inline-block;margin-left:6px;padding:0 7px;border:1px solid var(--line);border-radius:999px;font-size:12px;font-weight:400;
background:var(--bg);text-decoration:none;white-space:nowrap}
/* ревью: решение — первым экраном, остальное по разу */
.vgrid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}
@media (max-width:1000px){.vgrid{grid-template-columns:1fr}}
.vbox{border:1px solid var(--line);border-left:4px solid var(--line);border-radius:10px;padding:10px 16px;background:var(--soft)}
.vbox.merge{border-left-color:#bf8700} .vbox.merge.none{border-left-color:var(--add-fg)} .vbox.spec{border-left-color:#1a7f37}
.vbox h3{margin:2px 0 6px;font-size:16px}
.vbox h3 a{font-weight:400;font-size:14px}
ol.items{margin:0;padding-left:22px} ol.items>li{margin:8px 0}
ol.items .why{color:var(--muted);font-size:13.5px;margin-top:2px}
ol.items .todo{margin-top:3px}
ol.items>li>b{font-weight:600}
ol.items li:target{background:var(--info);border-radius:6px}
section.rv{margin-top:34px;padding-top:18px;border-top:1px solid var(--line)}
section.rv>h2{font-size:21px;margin:0 0 8px}
section.rv p.rk{margin:16px 0 4px;font-weight:700;color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.04em}
table.ck td.st{width:1%;white-space:nowrap} table.ck td.ar{width:34%;font-weight:600}
table.ck .see{color:var(--muted)}
details.okreq>summary{cursor:pointer;color:var(--accent);font-weight:600;margin:8px 0}
@media (max-width:900px){.tb{position:static;flex-wrap:wrap;height:auto;padding:8px 12px;white-space:normal}.tb-crumb,.tb-jump{display:none}nav{top:0}}
.rv .fact{color:var(--muted);font-size:13.5px;margin-top:2px} .rv .todo{margin-top:4px;font-weight:600} .rv td.st,.rv td.go{white-space:nowrap;width:1%}
.verdict ol.items .todo,.rv ol.items .todo{font-weight:400}
@media print{.tb,a.next{display:none!important}}
@media (max-width:900px){.layout{grid-template-columns:1fr}nav{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)}main{padding:24px 16px}}
@media print{nav,.done{display:none}details.anatomy>*,details.review>*,details.more>*,.think details>*{display:block}table.gd tr.hid{display:table-row}table.gd tr.exp{display:none}.term::after{display:none}.layout{display:block}details.q{break-inside:avoid}details.q>*{display:block}}
"""

JS = r"""
(function(){
  var B=document.body,root=document.documentElement,page=B.dataset.page||'',learn=B.dataset.learn||'';
  function $(s){return document.querySelector(s)} function $$(s){return [].slice.call(document.querySelectorAll(s))}
  // прогресс общий для обеих страниц: ключ — страница обучения (старый формат {id:true} переносится)
  var key='mr-mentor:'+location.pathname.replace(/[^\/]*$/,'')+learn,st={done:{},pos:null};
  try{var raw=JSON.parse(localStorage.getItem(key)||'null');if(raw&&raw.done)st=raw;else if(raw)st.done=raw}catch(e){}
  function save(){try{localStorage.setItem(key,JSON.stringify(st))}catch(e){}}
  var all=[];try{all=JSON.parse($('#mr-steps').textContent)}catch(e){}
  function shown(el){return !!el&&el.getClientRects().length>0}
  function upd(){
    var steps=all,c=steps.filter(function(x){return st.done[x.id]}).length,p=$('#tbprog');
    if(p){p.hidden=!steps.length;if(steps.length){p.querySelector('i').style.width=(100*c/steps.length)+'%';
      p.querySelector('.t').textContent=c+' из '+steps.length+' файлов';p.title='Разобрано файлов: '+c+' из '+steps.length}}
    $$('details.ol[data-ch]').forEach(function(d){d.classList.toggle('done2',!!st.done['ch-'+d.dataset.ch])});
    $$('.done input').forEach(function(x){x.checked=!!st.done[x.dataset.id]});
    $$('nav a.oli[data-step],nav a.gn[data-step]').forEach(function(a){a.classList.toggle('done',!!st.done[a.dataset.step])});
    $$('details.ol[data-steps]').forEach(function(d){var ids=d.dataset.steps.split(' '),n=ids.filter(function(i){return st.done[i]}).length,
      s=d.querySelector('.cnt');if(s){s.textContent=n+'/'+ids.length;s.classList.toggle('full',n===ids.length)}})}
  $$('.done input').forEach(function(x){x.addEventListener('change',function(){st.done[x.dataset.id]=x.checked;save();upd()})});
  $$('a.next[data-done]').forEach(function(a){a.addEventListener('click',function(){st.done[a.dataset.done]=true;save();upd()})});
  upd();
  // «Продолжить»: место, где читатель был в прошлый раз
  var cont=$('#tbcont'),resume=st.pos;
  function target(p){return p&&(p.chunk&&(page!=='learn'||document.getElementById('chunk-'+p.chunk))?'chunk-'+p.chunk:p.id)}
  function showCont(){if(!cont)return;cont.hidden=true;
    if(resume&&resume.id&&resume.id!=='top'&&(page!=='learn'||document.getElementById(target(resume)))){
      cont.hidden=false;cont.textContent='Продолжить: '+resume.label;cont.href=(page==='learn'?'':learn)+'#'+target(resume)}}
  if(page!=='learn')showCont();
  function unfold(r){var t=document.getElementById('fold-'+r.dataset.fold);if(!t)return;
    r.parentNode.insertBefore(t.content.cloneNode(true),r);
    if(r.dataset.owner){var c=document.getElementById(r.dataset.owner);if(c)c.rowSpan+=(+r.dataset.m)-1}
    t.remove();r.remove()}
  $$('tr.exp').forEach(function(r){r.tabIndex=0;r.addEventListener('click',function(){unfold(r)});
    r.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();unfold(r)}})});
  // уровень: «Обзор» — файлы и методы, «Код» — те же карточки с открытым кодом. Свёрнутое по-прежнему открывается руками
  var lkey='mr-mentor:level',lvl='1';try{lvl=localStorage.getItem(lkey)||'1'}catch(e){}
  function setLvl(v){lvl=v;$$('details.lvl2').forEach(function(d){d.open=v==='2'});
    $$('.tb-lvl button').forEach(function(b){b.setAttribute('aria-pressed',b.dataset.lvl===v?'true':'false')});try{localStorage.setItem(lkey,v)}catch(e){}}
  $$('.tb-lvl button').forEach(function(b){b.addEventListener('click',function(){setLvl(b.dataset.lvl)})});
  if($('.tb-lvl'))setLvl(lvl);
  $$('.ex textarea').forEach(function(t){var k='mr-mentor:ex:'+location.pathname+':'+t.parentNode.dataset.ex;
    try{t.value=localStorage.getItem(k)||''}catch(e){}
    t.addEventListener('input',function(){try{localStorage.setItem(k,t.value)}catch(e){}})});
  window.addEventListener('beforeprint',function(){$$('tr.exp').forEach(unfold);$$('details').forEach(function(d){d.open=true})});
  var navEl=$('nav');
  // узкий экран: колонка стоит над текстом — граф и главы свёрнуты, чтобы текст начинался на первом экране
  if(innerWidth<=900)$$('details.nsec').forEach(function(d){d.open=false});
  if(page==='learn'&&navEl){
    var wkey='mr-mentor:navw2';
    try{var w=localStorage.getItem(wkey);if(w)root.style.setProperty('--navw',w)}catch(e){}
    // граница колонки: клик сворачивает и разворачивает, протяжка меняет ширину
    var grip=$('#navgrip'),fkey='mr-mentor:navfolded';
    try{if(localStorage.getItem(fkey)==='1')B.classList.add('navfolded')}catch(e){}
    if(grip){grip.hidden=false;grip.addEventListener('mousedown',function(e){e.preventDefault();var x0=e.clientX,moved=false;
      function mv(ev){if(!moved&&Math.abs(ev.clientX-x0)<4)return;
        if(!moved){moved=true;B.classList.add('dragging');B.classList.remove('navfolded')}
        var w=Math.max(240,Math.min(innerWidth*0.5,ev.clientX))+'px';root.style.setProperty('--navw',w);try{localStorage.setItem(wkey,w)}catch(x){}}
      function up(){document.removeEventListener('mousemove',mv);document.removeEventListener('mouseup',up);B.classList.remove('dragging');
        if(!moved){var f=B.classList.toggle('navfolded');try{localStorage.setItem(fkey,f?'1':'0')}catch(x){}}}
      document.addEventListener('mousemove',mv);document.addEventListener('mouseup',up)})}
  }
  // где я: глава, файл и кусок под верхним краем — подсветка в графе и главах, строка в шапке, запись места
  var allSecs=$$('main [data-label]'),allCards=$$('main .nb.chunk'),gn=$$('nav a.gn'),oli=$$('nav a.oli'),crumb=$('#crumb'),
      curS=null,curC=null,saveT=null,ticking=false;
  function keep(el){if(!el||!navEl||navEl.matches(':hover'))return;var r=el.getBoundingClientRect(),n=navEl.getBoundingClientRect();
    if(r.top<n.top+30||r.bottom>n.bottom-20)navEl.scrollTop+=r.top-n.top-n.height/3}
  function track(){ticking=false;
    var top=$('.tb')?$('.tb').offsetHeight:0,sec=null,ch=null,secs=allSecs.filter(shown),cards=allCards.filter(shown);
    for(var i=0;i<secs.length;i++){if(secs[i].getBoundingClientRect().top<top+90)sec=secs[i];else break}
    if(sec)cards.forEach(function(c){if(c.getBoundingClientRect().top<innerHeight*.5&&sec.contains(c))ch=c});
    var sid=sec&&sec.id,cid=ch&&(ch.dataset.cid||ch.id.slice(6));if(sid===curS&&cid===curC)return;curS=sid;curC=cid;
    gn.forEach(function(a){a.classList.toggle('cur',cid?a.dataset.chunk===cid:!!sid&&a.dataset.step===sid);a.classList.remove('curin')});
    var cg=$('nav a.gn.cur'),hid=cg&&cg.closest('ul.gtree details:not([open])');
    if(hid){var up;while((up=hid.parentElement.closest('ul.gtree details:not([open])')))hid=up;cg=hid.querySelector('summary .gn');if(cg)cg.classList.add('curin')}
    keep(cg);
    oli.forEach(function(a){a.classList.toggle('cur',a.dataset.chunk?a.dataset.chunk===cid:!!sid&&a.getAttribute('href')==='#'+sid)});
    var g=sec&&sec.dataset.ch;
    $$('details.ol').forEach(function(d){var me=!!g&&d.dataset.ch===g;d.classList.toggle('cur',me);
      if(me&&!d.open){d.open=true;d.dataset.auto='1'}else if(!me&&d.dataset.auto){d.open=false;delete d.dataset.auto}});
    keep($('nav a.oli.cur'));
    if(crumb)crumb.textContent=sec?(sec.dataset.crumb||sec.dataset.label)+(ch?' › '+ch.dataset.symbol:''):'';
    if(cont&&resume&&sid===resume.id)cont.hidden=true;
    clearTimeout(saveT);if(sec&&sid!=='top')saveT=setTimeout(function(){st.pos={id:sid,chunk:cid||'',label:(ch?ch.dataset.symbol+' · ':'')+sec.dataset.label};resume=null;save()},800)}
  if(page==='learn'){addEventListener('scroll',function(){if(!ticking){ticking=true;setTimeout(track,80)}},{passive:true});track()}
  var gt=$('.gtools');if(gt){gt.hidden=false;gt.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;
    var shut=b.dataset.fold==='1';$$('ul.gtree details').forEach(function(d){var k=0,p=d;while((p=p.parentElement.closest('ul.gtree details')))k++;d.open=!shut||k<2});
    curS=curC=undefined;track()})}
  // узел графа — обычная ссылка на кусок в тексте; «Назад» браузера возвращает к месту чтения. Alt+→/← — соседний кусок по графу
  var order=[];gn.forEach(function(a){var c=a.dataset.chunk;if(c&&order.indexOf(c)<0)order.push(c)});
  function flashEl(c){if(c&&/^chunk-/.test(c.id)){c.classList.add('flash');setTimeout(function(){c.classList.remove('flash')},1600)}}
  // переход по якорю: цель в свёрнутом ответе или главе — раскрыть; exact — ссылка снаружи (из ревью)
  function goTo(id,exact){if(!id)return;var el=document.getElementById(id);if(!el)return;
    if(!shown(el)){for(var d=el.parentElement;d;d=d.parentElement)if(d.tagName==='DETAILS')d.open=true}
    if(!shown(el))return;el.scrollIntoView();flashEl(el)}
  addEventListener('hashchange',function(){goTo(decodeURIComponent(location.hash.slice(1)))});
  document.addEventListener('click',function(e){var a=e.target.closest('a[href^="#"]');
    if(a&&a.getAttribute('href')===location.hash&&location.hash.length>1){e.preventDefault();goTo(decodeURIComponent(location.hash.slice(1)))}
  });
  if(location.hash.length>1)setTimeout(function(){goTo(decodeURIComponent(location.hash.slice(1)),true)},0);
  document.addEventListener('keydown',function(e){if(!e.altKey||(e.key!=='ArrowRight'&&e.key!=='ArrowLeft')||!order.length)return;
    var i=order.indexOf(curC),n=i<0?0:i+(e.key==='ArrowRight'?1:-1);if(n<0||n>=order.length)return;
    e.preventDefault();location.hash='chunk-'+order[n]});
})();
"""

STEP_NO = {}       # id шага → «гл. N» для подписи узла схемы
CHAPTER = {}       # id шага → номер главы (0 — вне плана, None — без плана)
STEP_LABEL = {}    # id шага → короткое имя: файл или «решение D1»
CHUNKS = {}        # id куска → {"symbol", "step"} из проекции v3
CHUNKS_RAW = {}    # то же, для привязки заданий к шагу
STEP_FILE = {}     # id шага → (заголовок, новый ли файл) для ячейки «Файлы» в плане доработки

VERDICT = {"askmerge": "⚠️ Код готов · ❓ вопрос до мержа", "merged": "✅ Влит · разбор для обучения", "ok": "✅ Можно мержить", "ask": "✅ Можно мержить · ❓ есть вопрос", "wait": "✅ Код готов · ⏳ мерж держит процесс", "fix": "⚠️ Мержить после правок", "rework": "❌ Переделать"}
CHECK = {"ok": "✅", "note": "ℹ️", "warn": "⚠️", "fail": "❌", "na": "—"}
REQ = {"ok": "✅", "partial": "⚠️", "gap": "❌"}
LEVEL = {"blocker": "блокер", "fix": "поправить", "note": "на заметку"}
# когда действовать по риску → заголовок группы; порядок групп — порядок на странице
WHEN = {"merge": "До мержа", "deploy": "После деплоя", "spec": "В спеку и смежникам", "desc": "В описание MR", "know": "Знать, мерж не блокирует"}

KIND_LABEL = {
    "main": "код", "migration": "миграция", "test": "тест", "fixture": "тестовые данные",
    "feature": "cucumber", "config": "конфиг", "doc": "док", "other": "прочее",
}


GLOSSARY = {}      # термин → определение; базовый словарь + glossary из JSON
_TERM_RE = None
_seen = set()      # термины, уже подчёркнутые в текущем шаге: подсказка только у первого упоминания
USED = {}          # термины, встретившиеся на странице, в порядке появления → раздел «Словарь»

_TOKEN = re.compile(r"`([^`]+)`|\[([^\]]+)\]\((https?://[^)\s]+|#[\w-]+|REVIEW#[\w-]+)\)")


def set_glossary(g):
    global _TERM_RE
    GLOSSARY.clear()
    GLOSSARY.update({k.strip("`"): v for k, v in g.items()})   # ключ `D-44` в JSON — то же, что D-44
    _TERM_RE = re.compile(r"(?<![\w.])(" + "|".join(_term_pattern(k) for k in _keys()) + r")(?!\w)") if GLOSSARY else None


def _keys():
    return sorted(GLOSSARY, key=len, reverse=True)


def _term_pattern(k):
    """Русские термины ловим без учёта регистра и с окончанием: «тоглом», «Миграцию», «Spring-контекста»."""
    p = re.escape(html.escape(k))
    return f"(?i:{p})[а-яё]{{0,3}}" if re.search(r"[а-яё]$", k, re.I) else p


def _key_of(found):
    """Словарный ключ по найденному в тексте слову (с окончанием и в любом регистре)."""
    if found in GLOSSARY:
        return found
    return next(k for k in _keys() if found.lower().startswith(k.lower()))


def _tip(term):
    return html.escape(re.sub(r"[`*]", "", GLOSSARY[term]), quote=True)


def _first(term):
    if term in _seen:
        return False
    _seen.add(term)
    USED.setdefault(term, GLOSSARY[term])
    return True


def inline(text, terms=True):
    """Мини-разметка: `код`, **жирный**, [текст](url). Всё остальное экранируется.

    Термины из словаря получают подсказку при наведении — только первое упоминание в шаге."""
    if "**" in text and "`" in text:
        # **…`код`…** — жирный поверх кода: режем на куски, чтобы звёздочки не остались буквально
        parts = re.split(r"\*\*(.+?)\*\*", text)
        if len(parts) > 1:
            return "".join(f"<b>{inline(p, terms)}</b>" if i % 2 else inline(p, terms) for i, p in enumerate(parts))
    out, pos = [], 0
    for m in _TOKEN.finditer(text):
        out.append(_fmt(text[pos:m.start()], terms))
        if m.group(1) is not None:
            c = m.group(1)
            if terms and c in GLOSSARY and _first(c):
                out.append(f'<code class="term" tabindex="0" data-tip="{_tip(c)}">{html.escape(c)}</code>')
            else:
                out.append("<code>" + html.escape(c) + "</code>")
        else:
            href = html.escape(m.group(3))
            ext = "" if href.startswith(("#", "REVIEW#")) else ' target="_blank" rel="noopener"'
            out.append(f'<a href="{href}"{ext}>{inline(m.group(2), terms=False)}</a>')
        pos = m.end()
    out.append(_fmt(text[pos:], terms))
    return "".join(out)


def _fmt(s, terms=False):
    s = html.escape(s)
    if terms and _TERM_RE:
        def sub(m):
            t = _key_of(html.unescape(m.group(1)))
            if _first(t):
                return f'<span class="term" tabindex="0" data-tip="{_tip(t)}">{m.group(1)}</span>'
            return m.group(1)
        s = _TERM_RE.sub(sub, s)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)


_HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)")
_DIFF_META = ("diff --git", "index ", "--- ", "+++ ", "new file", "deleted file", "similarity", "rename ", "old mode", "new mode")
PLATE = {"block": "risk", "fix": "risk", "ask": "warn", "know": "note"}
NOTE_LABEL = {"why": "зачем", "risk": "риск", "warn": "внимание", "info": "справка", "note": "на заметку"}
_fold_no = [0]


def parse_diff(text):
    """Unified diff → строки (вид, старый номер, новый номер, текст). Номера считаем по заголовкам @@."""
    rows, old, new = [], 0, 0
    for line in text.rstrip("\n").split("\n"):
        if line.startswith(_DIFF_META) or line.startswith("\\"):
            continue
        m = _HUNK.match(line)
        if m:
            old, new = int(m.group(1)), int(m.group(2))
            rows.append(("hunk", None, None, line))
        elif line.startswith("+"):
            rows.append(("add", None, new, line[1:])); new += 1
        elif line.startswith("-"):
            rows.append(("del", old, None, line[1:])); old += 1
        else:
            rows.append(("ctx", old, new, line[1:] if line.startswith(" ") else line)); old += 1; new += 1
    return rows


def diff_block(b):
    """Дифф файла в одну колонку, комментарии — плашкой в потоке кода, как в GitLab.

    Блок файла (`parts` из anatomy) стоит над первой строкой своего диапазона — это заголовок куска.
    Комментарий к строке — под ней; к диапазону («30-33») — под последней строкой диапазона.
    notes: [{"line": 12, "text": …}] — к новой строке 12; {"line": "30-33"} — к диапазону; {"line": "-5"} — к удалённой.
    Длинные куски без объяснений сворачиваются в «Показать N строк»."""
    rows = parse_diff(b["diff"])
    _HL_LANG[0] = lang_of(b.get("file", ""))

    def key(r):
        return f"-{r[1]}" if r[0] == "del" else (str(r[2]) if r[2] is not None else None)

    before, after = {}, {}   # ключ строки → плашки над ней / под ней
    for part in b.get("parts", []):
        lo, hi = note_range(part.get("lines", ""))
        if hi is None:
            lo = part.get("at", lo)
        before.setdefault(str(lo), []).append({"kind": "part", "name": part["name"], "text": part["what"], "lines": part.get("lines", "")})
    for ch in b.get("chunks", []):
        lo, _ = note_range(ch.get("lines", ""))
        before.setdefault(str(lo), []).append(ch)
    for n in b.get("check_notes", []) + b.get("notes", []):
        lo, hi = note_range(n["line"])
        if hi is not None:
            after.setdefault(str(hi), []).append({**n, "_range": f"{lo}–{hi}"})
        else:
            after.setdefault(str(n["line"]), []).append(n)

    # плашка над строкой, которой нет в диффе (диапазон начинается с неизменённой строки вне хунка) — к первой строке диапазона из диффа
    keys = {key(r) for r in rows}
    for k in [k for k in before if k not in keys]:
        lo = int(k) if k.isdigit() else None
        tgt = next((key(r) for r in rows if lo is not None and r[2] is not None and r[0] != "del" and r[2] >= lo), None)
        if tgt:
            before.setdefault(tgt, []).extend(before.pop(k))
    for k in [k for k in after if k not in keys]:
        hi = int(k) if k.isdigit() else None
        tgt = next((key(r) for r in reversed(rows) if hi is not None and r[2] is not None and r[0] != "del" and r[2] <= hi), None)
        if tgt:
            after.setdefault(tgt, []).extend(after.pop(k))

    # какие строки видны: заголовки хунков, строки с плашками и их окрестность
    keep_ctx, fold = b.get("context", 2), b.get("fold", 6)
    marked = sorted(i for i, r in enumerate(rows) if key(r) in before or key(r) in after)
    visible = {i for i, r in enumerate(rows) if r[0] == "hunk"}
    if not marked:
        visible |= set(range(min(len(rows), b.get("head", 12))))
    for i in marked:
        visible |= set(range(max(0, i - keep_ctx), min(len(rows), i + keep_ctx + 1)))
    # импорты и package не показываем: они свернутся в «Показать N строк»
    visible = {i for i in visible if not re.match(r"\s*(import|package)\s", rows[i][3] or "")}
    if b.get("focus"):
        # глава показывает только свои куски: остальное — свёрнуто
        def in_focus(r):
            return r[2] is not None and r[0] != "del" and any(lo <= r[2] <= hi for lo, hi in b["focus"] if lo)
        visible = {i for i in visible if rows[i][0] == "hunk" or in_focus(rows[i])}
    # код куска виден целиком: кусок и есть то, что объясняется (до 45 строк)
    for ch in b.get("chunks", []):
        lo, hi = note_range(ch.get("lines", ""))
        if isinstance(lo, int) and isinstance(hi, int) and hi - lo <= CHUNK_MAX_LINES:
            visible |= {i for i, r in enumerate(rows) if r[2] is not None and r[0] != "del" and lo <= r[2] <= hi}

    fid = b.get("id") or re.sub(r"[^\w]+", "-", b["file"].split("/")[-1]).strip("-").lower()

    def note_row(items, cls):
        return f'<tr class="note {cls}"><td colspan="3">{_side(items)}</td></tr>'

    out, i = [], 0
    while i < len(rows):
        if i not in visible:
            j = i
            while j < len(rows) and j not in visible:
                j += 1
            if j - i > fold:
                _fold_no[0] += 1
                inner = "".join(_drow(rows[k], fid, "") for k in range(i, j))
                out.append(f'<tr class="exp" data-fold="{_fold_no[0]}"><td colspan="3">↕ Показать {j - i} строк без комментариев</td></tr>'
                           f'<template id="fold-{_fold_no[0]}">{inner}</template>')
            else:
                out += [_drow(rows[k], fid, "") for k in range(i, j)]
            i = j
            continue
        r = rows[i]
        if key(r) in before:
            out.append(note_row(before[key(r)], "above"))
        out.append(_drow(r, fid, ""))
        if key(r) in after:
            out.append(note_row(after[key(r)], "below"))
        i += 1
    add = sum(r[0] == "add" for r in rows)
    rem = sum(r[0] == "del" for r in rows)
    status = b.get("status") or ("новый файл" if rem == 0 and rows and rows[0][3].startswith("@@ -0,0") else "")
    head = (f'<div class="dhead"><code>{html.escape(b["file"])}</code><span class="add">+{add}</span>'
            f'<span class="del">−{rem}</span>' + (f'<span class="kind">{html.escape(status)}</span>' if status else "")
            + (f'<span>{inline(b["caption"], terms=False)}</span>' if b.get("caption") else "") + "</div>")
    cols = '<colgroup><col style="width:46px"><col style="width:46px"><col></colgroup>'
    body = f'<div class="dfile" id="{fid}">{head}<table class="gd">{cols}<tbody>{"".join(out)}</tbody></table></div>'
    if b.get("lvl2"):
        return (f'<details class="lvl2"><summary>Код с пояснениями <span class="add">+{add}</span> <span class="del">−{rem}</span></summary>'
                f'{body}</details>')
    return body


def _files_word(n):
    k = 2 if 11 <= n % 100 <= 14 else 0 if n % 10 == 1 else 1 if 2 <= n % 10 <= 4 else 2
    return f"{n} {('файл', 'файла', 'файлов')[k]}"


def picture_block(pic):
    """Часть 1 обучения: зачем, было → стало, карта файлов по слоям. Один экран, имена — настоящие."""
    out = []
    if pic.get("why"):
        out.append(f'<div class="pic-why"><span class="lbl">Зачем</span> {inline(pic["why"])}</div>')
    if pic.get("before") or pic.get("after"):
        out.append('<div class="pic-ba">'
                   + (f'<div class="pic-b"><span class="lbl">Было</span>{inline(pic["before"])}</div>' if pic.get("before") else "")
                   + (f'<div class="pic-a"><span class="lbl">Стало</span>{inline(pic["after"])}</div>' if pic.get("after") else "")
                   + "</div>" + (f'<p class="pic-key"><b>Главное:</b> {inline(pic["key"])}</p>' if pic.get("key") else ""))
    rows = []
    for L in pic.get("map", []):
        icon = next((i for k, i in ROLE_ICON if L["layer"].startswith(k)), "🧪" if L["layer"] == "тесты" else "·")
        if L["layer"] == "тесты":
            names = ", ".join(f'<a href="#{html.escape(f["sid"])}">{html.escape(f["name"])}</a>' if f.get("sid") else html.escape(f["name"])
                              for f in L["files"])
            rows.append(f'<tr><th>{icon} тесты</th><td><span class="pic-same">{_files_word(len(L["files"]))}: {names}</span></td></tr>')
            continue
        items = []
        for f in L["files"]:
            name = html.escape(f["name"])
            link = f'<a href="#{html.escape(f["sid"])}" title="{html.escape(re.sub(r"[`*]", "", f.get("note", "")), quote=True)}">{name}</a>' if f.get("sid") else name
            items.append(f'<li class="{"heart" if f.get("heart") else ""}">{"★ " if f.get("heart") else ""}<code>{link}</code>'
                         + (f' <span class="fc-tag">{f["tag"]}</span>' if f.get("tag") else "")
                         + (f' <span class="pic-same">+ ещё {f["same"]} с той же правкой</span>' if f.get("same") else "")
                         + (' <span class="pic-heart">сердце MR</span>' if f.get("heart") else "")
                         + (f' <span class="pic-same">· {html.escape(f["sub"])}</span>' if f.get("sub") else "") + "</li>")
        rows.append(f'<tr><th>{icon} {html.escape(L["layer"])}</th><td><ul>{"".join(items)}</ul></td></tr>')
    if rows:
        out.append('<h3>Карта файлов</h3><p class="sub">Слои — сверху вниз, как идёт запрос. Клик по файлу — к его карточке в части «Файлы по порядку».</p>'
                   f'<table class="pic-map"><tbody>{"".join(rows)}</tbody></table>')
    return "".join(out)


def filecard_block(b):
    """Карточка файла, уровень 1: роль слоя, методы с объявлением из кода. Тело методов — уровень 2, под катом."""
    role = f'<span class="fc-role">{html.escape(b["role"])}</span>' if b.get("role") else ""
    lead = f'<p class="fc-lead">{inline(b["lead"])}</p>' if b.get("lead") else ""
    items = []
    for m in b.get("methods", []):
        tag = {"new": "новый", "modified": "правка", "moved": "перенесён"}.get(m.get("change"), "")
        wk = (f' <a class="wk {PLATE.get(m["weak"], "note")}" href="#chunk-{html.escape(m["cid"])}" title="Слабое место — в коде">'
              f'{ {"block": "!", "fix": "!", "ask": "?", "know": "i"}[m["weak"]] }</a>' if m.get("weak") else "")
        sig = f'<code class="fc-sig">{highlight(m["sig"])}</code>' if m.get("sig") else f'<code>{html.escape(m["name"])}</code>'
        items.append(f'<li><a class="fc-m" href="#chunk-{html.escape(m["cid"])}">{sig}</a>'
                     + (f' <span class="fc-tag">{tag}</span>' if tag else "") + wk
                     + f'<div class="fc-p">{inline(m["purpose"])}</div></li>')
    meth = f'<ul class="fc-list">{"".join(items)}</ul>' if items else ""
    return f'<div class="filecard">{role}{lead}{meth}</div>'


def note_range(line):
    """"30-33" или "30–33" → (30, 33); одиночная строка и "-5" (удалённая) → (строка, None)."""
    m = re.fullmatch(r"(\d+)\s*[-–]\s*(\d+)", str(line))
    if m:
        return int(m.group(1)), int(m.group(2))
    return (int(line) if str(line).isdigit() else line), None


def weak_id(fid):
    return f' id="weak-{html.escape(fid)}"' if fid else ""


def chunk_links(n, cls):
    """Связи куска одной строкой: кто зовёт, кого зовёт, какие ответы отдаёт и когда. Общая для карточки и строки уровня 2."""
    out = []
    if n.get("callers"):
        out.append(f'<span class="lbl">Кто зовёт</span> {", ".join(inline(x, terms=False) for x in n["callers"])}')
    if n.get("callees"):
        out.append(f'<span class="lbl">Кого зовёт</span> {", ".join(inline(x, terms=False) for x in n["callees"])}')
    if n.get("exits"):
        out.append(f'<span class="lbl">Исходы</span> <span class="ex">{"; ".join(inline(x, terms=False) for x in n["exits"])}</span>')
    return f'<div class="{cls}">{" · ".join(out)}</div>' if out else ""


def _side(items):
    """Содержимое ячейки справа: блок файла, комментарии «зачем», замечания."""
    side = ""
    for n in items:
        k = n.get("kind", "why")
        if k == "chunk":
            label = f'{inline(n["name"], terms=False)} · {html.escape(str(n["lines"]))}'
            how = ("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in n["how"]) + "</ol>") if n.get("how") else ""
            dec = f' <a href="#{n["decision"]}">Почему так →</a>' if n.get("decision") else ""
            weak = "".join(f'<div class="cw {PLATE.get(w["severity"], "note")}"{weak_id(w.get("fid"))}><b>Слабое место:</b> {inline(w["claim"])}{review_ref(w.get("fid"))}'
                           + (f'<div class="cwhy">{inline(w["why"])}</div>' if w.get("why") else "") + "</div>" for w in n.get("weak", []))
            sym = html.escape(re.sub(r"[`*]", "", n["name"]), quote=True)
            side += (f'<div class="nb chunk" id="chunk-{html.escape(n.get("cid", ""))}" data-symbol="{sym}" data-lines="{html.escape(str(n["lines"]))}">'
                     f'<b class="t">{label}</b> {inline(n["purpose"])}{dec}'
                     + (f'<div class="cwhyrole"><span class="lbl">Зачем</span> {inline(n["why"])}</div>' if n.get("why") else "")
                     + chunk_links(n, "clinks")
                     + (f'<div class="chow"><span class="lbl">Как работает</span>{how}</div>' if how else "") + weak + "</div>")
            continue
        if k == "part":
            label = f'{inline(n["name"], terms=False)}' + (f' · {html.escape(str(n["lines"]))}' if n.get("lines") else "")
            side += f'<div class="nb part"><b class="t">{label}</b> {inline(n["text"])}</div>'
        elif k == "why":
            ref = n.get("_range") or n.get("_ref")
            ref = f'<span class="ref">стр. {ref}</span>' if ref else ""
            side += f'<div class="nb why">{ref}{inline(n["text"])}</div>'
        else:
            ref = n.get("_range") or n.get("_ref")
            ref = f'<span class="ref">стр. {ref}</span>' if ref else ""
            label = "Слабое место" if n.get("finding") else NOTE_LABEL.get(k, k)
            side += f'<div class="nb {k}"{weak_id(n.get("fid"))}>{ref}<b class="t">{label}:</b>{inline(n["text"])}{review_ref(n.get("fid"))}</div>'
    return side



# Подсветка синтаксиса как в GitLab: текст кода обычного цвета, токены — своим. Лексер грубый, но не ломает текст.
# Кусок до 45 строк виден целиком: больше уже не читается за один взгляд, такой кусок делят (references/fields.md, «Куски кода»)
CHUNK_MAX_LINES = 45
_KW = {
    "kt": "package import class interface object fun val var return if else when try catch finally throw is in as null true false "
          "override private public internal protected companion sealed abstract enum this super for while do "
          "break continue suspend lateinit typealias const",
    "java": "package import class interface enum extends implements return if else switch case default try catch finally throw "
            "throws new null true false public private protected static final void this super for while do break continue",
    "sql": "select from where and or not insert into values update set delete create table index alter add drop null "
           "primary key references on join left inner group by order limit as is default constraint unique",
    "feature": "Функционал Сценарий Структура сценария Предыстория Дано Когда Тогда И Но Примеры",
}
_LANG = {"kts": "kt", "kt": "kt", "java": "java", "sql": "sql", "feature": "feature", "json": "json", "yaml": "yaml", "yml": "yaml"}
_HL_LANG = [""]


def lang_of(path):
    return _LANG.get(path.rsplit(".", 1)[-1].lower(), "") if path and "." in path else ""


def _tok_re(lang):
    comment = {"sql": r"--.*", "feature": r"#.*", "yaml": r"#.*"}.get(lang, r"//.*|/\*.*?(?:\*/|$)")
    kw = _KW.get(lang, "")
    kwre = (r"\b(?:" + "|".join(sorted(map(re.escape, kw.split()), key=len, reverse=True)) + r")\b") if kw else r"(?!x)x"
    return re.compile(
        rf"(?P<c>{comment})|(?P<s>\"(?:\\.|[^\"\\])*\"?|'(?:\\.|[^'\\])*'?)|(?P<a>@[A-Za-z_]\w*)"
        rf"|(?P<k>{kwre})|(?P<n>\b\d[\d_.]*\b)|(?P<t>\b[A-Z][A-Za-z0-9_]*\b)",
        re.I if lang == "sql" else 0)


_TOK = {}


def highlight(text, lang=None):
    lang = _HL_LANG[0] if lang is None else lang
    if lang not in ("kt", "java", "sql", "feature", "json", "yaml"):
        return html.escape(text)
    rx = _TOK.setdefault(lang, _tok_re(lang))
    out, pos = [], 0
    for m in rx.finditer(text):
        kind = m.lastgroup
        if kind == "t" and lang in ("sql", "feature", "json", "yaml"):
            continue
        out.append(html.escape(text[pos:m.start()]))
        out.append(f'<span class="tk-{kind}">{html.escape(m.group())}</span>')
        pos = m.end()
    out.append(html.escape(text[pos:]))
    return "".join(out)


def _drow(r, fid, cm):
    kind, old, new, text = r
    hid, cls = "", kind
    anchor = f' id="{fid}-L{new}"' if new is not None and kind != "del" else ""
    if kind == "hunk":
        return f'<tr class="{cls}"{hid}><td class="ln"></td><td class="ln"></td><td class="cd">{html.escape(text)}</td>{cm}</tr>'
    sign = {"add": "+", "del": "−"}.get(kind, " ")
    return (f'<tr class="{cls}"{hid}{anchor}><td class="ln">{old or ""}</td><td class="ln">{new if kind != "del" else ""}</td>'
            f'<td class="cd"><span class="sg">{sign}</span>{highlight(text)}</td>{cm}</tr>')


def code_block(b):
    lang = b.get("lang", "")
    hl = set(b.get("highlight", []))
    lines = b["code"].rstrip("\n").split("\n")
    rendered = []
    for i, line in enumerate(lines, 1):
        esc = html.escape(line) or " "
        if lang == "diff" and line.startswith("+") and not line.startswith("+++"):
            rendered.append(f'<span class="l-add">{esc}</span>')
        elif lang == "diff" and line.startswith("-") and not line.startswith("---"):
            rendered.append(f'<span class="l-del">{esc}</span>')
        elif lang == "diff" and line.startswith("@@"):
            rendered.append(f'<span class="l-hunk">{esc}</span>')
        elif i in hl:
            rendered.append(f'<span class="hl">{highlight(line, _LANG.get(lang, lang)) or " "}</span>')
        else:
            rendered.append((highlight(line, _LANG.get(lang, lang)) or " ") + "\n")
    body = "".join(x if x.endswith("\n") else x for x in rendered)
    cap = b.get("caption") or (b.get("file") or "")
    cap_html = f'<span class="cap">{inline(cap, terms=False)}</span>' if cap else ""
    return f"<pre>{cap_html}<code>{body}</code></pre>"


def block(b):
    t = b["type"]
    if t == "p":
        return f"<p>{inline(b['text'])}</p>"
    if t == "h":
        return f"<h3>{inline(b['text'])}</h3>"
    if t == "code":
        return code_block(b)
    if t == "diff":
        return diff_block(b)
    if t == "list":
        tag = "ol" if b.get("ordered") else "ul"
        return f"<{tag}>" + "".join(f"<li>{inline(i)}</li>" for i in b["items"]) + f"</{tag}>"
    if t == "table":
        head = "".join(f"<th>{inline(h)}</th>" for h in b["head"])
        rows = "".join("<tr>" + "".join(f"<td>{inline(str(c))}</td>" for c in r) + "</tr>" for r in b["rows"])
        return f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"
    if t == "callout":
        kind = b.get("kind", "info")
        title = f'<b class="t">{inline(b["title"])}</b>' if b.get("title") else ""
        return f'<div class="callout {kind}">{title}{inline(b["text"])}</div>'
    if t == "files":
        rows = []
        for f in b["items"]:
            kind = KIND_LABEL.get(f.get("kind", "other"), f.get("kind", ""))
            step = f'<a href="#{f["step"]}">шаг</a>' if f.get("step") else ""
            rows.append(
                f'<tr><td><code>{html.escape(f["path"])}</code></td><td><span class="kind">{kind}</span></td>'
                f'<td class="num"><span class="add">+{f.get("added", 0)}</span> <span class="del">−{f.get("removed", 0)}</span></td>'
                f"<td>{step}</td></tr>")
        return ('<table class="files"><thead><tr><th>Файл</th><th>Тип</th><th>Строки</th><th></th></tr></thead><tbody>'
                + "".join(rows) + "</tbody></table>")
    if t == "annotated":
        rows = []
        for line, note in b["lines"]:
            cls = "c add" if line.startswith("+") else "c"
            rows.append(f'<tr><td class="{cls}">{html.escape(line) or " "}</td><td class="x">{inline(note) if note else ""}</td></tr>')
        cap = f'<caption class="cap" style="text-align:left">{inline(b["caption"], terms=False)}</caption>' if b.get("caption") else ""
        return f'<table class="anno">{cap}<tbody>{"".join(rows)}</tbody></table>'
    if t == "think":
        def row(c, l, v):
            return f'<div class="row {c}"><div class="lbl">{l}</div><div class="val">{v}</div></div>'
        did = inline(b["did"]) if b.get("did") else ""
        if b.get("cmd"):
            did += f'<pre><code>{html.escape(b["cmd"])}</code></pre>'
        hidden = (row("", "Что сделал", did) if did else "") + (row("", "Что увидел", inline(b["saw"])) if b.get("saw") else "")
        tr = b.get("trace", "")
        if b.get("source"):
            tr = b["source"]
        recon = (not tr or tr.startswith("реконструкция")) and not b.get("source")
        rest = tr[len("реконструкция"):].lstrip(" :—") if recon else tr
        trace = (f'<div class="trace recon">реконструкция по коду{(": " + inline(rest)) if rest else ""}</div>'
                 if recon else f'<div class="trace">откуда известно: {inline(rest)}</div>')
        rej = ""
        if b.get("rejected"):
            rej = row("r", "Отбросил", "<ul>" + "".join(f"<li>{inline(x)}</li>" for x in b["rejected"]) + "</ul>")
        q = "" if b.get("question_in_title") else row("q", "Вопрос", inline(b["question"]))
        details = f'<details><summary>Как искал и откуда известно</summary>{hidden}{trace}</details>' if (hidden or not b.get("source")) else trace
        return f'<div class="think">{q}{row("d", "Решение", inline(b["decided"]))}{rej}{details}</div>'
    if t == "more":
        return (f'<details class="more"><summary>{inline(b.get("title", "Для углубления"), terms=False)}</summary>'
                + "".join(block(x) for x in b["blocks"]) + "</details>")
    if t == "flow":
        nodes = []
        for n in b["nodes"]:
            cls = "fnode changed" if n.get("step") else "fnode"
            inner = f"<b>{inline(n['label'], terms=False)}</b>"
            if n.get("note"):
                inner += f'<span class="fnote">{inline(n["note"], terms=False)}</span>'
            if n.get("step"):
                if STEP_NO.get(n["step"]):
                    inner += f'<span class="fstep">{STEP_NO[n["step"]]}</span>'
                nodes.append(f'<a class="{cls}" href="#{n["step"]}">{inner}</a>')
            else:
                nodes.append(f'<div class="{cls}">{inner}</div>')
        cap = f'<p class="sub">{inline(b["caption"])}</p>' if b.get("caption") else ""
        return cap + '<div class="flow">' + '<span class="arr">→</span>'.join(nodes) + "</div>"
    if t == "trace":
        cards = []
        for i, st in enumerate(b["steps"], 1):
            head = (f'<div class="tsh"><span class="tsn">{i}</span><b>{inline(st["who"], terms=False)}</b>'
                    + (f'<span class="tsr">{inline(st["role"], terms=False)}</span>' if st.get("role") else "")
                    + (f'<span class="tsf">{html.escape(st["where"])}</span>' if st.get("where") else "") + "</div>")
            def row(lbl, val, code=False):
                if not val:
                    return ""
                v = (f'<pre class="tsc"><code>{highlight(val, _LANG.get(st.get("lang"), st.get("lang")))}</code></pre>' if code else inline(val))
                return f'<div class="tsrow"><span class="lbl">{lbl}</span><div class="tsv">{v}</div></div>'
            body = (row("Пришло", st.get("in")) + row("Делает", st.get("does")) + row("Код", st.get("code"), True)
                    + row("Запрос в базу", st.get("query"), True) + row("Вернулось", st.get("returned")) + row("Ушло дальше", st.get("out")))
            cards.append(f'<li class="tstep">{head}{body}</li>')
        return f'<ol class="trace">{"".join(cards)}</ol>'
    if t == "mechwalk":
        cards = []
        for i, st in enumerate(b["steps"], 1):
            head = (f'<div class="tsh"><span class="tsn">{i}</span><b>{inline(st["does"], terms=False)}</b>'
                    + (f'<span class="tsf">{html.escape(st["at"])}</span>' if st.get("at") else "") + "</div>")
            body = (f'<pre class="tsc"><code>{highlight(st["code"], _LANG.get(b.get("lang"), b.get("lang")))}</code></pre>' if st.get("code") else "")
            body += f'<div class="tsrow"><span class="lbl">На примере</span><div class="tsv">{inline(st["result"])}</div></div>' if st.get("result") else ""
            body += f'<div class="tsrow"><span class="lbl">Не выйдет, если</span><div class="tsv">{inline(st["fails"])}</div></div>' if st.get("fails") else ""
            cards.append(f'<li class="tstep">{head}{body}</li>')
        return f'<ol class="trace">{"".join(cards)}</ol>'
    if t == "callgraph":
        cap = f'<p class="sub">{inline(b["caption"])}</p>' if b.get("caption") else ""
        return (cap + '<p class="cg-pointer">Граф вызовов — в левой колонке: клик по узлу ведёт к куску в тексте, «Назад» в браузере — обратно.</p>'
                + f'<div class="cg cg-inline"><ul>{callgraph_node(b["root"])}</ul></div>')
    if t == "filecard":
        return filecard_block(b)
    if t == "samecard":
        rows = "".join(f"<tr>{''.join(f'<td>{inline(c)}</td>' for c in r)}</tr>" for r in b["rows"])
        return (f'<div class="samecard"><p><b>Та же правка ещё в {b["count"]} файлах.</b> Код такой же, как выше; разбирать каждый не нужно.</p>'
                f'<table><thead><tr><th>Файл</th><th>Метод</th><th>Что меняет</th></tr></thead><tbody>{rows}</tbody></table>'
                f'<details class="lvl2"><summary>Код каждого файла</summary>{"".join(block(x) for x in b["diffs"])}</details></div>')
    if t == "plan":
        return plan_block(b)
    if t == "anatomy":
        return anatomy_block(b)
    raise ValueError(f"Неизвестный тип блока: {t}")


ROLE_ICON = [("официант", "🍽"), ("меню", "📋"), ("помощник", "🔪"), ("повар", "👨‍🍳"), ("склад", "📦"),   # «помощник повара» — раньше «повара»
             ("поставщик", "🚚"), ("рецепт", "📜"), ("записка", "✉"), ("тарелка", "🍲"), ("продукты", "🥕"), ("гость", "🙋")]


KIND_ROLE = {"error": "ответ с ошибкой", "result": "ответ", "store": "данные"}


def graph_nav(n, roles):
    """Узел графа в левой колонке — карточка, как в полном графе, но плотнее.

    Над карточкой — плашка «номер · условие вызова». В карточке: слой и файл, значок и имя куска, пояснение узла.
    Справа от карточки — глава, метка замечания (ссылка на пункт ревью) и у свёрнутой ветки — сколько узлов внутри.
    Узел с детьми — <details>: ▾ сворачивает ветку. Клик по карточке — кусок в тексте."""
    role = re.sub(r"[`*]", "", n.get("role") or KIND_ROLE.get(n.get("kind"), ""))
    icon = next((i for k, i in ROLE_ICON if k in role.lower()), "")
    if icon:
        roles.setdefault(icon, role)          # в легенде — метафора и слой, как в подписи узла
    layer = role.split(" — ")[-1]
    sym = re.sub(r"[`*]", "", n["label"])
    file = re.sub(r"\.(kt|java)$", "", n.get("file", ""))
    kids = n.get("children", [])

    def count(x):
        return sum(1 + count(c) for c in x.get("children", []))
    edge = n.get("edge", "") or ""
    cond = f'<span class="cond">{inline(edge, terms=False)}</span>' if edge else ""
    l2 = (f'<span class="rl">{html.escape(layer)}</span>' if layer else "") + (
        f" · {html.escape(file)}" if file and file != sym else "")
    title = html.escape(re.sub(r"[`*]", "", " · ".join(x for x in (role, n.get("file", "")) if x)), quote=True)
    inner = ((f'<span class="l2">{l2}</span>' if l2 else "")
             + f'<span class="l1">{icon + " " if icon else ""}{inline(n["label"], terms=False)}</span>'
             + (f'<span class="nt">{inline(n["note"], terms=False)}</span>' if n.get("note") else ""))
    cls = "gn " + n.get("kind", "")
    if n.get("chunk"):
        body = (f'<a class="{cls}" href="#chunk-{html.escape(n["chunk"])}" data-chunk="{html.escape(n["chunk"])}" data-step="{n["step"]}" '
                f'title="{title}">{inner}</a>')
    elif n.get("step"):
        body = f'<a class="{cls}" href="#{n["step"]}" data-step="{n["step"]}" title="{title}">{inner}</a>'
    else:
        body = f'<span class="{cls}" title="{title}">{inner}</span>'
    g = CHAPTER.get(n.get("step"))
    badges = f'<span class="gl" title="глава {g}">гл.{g}</span>' if g else ""
    if n.get("weak"):
        sev = n["weak"]
        tip = "; ".join(f"{group_name(RISK_REF[f][0])} · {RISK_REF[f][1]}" for f in n.get("fids", []) if f in RISK_REF)
        mark = "!" if sev in ("block", "fix") else "?" if sev == "ask" else "i"
        first = next((f for f in n.get("fids", []) if f in RISK_REF), None)
        attrs = f'class="wk {PLATE.get(sev, "note")}" title="{html.escape("в ревью: " + tip if tip else "у куска есть замечание")}"'
        attrs = attrs.replace('title="в ревью: ', 'title="к слабому месту ниже в коде, на этой странице · ')
        badges += (f'<a {attrs} href="#weak-{html.escape(first)}">{mark}</a>' if first and LINK["review"]
                   else f'<span {attrs}>{mark}</span>')
    if kids:
        badges += f'<span class="hn" title="в свёрнутой ветке {count(n)} узл.">+{count(n)}</span>'
    gb = f'<span class="gb">{badges}</span>' if badges else ""
    if not kids:
        return f'<li>{cond}<div class="grow"><span class="tg leaf"></span>{body}{gb}</div></li>'
    return (f'<li>{cond}<details open><summary class="grow" title="▾ — свернуть ветку"><span class="tg"></span>{body}{gb}</summary>'
            f'<ul>{"".join(graph_nav(c, roles) for c in kids)}</ul></details></li>')


def callgraph_node(n):
    """Узел дерева вызовов: роль слоя, блок, подпись ветки (edge) и дети. kind: error · store · result."""
    cls = " ".join(x for x in ("cnode", "changed" if n.get("step") else "", n.get("kind", "")) if x)
    inner = f'<span class="crole">{inline(n["role"], terms=False)}</span>' if n.get("role") else ""
    inner += f"<b>{inline(n['label'], terms=False)}</b>"
    if n.get("note"):
        inner += f'<span class="fnote">{inline(n["note"], terms=False)}</span>'
    if n.get("step"):
        if STEP_NO.get(n["step"]):
            inner += f'<span class="fstep">{STEP_NO[n["step"]]}</span>'
        href = f'#chunk-{html.escape(n["chunk"])}' if n.get("chunk") else f'#{n["step"]}'
        box = f'<a class="{cls}" href="{href}">{inner}</a>'
    else:
        box = f'<div class="{cls}">{inner}</div>'
    edge = f'<span class="edge">{inline(n["edge"], terms=False)}</span>' if n.get("edge") else ""
    kids = "".join(callgraph_node(c) for c in n.get("children", []))
    return f"<li>{edge}{box}" + (f"<ul>{kids}</ul>" if kids else "") + "</li>"


ROLE_CHECK = {"ok": "✅", "note": "ℹ️", "warn": "⚠️", "fail": "❌", "na": "—"}


def place_parts(step):
    """Части файла из anatomy ставит в дифф шага: к первой строке части, которая есть в диффе.

    У нового файла видны все строки. У изменённого — только хунки: часть без видимой строки остаётся
    в таблице «Как читать файл». Помечает части полем `_placed`, дифф получает `parts`."""
    an = next((b for b in step.get("blocks", []) if b["type"] == "anatomy"), None)
    df = next((b for b in step.get("blocks", []) if b["type"] == "diff"), None)
    if not an or not df:
        return
    new_lines = sorted(r[2] for r in parse_diff(df["diff"]) if r[2] is not None and r[0] != "del")
    placed = []
    for x in an.get("parts", []):
        nums = [int(n) for n in re.findall(r"\d+", str(x.get("lines", "")))]
        if not nums:
            continue
        lo, hi = nums[0], nums[-1]
        at = next((n for n in new_lines if lo <= n <= hi), None)
        x["_placed"] = at is not None
        if at is not None:
            placed.append({**x, "at": at})
    df["parts"] = placed
    # проверка с номером строки и не ✅ — ещё и справа от своей строки, как тред ревью
    df["check_notes"] = []
    for c in an.get("checks", []):
        c["_placed"] = bool(c.get("line") and c.get("status") in ("note", "warn", "fail") and int(str(c["line"]).split("-")[0]) in new_lines)
        if c["_placed"]:
            df["check_notes"].append({"line": c["line"], "kind": {"note": "note", "warn": "warn", "fail": "risk"}[c["status"]], "text": c["text"]})


def anatomy_block(b):
    """«Как читать файл»: из каких частей файл (по строкам) и проверка по чек-листу его роли.
    Свёрнут, пока все проверки ✅: с ℹ️/⚠️/❌ открыт — читатель видит замечание сразу."""
    parts = "".join(f'<tr><td class="ln">{html.escape(str(x.get("lines", "")))}</td><td><b>{inline(x["name"], terms=False)}</b></td>'
                    f'<td>{inline(x["what"])}</td></tr>' for x in b.get("parts", []) if not x.get("_placed"))
    checks = "".join(f'<tr><td class="st">{ROLE_CHECK.get(c.get("status", "ok"), "")}</td><td>{inline(c["text"])}</td></tr>'
                     for c in b.get("checks", []) if not c.get("_placed"))
    is_open = " open" if any(c.get("status") in ("note", "warn", "fail") and not c.get("_placed") for c in b.get("checks", [])) else ""
    role = f' · роль: {inline(b["role"], terms=False)}' if b.get("role") else ""
    placed = any(x.get("_placed") for x in b.get("parts", []))
    note = '<p class="sub">Части файла — в коде, плашкой над первой строкой части; замечания — под своей строкой.</p>' if placed else ""
    return (f'<details class="anatomy"{is_open}><summary>Как читать файл{role}</summary>{note}'
            + (f'<table><thead><tr><th>Строки</th><th>Часть</th><th>Что делает</th></tr></thead><tbody>{parts}</tbody></table>' if parts else "")
            + (f'<table><thead><tr><th></th><th>Проверка по роли файла</th></tr></thead><tbody>{checks}</tbody></table>' if checks else "")
            + "</details>")


def plan_block(b):
    """План доработки: задача → что нужно → где это в сервисе → какие файлы → почему здесь."""
    out = ['<div class="plan" id="plan">']
    if b.get("task"):
        out.append(f'<p class="pk"><b>Задача:</b> {inline(b["task"])}</p>')
    kind = f'<p class="pk"><b>Тип задачи:</b> {inline(b["kind"])}</p>' if b.get("kind") else ""
    if kind and not b.get("try"):
        out.append(kind)

    def files(ids):
        cells = []
        for sid in ids:
            title, new = STEP_FILE.get(sid, (sid, False))
            badge = '<span class="kind">новый</span>' if new else '<span class="kind">правка</span>'
            cells.append(f'<a href="#{sid}"><code>{html.escape(title)}</code></a>{badge}')
        return "<br>".join(cells)
    rows = "".join(f'<tr><td class="no"><a href="#ch-{k}">{k}</a></td><td><b>{inline(r["need"])}</b></td><td>{inline(r.get("where", ""))}</td>'
                   f'<td class="pf">{files(r.get("files", []))}</td><td>{inline(r.get("why", ""))}</td></tr>'
                   for k, r in enumerate(b["rows"], 1))
    table = ('<table><thead><tr><th>#</th><th>Что нужно</th><th>Где это в сервисе</th><th>Файлы</th><th>Почему здесь</th></tr></thead>'
             f"<tbody>{rows}</tbody></table>")
    if b.get("try"):
        out.append(f'<div class="callout try"><b class="t">Попробуй сам</b>{inline(b["try"])}</div>')
        out.append(f'<details class="more"><summary>Показать план автора</summary>{kind}{table}</details>')
    else:
        out.append(table)
    return "".join(out) + "</div>"


LINK = {"prefix": "", "open_review": False, "review": ""}
RISK_REF = {}      # id замечания → (группа «когда действовать», номер в группе) — как в ревью


def risk_groups(risks):
    """Замечания по группам «когда действовать» в порядке ревью; заполняет RISK_REF."""
    groups = {}
    for r in risks:
        w = r.get("when") or ("merge" if r.get("level") in ("blocker", "fix") else "know")
        groups.setdefault(w, []).append(r)
    RISK_REF.clear()
    for w, rs in groups.items():
        for k, r in enumerate(rs, 1):
            if r.get("_fid"):
                RISK_REF[r["_fid"]] = (w, k)
    return groups


def group_name(w):
    return "Расхождения со спекой" if w == "spec" else WHEN.get(w, w)


def review_ref(fid):
    """«в ревью: До мержа · 2» — ссылка со слабого места в коде на тот же пункт ревью."""
    if fid not in RISK_REF or not LINK["review"]:
        return ""
    w, k = RISK_REF[fid]
    return f' <a class="rvref" href="{html.escape(LINK["review"])}#risk-{html.escape(fid)}">в ревью: {group_name(w)} · {k}</a>'   # ревью-страница ссылается на страницу обучения


def code_link(sid=None, chunk=None):
    """Ссылка к коду: имя куска (или файла) и глава. Сквозных номеров шагов нет — они путались с пунктами спеки."""
    if chunk in CHUNKS:
        sid, name, href = CHUNKS[chunk]["step"], f'<code>{html.escape(CHUNKS[chunk]["symbol"])}</code>', f"#chunk-{chunk}"
    elif sid:
        name, href = html.escape(STEP_LABEL.get(sid, sid)), f"#{sid}"
    else:
        return ""
    g = CHAPTER.get(sid)
    return f'<a class="tocode" href="{LINK["prefix"]}{href}">{name}' + (f'<span class="gl">гл. {g}</span>' if g else "") + "</a>"


def step_link(sid, chunk=None):
    return code_link(sid, chunk)


def verdict_block(v, spec=None):
    """Ревью: решение первым экраном (вердикт, что до мержа, расхождения со спекой), потом остальные замечания,
    чек-лист, требования и «Проверь сам». Каждое замечание стоит один раз; чек-лист и требования ссылаются на него."""
    st = v.get("status", "fix")
    risks = v.get("risks", [])

    groups = risk_groups(risks)
    ref = RISK_REF

    def rid(r):
        return f' id="risk-{html.escape(r["_fid"])}"' if r.get("_fid") else ""

    def item(r, why=True):
        return (f'<li{rid(r)}><b>{inline(r["text"])}</b>'
                + (f'<div class="why">{inline(r["why"])}</div>' if why and r.get("why") else "")
                + (f'<div class="todo">→ {inline(r["do"])}</div>' if r.get("do") else "")
                + (f' {code_link(r.get("step"), r.get("chunk"))}' if r.get("step") or r.get("chunk") else "") + "</li>")

    def see(fid):
        w, k = ref[fid]
        return f'<a href="#risk-{html.escape(fid)}">{group_name(w)} · {k}</a>'

    def count(items, field, icons):
        c = {}
        for x in items:
            c[x.get(field)] = c.get(x.get(field), 0) + 1
        return " · ".join(f"{icons[k]} {c[k]}" for k in icons if c.get(k))
    tally = []
    if v.get("checks"):
        tally.append("чек-лист: " + count(v["checks"], "status", {"ok": "✅", "note": "ℹ️", "warn": "⚠️", "fail": "❌"}))
    if v.get("requirements"):
        tally.append("требования: " + count(v["requirements"], "status", {"ok": "✅", "partial": "⚠️", "gap": "❌"}))
    out = [f'<section class="verdict {st}" id="verdict"><p class="vh">{VERDICT.get(st, st)}</p>',
           f"<p>{inline(v['summary'])}</p>"]
    if tally:
        out.append(f'<p class="tally">{" · ".join(tally)}</p>')
    merge, sp = groups.get("merge", []), groups.get("spec", [])
    box = (f'<div class="vbox merge" id="merge"><h3>До мержа: {len(merge)}</h3><ol class="items">' + "".join(item(r) for r in merge) + "</ol></div>"
           if merge else '<div class="vbox merge none" id="merge"><h3>До мержа: ничего</h3><p>Код можно вливать после аппрува.</p></div>')
    if sp:
        link = f' · <a href="{html.escape(spec)}" target="_blank" rel="noopener">открыть спеку</a>' if spec else ""
        box += (f'<div class="vbox spec" id="spec"><h3>Расхождения со спекой: {len(sp)}{link}</h3><ol class="items">'
                + "".join(item(r, why=False) for r in sp) + "</ol></div>")
    out.append(f'<div class="vgrid">{box}</div></section>')

    rest = [w for w in WHEN if w in groups and w not in ("merge", "spec")] + [w for w in groups if w not in WHEN]
    if rest:
        body = "".join(f'<p class="rk">{WHEN.get(w, w)}</p><ol class="items">' + "".join(item(r) for r in groups[w]) + "</ol>" for w in rest)
        out.append(f'<section class="rv" id="risks"><h2>Остальные замечания: {sum(len(groups[w]) for w in rest)}</h2>'
                   f'<p class="sub">Мерж не блокируют. Сгруппированы по тому, когда действовать.</p>{body}</section>')
    if v.get("checks"):
        def ck(c):
            more = re.search(r" и ещё (\d+)$", c["text"])
            if c.get("_fid") in ref:
                val = f'<span class="see">см. </span>{see(c["_fid"])}' + (f' <span class="see">и ещё {more.group(1)}</span>' if more else "")
            else:
                val = inline(c["text"]) + (f'<div class="todo">→ {inline(c["do"])}</div>' if c.get("do") else "")
            return (f'<tr><td class="st">{CHECK.get(c.get("status"), c.get("status", ""))}</td>'
                    f'<td class="ar">{inline(c["area"], terms=False)}</td><td>{val}</td></tr>')
        out.append('<section class="rv" id="checklist"><h2>Чек-лист ревьюера</h2>'
                   f'<table class="ck"><tbody>{"".join(ck(c) for c in v["checks"])}</tbody></table></section>')
    if v.get("requirements"):
        def req_row(r):
            meta = " · ".join(x for x in [f"код: {inline(r['where'])}" if r.get("where") else "",
                                          f"тест: {inline(r['proof'])}" if r.get("proof") else ""] if x)
            todo = (f'<div class="todo">→ см. {see(r["_fid"])}</div>' if r.get("_fid") in ref
                    else f'<div class="todo">→ {inline(r["do"])}</div>' if r.get("do") else "")
            return (f'<tr><td class="st">{REQ.get(r.get("status", "ok"), "")}</td><td><b>{inline(r["req"])}</b>'
                    + (f'<div class="fact">{meta}</div>' if meta else "") + todo
                    + f'</td><td class="go">{code_link(r.get("step"), r.get("chunk"))}</td></tr>')
        bad = [r for r in v["requirements"] if r.get("status") != "ok"]
        good = [r for r in v["requirements"] if r.get("status") == "ok"]
        body = f'<table class="vlist"><tbody>{"".join(req_row(r) for r in bad)}</tbody></table>' if bad else ""
        if good:
            body += (f'<details class="okreq"{"" if bad else " open"}><summary>✅ Выполнено и доказано тестом: {len(good)}</summary>'
                     f'<table class="vlist"><tbody>{"".join(req_row(r) for r in good)}</tbody></table></details>')
        out.append(f'<section class="rv verdict-reqs" id="reqs"><h2>Требования задачи: сделано и доказано?</h2>{body}</section>')
    if v.get("probes"):
        rows_ = "".join(f'<tr><td><a href="{html.escape(LINK.get("prefix", ""))}#chunk-{html.escape(r["at"])}"><code>{html.escape(r["symbol"])}</code></a></td>'
                        f'<td><b>{html.escape(r["kind"])}:</b> {inline(r["input"])}</td><td>{inline(r["code"])}</td>'
                        + (f'<td>⚠ <a href="#risk-{html.escape(r["finding"])}">{inline(r["claim"], terms=False)}</a></td>' if r["finding"]
                           else f'<td>✅ {inline(r["ok"])}</td>') + "</tr>" for r in v["probes"])
        bad_ = sum(1 for r in v["probes"] if r["finding"])
        out.append(f'<section class="rv" id="probes"><h2>Кривые входы и старые данные: {len(v["probes"])} проб, слабых мест {bad_}</h2>'
                   '<p class="fact">ИИ пишет код под хороший пример. Здесь — что код сделает на записи до MR, на входе не того формата, на пустом и чужом.</p>'
                   f'<table class="ck"><tr><th>Где</th><th>Что пришло</th><th>Что сделает код</th><th>Итог</th></tr>{rows_}</table></section>')
    if v.get("verify"):
        out.append('<section class="rv" id="verify"><h2>Проверь сам</h2><ol>' + "".join(f"<li>{inline(x)}</li>" for x in v["verify"]) + "</ol></section>")
    return "".join(out)


def risks_block(risks):
    """Риски по группам «когда действовать» — для старого формата без проекции v3."""
    groups = {}
    for r in risks:
        w = r.get("when") or ("merge" if r.get("level") in ("blocker", "fix") else "know")
        groups.setdefault(w, []).append(r)
    out = ["<h3>Что сделать по рискам</h3>"]
    for w in [k for k in WHEN if k in groups and k != "spec"] + [k for k in groups if k not in WHEN]:
        rows = "".join(
            f'<tr><td class="st">{"🛑" if r.get("level") == "blocker" else "•"}</td><td><b>{inline(r["text"])}</b>'
            + (f'<div class="rwhy">{inline(r["why"])}</div>' if r.get("why") else "")
            + (f'<div class="todo">→ {inline(r["do"])}</div>' if r.get("do") else "")
            + f'</td><td class="go">{step_link(r.get("step"))}</td></tr>' for r in groups[w])
        out.append(f'<p class="rk">{WHEN.get(w, w)}</p><table class="vlist"><tbody>{rows}</tbody></table>')
    return "".join(out)


EX_KIND = {"predict": "Предскажи", "explain": "Объясни своими словами", "break": "Что сломается, если…", "where": "Где менять",
           "retell": "Перескажи"}


def exercise_block(q, raw=False):
    """Задание: вопрос, код по желанию, поле для своего ответа, ответ под «Сверить». Ответ хранится в браузере."""
    kind = q.get("kind", "predict")
    code = f'<pre><code>{highlight(q["code"])}</code></pre>' if q.get("code") else ""
    ans = q["a"] if raw else f"<p>{inline(q['a'])}</p>"
    return (f'<div class="ex" id="ex-{html.escape(q["id"])}" data-ex="{html.escape(q["id"])}"><span class="ex-kind {kind}">{EX_KIND.get(kind, kind)}</span> '
            f'{inline(q["q"])}{code}<textarea rows="{4 if kind == "retell" else 2}" placeholder="{"Три фразы своими словами" if kind == "retell" else "Твой ответ — одна-две фразы"}. Сначала напиши, потом сверь."></textarea>'
            f'<details class="ex-a"><summary>Сверить</summary>{ans}</details></div>')


def chapter_check(r, g):
    """Проверь себя в конце главы: вопросы на понимание, ответ раскрывается."""
    qs = r.get("check") or []
    if not qs:
        return ""
    items = "".join(f'<details class="q"><summary>{inline(q["q"], terms=False)}</summary><p>{inline(q["a"])}</p></details>' for q in qs)
    return f'<div class="chcheck"><b>Проверь себя — глава {g}</b>{items}</div>'


def before_after_block(items):
    """Урок на реальной ошибке ИИ: как было, как стало, почему."""
    out = []
    for b in items:
        lang = _LANG.get(b.get("before", {}).get("lang", ""), b.get("before", {}).get("lang", ""))
        def code(x):
            return f'<pre class="tsc"><code>{highlight(x.get("code", ""), lang)}</code></pre>' if x else ""
        link = f' <a href="{b["link"]}">к коду →</a>' if b.get("link") else ""
        out.append(f'<div class="ba"><h3>{inline(b["title"], terms=False)}</h3>'
                   f'<div class="bagrid"><div><span class="lbl was">Было</span>{code(b.get("before"))}</div>'
                   f'<div><span class="lbl now">Стало</span>{code(b.get("after"))}</div></div>'
                   f'<p><b>Почему:</b> {inline(b.get("why", ""))}{link}</p></div>')
    return f'<section class="step" id="before-after"><h2><span class="n">↺</span>Урок: было → стало</h2>{"".join(out)}</section>'


def lessons_block(items):
    rows = "".join(f'<div class="callout lesson"><b class="t">{inline(x["title"], terms=False)}</b>{inline(x["text"])}'
                   + (f' {step_link(x["step"])}' if x.get("step") else "") + "</div>" for x in items)
    return f'<section class="step" id="lessons"><h2><span class="n">★</span>Чему учиться на этом MR</h2>{rows}</section>'


def plan_rows(doc):
    return [r for b in doc.get("intro", []) if b.get("type") == "plan" for r in b["rows"]]


def ordered_steps(doc):
    """Шаги в порядке чтения и глава плана у каждого шага.

    Есть план — страница идёт главами по его пунктам: в главе сначала решения (`decisions`), потом файлы
    (`files`). Шаги вне плана — в конце, главой «Вне плана». Возвращает [(шаг, № главы или 0 или None)]."""
    rows = plan_rows(doc)
    steps = doc["steps"]
    if not rows:
        return [(s, None) for s in steps]
    by_id = {s["id"]: s for s in steps}
    out, used = [], set()
    for k, r in enumerate(rows, 1):
        for sid in r.get("decisions", []) + r.get("files", []):
            if sid in by_id and sid not in used:
                out.append((by_id[sid], k))
                used.add(sid)
    out += [(s, 0) for s in steps if s["id"] not in used]
    return out


def group_card(g, r, title):
    """Карточка главы — три ответа пункта плана: что хотели, почему так, как работает."""
    def row(label, val):
        return f'<div class="row"><div class="lbl">{label}</div><div class="val">{val}</div></div>' if val else ""
    what = inline(r["where"]) if r.get("where") else ""
    how = "<ol>" + "".join(f"<li>{inline(x)}</li>" for x in r["how"]) + "</ol>" if r.get("how") else ""
    learn_ = f'<p class="chlearn"><b>Что поймёшь:</b> {inline(r["learn"])}</p>' if r.get("learn") else ""
    return (f'<div class="chapter" id="ch-{g}"><h2><span class="n">Глава {g or "·"}.</span> {inline(title, terms=False)}</h2>{learn_}'
            f'<div class="pgroup">'
            + row("Где в сервисе", what) + row("Почему так", inline(r.get("why", ""))) + row("Как работает", how) + "</div></div>")


def doc_lang(doc):
    """Язык MR: поле `lang` JSON или большинство файлов .kt / .java в диффах."""
    if doc.get("lang"):
        return doc["lang"]
    files = [b.get("file", "") for s in doc.get("steps", []) for b in s.get("blocks", []) if b.get("type") == "diff"]
    return "kotlin" if sum(f.endswith(".kt") for f in files) > sum(f.endswith(".java") for f in files) else "java"


def resolve_glossary(base, lang):
    """Базовый термин — общая строка или варианты по языкам {"java": …, "kotlin": …}.
    Термина нет в языке MR — он не попадает в словарь: в Kotlin-MR нет `static`, в Java нет `data class`."""
    out = {}
    for k, v in base.items():
        v = v.get(lang) if isinstance(v, dict) else v
        if v:
            out[k] = v
    return out


def navbox(doc, outline):
    """Левая колонка: граф пути запроса и главы — одновременно, без вкладок. Граф компактный: строка на узел."""
    g = next((b for b in doc.get("intro", []) if b.get("type") == "callgraph"), None)
    if not g:
        return outline
    roles = {}
    tree = graph_nav(g["root"], roles)
    legend = " · ".join(f"{i} {html.escape(r)}" for i, r in roles.items())
    marks = ('<br><span class="wk risk">!</span> поправить · <span class="wk warn">?</span> вопрос · <span class="wk note">i</span> знать'
             if '"weak"' in json.dumps(g) else "")
    return ('<div id="navgrip" hidden title="Клик — свернуть или развернуть, потяни — изменить ширину"><span>‹</span></div>'
            '<details class="nsec" open><summary>Граф: путь запроса</summary>'
            f'<div class="gtools" hidden><button type="button" data-fold="1">Свернуть до слоёв</button><button type="button" data-fold="0">Развернуть всё</button></div><ul class="gtree">{tree}</ul>'
            f'<p class="glegend">{legend}{marks}'
            '<span><br>Плашка над узлом — порядок и условие вызова. Клик по карточке — к куску в тексте, «Назад» — обратно; ▾ сворачивает ветку. Alt+→ / Alt+← — соседний кусок по графу.</span></p></details>'
            f'<details class="nsec" open><summary>Главы</summary>{outline}</details>')


# Страница обучения: часть 1 — пять вопросов к MR, ответ свёрнут; часть 2 — справочник с главами.
# Вопрос: (заголовок, задание «подумай сам», заголовки разделов картины MR, из которых собран ответ).
QUESTIONS = [
    ("Зачем этот MR?", "кто будет вызывать новый код и какую задачу он решит? Одна-две фразы.", ["суть mr", "контекст задачи"]),
    ("Что на входе и что на выходе?", "что приходит в запросе и что уходит в ответе — на конкретных значениях. Подсказка: пример в описании MR или в тесте.", ["пример"]),
    ("Где запрос входит в код?", "какой файл и какой метод первыми получают запрос? Подсказка: верхний узел графа слева.", ["вход в код"]),
    ("Куда идёт запрос дальше?", "пройди от входа вниз по графу слева: какие куски вызываются по очереди и что каждый отдаёт следующему?", ["путь одного запроса", "слои и цепочка"]),
    ("Как работает главное в MR?", "возьми данные из примера и пройди код по шагам: какой файл открывается, что он делает с этими данными, где может не получиться?", ["главный механизм"]),
    ("Что может пойти не так?", "на каждой развилке спроси «а если нет?»: какие ответы с ошибкой есть, что доказывают тесты, какой старый код задет?", ["ветки", "кривые входы", "что обещают тесты", "правки старого кода"]),
    ("Не добавил ли ИИ лишнего?", "какие файлы MR запрос не вызывает? Зачем каждый из них?", ["файлы mr вне пути"]),
]
REFERENCE = ["как устроен сервис", "план доработки"]


def active_questions(doc):
    """Вопросы страницы обучения, для которых в картине MR есть раздел с ответом."""
    hs = [b["text"].lower() for b in doc.get("intro", []) if b.get("type") == "h"]
    return [q for q in QUESTIONS if any(h.startswith(key) for key in q[2] for h in hs)]


def topbar(doc, mode, other, steps_json, jumps=""):
    """Шапка обеих страниц: MR, переключатель «Ревью · Обучение», вердикт, где я, прогресс и «Продолжить»."""
    mr = doc.get("mr", {})
    name = inline(mr.get("ref") or doc.get("nav_title", "MR"), terms=False)
    st = doc.get("verdict", {}).get("status", "")
    out = [f'<header class="tb"><a class="tb-mr" href="#top">{name}</a>']
    if mode in ("review", "learn"):
        rv, ln = ("#top", html.escape(other)) if mode == "review" else (html.escape(other), "#top")
        cur = ' aria-current="page"'
        mark = (f' title="Вердикт: {html.escape(VERDICT.get(st, st))}">Ревью {VERDICT.get(st, st).split(" ")[0]}' if mode == "learn" and st else ">Ревью")
        out.append(f'<div class="tb-tabs" role="navigation" aria-label="Страницы разбора">'
                   f'<a href="{rv}"{cur if mode == "review" else ""}{mark}</a><a href="{ln}"{cur if mode == "learn" else ""}>Обучение</a></div>')
    if mode == "learn":
        out.append('<div class="tb-lvl" role="group" aria-label="Уровень разбора">'
                   '<button type="button" data-lvl="1" title="Файлы и методы: что делает каждый">Обзор</button>'
                   '<button type="button" data-lvl="2" title="Тот же разбор, код открыт с пояснениями">Код</button></div>')
    if st and mode != "learn":
        href = "#verdict" if mode != "learn" else f"{html.escape(other)}#verdict"
        out.append(f'<a class="tb-v {st}" href="{href}">{VERDICT.get(st, st)}</a>')
    out.append(f'<div class="tb-jump" role="navigation" aria-label="Разделы ревью">{jumps}</div>' if jumps else
               '<span class="tb-crumb" id="crumb" aria-live="polite"></span>')
    out.append('<span class="tb-prog" id="tbprog" hidden><span class="bar"><i></i></span><span class="t"></span></span>'
               f'<a class="tb-cont" id="tbcont" hidden href="#">Продолжить</a></header>')
    return "".join(out) + f'<script type="application/json" id="mr-steps">{steps_json}</script>'


def page(title, body_attrs, inner):
    return ("<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body {body_attrs}>{inner}<script>{JS}</script></body></html>")


def render(doc, base_glossary=None, mode="full", other="", learn_name=""):
    order = ordered_steps(doc)
    steps = [s for s, _ in order]
    group_of = {s["id"]: g for s, g in order}
    rows = plan_rows(doc)

    def group_title(g):
        return rows[g - 1]["need"] if g else "Вне плана"

    def ch_name(g):
        return f"Глава {g}. {re.sub(r'[`*]', '', group_title(g))}" if g else "Вне плана"

    def is_decision(s):
        """Решение главы: стоит в преамбуле главы, без строки «файл N из M»."""
        return s.get("part") == "design" and group_of.get(s["id"]) is not None

    set_glossary({**resolve_glossary(base_glossary or {}, doc_lang(doc)), **doc.get("glossary", {})})
    USED.clear()
    CHAPTER.clear()
    CHAPTER.update({s["id"]: group_of.get(s["id"]) for s in steps})
    STEP_NO.clear()
    STEP_NO.update({s["id"]: f"гл. {group_of[s['id']]}" if group_of.get(s["id"]) else "" for s in steps})
    STEP_LABEL.clear()
    STEP_LABEL.update({s["id"]: ("решение " + re.sub(r"[`*]", "", s["title"]).split(" · ")[0]) if s.get("part") == "design"
                       else re.sub(r"[`*]", "", s["title"]) for s in steps})
    CHUNKS.clear()
    CHUNKS.update(doc.get("_chunks", {}))
    CHUNKS_RAW.clear()
    CHUNKS_RAW.update(doc.get("_chunks", {}))
    STEP_FILE.clear()
    STEP_FILE.update({s["id"]: (re.sub(r"[`*]", "", s["title"]),
                                any("new file mode" in b.get("diff", "") or b.get("status") == "added"
                                    for b in s.get("blocks", []) if b["type"] == "diff")) for s in steps})
    mr = doc.get("mr", {})
    files_of = {}                     # глава → файлы по порядку: «файл 2 из 3» и счётчик в оглавлении
    for s in steps:
        if not is_decision(s):
            files_of.setdefault(group_of.get(s["id"]), []).append(s["id"])
    readable = [s for s in steps if not is_decision(s)]
    learn = mode == "learn"
    ex_at, ex_end = {}, {}           # шаг → задания после файла; глава → задания без куска
    for g_, r_ in enumerate(rows, 1):
        for j, q in enumerate(r_.get("check") or [], 1):
            q = {**q, "id": f"{g_}-{j}"}
            sid = CHUNKS_RAW.get(q.get("chunk"), {}).get("step") if q.get("chunk") else None
            (ex_at.setdefault(sid, []) if sid else ex_end.setdefault(g_, [])).append(q)
    last_of = {}
    for s_ in steps:
        if not is_decision(s_) and group_of.get(s_["id"]):
            last_of[group_of[s_["id"]]] = s_["id"]
    ch_nums = list(dict.fromkeys(group_of[s["id"]] for s in steps if group_of.get(s["id"]) is not None))
    # прогресс по уровню: на 1 — главы («разобрал главу»), на 2 — файлы
    prog = [{"id": s["id"], "label": STEP_LABEL[s["id"]]} for s in readable]
    steps_json = json.dumps(prog, ensure_ascii=False).replace("</", "<\\/")


    # ---------- оглавление: главы свёрнуты, открыта текущая; в главе — решения, файлы и куски
    def chunks_of(s):
        return [c for b in s.get("blocks", []) if b["type"] == "diff" for c in b.get("chunks", [])]
    intro_h = [b["text"] for b in doc.get("intro", []) if b.get("type") == "h"]

    ol = []
    ol_tail = []
    if learn:
        qs_ = [(f"q-{i}", q[0]) for i, q in enumerate(active_questions(doc), 1)]
        ol.append('<a class="oli" href="#part-1" data-ch="intro"><b>Часть 1. Картина MR</b></a>')
        if any(h.lower().startswith("путь одного запроса") for h in intro_h):
            ol.append('<a class="oli" href="#part-2"><b>Часть 2. Один запрос насквозь</b></a>')
        ol.append('<a class="oli" href="#part-3"><b>Часть 3. Файлы по порядку</b></a>')
        ol_tail.append('<details class="ol" data-ch="check"><summary><a href="#part-4">Часть 4. Итог</a></summary>'
                       + ('<a class="oli" href="#ex-retell">Перескажи MR</a>' if doc.get("retell") else "")
                       + '<a class="oli" href="#reviewer">Взгляд ревьюера</a>'
                       + ('<a class="oli" href="#before-after">Урок: было → стало</a>' if doc.get("before_after") else "") + "</details>")
    elif intro_h:
        ol.append('<details class="ol" data-ch="intro"><summary><a href="#top">Картина MR</a></summary>'
                  + "".join(f'<a class="oli" href="#intro-{k}">{inline(t, terms=False)}</a>'
                            for k, t in enumerate(intro_h, 1)) + "</details>")
    chapters = []
    for s in steps:
        g = group_of.get(s["id"])
        if not chapters or chapters[-1][0] != g:
            chapters.append((g, []))
        chapters[-1][1].append(s)
    for g, ss in chapters:
        items = []
        for s in ss:
            if is_decision(s):
                items.append(f'<a class="oli q" href="#{s["id"]}">? {inline(s["title"], terms=False)}</a>')
                continue
            items.append(f'<a class="oli" href="#{s["id"]}" data-step="{s["id"]}">{inline(s["title"], terms=False)}</a>')
            items += [f'<a class="oli sub" href="#chunk-{html.escape(c["cid"])}" data-chunk="{html.escape(c["cid"])}">{inline(c["name"], terms=False)}</a>'
                      for c in chunks_of(s) if c.get("cid")]
        if g is None:
            ol += items
            continue
        ids = " ".join(files_of.get(g, []))
        ol.append(f'<details class="ol" data-ch="{g}" data-steps="{ids}"><summary><a href="#ch-{g}">{html.escape(ch_name(g))}</a>'
                  f'<span class="cnt"></span></summary>{"".join(items)}</details>')
    tail = []                         # (якорь, подпись)
    if doc.get("lessons"):
        tail.append(("lessons", "★ Чему учиться"))
    if doc.get("quiz"):
        tail.append(("quiz", "? Самопроверка"))

    chips = []
    if mr.get("url"):
        chips.append(f'<span class="chip"><a href="{html.escape(mr["url"])}" target="_blank" rel="noopener">{inline(mr.get("ref", "MR"), terms=False)}</a></span>')
    if mr.get("spec"):
        chips.append(f'<span class="chip"><a href="{html.escape(mr["spec"])}" target="_blank" rel="noopener">спека</a></span>')
    for k in ("branch", "target", "task", "stats"):
        if mr.get(k):
            chips.append(f'<span class="chip">{inline(mr[k], terms=False)}</span>')

    parts = [f'<header id="top" data-label="Начало"><h1>{inline(doc["title"], terms=False)}</h1>',
             f'<p class="sub">{inline(doc.get("subtitle", ""), terms=False)}</p>',
             f'<div class="meta">{"".join(chips)}</div></header>']
    _seen.clear()
    LINK["prefix"], LINK["open_review"] = (other, True) if mode == "review" else ("", False)
    LINK["review"] = other if mode == "learn" else ""
    risk_groups(doc.get("verdict", {}).get("risks", []))
    title = re.sub(r'[`*]', '', doc['title'])
    if mode == "review":
        v = doc.get("verdict", {})
        parts.append(verdict_block(v, mr.get("spec")))
        parts.append(f'<footer>{inline(doc.get("footer", ""), terms=False)}</footer>')
        rs = v.get("risks", [])
        n_merge = sum(1 for r in rs if (r.get("when") or ("merge" if r.get("level") in ("blocker", "fix") else "know")) == "merge")
        n_spec = sum(1 for r in rs if r.get("when") == "spec")
        n_rest = len(rs) - n_merge - n_spec
        bad = sum(1 for r in v.get("requirements", []) if r.get("status") != "ok")
        jumps = (f'<a href="#merge">До мержа: {n_merge}</a>' + (f'<a href="#spec">Спека: {n_spec}</a>' if n_spec else "")
                 + (f'<a href="#risks">Остальное: {n_rest}</a>' if n_rest else "") + ('<a href="#checklist">Чек-лист</a>' if v.get("checks") else "")
                 + (f'<a href="#reqs">Требования{f": ⚠ {bad}" if bad else ""}</a>' if v.get("requirements") else "")
                 + (f'<a href="#probes">Кривые входы: {len(v["probes"])}</a>' if v.get("probes") else "")
                 + ('<a href="#verify">Проверь сам</a>' if v.get("verify") else ""))
        return page(f"Ревью · {title}", f'class="reviewpage" data-page="review" data-learn="{html.escape(learn_name)}"',
                    topbar(doc, mode, other, steps_json, jumps) + f'<main class="single">{"".join(parts)}</main>')
    if doc.get("verdict") and mode != "learn":
        parts.append(verdict_block(doc["verdict"], mr.get("spec")))
    # картина MR: в полном разборе — разделы подряд; на странице обучения — вопросы с ответом под катом
    secs, k = [], 0
    for b in doc.get("intro", []):
        if b.get("type") == "h":
            k += 1
            secs.append((k, b["text"], []))
        elif secs and learn and b.get("type") == "callgraph":
            secs[-1][2].append('<p class="cg-pointer">Граф вызовов — в левой колонке: клик по узлу ведёт к куску в тексте, «Назад» в браузере — обратно.</p>')
        elif secs:
            secs[-1][2].append(block({kk: vv for kk, vv in b.items() if kk != "lv"}))

    def sec_html(k_, t_, body):
        return (f'<div class="isec"><h3 id="intro-{k_}" data-label="{html.escape(t_)}" data-crumb="Картина MR › {html.escape(t_)}" '
                f'data-ch="intro">{inline(t_)}</h3>{"".join(body)}</div>')
    if learn:
        def find(keys):
            return [x for x in secs if any(x[1].lower().startswith(key) for key in keys)]
        ex = find(["пример"])
        svc = find(["как устроен сервис"])
        parts.append('<section class="part" id="part-1" data-label="Часть 1. Картина MR" data-ch="intro"><h2>Часть 1. Картина MR</h2>'
                     + picture_block(doc.get("picture") or {})
                     + ("<h3>На входе и на выходе</h3>" + "".join(ex[0][2]) if ex else "")
                     + ("".join(svc[0][2]) if svc else "") + "</section>")
        walk = find(["путь одного запроса", "ветки", "главный механизм"])
        if walk:
            parts.append('<section class="part" id="part-2" data-label="Часть 2. Один запрос насквозь" data-ch="intro"><h2>Часть 2. Один запрос насквозь</h2>'
                         '<p>Разобранный пример: один обычный запрос идёт по коду, на каждом шаге — что пришло, какой код сработал, что вышло. '
                         'Сначала по слоям, потом внутрь сердца MR.</p>' + "".join(sec_html(*x) for x in walk) + "</section>")
        parts.append('<section class="part" id="part-3" data-label="Часть 3. Файлы по порядку"><h2>Часть 3. Файлы по порядку</h2>'
                     '<p>Файлы идут по ходу запроса, как на карте. У файла — роль и методы, после него — 1–2 задания. '
                     'Сначала напиши ответ сам, потом нажми «Сверить». Кнопка «Код» в шапке открывает код всех файлов.</p></section>')
        qparts = ['<section class="part" id="part-4" data-label="Часть 4. Итог" data-ch="check"><h2>Часть 4. Итог</h2></section>']
        if doc.get("retell"):
            qparts.append(exercise_block({"id": "retell", "kind": "retell",
                                          "q": "Перескажи MR сеньору в трёх фразах: зачем он, как устроено главное, куда идёт запрос.",
                                          "a": "<ol>" + "".join(f"<li>{inline(x)}</li>" for x in doc["retell"]) + "</ol>"}, raw=True))
        rv = [(q, find(q[2])) for q in QUESTIONS if q[0] in ("Что может пойти не так?", "Не добавил ли ИИ лишнего?")]
        rv = [(q, b) for q, b in rv if b]
        if rv:
            qparts.append('<h3 id="reviewer" data-label="Взгляд ревьюера" data-ch="check">Взгляд ревьюера</h3>'
                          + "".join(f'<details class="more"><summary>{html.escape(q[0])}</summary>'
                                    f'<p class="qthink"><b>Подумай сам:</b> {inline(q[1], terms=False)}</p>'
                                    + "".join(sec_html(*x) for x in b) + "</details>" for q, b in rv))
        if doc.get("before_after"):
            _seen.clear()
            qparts.append(before_after_block(doc["before_after"]).replace('id="before-after"', 'id="before-after" data-label="Урок: было → стало"', 1))
    else:
        parts += [sec_html(*x) for x in secs]
    if rows and readable:
        parts.append(f'<a class="next" href="#ch-1">Начать: {html.escape(ch_name(1))} →</a>')

    def next_of(i):
        """Куда идти после файла: следующий файл главы, следующая глава или итоги."""
        s = readable[i]
        if i + 1 < len(readable):
            n = readable[i + 1]
            g0, g1 = group_of.get(s["id"]), group_of.get(n["id"])
            if g1 != g0 and g1 is not None:
                return f"#ch-{g1}", ch_name(g1)
            return f'#{n["id"]}', STEP_LABEL[n["id"]]
        if learn:
            return "#part-4", "Часть 4. Итог"
        for sid, label in tail:
            if sid != "glossary":
                return f"#{sid}", label.lstrip("★? ")
        if doc.get("glossary"):
            return "#glossary", "Словарь"
        return None

    for i, s in enumerate(steps, 1):
        _seen.clear()
        g = group_of.get(s["id"])
        crumb = html.escape(ch_name(g)) + " › " if g is not None else ""
        if g is not None and (i == 1 or group_of.get(steps[i - 2]["id"]) != g):
            card = group_card(g, rows[g - 1] if g else {}, group_title(g))
            parts.append(card.replace(f'<div class="chapter" id="ch-{g}">',
                                      f'<div class="chapter" id="ch-{g}" data-ch="{g}" data-label="{html.escape(ch_name(g))}">', 1))
            if not learn:
                parts.append(chapter_check(rows[g - 1] if g else {}, g))
        place_parts(s)
        if is_decision(s):
            parts.append(
                f'<section class="decision" id="{s["id"]}" data-ch="{g}" data-label="{html.escape(STEP_LABEL[s["id"]])}" '
                f'data-crumb="{crumb}{html.escape(STEP_LABEL[s["id"]])}">'
                f'<h3><span class="kindtag">вопрос главы</span>{inline(s["title"], terms=False)}</h3>'
                + "".join(block(b) for b in s.get("blocks", []))
                + "</section>")
            continue
        files = "".join(f"<code>{html.escape(f)}</code>" for f in s.get("files", []))
        tag = '<span class="kindtag">решение</span>' if s.get("part") == "design" and g is not None else ""
        mine = files_of.get(g, [])
        kick = (f'<span class="kick">{html.escape(ch_name(g))} · файл {mine.index(s["id"]) + 1} из {len(mine)}</span>' if g is not None
                else f'<span class="kick">{readable.index(s) + 1} из {len(readable)}</span>')
        nx = next_of(readable.index(s))
        nxt = (f'<a class="next" href="{nx[0]}" data-done="{s["id"]}">Разобрал, дальше: {html.escape(nx[1])} →</a>' if nx else "")
        parts.append(
            f'<section class="step" id="{s["id"]}" data-ch="{g if g is not None else ""}" data-label="{html.escape(STEP_LABEL[s["id"]])}" '
            f'data-crumb="{crumb}{html.escape(STEP_LABEL[s["id"]])}">'
            f'<label class="done"><input type="checkbox" data-id="{s["id"]}"> разобрал</label>'
            f'<h2>{kick}{tag}{inline(s["title"], terms=False)}</h2>'
            + (f'<div class="stepfiles">{files}</div>' if files else "")
            + "".join(block(b) for b in s.get("blocks", []))
            + ("".join(exercise_block(q) for q in ex_at.get(s["id"], []))
               + ("".join(exercise_block(q) for q in ex_end.get(g, [])) if last_of.get(g) == s["id"] else "") if learn else "")
            + nxt + "</section>")

    def qa(q):
        return (f'<details class="q"><summary>{inline(q["q"], terms=False)}</summary>'
                + "".join(block(b) if isinstance(b, dict) else f"<p>{inline(b)}</p>" for b in (q["a"] if isinstance(q["a"], list) else [q["a"]]))
                + "</details>")
    if learn:
        parts += qparts
    if doc.get("before_after") and not learn:
        _seen.clear()
        parts.append(before_after_block(doc["before_after"]).replace('id="before-after"', f'id="before-after" data-label="Урок: было → стало"', 1))
    if doc.get("lessons"):
        _seen.clear()
        parts.append(lessons_block(doc["lessons"]).replace('id="lessons"', f'id="lessons" data-label="Чему учиться"', 1))

    if doc.get("quiz"):
        _seen.clear()
        qs = "".join(qa(q) for q in doc["quiz"])
        parts.append(f'<section class="step" id="quiz" data-label="Самопроверка"><h2><span class="n">?</span>Самопроверка</h2>'
                     f"<p>Сначала ответь, потом раскрой ответ.</p>{qs}</section>")

    if USED:
        def dt(k):
            return f"<dt>{html.escape(k)}</dt>" if re.search(r"[а-яё ]", k, re.I) else f"<dt><code>{html.escape(k)}</code></dt>"
        items = "".join(dt(k) + f"<dd>{inline(v, terms=False)}</dd>" for k, v in sorted(USED.items(), key=lambda kv: kv[0].lower()))
        parts.append('<section class="step" id="glossary" data-label="Словарь"><h2><span class="n">Aa</span>Словарь</h2>'
                     '<p>Термины, которые встретились в разборе. В тексте у первого упоминания в шаге — подсказка при наведении.</p>'
                     f'<dl class="gloss">{items}</dl></section>')
        tail.append(("glossary", "Aa Словарь"))
    ol += ol_tail + [f'<a class="oli" href="#{sid}">{html.escape(label)}</a>' for sid, label in tail]
    parts.append(f'<footer>{inline(doc.get("footer", ""), terms=False)}</footer>')
    parts = [x.replace('href="REVIEW#', f'href="{html.escape(other) if learn else ""}#') for x in parts]
    graph = any(b.get("type") == "callgraph" for b in doc.get("intro", []))
    cls = 'class="hasgraph" ' if graph else ""
    return page(title, f'{cls}data-page="{"learn" if mode == "learn" else "full"}" data-learn="{html.escape(learn_name)}"',
                topbar(doc, mode, other, steps_json)
                + f'<div class="layout"><nav aria-label="Граф и главы">{navbox(doc, "".join(ol))}</nav><main>{"".join(parts)}</main></div>')


# Лимиты внимания читателя. Превышение — строка «проверка:», страница всё равно рисуется.
BUDGET = {
    "page": 2600,        # слов на виду в маршруте чтения: около 15 минут при 180 словах в минуту
    "plan": 8,           # глав: больше не удержать в голове как одну картину
    "how": 70,           # слов в how главы: путь выполнения, а не пересказ строк
    "requirements": 8,   # требований: похожие условия группируются
    "step": 220,         # слов на виду в одном шаге вне кода
    "file": 900,         # слов в комментариях к одному файлу
    "coverage": 0.9,     # доля изменённых строк, которые должны попасть в куски
    "steps": 6,          # шагов пути запроса: соседние шаги одного слоя склеиваются
    "callouts": 2,       # врезок в шаге
    "lessons": 3,        # приёмов в «Чему учиться»
    "quiz": 3,           # вопросов самопроверки
}


def _words(o, skip=("code", "cmd", "lines", "path", "kind", "type", "lang", "step", "id", "level", "status", "url")):
    if isinstance(o, str):
        return len(re.findall(r"\w+", o))
    if isinstance(o, dict):
        return sum(_words(v) for k, v in o.items() if k not in skip)
    if isinstance(o, list):
        return sum(_words(x) for x in o)
    return 0


def _visible(blocks):
    """Слова, которые читатель видит без кликов: без кода, блоков more и свёрнутой части карточки think."""
    n = 0
    for b in blocks:
        if b["type"] == "more":
            continue
        if b["type"] == "think":
            n += _words(b.get("question", "")) + _words(b.get("decided", "")) + _words(b.get("rejected", []))
        elif b["type"] == "anatomy":
            # блоки файла стоят в коде, как комментарии — в лимит страницы не входят
            if any(c.get("status") in ("note", "warn", "fail") for c in b.get("checks", [])):
                n += _words([c.get("text", "") for c in b.get("checks", [])])
        elif b["type"] == "plan":
            n += _words([b.get("task", ""), b.get("kind", ""), b.get("try", "")])
            n += sum(_words([r.get("need", ""), r.get("where", ""), r.get("why", ""), r.get("how", [])]) for r in b["rows"])
        elif b["type"] == "diff":
            n += _words([x["text"] for x in b.get("notes", [])])
        elif b["type"] == "annotated":
            n += _words([note for _, note in b["lines"]])
        else:
            n += _words(b)
    return n


def _remarks(blocks):
    """Замечания risk/warn в блоках шага, включая свёрнутые: callout'ы и комментарии к строкам диффа."""
    for b in blocks:
        if b["type"] == "callout" and b.get("kind") in ("risk", "warn"):
            yield b.get("title") or b["text"]
        elif b["type"] == "diff":
            for n in b.get("notes", []):
                if n.get("kind") in ("risk", "warn"):
                    yield f'строка {n["line"]}: {n["text"]}'
        elif b["type"] == "anatomy":
            for c in b.get("checks", []):
                if c.get("status") in ("warn", "fail"):
                    yield f'как читать файл: {c["text"]}'
        elif b["type"] == "more":
            yield from _remarks(b["blocks"])


def check_verdict_coverage(doc):
    """Каждое замечание risk/warn на странице должно стоять в verdict.risks со ссылкой на свой шаг."""
    linked = {}
    for r in doc.get("verdict", {}).get("risks", []):
        linked[r.get("step")] = linked.get(r.get("step"), 0) + 1
    warns = []
    for i, s in enumerate(doc["steps"], 1):
        found = list(_remarks(s.get("blocks", [])))
        if len(found) > linked.get(s["id"], 0):
            warns.append(f"шаг {i}: замечаний risk/warn {len(found)}, в verdict.risks со step «{s['id']}» — "
                         f"{linked.get(s['id'], 0)}. Внеси в вердикт или убери из текста: " + "; ".join(x[:50] for x in found))
    return warns


def check_plan(doc):
    """План доработки: есть в intro, каждый файл стоит в плане, ссылки ведут на шаги."""
    plans = [b for b in doc.get("intro", []) if b.get("type") == "plan"]
    if not plans:
        return ["в intro нет plan «План доработки» — читатель не увидит, как из задачи получился список файлов"]
    warns = []
    ids = {s["id"] for s in doc["steps"]}
    rows = [r for p in plans for r in p["rows"]]
    if len(rows) > BUDGET["plan"]:
        warns.append(f"строк плана {len(rows)}, лимит {BUDGET['plan']}: объедини пункты одного слоя")
    planned = set()
    for r in rows:
        for sid in r.get("files", []):
            if sid not in ids:
                warns.append(f"план «{r['need'][:40]}»: нет шага {sid}")
            planned.add(sid)
        if not r.get("why"):
            warns.append(f"план «{r['need'][:40]}»: нет why — почему изменение здесь, а не в другом месте")
        if "/" not in r.get("where", "") and not doc.get("_v3"):
            warns.append(f"план «{r['need'][:40]}»: в where нет пакета — назови папку файлов и соседа-образец")
        if not r.get("how") and not doc.get("_v3"):
            warns.append(f"план «{r['need'][:40]}»: нет how — как код пункта работает при запуске, по шагам")
        elif _words(r["how"]) > BUDGET["how"]:
            warns.append(f"план «{r['need'][:40]}»: how {_words(r['how'])} слов, лимит {BUDGET['how']} — оставь путь выполнения, детали в комментарии к строкам")
    for r in rows:
        for sid in r.get("decisions", []):
            if sid not in ids:
                warns.append(f"план «{r['need'][:40]}»: нет решения {sid}")
            planned.add(sid)
    loose = [s["title"] for s in doc["steps"] if s.get("part") == "design" and s["id"] not in planned]
    if loose:
        warns.append("решения вне глав: " + "; ".join(loose) + " — впиши id в plan.rows[].decisions той главы, где решение применено")
    code_ext = (".kt", ".java", ".py", ".ts", ".js", ".go", ".scala", ".groovy")
    for s in ([] if doc.get("_v3") else doc["steps"]):
        files = [b.get("file", "") for b in s.get("blocks", []) if b["type"] == "diff"]
        if (s.get("part") == "changes" and any(f.endswith(code_ext) and "/resources/" not in f for f in files)
                and not any(b["type"] == "anatomy" for b in s.get("blocks", []))):
            warns.append(f"файл «{s['title']}»: нет anatomy «Как читать файл» — части по строкам и проверка по роли")
    missed = [s["title"] for s in doc["steps"] if s.get("part") == "changes" and s["id"] not in planned]
    if missed:
        warns.append("файлы вне плана: " + ", ".join(missed) + " — у каждого файла должна быть причина из задачи")
    for i, s in enumerate(doc["steps"], 1):
        if s.get("part") == "design":
            for b in s.get("blocks", []):
                if b["type"] == "think" and "rejected" not in b:
                    warns.append(f"шаг {i}: в think нет rejected — какие варианты автор отбросил и почему; не было — []")
    return warns


_TRIVIAL = re.compile(r"^\s*(import |package |[})\]]+[,;]?\s*$|$)")


def note_coverage(step):
    """Доля значимых строк файла кода внутри блоков anatomy или комментариев: импорты, скобки и пустые не считаются.
    Возвращает (доля, покрыто, всего, непокрытые номера) или None, если файл не код."""
    code_ext = (".kt", ".java", ".py", ".ts", ".js", ".go", ".scala", ".groovy")
    for b in step.get("blocks", []):
        if b["type"] != "diff" or not b.get("file", "").endswith(code_ext) or "/resources/" in b.get("file", ""):
            continue
        sig = [r[2] for r in parse_diff(b["diff"]) if r[0] == "add" and r[2] is not None and not _TRIVIAL.match(r[3])]
        if not sig:
            return None
        cov = set()
        an = next((x for x in step.get("blocks", []) if x["type"] == "anatomy"), {})
        for n in b.get("notes", []) + [{"line": x.get("lines", "")} for x in an.get("parts", [])]:
            lo, hi = note_range(n["line"])
            cov |= set(range(lo, hi + 1)) if hi is not None else ({lo} if isinstance(lo, int) else set())
        miss = [x for x in sig if x not in cov]
        return (1 - len(miss) / len(sig), len(sig) - len(miss), len(sig), miss)
    return None


def header_parts(doc):
    """Файлы, где часть anatomy объясняет только шапку: package, import, пустые строки. Шапку объясняют один раз
    на страницу — в 26 файлах подряд «package — адрес, import — инструменты» это шум, а не обучение."""
    out = []
    for s in doc["steps"]:
        if s.get("part") != "changes":
            continue
        an = next((b for b in s.get("blocks", []) if b["type"] == "anatomy"), {})
        df = next((b for b in s.get("blocks", []) if b["type"] == "diff"), None)
        if not df:
            continue
        text = {r[2]: r[3] for r in parse_diff(df["diff"]) if r[2] is not None}
        for x in an.get("parts", []):
            lo, hi = note_range(x.get("lines", ""))
            if not isinstance(lo, int):
                continue
            known = [text[n] for n in range(lo, (hi or lo) + 1) if n in text]
            if known and all(_TRIVIAL.match(t) for t in known):
                out.append(s["title"])
    return out


_SHORT_ID = re.compile(r"(?<![\w-])([A-ZА-Я]{1,3}-\d{1,3})(?![\w-])")


def verdict_ids(doc):
    """Короткие ID из спеки и команды (D-44, BR-3) в вердикте без словарной статьи: джун не знает, что это."""
    v = doc.get("verdict", {})
    texts = [v.get("summary", "")]
    texts += [c.get(k, "") for c in v.get("checks", []) for k in ("text", "do")]
    texts += [r.get(k, "") for r in v.get("requirements", []) for k in ("req", "do")]
    texts += [r.get(k, "") for r in v.get("risks", []) for k in ("text", "why", "do")]
    found = dict.fromkeys(m for t in texts for m in _SHORT_ID.findall(t))
    return [x for x in found if x not in GLOSSARY]


_HISTORY = re.compile(r"по ревью|убран[аоы]? по|[Бб]ыло «|нашёл баг|нашел баг|первая версия|\b(?=[0-9a-f]*[a-f])[0-9a-f]{8}\b|состояние на \d", re.I)


def check_history(doc):
    """Рассказы о ходе работы и хэши коммитов в тексте: читатель видит код MR, а не его историю."""
    hits = []

    def walk(o, path):
        if isinstance(o, str):
            m = _HISTORY.search(o)
            if m:
                hits.append(f"{path}: «{m.group()}»")
        elif isinstance(o, dict):
            for k, v in o.items():
                if k not in ("diff", "code", "cmd", "file", "url", "mr", "trace", "did", "saw"):
                    walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
    walk({k: v for k, v in doc.items() if k not in ("glossary",)}, "")
    return [f"рассказ о ходе работы или хэш в тексте — {h}" for h in hits[:8]]


def check_budget(doc):
    """Бюджет текста: разбор, который не читают до конца, не учит. Возвращает список предупреждений."""
    doc = {**doc, "steps": [s for s, _ in ordered_steps(doc)]}   # номера шагов — как на странице
    warns = []
    steps = [s for s in doc["steps"] if s["id"] != "files" and s.get("part") != "changes"]
    if not doc.get("verdict"):
        warns.append("нет блока verdict — читатель не узнает, правильно ли сделан MR")
    if len(steps) > BUDGET["steps"]:
        warns.append(f"шагов {len(steps)}, лимит {BUDGET['steps']}: объедини шаги про тесты, CI и «после мержа»")
    total = _words(doc.get("verdict", {}).get("summary", "")) + _visible(doc.get("intro", [])) + _words(doc.get("lessons", []))
    total += sum(_words([r.get("text", ""), r.get("do", "")]) for r in doc.get("verdict", {}).get("risks", []) if r.get("when") == "spec")
    total += sum(_words(q["q"]) for q in doc.get("quiz", []))
    for i, s in enumerate(doc["steps"], 1):
        v = _visible(s.get("blocks", []))
        total += v if s.get("part") != "changes" else _visible([b for b in s.get("blocks", []) if b["type"] != "diff"])
        if s["id"] != "files" and s.get("part") != "changes" and v > BUDGET["step"]:
            warns.append(f"шаг {i} «{s['title']}»: {v} слов на виду, лимит {BUDGET['step']} — лишнее в more")
        callouts = [b for b in s.get("blocks", []) if b["type"] == "callout"]
        if len(callouts) > BUDGET["callouts"]:
            warns.append(f"шаг {i}: {len(callouts)} callout'а, лимит {BUDGET['callouts']}")
        notes = sum(len(b.get("notes", [])) for b in s.get("blocks", []) if b["type"] == "diff")
        if s.get("part") == "changes":
            v = _visible([b for b in s.get("blocks", []) if b["type"] != "anatomy"])
        if s.get("part") == "changes" and v > BUDGET["file"]:
            warns.append(f"файл {i} «{s['title']}»: {v} слов в комментариях, лимит {BUDGET['file']} — объединяй строки в диапазоны")
        if s.get("part") == "changes" and not doc.get("_v3"):
            cov = note_coverage(s)
            if cov and cov[0] < BUDGET["coverage"]:
                warns.append(f"файл {i} «{s['title']}»: блоки anatomy покрывают {cov[1]} из {cov[2]} значимых строк — "
                             f"добавь блок с объяснением (без блока: {', '.join(map(str, cov[3][:12]))})")
        if any(b.get("kind") == "lesson" for b in callouts):
            warns.append(f"шаг {i}: callout lesson — приёмы переносятся в lessons")
    warns += [] if doc.get("_v3") else check_verdict_coverage(doc)
    intro_flat = [x for b in doc.get("intro", []) for x in ([b] + (b.get("blocks", []) if b.get("type") == "more" else []))]
    if not any(b.get("type") == "flow" for b in intro_flat):
        warns.append("в intro нет flow «Как устроен сервис» — новичок не увидит картину до решений")
    if not any(b.get("type") == "callgraph" for b in doc.get("intro", [])):
        warns.append("в intro нет callgraph «Слои и цепочка вызовов» — читатель не увидит, зачем тронут каждый файл")
    warns += check_plan(doc)
    warns += [] if doc.get("_v3") else check_history(doc)
    v = doc.get("verdict", {})
    checks, risks = v.get("checks", []), v.get("risks", [])
    expect = ("rework" if any(c.get("status") == "fail" for c in checks) or any(r.get("level") == "blocker" for r in risks)
              else "fix" if any(r.get("level") == "fix" for r in risks) else "ok")
    if v and v.get("status") != expect and not doc.get("_v3"):
        warns.append(f"verdict.status «{v.get('status')}», а по чек-листу и рискам выходит «{expect}»: "
                     "rework — fail или blocker, fix — риск fix, иначе ok")
    hp = header_parts(doc)
    if len(hp) > 1:
        warns.append(f"шапка файла (package/import) объяснена в {len(hp)} файлах: {', '.join(hp[:4])}… — "
                     "оставь только в первом файле, в остальных начинай с первой значимой строки")
    ids = verdict_ids(doc)
    if ids:
        warns.append(f"в вердикте ID без словаря: {', '.join(ids)} — добавь в glossary, что это и где лежит")
    for r in risks:
        if r.get("level") in ("blocker", "fix") and not r.get("why") and not doc.get("_v3"):
            warns.append(f"риск «{r['text'][:40]}»: {r['level']} без why — чем грозит на конкретном значении")
        if (not r.get("do") or r.get("when") not in WHEN) and not doc.get("_v3"):
            warns.append(f"риск «{r['text'][:40]}»: нужны do (что сделать) и when (merge · deploy · spec · know)")
    for c in checks:
        if c.get("status") in ("warn", "fail") and not c.get("do"):
            warns.append(f"чек-лист «{c['area']}»: {c['status']} без do — читатель не знает, что сделать")
    reqs = v.get("requirements", [])
    if len(reqs) > BUDGET["requirements"]:
        warns.append(f"требований {len(reqs)}, лимит {BUDGET['requirements']}: сгруппируй похожие условия")
    for r in reqs:
        if "status" not in r:
            warns.append(f"требование «{r['req'][:40]}»: нет status (ok · partial · gap)")
        elif r["status"] in ("partial", "gap") and not r.get("do"):
            warns.append(f"требование «{r['req'][:40]}»: {r['status']} без do — читатель не знает, проблема ли это")
    if len(doc.get("lessons", [])) > BUDGET["lessons"]:
        warns.append(f"приёмов {len(doc['lessons'])}, лимит {BUDGET['lessons']}")
    if len(doc.get("quiz", [])) > BUDGET["quiz"]:
        warns.append(f"вопросов самопроверки {len(doc['quiz'])}, лимит {BUDGET['quiz']}")
    if total > BUDGET["page"]:
        warns.append(f"на виду {total} слов, лимит {BUDGET['page']}")
    return total, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--force", action="store_true", help="рендерить v3 даже с ошибками валидации")
    ap.add_argument("--no-base-glossary", action="store_true", help="не подмешивать references/glossary-base.json")
    a = ap.parse_args()
    doc = json.loads(a.json.read_text(encoding="utf-8"))
    if "chunks" not in doc:
        print("ошибка: в JSON нет chunks — это не разбор по references/schema.md", file=sys.stderr)
        return 1
    from validate import validate
    from project import project
    errors, notes = validate(doc)
    for e in errors:
        print("  ошибка: " + e, file=sys.stderr)
    for n in notes:
        print("  проверка: " + n, file=sys.stderr)
    if errors and not a.force:
        print(f"{len(errors)} ошибок — исправь JSON (или --force, чтобы всё равно отрендерить)", file=sys.stderr)
        return 1
    doc = project(doc)
    base = {}
    base_path = Path(__file__).resolve().parent.parent / "references" / "glossary-base.json"
    if not a.no_base_glossary and base_path.exists():
        base = json.loads(base_path.read_text(encoding="utf-8"))
    out = a.out or a.json.with_suffix(".html")
    if doc.get("_v3"):
        # две страницы из одних фактов: ревью — коротко для решения, обучение — граф, путь запроса, главы
        learn = out.with_name(out.stem + "-learn.html")
        learn.write_text(render(doc, base, mode="learn", other=out.name, learn_name=learn.name), encoding="utf-8")
        out.write_text(render(doc, base, mode="review", other=learn.name, learn_name=learn.name), encoding="utf-8")
        print(out)
        print(learn)
    else:
        out.write_text(render(doc, base), encoding="utf-8")
        print(out)
    total, warns = check_budget(doc)
    print(f"Текст на виду: {total} слов (~{max(1, round(total / 180))} мин чтения)", file=sys.stderr)
    for w in warns:
        print("  проверка: " + w, file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
