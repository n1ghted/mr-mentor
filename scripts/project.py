"""Проекция разбора v3 в документ, который рисует render.py.

В v3 автор пишет каждый факт один раз: требования, куски кода, замечания, решения, тесты. Всё, что читатель
видит в нескольких местах — вердикт, чек-лист, таблица требований, риски, расхождения со спекой, плашки в коде,
граф вызовов, главы, таблица тестов, правки старого кода, — строится здесь из этих фактов. Поэтому один факт
не может разойтись сам с собой: источник у него один.
"""
import re
import subprocess

SEVERITY = ("block", "fix", "ask", "know")          # единственная шкала серьёзности
LEVEL = {"block": "blocker", "fix": "fix", "ask": "note", "know": "note"}
CHECK_OF = {"block": "fail", "fix": "warn", "ask": "warn", "know": "note"}
PLATE_OF = {"block": "risk", "fix": "risk", "ask": "warn", "know": "note"}
AREAS = [("scope", "Сделано то, что просит задача"), ("extra", "Нет лишнего"), ("data", "Данные: null, границы"),
         ("deploy", "Деплой: миграции, тоглы"), ("tests", "Тесты доказывают требования"), ("ci", "CI и ревью")]

# роль слоя по пакету файла: первая подходящая строка
ROLES = [
    (r"/test/.*\.feature$|/features/", "сценарий на поднятом сервисе"),
    (r"/test/.*(fixture|resources)/", "тестовые данные"),
    (r"/test/.*/cucumber/(step|steps)/", "шаги сценариев"),
    (r"/test/.*/cucumber/", "настройка сценариев"),
    (r"/test/", "юнит-тест"),
    (r"ExceptionHandler", "официант — обработчик ошибок"),
    (r"/application/web/model/|Dto\.kt$|Response\.kt$|Request\.kt$", "тарелка подачи — DTO"),
    (r"/application/", "официант — контроллер"),
    (r"/ports/in/", "меню — порт"),
    (r"/ports/out/", "склад — порт"),
    (r"/core/model/.*Exception", "записка повара — исключение"),
    (r"/core/model/", "продукты — модель"),
    (r"/core/services/.*Facade\.kt$", "повар — фасад"),
    (r"/core/services/", "помощник повара — вычисления"),
    (r"/infrastructure/.*(Repository|Persistence|Dao|Adapter)", "склад — база"),
    (r"Configuration\.(kt|java)$", "рецепт — конфигурация экрана"),
    (r"/infrastructure/", "поставщик — внешний сервис"),
    # Java-раскладка (controller/service/repository/model, db/migration)
    (r"/db/migration/|\.sql$", "склад — миграция"),
    (r"/(controller|rest|web|api)/", "официант — контроллер"),
    (r"/(dto)/", "тарелка подачи — DTO"),
    (r"/(repository|dao|persistence|client|integration|adapter)/", "поставщик или склад — адаптер"),
    (r"/(model|entity|domain/model)/", "продукты — модель"),
    (r"Facade\.(java|kt)$|Service\.(java|kt)$", "повар — сервис"),
    (r"/(enricher|converter|mapper)/", "помощник повара — обогащение"),
    (r"/(service|domain|handler|processor|logic)/", "помощник повара — вычисления"),
]


def role_of(path):
    for rx, role in ROLES:
        if re.search(rx, path):
            return role
    return ""


# Клиентских данных на странице быть не должно, даже тестовых: диффы чистятся до рендера.
_PII = [
    (re.compile(r"(?<![\d{,])\d{20}(?![\d},])"), "<счёт>"),
    (re.compile(r"(?<![\d{,])\d{16}(?![\d},])"), "<16 цифр>"),
    (re.compile(r"(?<![\d{,])\d{12}(?![\d},])"), "<ИНН>"),
    (re.compile(r"(?<![\d{,])\d{10}(?![\d},])"), "<10 цифр>"),
    (re.compile(r"(?<![\d{,])\d{4} ?\d{6}(?![\d},])"), "<паспорт>"),
    (re.compile(r"\+?7[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}"), "<телефон>"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<email>"),
    (re.compile(r"([Cc][Nn][Uu][Mm][Aa]?[\"':= ]{1,4})(?=[A-Z0-9]*\d)[A-Z0-9]{5,10}\b"), r"\1<номер клиента>"),
    (re.compile(r"\b[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+(вич|вна|ична|ич)\b"), "<ФИО>"),
    (re.compile(r"\b[А-ЯЁ][а-яё]+(?:ов|ев|ёв|ин|ын|ова|ева|ина|ына|ский|ская|цкий|цкая) [А-ЯЁ][а-яё]+(?: [А-ЯЁ][а-яё]+)?\b"), "<ФИО>"),
]


# номер клиента в фикстурах стоит и голым литералом (SQL VALUES, `равно "…"`): значения под ключами учим по всему диффу MR
_ID_KEY = re.compile(r"(?i)\b(?:cnuma?|user_?id|client_?id|customer_?id)\b[\"'\s]*[:=]+\s*[\"']?([A-Z0-9]{5,12})\b")
_LEARNED = set()


def _git(repo, *args):
    """git в клоне MR; ошибка git — остановка с текстом git, а не пустой дифф и страница без кода."""
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"ошибка: git {' '.join(args[:2])} в {repo}: {r.stderr.strip()}")
    return r


def learn_ids(repo, rng):
    if not repo:
        return
    r = _git(repo, "diff", rng)
    _LEARNED.update(v for v in _ID_KEY.findall(r.stdout) if re.search(r"\d", v))


def sanitize(text):
    for v in _LEARNED:
        text = re.sub(rf"(?<![\w]){re.escape(v)}(?![\w])", "<номер клиента>", text)
    for rx, repl in _PII:
        text = rx.sub(repl, text)
    return text


def git_diff(repo, rng, path, limit=None):
    if not repo:
        return ""
    out = _git(repo, "diff", rng, "--", path).stdout
    if limit:
        lines = out.split("\n")
        if len(lines) > limit:
            out = "\n".join(lines[:limit]) + f"\n+… ещё {len(lines) - limit} строк данных — смотри в MR\n"
    return sanitize(out)


_DECL = r"\b(?:fun|val|var|class|object|interface|enum class|data class)\b"


def signature(diff, chunk):
    """Строка объявления куска из диффа: «fun cancel(orderId: UUID, clientId: String): …». Нет — пусто."""
    name = re.escape(chunk["symbol"].split(".")[-1])
    lo, hi = lines_of(chunk["lines"])
    new = 0
    for line in diff.split("\n"):
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", line)
        if m:
            new = int(m.group(1))
            continue
        if line.startswith(("---", "+++", "diff ", "index ")) or line.startswith("-"):
            continue
        text = line[1:] if line[:1] in "+ " else line
        if lo and hi and lo <= new <= hi and re.search(rf"{_DECL}[^=\n]*?(?<![\w.]){name}\b", text):
            sig = re.sub(r"\s*[{=]\s*$", "", text.strip())
            return sig if len(sig) <= 140 else sig[:137] + "…"
        new += 1
    return ""


# фикстуры и SQL-данные показываются началом: схема видна по первым строкам, остальное — в MR
DATA_LINES = 60            # файл данных отдельным шагом
DATA_LINES_IN_GROUP = 40   # файл данных в общем шаге с другими тестами


def lines_of(spec):
    nums = [int(n) for n in re.findall(r"\d+", str(spec))]
    return (nums[0], nums[-1]) if nums else (None, None)


def plural(n, forms=("файл", "файла", "файлов")):
    k = 2 if 11 <= n % 100 <= 14 else 0 if n % 10 == 1 else 1 if 2 <= n % 10 <= 4 else 2
    return f"{n} {forms[k]}"


def step_id(path):
    return "f-" + re.sub(r"[^\w]+", "-", path.split("/")[-1].rsplit(".", 1)[0]).strip("-").lower()


def project(v3):
    meta = v3.get("meta", {})
    repo, rng = meta.get("repo"), meta.get("range")
    learn_ids(repo, rng)
    chunks = {c["id"]: c for c in v3.get("chunks", [])}
    outcomes = {o["id"]: o for o in v3.get("outcomes", [])}
    reqs = v3.get("requirements", [])
    findings = v3.get("findings", [])
    tests = v3.get("tests", [])
    decisions = {d["id"]: d for d in v3.get("decisions", [])}
    plan = v3.get("plan", {})

    # шаг = файл в главе: если куски одного файла стоят в разных строках плана, у файла шаг в каждой главе
    units, row_of_chunk = [], {}    # [(файл, № строки)] в порядке плана
    for k, r in enumerate(plan.get("rows", [])):
        for cid in r.get("chunks", []):
            row_of_chunk[cid] = k
            u = (chunks[cid]["file"], k)
            if u not in units:
                units.append(u)
        for f in r.get("files", []):
            if not any(u[0] == f for u in units):
                units.append((f, k))
    rows_of_file = {}
    for f, k in units:
        rows_of_file.setdefault(f, []).append(k)
    unit_sid = {(f, k): step_id(f) + (f"-{k + 1}" if len(rows_of_file[f]) > 1 else "") for f, k in units}
    files = [f for f, _ in units]
    sid_of = {}
    for (f, k), sid in unit_sid.items():
        sid_of.setdefault(f, sid)
    chunk_step = {cid: unit_sid.get((c["file"], row_of_chunk.get(cid))) or sid_of.get(c["file"]) for cid, c in chunks.items()}
    # та же правка в другом файле: все куски файла с same_as — файл показывается в карточке образца, а не своим шагом
    copies = {}                     # шаг образца → [(файл, глава)] в порядке плана
    for f, k in units:
        cs_ = [c for c in chunks.values() if c["file"] == f and row_of_chunk.get(c["id"]) == k]
        if cs_ and all(c.get("same_as") in chunks for c in cs_):
            host = chunk_step[cs_[0]["same_as"]]
            copies.setdefault(host, []).append((f, k))
            for c in cs_:
                chunk_step[c["id"]] = host
            sid_of[f] = host

    callers = {}
    for c in chunks.values():
        for x in c.get("calls", []):
            callers.setdefault(x["to"], []).append(c["id"])
    entry_ = v3.get("entry") or {}
    for x in entry_.get("calls", []):
        callers.setdefault(x["to"], []).append("__entry__")

    def ref_name(cid):
        if cid == "__entry__":
            return entry_.get("label", "точка входа")
        c = chunks.get(cid)
        return f"[`{c['symbol'].split('.')[-1]}`](#chunk-{cid})" if c else outcomes.get(cid, {}).get("label", cid)

    def f_step(f):
        at = f.get("at", {})
        return chunk_step.get(at.get("chunk")) if at else None

    def why(f):
        b = f.get("breaks") or {}
        parts = [f"если {b['on']}" if b.get("on") else "", b.get("effect", ""),
                 f"заметно по: {b['notice']}" if b.get("notice") else ""]
        return " → ".join(p for p in parts if p)

    # ---------- вердикт
    worst = min((SEVERITY.index(f["severity"]) for f in findings), default=len(SEVERITY))
    code_fix = any(f["severity"] in ("block", "fix") and f.get("area") != "ci" for f in findings)
    if worst == 0:
        status = "rework"
    elif code_fix:
        status = "fix"
    elif any(f["severity"] == "ask" and f.get("when") == "merge" for f in findings):
        status = "askmerge"
    elif any(f["severity"] == "fix" for f in findings):
        status = "wait"
    elif any(f["severity"] == "ask" for f in findings):
        status = "ask"
    else:
        status = "ok"

    implemented = {r: [c for c in chunks.values() if r in c.get("implements", [])] for r in (x["id"] for x in reqs)}
    proved = {r: [t for t in tests if r in t.get("proves", [])] for r in (x["id"] for x in reqs)}

    requirements = []
    for r in reqs:
        fs = [f for f in findings if f.get("req") == r["id"]]
        cs, ts = implemented[r["id"]], proved[r["id"]]
        by = r.get("by", "code")
        has_impl = bool(cs) or by in ("test", "config", "manual")
        st = "gap" if not has_impl or any(f["severity"] == "block" for f in fs) else (
            "partial" if (not ts and by != "test") or any(f["severity"] in ("fix", "ask") for f in fs) else "ok")
        row = {"req": f"{r['id']}. {r['text']}", "status": st,
               "where": ", ".join(f"`{c['symbol']}`" for c in cs[:2]) or {"config": "настройка сервиса", "manual": "вне кода MR", "test": "тест"}.get(by, "—"),
               "proof": "; ".join(t["scenario"] for t in ts[:2]) or ("проверить вручную на стенде" if by in ("config", "manual") else "тестом не покрыто"),
               "step": (f_step(fs[0]) if fs and f_step(fs[0]) else chunk_step.get(cs[0]["id"]) if cs else None)}
        if fs and fs[0].get("id"):
            row["_fid"] = fs[0]["id"]
        if cs:
            row["chunk"] = cs[0]["id"]
        if st != "ok":
            row["do"] = (fs[0]["do"] if fs else
                         ("Проверить на стенде." if by in ("config", "manual") else
                          "Добавить тест на это требование." if not ts else "Реализовать требование."))
        requirements.append(row)

    checks = []
    for area, title in AREAS:
        fs = [f for f in findings if f.get("area") == area]
        if area == "scope":
            miss = [r for r in reqs if not implemented[r["id"]] and r.get("by", "code") == "code"]
            if miss:
                fs = fs or [{"severity": "block", "claim": "Без кода: " + "; ".join(r["text"] for r in miss), "do": "Реализовать."}]
        if area == "tests":
            miss = [r for r in reqs if not proved[r["id"]] and r.get("by", "code") == "code"]
            if miss and not fs:
                fs = [{"severity": "ask", "claim": "Без теста: " + "; ".join(r["text"] for r in miss),
                       "do": "Проверить вручную или добавить сценарий."}]
        live = meta.get("mr", {}).get("status") if area == "ci" else None
        if live and meta.get("mr", {}).get("state") != "merged":
            ap, need = live.get("approvals", 0), live.get("approvals_required", 1)
            parts_ = [f"Draft: {'да' if live.get('draft') else 'нет'}", f"одобрений {ap} из {need}",
                      f"открытых тредов {live.get('open_threads', 0)}"] + ([f"пайплайн {live['pipeline']}"] if live.get("pipeline") else [])
            line = " · ".join(parts_) + (f" (срез {live['checked_at']})" if live.get("checked_at") else "")
            if live.get("draft") or ap < need or live.get("open_threads") or live.get("pipeline") not in (None, "success"):
                fs = fs + [{"severity": "ask", "claim": line, "do": ", ".join(x for x, c_ in (("снять Draft", live.get("draft")), ("закрыть треды", live.get("open_threads")),
                                                           ("получить одобрение", ap < need), ("починить пайплайн", live.get("pipeline") not in (None, "success"))) if c_).capitalize()
                       + " — перед мержем проверить в GitLab ещё раз."}]
            elif not fs:
                checks.append({"area": title, "status": "ok", "text": line})
                continue
        if not fs:
            text = {"scope": "Каждое требование реализовано кодом", "tests": "На каждое требование есть тест",
                    }.get(area, "Замечаний нет")
            checks.append({"area": title, "status": "ok", "text": text})
            continue
        f = min(fs, key=lambda x: SEVERITY.index(x["severity"]))
        more = f" и ещё {len(fs) - 1}" if len(fs) > 1 else ""
        c = {"area": title, "status": CHECK_OF[f["severity"]], "text": f["claim"] + more}
        if c["status"] != "ok":
            c["do"] = f.get("do", "")
        if f_step(f):
            c["step"] = f_step(f)
        if f.get("id"):
            c["_fid"] = f["id"]   # чек-лист ссылается на замечание, а не повторяет его текст
        checks.append(c)

    risks = []
    for f in sorted(findings, key=lambda x: (SEVERITY.index(x["severity"]), x.get("area") == "ci")):
        r = {"level": LEVEL[f["severity"]], "when": f.get("when", "know"), "text": f["claim"], "do": f.get("do", ""), "_fid": f.get("id", "")}
        if (f.get("at") or {}).get("chunk") in chunks:
            r["chunk"] = f["at"]["chunk"]
        if why(f):
            r["why"] = why(f)
            r["at_code"] = bool(f_step(f))   # на странице обучения полный текст стоит у строки кода
        if f_step(f):
            r["step"] = f_step(f)
        risks.append(r)

    if meta.get("mr", {}).get("state") == "merged":
        status = {"ok": "merged", "ask": "merged", "wait": "merged", "askmerge": "merged"}.get(status, status)
    verdict = {"status": status, "summary": v3.get("summary", ""), "checks": checks,
               "requirements": requirements, "risks": risks, "verify": v3.get("verify", [])}
    KIND = {"old": "старые данные", "malformed": "не тот формат", "empty": "пусто", "foreign": "чужое", "boundary": "граница"}
    fclaim = {f["id"]: f["claim"] for f in findings}
    probe_rows = []
    for pr in v3.get("probes", []):
        c = chunks.get(pr["at"], {})
        probe_rows.append({"at": pr["at"], "symbol": c.get("symbol", pr["at"]).split(".")[-1], "kind": KIND.get(pr["kind"], pr["kind"]),
                           "input": pr["input"], "code": pr["code"], "finding": pr.get("finding", ""),
                           "claim": fclaim.get(pr.get("finding"), ""), "ok": pr.get("ok", "")})
    verdict["probes"] = probe_rows

    # ---------- шаги-файлы: куски кода — карточкой над диапазоном, замечания — под своей строкой или в карточке
    steps = []
    chunk_files = {c["file"] for c in chunks.values()}
    grouped = {}                    # строка плана → шаг для её файлов без кусков
    for k, r in enumerate(plan.get("rows", [])):
        loose = [f for f in r.get("files", []) if f not in chunk_files]
        if len(loose) > 1:
            gid = f"g-{k + 1}"
            rows_t, diffs = [], []
            for f in loose:
                note = next((x.get("note") for x in v3.get("files", []) if x["path"] == f), "")
                data = "/resources/" in f or f.endswith((".sql", ".json", ".yaml", ".yml", ".csv"))
                proves = [t for t in tests if t.get("file") == f]
                what = "; ".join(f"{t['scenario']} ({', '.join(t.get('proves', []))})" for t in proves) or note or role_of(f)
                rows_t.append([f"`{f.split('/')[-1]}`", what])
                diffs.append({"type": "more", "title": f"`{f.split('/')[-1]}`",
                              "blocks": [{"type": "diff", "file": f, "diff": git_diff(repo, rng, f, limit=DATA_LINES_IN_GROUP if data else None), "notes": []}]})
            blocks = [{"type": "table", "head": ["Файл", "Что доказывает"], "rows": rows_t},
                      {"type": "more", "title": f"Диффы: {plural(len(loose))}", "blocks": diffs}]
            steps.append({"id": gid, "part": "changes", "title": f"{r['need']}: {plural(len(loose))}", "blocks": blocks})
            for f in loose:
                sid_of[f] = gid
            grouped[k] = gid
    for f, k in units:
        if sid_of[f].startswith("g-"):
            continue
        cs = sorted((c for c in chunks.values() if c["file"] == f and row_of_chunk.get(c["id"], k) == k),
                    key=lambda c: lines_of(c["lines"])[0] or 0)
        if any(f == x for x, _ in sum(copies.values(), [])):
            continue
        role = role_of(f)
        lead = next((x.get("note") for x in v3.get("files", []) if x["path"] == f), "")
        data = "/resources/" in f or f.endswith((".sql", ".json", ".yaml", ".yml", ".csv"))
        diff = git_diff(repo, rng, f, limit=DATA_LINES if data and not cs else None)
        parts, notes = [], []
        for c in cs:
            weak = [x for x in findings if x.get("at", {}).get("chunk") == c["id"] and not x["at"].get("line")]
            parts.append({"kind": "chunk", "cid": c["id"], "name": f"`{c['symbol']}`", "lines": c["lines"], "purpose": c["purpose"],
                          "why": c.get("why", ""),
                          "callers": [ref_name(x) for x in dict.fromkeys(callers.get(c["id"], []))],
                          "callees": [ref_name(x["to"]) for x in c.get("calls", []) if x["to"] in chunks],
                          "exits": [f"данные {outcomes[x['to']]['label']}" if outcomes[x["to"]].get("kind") == "store" else
                                    (f"{x['when']} → " if x.get("when") and not str(x["when"]).isdigit() else "") + outcomes[x["to"]]["label"]
                                    for x in c.get("calls", []) if x["to"] in outcomes],
                          "how": c.get("how", []), "decision": c.get("decision"),
                          "weak": [{"severity": x["severity"], "claim": x["claim"], "fid": x.get("id", ""),
                                    "why": " · ".join(p for p in (why(x), f"что делать: {x['do']}" if x.get("do") and x["severity"] != "know" else "") if p)} for x in weak]
                                   + ([{"severity": "none", "claim": "нет — " + c["no_weak"]}] if c.get("no_weak") else [])})
            for rl in c.get("rule_lines", []):
                notes.append({"line": rl["line"], "text": rl["text"]})
        for x in findings:
            at = x.get("at", {})
            if at.get("line") and at.get("chunk") in {c["id"] for c in cs}:
                notes.append({"line": at["line"], "kind": PLATE_OF[x["severity"]], "finding": True, "fid": x.get("id", ""),
                              "text": x["claim"] + (f" — {why(x)}" if why(x) else "") + (f" → {x['do']}" if x.get("do") and x["severity"] != "know" else "")})
        def method(c):
            sev = [x["severity"] for x in findings if (x.get("at") or {}).get("chunk") == c["id"]]
            return {"cid": c["id"], "name": c["symbol"].split(".")[-1], "purpose": c["purpose"], "sig": signature(diff, c),
                    "change": c.get("change", ""), "weak": min(sev, key=SEVERITY.index) if sev else ""}
        card = {"type": "filecard", "role": role, "lead": lead, "methods": [method(c) for c in cs],
                "add": sum(1 for x in diff.split("\n") if x.startswith("+") and not x.startswith("+++")),
                "del": sum(1 for x in diff.split("\n") if x.startswith("-") and not x.startswith("---"))}
        blocks = [card]
        dfb = {"type": "diff", "file": f, "diff": diff, "notes": notes, "chunks": parts, "lvl2": True}
        if len(rows_of_file.get(f, [])) > 1:
            dfb["focus"] = [lines_of(c["lines"]) for c in cs]
            dfb["caption"] = "показаны только куски этой главы, остальной файл — в других главах"
        blocks.append(dfb)
        same = copies.get(unit_sid[(f, k)], [])
        if same:
            # одна и та же правка в других файлах: на виду — файл, метод и что меняет; дифф каждого — под катом
            rows_s, diffs_s = [], []
            for f2, k2 in same:
                cs2 = sorted((c for c in chunks.values() if c["file"] == f2 and row_of_chunk.get(c["id"]) == k2),
                             key=lambda c: lines_of(c["lines"])[0] or 0)
                d2 = git_diff(repo, rng, f2)
                rows_s.append([f"`{f2.split('/')[-1]}`", ", ".join(f"[`{c['symbol'].split('.')[-1]}`](#chunk-{c['id']})" for c in cs2),
                               "; ".join(c["purpose"] for c in cs2)])
                parts2 = [{"kind": "chunk", "cid": c["id"], "name": f"`{c['symbol']}`", "lines": c["lines"], "purpose": c["purpose"],
                           "why": "", "callers": [], "callees": [], "exits": [], "how": c.get("how", []), "decision": None, "weak": []}
                          for c in cs2]
                diffs_s.append({"type": "more", "title": f"`{f2.split('/')[-1]}`",
                                "blocks": [{"type": "diff", "file": f2, "diff": d2, "notes": [], "chunks": parts2}]})
            blocks.append({"type": "samecard", "count": len(same), "rows": rows_s, "diffs": diffs_s})
        title = f.split("/")[-1]
        steps.append({"id": unit_sid[(f, k)], "part": "changes", "title": title, "blocks": blocks})

    for d in decisions.values():
        src = {"review": "тред ревью", "spec": "спека", "jira": "задача в Jira", "desc": "описание MR", "code": "код MR",
               "discussion": "обсуждение с командой"}
        blocks = [{"type": "think", "question": d["question"], "question_in_title": True, "decided": d["decided"],
                   "rejected": d.get("rejected", [])}]
        if d.get("source"):
            blocks[0]["source"] = ", ".join(src.get(x, x) for x in d["source"])
        if d.get("code"):
            blocks.append({"type": "code", **d["code"]})
        steps.append({"id": d["id"], "part": "design", "title": f"{d['id']} · {d['question']}", "blocks": blocks})

    rows = []
    for r in plan.get("rows", []):
        fs = []
        for cid in r.get("chunks", []):
            s = chunk_step[cid]
            if s not in fs:
                fs.append(s)
        for x in r.get("files", []):
            if sid_of[x] not in fs:
                fs.append(sid_of[x])
        ds = [d for d in r.get("decisions", []) if d in decisions]
        for cid in r.get("chunks", []):
            d = chunks[cid].get("decision")
            if d and d not in ds and d in decisions:
                ds.append(d)
        rows.append({"need": r["need"], "where": r.get("where", ""), "why": r.get("why", ""), "files": fs,
                     "decisions": ds, "how": r.get("how", []), "learn": r.get("learn", ""), "check": r.get("check", [])})

    # ---------- граф вызовов из chunks.calls
    drawn = set()

    def node_of(ref, when=None, seen=()):
        if ref in outcomes:
            o = outcomes[ref]
            n = {"label": o["label"], "kind": o.get("kind", "error")}
            if ref in drawn:
                n["note"] = "тот же исход, что выше"
            elif o.get("note"):
                n["note"] = o["note"]
            drawn.add(ref)
        elif ref in chunks:
            c = chunks[ref]
            n = {"label": f"`{c['symbol']}`", "role": c.get("role") or role_of(c["file"]), "step": chunk_step[ref], "chunk": ref,
                 "file": c["file"].split("/")[-1]}
            sev = [x["severity"] for x in findings if (x.get("at") or {}).get("chunk") == ref]
            if sev:
                n["weak"] = min(sev, key=SEVERITY.index)
                n["fids"] = [x["id"] for x in findings if (x.get("at") or {}).get("chunk") == ref and x.get("id")]   # узел графа помечен, если у куска есть замечание
            if c.get("why") or c.get("graph_note"):
                n["note"] = c.get("why") or c["graph_note"]
            if ref not in seen:
                kids = [node_of(x["to"], x.get("when"), seen + (ref,)) for x in c.get("calls", [])]
                if kids:
                    n["children"] = kids
        else:
            n = {"label": ref}
        if when:
            n["edge"] = when
        return n

    entry = v3.get("entry")
    graph = None
    if entry:
        root = {"label": entry["label"], "role": "гость"}
        if entry.get("note"):
            root["note"] = entry["note"]
        root["children"] = [node_of(x["to"], x.get("when")) for x in entry.get("calls", [])]
        graph = {"type": "callgraph", "root": root}

    # ---------- intro
    intro = []
    svc = v3.get("service")
    if svc:
        blocks = [b for b in [
            {"type": "p", "text": svc["about"]} if svc.get("about") else None,
            {"type": "p", "text": "Стек: " + svc["stack"]} if svc.get("stack") else None,
            {"type": "flow", "nodes": svc["flow"]} if svc.get("flow") else None,
            {"type": "table", "head": ["Понятие", "Что это для бизнеса", "Где в коде"], "rows": svc["model"]} if svc.get("model") else None,
        ] if b]
        intro += [{"type": "h", "text": "Как устроен сервис"},
                  {"type": "more", "title": "Справка: что делает сервис, путь данных, модель предметной области", "blocks": blocks}]
    ctx = v3.get("context")
    if ctx:
        intro.append({"type": "h", "text": "Контекст задачи"})
        intro.append({"type": "p", "text": ctx["text"]})
        if ctx.get("terms"):
            intro.append({"type": "table", "head": ["Термин", "Что значит"], "rows": [[k, v] for k, v in ctx["terms"].items()]})
    entry = v3.get("entry")
    if entry:
        first = [x["to"] for x in entry.get("calls", []) if x["to"] in chunks]
        lines = [f"[`{chunks[c]['symbol']}`](#chunk-{c}) — {chunks[c].get('role') or role_of(chunks[c]['file']) or 'кусок'}, файл `{chunks[c]['file'].split('/')[-1]}`"
                 + (f": {chunks[c]['purpose']}" if chunks[c].get("purpose") else "") for c in first]
        intro += [{"type": "h", "text": "Вход в код"},
                  {"type": "p", "text": f"Запрос присылает **{entry['label']}**" + (f" — {entry['note']}" if entry.get("note") else "") + "."
                   + (" В сервисе его первым получает:" if lines else "")}]
        if lines:
            intro.append({"type": "list", "items": lines})
    layer_rows, short = None, []
    trace = v3.get("trace")
    if trace:
        intro.append({"type": "h", "text": "Путь одного запроса"})
        if trace.get("title"):
            intro.append({"type": "p", "text": trace["title"]})
        items, short = [], []
        for st_ in trace["steps"]:
            ref = st_.get("at")
            if ref in chunks:
                who = f"[`{chunks[ref]['symbol']}`](#chunk-{ref})"
                role = chunks[ref].get("role") or role_of(chunks[ref]["file"])
                who += f" — {role}" if role else ""
            elif ref in outcomes:
                who = outcomes[ref]["label"]
            else:
                who = st_.get("label", ref or "")
            parts_ = [who if "](" in who else f"**{who}**"]
            if st_.get("in"):
                parts_.append(f"получает {st_['in']}")
            if st_.get("does"):
                parts_.append(st_["does"])
            if st_.get("out"):
                parts_.append(f"→ {st_['out']}")
            items.append(" · ".join(parts_))
            if ref in chunks:
                role = chunks[ref].get("role") or role_of(chunks[ref]["file"]) or ""
                layer = role.split(" — ")[-1] if role else chunks[ref]["symbol"].split(".")[-1]
            elif ref in outcomes:
                o = outcomes[ref]
                layer = {"store": "данные", "result": "ответ", "error": "отказ"}.get(o.get("kind"), "исход") + " " + o["label"]
            else:
                layer = "вход " + st_.get("label", ref or "")
            if short and short[-1][0] == layer:     # соседние шаги одного слоя — одной строкой; длинную склейку не делаем
                joined = "; ".join(x for x in (short[-1][1], st_.get("does", "")) if x)
                if len(joined) <= 60:
                    short[-1] = (layer, joined)
                continue
            short.append((layer, st_.get("does", "")))
        cards = []
        for st_ in trace["steps"]:
            ref = st_.get("at")
            if ref in chunks:
                c = chunks[ref]
                who = f"[`{c['symbol'].split('.')[-1]}`](#chunk-{ref})"
                role = c.get("role") or role_of(c["file"]) or ""
                where = c["file"].split("/")[-1]
            elif ref in outcomes:
                who, role, where = outcomes[ref]["label"], {"store": "данные", "result": "ответ", "error": "отказ"}.get(outcomes[ref].get("kind"), ""), ""
            else:
                who, role, where = st_.get("label", ref or ""), "вход", ""
            cards.append({"who": who, "role": role, "where": where, "in": st_.get("in", ""), "does": st_.get("does", ""),
                          "out": st_.get("out", ""), "code": st_.get("code", ""), "lang": meta.get("lang", ""),
                          "query": st_.get("query", ""), "returned": st_.get("returned", "")})
        intro.append({"type": "trace", "steps": cards})
        def name(ref):
            if ref in chunks:
                return f"[`{chunks[ref]['symbol']}`](#chunk-{ref})"
            if ref in outcomes:
                return outcomes[ref]["label"]
            return ref
        if trace.get("branches"):
            intro.append({"type": "h", "text": "Ветки: где запрос свернёт"})
            intro.append({"type": "list", "items": [f"**Если {br['when']}** — " + " → ".join(name(x) for x in br["path"])
                                                    + (f". **Итог:** {br['result']}" if br.get("result") else "") for br in trace["branches"]]})
    mech = v3.get("mechanism")
    walk = [x for x in (mech or {}).get("steps", []) if isinstance(x, dict)]
    if walk:
        # главный механизм — пример по шагам на реальных файлах: что лежит, что делает код, где, что вышло, когда не выйдет
        intro.append({"type": "h", "text": "Главный механизм на примере"})
        if mech.get("example"):
            intro.append({"type": "code", **mech["example"]})
        intro.append({"type": "mechwalk", "lang": meta.get("lang", ""), "steps": walk})
        if mech.get("takeaway"):
            intro.append({"type": "p", "text": f"**Главное:** {mech['takeaway']}"})
    intro.append({"type": "h", "text": "Слои и цепочка вызовов"})
    if mech and not walk:
        if mech.get("example"):
            intro.append({"type": "p", "text": "Как это устроено на примере:"})
            intro.append({"type": "code", **mech["example"]})
        if mech.get("steps"):
            intro.append({"type": "p", "text": "По шагам:" if mech.get("example") else "Как это устроено по шагам:"})
            intro.append({"type": "list", "ordered": True, "items": mech["steps"]})
    if graph:
        intro.append({"type": "p", "text": "Код устроен как ресторан: у каждого слоя своя роль, таблица ниже."})
        intro.append(graph)
    LAYERS = [("официант", ["Официант — контроллер, обработчик ошибок", "принимает запрос, отдаёт ответ или код ошибки", "бизнес-правил"]),
              ("меню", ["Меню — порт", "перечисляет, что умеет домен", "кода"]),
              ("повар", ["Повар — фасад или сервис", "выполняет правила задачи", "HTTP-кодов"]),
              ("помощник", ["Помощник повара — обогащение, вычисления", "одно правило или преобразование по заказу повара", "решений о доступе и HTTP"]),
              ("склад", ["Склад — база, миграции, внешние сервисы", "хранит и достаёт данные", "бизнес-решений"]),
              ("поставщик", ["Поставщик — клиент внешнего сервиса", "ходит за данными наружу", "бизнес-решений"]),
              ("рецепт", ["Рецепт — конфигурация экрана", "описывает поля экрана и их правила", "походов в базу и наружу"]),
              ("записка", ["Записка повара — исключение", "сообщает об отказе наверх", "HTTP-кодов"]),
              ("продукты", ["Продукты — модель", "данные внутри сервиса", "логики"]),
              ("тарелка", ["Тарелка подачи — DTO", "форма ответа наружу", "логики"])]
    present = {role_of(c["file"]) or c.get("role", "") for c in chunks.values()} | {c.get("role", "") for c in chunks.values()}
    rows_l = [row for key, row in LAYERS if any(key in (r or "").lower() for r in present)]
    if rows_l:
        intro.append({"type": "table", "head": ["Слой в этом MR", "Делает", "Чего там быть не должно"], "rows": rows_l})
    # «Суть MR» — наверху, до контекста: главная идея и цепочка слоёв пути одного запроса
    core = []
    if plan.get("task"):
        core.append({"type": "p", "text": plan["task"]})
    if core:
        intro[0:0] = [{"type": "h", "text": "Суть MR"}] + core
    plan_block = {"type": "plan", "task": plan.get("task", ""), "kind": plan.get("kind", ""), "rows": rows}
    intro += [{"type": "h", "text": "План доработки"}, plan_block]
    if v3.get("example"):
        intro += [{"type": "h", "text": "Пример: запрос и ответ"}] + v3["example"]
    if tests:
        trows = [[t["scenario"], f"`{t['expect']}`" if t.get("expect") else "", ", ".join(t.get("proves", []))] for t in tests]
        trows += [[f"**Не проверяют:** {r['id']}. {r['text']}", "", "проверить вручную"] for r in reqs
                  if not proved[r["id"]] and r.get("by", "code") != "test"]
        intro += [{"type": "h", "text": "Что обещают тесты"},
                  {"type": "table", "head": ["Сценарий", "Ответ", "Требования"], "rows": trows}]
    # файлы MR вне пути запроса: ИИ мог добавить лишнее — у каждого такого файла должно быть «зачем»
    reach, stack = set(), [x["to"] for x in (v3.get("entry") or {}).get("calls", [])]
    while stack:
        cid = stack.pop()
        if cid in reach or cid not in chunks:
            continue
        reach.add(cid)
        stack += [x["to"] for x in chunks[cid].get("calls", [])]
    changed = []
    if repo:
        changed = [f for f in _git(repo, "diff", "--name-only", rng).stdout.split() if f]
    on_path = {chunks[c]["file"] for c in reach}
    tests_ = [f for f in changed if "/src/test/" in "/" + f or f.startswith("src/test/")]
    # порты, исключения, модели, которые импортирует код пути, — тоже путь: граф просто не заходит в интерфейсы
    def used_by_path(f):
        name = f.split("/")[-1].rsplit(".", 1)[0]
        for g in on_path:
            r_ = subprocess.run(["git", "-C", repo, "show", f"{rng.split('...')[-1]}:{g}"], capture_output=True, text=True)
            if re.search(rf"\b{re.escape(name)}\b", r_.stdout):
                return True
        return False
    via = [f for f in changed if f not in on_path and f not in tests_ and repo and used_by_path(f)]
    outside = [f for f in changed if f not in on_path and f not in tests_ and f not in via]
    via_txt = f", их порты, исключения и модели — {len(via)}" if via else ""
    if changed:
        orows = []
        for f in outside:
            cs_ = [c for c in chunks.values() if c["file"] == f]
            why_ = next((x.get("note") for x in v3.get("files", []) if x["path"] == f), "") or "; ".join(
                (c.get("why") or c["purpose"]) for c in cs_[:2])
            sid_ = sid_of.get(f)
            name_ = f"[`{f.split('/')[-1]}`](#{sid_})" if sid_ else f"`{f.split('/')[-1]}`"
            orows.append([name_, role_of(f) or "—", why_ or "⚠ объяснения нет — спроси автора, зачем файл"])
        intro += [{"type": "h", "text": "Файлы MR вне пути запроса"},
                  {"type": "p", "text": f"Файлов в MR: {len(changed)}. На пути запроса — {len(on_path)}{via_txt}, тесты и фикстуры — {len(tests_)}, "
                   f"вне пути — {len(outside)}. У каждого файла вне пути должно быть «зачем»: нет — первый кандидат на лишнее."}]
        if orows:
            intro.append({"type": "table", "head": ["Файл", "Слой", "Зачем, если запрос его не вызывает"], "rows": orows})
    if probe_rows:
        bad_ = [r for r in probe_rows if r["finding"]]
        intro += [{"type": "h", "text": "Кривые входы и старые данные"},
                  {"type": "p", "text": f"Код прогнали на {len(probe_rows)} пробах: записи до MR, вход не того формата, пустое и чужое. "
                   f"Слабых мест — {len(bad_)}" + (": " + "; ".join(r["claim"] for r in bad_) if bad_ else "") + ". "
                   "[Таблица проб — на странице ревью →](REVIEW#probes)"}]
        if False:
            intro += [{"type": "table", "head": ["Где", "Что пришло", "Что сделает код", "Итог"],
                   "rows": [[f"[`{r['symbol']}`](#chunk-{r['at']})", f"**{r['kind']}:** {r['input']}", r["code"],
                             (f"⚠ {r['claim']}" if r["finding"] else f"✅ {r['ok']}")] for r in probe_rows]}]
    ba = v3.get("before_after", [])
    mod = [c for c in chunks.values() if c.get("change") == "modified"
           and "new file mode" not in git_diff(repo, rng, c["file"])[:400]]
    if mod:
        intro += [{"type": "h", "text": "Правки старого кода — зона риска"},
                  {"type": "table", "head": ["Кусок", "Что поменялось", "Кого задевает"],
                   "rows": [[f"[`{c['symbol']}`](#chunk-{c['id']})", c["purpose"], c.get("affects", "—")] for c in mod]}]

    # ---------- картина MR для страницы обучения: зачем, было → стало, карта файлов по слоям
    LAYER_ORDER = ["официант", "тарелка", "меню", "повар", "помощник", "записка", "продукты", "склад", "рецепт", "поставщик",
                   "сценарий", "шаги", "настройка", "юнит", "тестовые"]
    heart = ""
    for st_ in (mech or {}).get("steps", []):
        if isinstance(st_, dict) and st_.get("at"):
            heart = st_["at"].split(":")[0].split("/")[-1]
            break
    layers, seen_f = {}, set()
    for f, k in units:
        if f in seen_f:
            continue
        seen_f.add(f)
        cs_ = [c for c in chunks.values() if c["file"] == f]
        if cs_ and all(c.get("same_as") for c in cs_):
            continue                      # копии — строкой у образца
        role = role_of(f) or (cs_[0].get("role", "") if cs_ else "") or "другое"
        layer = role if role.split(" ")[0] not in ("юнит-тест", "сценарий", "шаги", "настройка", "тестовые") else "тесты"
        name = f.split("/")[-1]
        changes = {c.get("change") for c in cs_}
        tag = "правка" if "modified" in changes else "новый" if changes == {"new"} else ""
        note = next((x.get("note") for x in v3.get("files", []) if x["path"] == f), "") or (cs_[0]["purpose"] if cs_ else "")
        host = sid_of.get(f)
        same = len(copies.get(host, [])) if host == unit_sid.get((f, k)) else 0
        # слой — по первому слову роли («официант»), уточнение («контроллер») — у файла
        head, _, sub = layer.partition(" — ")
        head = "повар" if head == "помощник повара" else head
        layers.setdefault(head, []).append({"name": name, "sid": host, "tag": tag, "heart": name == heart, "note": note, "same": same,
                                            "sub": sub if layer != "тесты" else ""})
    def layer_key(l):
        w = l.split(" ")[0].replace("-", "")
        return next((i for i, x in enumerate(LAYER_ORDER) if w.startswith(x)), 90 if l == "тесты" else 80)
    pic = v3.get("picture") or {}
    picture = {"why": plan.get("task", ""), "before": pic.get("before", ""), "after": pic.get("after", ""), "key": pic.get("key", ""),
               "map": [{"layer": l, "files": layers[l]} for l in sorted(layers, key=layer_key)]}

    fid = {f["id"]: f for f in findings}
    lessons = []
    for l in v3.get("lessons", []):
        st_ = l.get("step")
        if st_ in fid and f_step(fid[st_]):
            st_ = f_step(fid[st_])
        elif st_ in chunk_step:
            st_ = chunk_step[st_]
        lessons.append({**l, "step": st_} if st_ else l)

    doc = {"title": meta.get("title", "Разбор MR"), "nav_title": meta.get("nav_title", "Разбор MR"),
           "subtitle": meta.get("subtitle", ""), "lang": meta.get("lang", ""), "mr": meta.get("mr", {}),
           "verdict": verdict, "intro": intro, "steps": steps, "lessons": lessons,
           "before_after": [{**b, "link": (f"#chunk-{b['chunk']}" if b.get("chunk") in chunks else "")} for b in ba],
           "quiz": v3.get("quiz", []), "glossary": {**(v3.get("context") or {}).get("terms", {}), **v3.get("glossary", {})},
           "picture": picture, "footer": "Сгенерировано скиллом `mr-mentor`.",
           "retell": [x for x in [
               (v3.get("mechanism") or {}).get("text", ""),
               ("Запрос идёт: " + " → ".join(l for l, _ in short) + ".") if short else ""] if x],
           "_v3": True, "_chunks": {cid: {"symbol": c["symbol"], "step": chunk_step[cid]} for cid, c in chunks.items()}}
    return doc
