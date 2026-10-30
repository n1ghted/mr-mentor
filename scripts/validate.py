"""Механическая проверка разбора v3: то, что раньше держалось на правилах в тексте.

Ошибка — рендер отказывается рисовать: факт лежит не там, ссылка в пустоту, якорь не на месте.
Проверка — рисует, но предупреждает: пересказ замечания, кусок без «как работает», непокрытые строки.
"""
import re
import subprocess

TOP = {"picture", "meta", "summary", "context", "trace", "before_after", "service", "mechanism", "requirements", "entry", "chunks", "outcomes", "findings",
       "decisions", "tests", "probes", "plan", "files", "example", "verify", "lessons", "quiz", "glossary"}
# кусок с 8 и больше изменёнными строками уже логика, а не объявление: ему нужен how
HOW_FROM_LINES = 8
FIELDS = {
    "requirements": {"id", "text", "source", "by"},
    "chunks": {"id", "file", "lines", "symbol", "change", "anchor", "purpose", "how", "calls", "implements", "decision",
               "rule_lines", "graph_note", "role", "affects", "no_weak", "why", "same_as"},
    "outcomes": {"id", "kind", "label", "note"},
    "findings": {"id", "severity", "when", "area", "claim", "breaks", "do", "at", "req"},
    "decisions": {"id", "question", "decided", "rejected", "code", "evidence_private", "source"},
    "tests": {"id", "file", "scenario", "proves", "expect"},
    "probes": {"id", "at", "kind", "input", "code", "finding", "ok"},  # proves — требования или решения
}
ENUM = {("findings", "severity"): {"block", "fix", "ask", "know"},
        ("findings", "when"): {"merge", "deploy", "spec", "desc", "know"},
        ("findings", "area"): {"scope", "extra", "data", "deploy", "tests", "ci"},
        ("chunks", "change"): {"new", "modified", "moved"},
        ("requirements", "by"): {"code", "test", "config", "manual"},
        ("outcomes", "kind"): {"error", "result", "store"},
        ("probes", "kind"): {"old", "malformed", "empty", "foreign", "boundary"}}
REQUIRED = {"chunks": {"id", "file", "lines", "symbol", "purpose"}, "findings": {"id", "severity", "when", "area", "claim"},
            "decisions": {"id", "question", "decided", "rejected"}, "requirements": {"id", "text"},
            "tests": {"id", "scenario", "proves"}, "probes": {"id", "at", "kind", "input", "code"}}
# оценочные слова — признак замечания, спрятанного в описании
JUDGE = re.compile(r"\bриск|не покрыт|нет теста|без теста|расхожд|опасн|\bбаг|сломает|упадёт|ошибочн", re.I)
HISTORY = re.compile(r"(?i:по ревью|убран[аоы]? по|[Бб]ыло «|нашёл баг|нашел баг|первая версия|в прошлой версии|состояние на)"
                     r"|\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b")


def _sig_raw(text):
    """Сигнатура факта: имена в бэктиках и числа от трёх знаков."""
    return set(re.findall(r"`([^`]+)`", text)) | set(re.findall(r"\b\d{3,}\b", text))


def _file_lines(repo, ref, path):
    if not repo:
        return None
    r = subprocess.run(["git", "-C", repo, "show", f"{ref}:{path}"], capture_output=True, text=True)
    return r.stdout.split("\n") if r.returncode == 0 else None


def _changed(repo, rng, path):
    """Номера добавленных строк файла по диффу."""
    r = subprocess.run(["git", "-C", repo, "diff", "-U0", rng, "--", path], capture_output=True, text=True)
    out, new = [], 0
    for line in r.stdout.split("\n"):
        m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
        if m:
            new = int(m.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            out.append((new, line[1:]))
            new += 1
    return out


def validate(v3):
    err, warn = [], []
    meta = v3.get("meta", {})
    repo, rng = meta.get("repo"), meta.get("range")
    # без клона и диапазона скрипт не возьмёт диффы: страницы выйдут без кода, поэтому это ошибка, а не проверка
    if not repo or not rng:
        err.append("meta.repo и meta.range обязательны: путь к локальному клону и диапазон вида origin/<целевая ветка>...HEAD")
        return err, warn
    r = subprocess.run(["git", "-C", repo, "rev-parse", "--git-dir"], capture_output=True, text=True)
    if r.returncode:
        err.append(f"meta.repo: {repo} — не git-репозиторий ({r.stderr.strip()})")
        return err, warn
    for ref in [x for x in re.split(r"\.{2,3}", rng) if x]:
        if subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}"], capture_output=True).returncode:
            err.append(f"meta.range: «{ref}» нет в {repo} — сделай git fetch или поправь диапазон")
    if err:
        return err, warn
    head = rng.split("...")[-1] if "..." in rng else "HEAD"

    for k in v3:
        if k not in TOP:
            err.append(f"лишнее поле верхнего уровня «{k}»: в v3 его нет — факт должен лежать в одном из {sorted(TOP)}")
    for coll, allowed in FIELDS.items():
        for i, x in enumerate(v3.get(coll, [])):
            for k in x:
                if k not in allowed:
                    err.append(f"{coll}[{i}] «{x.get('id', '?')}»: лишнее поле «{k}»")
            for k in REQUIRED.get(coll, ()):
                if not x.get(k) and x.get(k) != []:
                    err.append(f"{coll}[{i}] «{x.get('id', '?')}»: нет поля «{k}»")
            for (c, f), vals in ENUM.items():
                if c == coll and f in x and x[f] not in vals:
                    err.append(f"{coll} «{x.get('id')}»: {f} = «{x[f]}», можно {sorted(vals)}")

    ids = {}
    for coll in ("requirements", "chunks", "outcomes", "findings", "decisions", "tests", "probes"):
        for x in v3.get(coll, []):
            if x.get("id") in ids:
                err.append(f"id «{x['id']}» повторяется ({ids[x['id']]} и {coll})")
            ids[x.get("id")] = coll

    def ref(where, rid, colls):
        if rid not in ids or ids[rid] not in colls:
            err.append(f"{where}: ссылка «{rid}» не ведёт на {'/'.join(colls)}")

    chunks = {c["id"]: c for c in v3.get("chunks", []) if "id" in c}
    for c in chunks.values():
        for x in c.get("calls", []):
            ref(f"кусок {c['id']}.calls", x.get("to"), ("chunks", "outcomes"))
        for r in c.get("implements", []):
            ref(f"кусок {c['id']}.implements", r, ("requirements",))
        if c.get("decision"):
            ref(f"кусок {c['id']}.decision", c["decision"], ("decisions",))
    kinds = {q.get("kind", "predict") for r in v3.get("plan", {}).get("rows", []) for q in r.get("check", [])}
    for k_, need in (("explain", "объясни своими словами"), ("where", "где менять, если…")):
        if v3.get("plan", {}).get("rows") and k_ not in kinds:
            warn.append(f"задания: нет ни одного {k_} («{need}») — в MR нужно хотя бы одно")
    pic = v3.get("picture")
    if pic is not None:
        extra = set(pic) - {"before", "after", "key"}
        if extra:
            err.append(f"picture: лишние поля {sorted(extra)} — есть только before, after, key")
        for k in ("before", "after"):
            if not pic.get(k):
                err.append(f"picture.{k}: пусто — без «было» и «стало» картина MR не складывается")
    # same_as: та же правка, что в куске-образце той же главы; образец сам не копия
    row_of = {cid: k for k, r in enumerate(v3.get("plan", {}).get("rows", [])) for cid in r.get("chunks", [])}
    for c in chunks.values():
        a = c.get("same_as")
        if not a:
            continue
        ref(f"кусок {c['id']}.same_as", a, ("chunks",))
        if a in chunks:
            if chunks[a].get("same_as"):
                err.append(f"кусок {c['id']}.same_as: образец {a} сам ссылается на другой кусок — укажи исходный образец")
            if row_of.get(a) != row_of.get(c["id"]):
                err.append(f"кусок {c['id']}.same_as: образец {a} в другой главе плана — копия стоит в главе образца")
            if chunks[a]["file"] == c["file"]:
                err.append(f"кусок {c['id']}.same_as: образец {a} в том же файле — копия бывает только в другом файле")
    for f in {c["file"] for c in chunks.values() if c.get("same_as")}:
        if not all(c.get("same_as") for c in chunks.values() if c["file"] == f):
            err.append(f"файл {f.split('/')[-1]}: same_as есть не у всех кусков — файл с копией целиком копия, иначе разбери его сам")
    for x in (v3.get("entry") or {}).get("calls", []):
        ref("entry.calls", x.get("to"), ("chunks", "outcomes"))
    # кривые входы и старые данные: агент обязан пройти развилки не только на хорошем примере
    probes = v3.get("probes", [])
    for pr in probes:
        ref(f"проба {pr.get('id')}.at", pr.get("at"), ("chunks",))
        if pr.get("finding"):
            ref(f"проба {pr.get('id')}.finding", pr["finding"], ("findings",))
        if bool(pr.get("finding")) == bool(pr.get("ok")):
            err.append(f"проба {pr.get('id')}: нужно ровно одно — finding (нашлось слабое место) или ok (почему код выдержит, со строкой)")
    for pr in probes:
        for fld in ("code", "ok"):
            t_ = str(pr.get(fld, ""))
            if re.search(r"(?i)строк[аи]?\s+\d", t_) and not re.search(r"\w+\.(kt|java|kts|py|ts|js|go|sql|feature)\b", t_):
                warn.append(f"проба {pr.get('id')}.{fld}: «строка N» без файла — пиши `Файл.ext:N`, например `OrderFacade.kt:42`, иначе читатель не найдёт")
    mr_ = meta.get("mr", {})
    if mr_.get("url") and mr_.get("state") != "merged" and not mr_.get("status"):
        warn.append("meta.mr.status: нет живого статуса MR — {draft, approvals, approvals_required, open_threads, pipeline, checked_at} из GitLab")
    if v3.get("entry") or v3.get("trace"):
        kinds = {pr.get("kind") for pr in probes}
        if len(probes) < 3:
            warn.append(f"probes: {len(probes)} — пройди код хотя бы на трёх кривых входах: старые данные, вход не того формата, пустое/чужое")
        if not kinds & {"malformed", "empty"}:
            warn.append("probes: нет пробы malformed/empty — что сделает код, если параметр запроса не того формата или пустой")
        if any(o.get("kind") == "store" for o in v3.get("outcomes", [])) and "old" not in kinds:
            warn.append("probes: код читает базу, а пробы old нет — что будет на записи, созданной до MR (старый формат, старые справочники)")
    for f in v3.get("findings", []):
        at = f.get("at")
        if at:
            ref(f"замечание {f['id']}.at", at.get("chunk"), ("chunks",))
        if f.get("req"):
            ref(f"замечание {f['id']}.req", f["req"], ("requirements",))
        if f.get("severity") in ("block", "fix", "ask") and not (f.get("breaks") or {}).get("effect") and f.get("area") != "ci":
            warn.append(f"замечание {f['id']}: {f['severity']} без breaks.effect — чем грозит: breaks.on — при каком условии, effect — что увидит клиент или сервис")
    for st_ in (v3.get("trace") or {}).get("steps", []):
        if st_.get("at") and st_["at"] not in ids:
            err.append(f"trace: шаг ссылается на «{st_['at']}», такого куска или исхода нет")
    for t in v3.get("tests", []):
        for r in t.get("proves", []):
            ref(f"тест {t['id']}.proves", r, ("requirements", "decisions"))
    plan_chunks, plan_dec = [], set()
    for r in v3.get("plan", {}).get("rows", []):
        for did in r.get("decisions", []):
            ref(f"план «{r.get('need', '')[:30]}»", did, ("decisions",))
            plan_dec.add(did)
        for cid in r.get("chunks", []):
            ref(f"план «{r.get('need', '')[:30]}»", cid, ("chunks",))
            plan_chunks.append(cid)
    for cid in chunks:
        if cid not in plan_chunks:
            err.append(f"кусок {cid} не стоит ни в одной строке плана")
    used_dec = {c.get("decision") for c in chunks.values()} | plan_dec
    for d in v3.get("decisions", []):
        if d["id"] not in used_dec:
            warn.append(f"решение {d['id']} не привязано ни к одному куску — его не будет видно в главе")

    # якоря и диапазоны по коду ветки
    by_file = {}
    for c in chunks.values():
        if not re.fullmatch(r"\s*\d+\s*(-\s*\d+)?\s*", str(c.get("lines", ""))):
            err.append(f"кусок {c['id']}: lines «{c.get('lines')}» — нужен диапазон вида «86-98»")
            continue
        lo_hi = [int(n) for n in re.findall(r"\d+", str(c.get("lines", "")))]
        if not lo_hi:
            err.append(f"кусок {c['id']}: lines «{c.get('lines')}» — нужен диапазон «86-98»")
            continue
        lo, hi = lo_hi[0], lo_hi[-1]
        by_file.setdefault(c["file"], []).append((lo, hi, c["id"]))
        text = _file_lines(repo, head, c["file"])
        if text is None:
            if repo:
                err.append(f"кусок {c['id']}: файла {c['file']} нет в {head}")
            continue
        if hi > len(text):
            err.append(f"кусок {c['id']}: строки {lo}–{hi}, а в файле {len(text)}")
        if c.get("anchor") and not any(c["anchor"] in ln for ln in text[lo - 1:hi]):
            err.append(f"кусок {c['id']}: якорь «{c['anchor'][:40]}» не найден в строках {lo}–{hi} — код сдвинулся?")
        for rl in c.get("rule_lines", []):
            if not lo <= rl["line"] <= hi:
                err.append(f"кусок {c['id']}: rule_line {rl['line']} вне {lo}–{hi}")
        if len(c.get("rule_lines", [])) > 1:
            warn.append(f"кусок {c['id']}: {len(c['rule_lines'])} комментария к строкам — объясняй кусок целиком, строка — исключение")
        declaration = re.search(r"/ports/|/model/|/dto/|Query\.(kt|java)$|Exception", c["file"]) or re.fullmatch(r"[A-Z][A-Z0-9_]+", c.get("symbol", "").split(".")[-1])
        changed_in = len([n for n, _ in _changed(repo, rng, c["file"]) if lo <= n <= hi]) if repo else hi - lo
        if not c.get("how") and (c.get("calls") or (changed_in >= HOW_FROM_LINES and not declaration)):
            warn.append(f"кусок {c['id']} ({c['symbol']}): нет how — как он работает по шагам")
        called = any(c["id"] == x.get("to") for o in chunks.values() for x in o.get("calls", []))
        if (c.get("how") or c.get("calls") or called) and not c.get("why"):
            warn.append(f"кусок {c['id']} ({c['symbol']}): нет why — зачем этот кусок в цепочке, одной фразой")
        elif c.get("why") and c.get("purpose") and len(_sig_raw(c["why"]) & _sig_raw(" ".join(c.get("how", [])))) >= 3:
            warn.append(f"кусок {c['id']}: why пересказывает how — напиши роль куска, а не шаги")
        has_weak = any((f.get("at") or {}).get("chunk") == c["id"] for f in v3.get("findings", []))
        if len(c.get("how", [])) >= 2 and not has_weak and not c.get("no_weak"):
            warn.append(f"кусок {c['id']} ({c['symbol']}): нет слабого места — замечание с at.chunk или no_weak «почему его нет»")
        if c.get("symbol") and not c["file"].endswith((".sql", ".json", ".yaml", ".yml", ".xml", ".feature")) and not any(
                part in ln for part in (c["symbol"].split(".")[-1].split("(")[0], c["symbol"].split(".")[0]) for ln in text[lo - 1:hi]):
            warn.append(f"кусок {c['id']}: «{c['symbol']}» не встречается в строках {lo}–{hi}")
    for f in v3.get("findings", []):
        at = f.get("at") or {}
        c = chunks.get(at.get("chunk"))
        if c and at.get("line"):
            lo_hi = [int(n) for n in re.findall(r"\d+", str(c["lines"]))]
            if lo_hi and not lo_hi[0] <= at["line"] <= lo_hi[-1]:
                err.append(f"замечание {f['id']}: строка {at['line']} вне куска {c['id']} ({c['lines']})")
    for path, spans in by_file.items():
        spans.sort()
        for (a1, b1, i1), (a2, b2, i2) in zip(spans, spans[1:]):
            if a2 <= b1:
                err.append(f"куски {i1} и {i2} пересекаются ({a1}–{b1} и {a2}–{b2})")
        if repo and "src/main/" in path:
            loose = [n for n, t in _changed(repo, rng, path)
                     if t.strip() and not re.match(r"\s*(import |package |[})\]]+[,;]?\s*$|//|\*|/\*|@\w+|"
                                                    r"((public|private|internal|open|abstract|data|sealed)\s+)*(class|object|interface|enum class)\s|"
                                                    r"(private |protected )?(val|var) \w+: [\w<>?, .=()\"]+,?\s*$|\)( ?: ?[\w<>, ()]+)? ?\{?\s*$)", t)
                     and not any(a <= n <= b for a, b, _ in spans)]
            if loose:
                warn.append(f"{path.split('/')[-1]}: {len(loose)} изменённых строк вне кусков ({', '.join(map(str, loose[:8]))}…)")

    if repo:
        r_ = subprocess.run(["git", "-C", repo, "diff", "--name-only", rng], capture_output=True, text=True)
        in_plan = {c["file"] for c in chunks.values()} | {f for r in v3.get("plan", {}).get("rows", []) for f in r.get("files", [])}
        outside = [f for f in r_.stdout.split() if f and f not in in_plan]
        if outside:
            warn.append(f"{len(outside)} изменённых файлов MR нет в плане: {', '.join(x.split('/')[-1] for x in outside[:6])}"
                        + ("…" if len(outside) > 6 else "") + " — добавь в plan.rows[].files (тесты и фикстуры — одной строкой)")
    # нумерация шагов в calls: 1..n без пропусков и повторов
    for c in list(chunks.values()) + ([{"id": "entry", **v3["entry"]}] if v3.get("entry") else []):
        nums = [int(m.group()) for x in c.get("calls", []) for m in [re.match(r"\d+", str(x.get("when", "")))] if m]
        if nums and sorted(nums) != list(range(1, len(nums) + 1)):
            warn.append(f"{c['id']}.calls: номера шагов {nums} — нужно 1..{len(nums)} по порядку вызова в коде")
    # трассировка: вызывающий раньше вызываемого
    order = [st_.get("at") for st_ in (v3.get("trace") or {}).get("steps", [])]
    for i, a in enumerate(order):
        for x in chunks.get(a, {}).get("calls", []):
            if x["to"] in order[:i]:
                warn.append(f"trace: «{x['to']}» стоит раньше «{a}», который его вызывает — шаги в порядке вызова")
    msteps = (v3.get("mechanism") or {}).get("steps", [])
    if msteps and not all(isinstance(x, dict) for x in msteps):
        warn.append("mechanism.steps: шаги строками — нужен пример по шагам на реальных файлах: {does, at: `Файл.ext:N`, например `OrderFacade.kt:42`, code, result, fails}")
    for i, x in enumerate(m for m in msteps if isinstance(m, dict)):
        for k in ("does", "at", "code", "result"):
            if not x.get(k):
                warn.append(f"mechanism.steps[{i}]: нет {k} — шаг = что делает код, где (`Файл.ext:N`, например `OrderFacade.kt:42`), строка кода, что вышло на примере")
        if x.get("at") and not re.search(r"\w+\.\w+:\d+", x["at"]):
            warn.append(f"mechanism.steps[{i}].at «{x['at']}» — нужен `Файл.ext:N`, например `OrderFacade.kt:42`")
    if msteps and not any(isinstance(m, dict) and m.get("fails") for m in msteps):
        warn.append("mechanism.steps: ни у одного шага нет fails — где механизм не сработает и что получит клиент")
    if len((v3.get("trace") or {}).get("steps", [])) > 6:
        warn.append(f"trace: {len(v3['trace']['steps'])} шагов — не больше 6: соседние шаги одного слоя склей, детали оставь главам")
    for i, st_ in enumerate((v3.get("trace") or {}).get("steps", [])):
        if st_.get("at") in chunks and not st_.get("code"):
            warn.append(f"trace шаг {i + 1} ({st_['at']}): нет code — 1–5 строк кода шага, читатель учится по коду")
    store_steps = [st_ for st_ in (v3.get("trace") or {}).get("steps", []) if (v3.get("outcomes") and any(o["id"] == st_.get("at") and o.get("kind") == "store" for o in v3["outcomes"]))]
    for st_ in store_steps:
        if not st_.get("returned"):
            warn.append(f"trace: шаг базы {st_['at']} без returned — что вернула база, на значениях")
    for k_, r in enumerate(v3.get("plan", {}).get("rows", []), 1):
        if r.get("chunks") and not r.get("learn"):
            warn.append(f"план, глава {k_}: нет learn — «что поймёшь» одной фразой")
        if r.get("chunks") and not r.get("check"):
            warn.append(f"план, глава {k_}: нет check — 1–2 задания к кускам главы")
        for q in r.get("check", []):
            if set(q) - {"q", "a", "kind", "chunk", "code"}:
                err.append(f"план, глава {k_}: в задании лишние поля {sorted(set(q) - {'q', 'a', 'kind', 'chunk', 'code'})}")
            if q.get("kind", "predict") not in ("predict", "explain", "break", "where"):
                err.append(f"план, глава {k_}: тип задания «{q.get('kind')}» — есть predict, explain, break, where")
            if q.get("chunk") and q["chunk"] not in r.get("chunks", []):
                err.append(f"план, глава {k_}: задание ссылается на кусок «{q['chunk']}» не из этой главы")
            if q.get("kind") == "explain" and not q.get("code"):
                err.append(f"план, глава {k_}: задание explain без code — объяснять нечего")
    for br in (v3.get("trace") or {}).get("branches", []):
        if not br.get("result"):
            warn.append(f"trace.branches «{br.get('when', '')[:30]}»: нет result — чем кончается ветка («404», «флага нет»)")
    # внутренние id в читаемом тексте
    own = {i for i in ids if i}
    for where, text in [("verify", " ".join(v3.get("verify", []))), ("lessons", " ".join(l.get("text", "") for l in v3.get("lessons", [])))]:
        leak = sorted({t for t in re.findall(r"\b[A-Z][\w-]*\b", text) if t in own})
        if leak:
            warn.append(f"{where}: внутренние id {', '.join(leak)} в тексте — читатель их не видит, пиши словами")
    # кусок с несколькими функциями, названный одной
    for c in chunks.values():
        text = _file_lines(repo, head, c["file"]) if repo else None
        lo_hi = [int(n) for n in re.findall(r"\d+", str(c.get("lines", "")))]
        if text and lo_hi:
            funs = re.findall(r"\b(?:fun|void|public|private|protected)\s+(?:[\w<>?,\s]+\s)?(\w+)\s*\(", "\n".join(text[lo_hi[0] - 1:lo_hi[-1]]))
            funs = [f for f in dict.fromkeys(funs) if f not in ("if", "for", "while", "when", "catch")]
            if len(funs) > 1 and not all(f in c.get("symbol", "") + " " + c.get("purpose", "") for f in funs):
                warn.append(f"кусок {c['id']}: в строках {len(funs)} функции ({', '.join(funs[:4])}), а назван «{c['symbol']}» — раздели или назови все")
    # пересказ и спрятанные замечания
    desc = [(f"кусок {c['id']}", " ".join([c.get("purpose", "")] + c.get("how", []))) for c in chunks.values()]
    desc += [(f"решение {d['id']}", d.get("decided", "")) for d in v3.get("decisions", [])]
    desc += [(f"урок «{l.get('title', '')[:20]}»", l.get("text", "")) for l in v3.get("lessons", [])]
    desc += [(f"verify[{i}]", x) for i, x in enumerate(v3.get("verify", []))]
    desc += [("summary", v3.get("summary", ""))]
    for where, text in desc:
        if where.startswith(("урок", "verify", "summary")):
            continue
        if JUDGE.search(text):
            warn.append(f"{where}: оценочное слово «{JUDGE.search(text).group()}» — это замечание, вынеси в findings")
    fs = v3.get("findings", [])
    # исходы ручки («422 …») — общий словарь, по ним пересказ не считаем
    common_words = set()
    for o in v3.get("outcomes", []):
        common_words |= _sig_raw(o.get("label", "")) | set(re.findall(r"\b\d{3}\b", o.get("label", "")))

    def sig(text):
        raw = _sig_raw(text)
        return raw - common_words - {x for x in raw if re.fullmatch(r"\d{3}( .*)?", x)}
    for f in fs:
        s = sig(f["claim"])
        for where, text in desc:
            if where != "summary" and len(s & sig(text)) >= 2:
                warn.append(f"замечание {f['id']} пересказано в «{where}» (общее: {', '.join(sorted(s & sig(text))[:3])})")
    for i, a in enumerate(fs):
        for b in fs[i + 1:]:
            common = sig(a["claim"]) & sig(b["claim"])
            if len(common) >= 2:
                warn.append(f"замечания {a['id']} и {b['id']} похожи (общее: {', '.join(sorted(common)[:3])}) — одно ли это замечание?")

    def walk(o, path):
        if isinstance(o, str):
            m = HISTORY.search(o)
            if m:
                warn.append(f"{path}: история или хэш в тексте — «{m.group()}»")
        elif isinstance(o, dict):
            for k, v in o.items():
                if k not in ("evidence_private", "code", "anchor", "file", "lines", "meta", "example", "id", "to", "before_after", "query", "returned"):
                    walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
    walk({k: v for k, v in v3.items() if k not in ("meta", "glossary")}, "")
    # аббревиатуры предметной области на маршруте и в решениях — с расшифровкой при первом упоминании
    COMMON = {"MR", "API", "ID", "JSON", "HTTP", "DTO", "SQL", "CI", "PR", "URL", "UUID", "GET", "POST", "PUT", "DELETE",
              "REST", "OTP", "UI", "DB", "TTL", "JVM", "ИНН", "БИК", "ФИО", "PII", "OK", "NULL", "AND", "OR"}
    seen_text = " ".join([v3.get("summary", ""), (v3.get("context") or {}).get("text", "")]
                         + [" ".join(str(x.get(k, "")) for k in ("in", "does", "out")) for x in (v3.get("trace") or {}).get("steps", [])]
                         + [d.get("question", "") + " " + d.get("decided", "") for d in v3.get("decisions", [])])
    plain = re.sub(r"`[^`]*`", " ", seen_text)
    abbr = sorted({a for a in re.findall(r"(?<![\w-])[A-ZА-ЯЁ][A-ZА-ЯЁ0-9_]{1,11}(?![\w-])", plain)
                   if a not in COMMON and not re.fullmatch(r"[A-Z]\d+|RC|D\d*", a)})
    known_l = {k.lower() for k in set((v3.get("glossary") or {})) | set(((v3.get("context") or {}).get("terms") or {}))}
    miss = [a for a in abbr if not any(a.lower() in k for k in known_l)]
    if miss:
        warn.append(f"аббревиатуры без расшифровки: {', '.join(miss[:8])} — добавь в context.terms или glossary")
    for l in v3.get("lessons", []):
        if l.get("step") and l["step"] not in ids and not str(l["step"]).startswith(("f-", "g-")):
            err.append(f"урок «{l.get('title', '')[:30]}»: step «{l['step']}» — нужен id куска, замечания или решения")
    # ярлыки вида D-44 / TASK-123 на маршруте «10 минут» — с расшифровкой
    known = set((v3.get("glossary") or {})) | set(((v3.get("context") or {}).get("terms") or {}))
    first = " ".join([v3.get("summary", ""), (v3.get("context") or {}).get("text", "")]
                     + [" ".join(str(x.get(k, "")) for k in ("in", "does", "out")) for x in (v3.get("trace") or {}).get("steps", [])])
    for lab in sorted(set(re.findall(r"\b[A-Z]{1,4}-\d+\b", first))):
        if lab not in known and not lab.startswith(("RC-", "D", "R", "F", "C", "T", "O")) or (lab.startswith("D-") and lab not in known):
            warn.append(f"ярлык «{lab}» в вердикте, контексте или пути запроса без расшифровки — добавь в context.terms")
    from project import sanitize
    def pii(o, path):
        if isinstance(o, str):
            if sanitize(o) != o:
                err.append(f"{path}: похоже на клиентские данные — замени заглушкой (<ФИО>, <счёт>, <ИНН>)")
        elif isinstance(o, dict):
            for k, v in o.items():
                if k not in ("lines", "anchor", "file", "id", "to", "meta"):
                    pii(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                pii(v, f"{path}[{i}]")
    pii({k: v for k, v in v3.items() if k not in ("meta",)}, "")
    return err, warn
