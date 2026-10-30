# Схема разбора

Что писать в полях — `fields.md`. `meta.repo` и `meta.range` обязательны. Лишних полей нет: валидатор отклонит JSON
с полем, которого нет в схеме.

```text
meta         title, nav_title, lang, mr{url, ref, branch, task, stats, spec, state, status{draft, approvals, approvals_required, open_threads, pipeline, checked_at}}, repo, range
picture      before, after, key? — картина MR на странице обучения: что сервис делал до MR и что делает теперь
summary      2–3 фразы вердикта — единственный авторский текст вердикта
context      text, terms{термин: что значит}
trace        title, steps[{at (chunk|outcome id) | label, in, does, out, code, query, returned}] — в порядке вызова, не больше 6 шагов, branches[{when, path[], result}]
service      about, stack, flow[{label, note, step?}], model[[понятие, для бизнеса, где в коде]]
mechanism    text, example{lang, caption, code}, steps[{does, at `Файл:N`, code, result, fails?}], takeaway — пример по шагам на реальных файлах
requirements [{id, text, source?, by code|test|config|manual}]
entry        {label, note?, calls[{to, when?}]}
chunks       [{id, file, lines "86-98", symbol, purpose, why (роль в цепочке), how[], calls[{to, when?}], implements[R…],
               decision?, anchor?, rule_lines[{line, text}] ≤1, change new|modified|moved, affects?,
               graph_note?, role?, no_weak?, same_as?}] — same_as: id образца, правка та же в другом файле главы
outcomes     [{id, kind error|result|store, label, note?}]
findings     [{id, severity block|fix|ask|know, when merge|deploy|spec|desc|know,
               area scope|extra|data|deploy|tests|ci, claim, breaks{on, effect, notice}?, do,
               at{chunk, line?}?, req?}]
probes       [{id, at (chunk id), kind old|malformed|empty|foreign|boundary, input, code, finding (id) | ok}] — код на кривых входах, шаг 4а
decisions    [{id, question, decided, rejected[], code{lang, caption, code}?, source[review|spec|jira|desc|code|discussion]?, evidence_private?}]
tests        [{id, file?, scenario, proves[R…|D…], expect?}]
plan         {task, kind, rows[{need, learn, check[{kind predict|explain|break|where, chunk, q, a, code?}], where, why, chunks[] (может быть [] у строки с тестами), files[]? — файлы без кусков (тесты, фикстуры), decisions[]?}]}
             affects у куска — строка
files        [{path, note}]       — вводная к файлу (верхний уровень), не путать с plan.rows[].files
example      [блоки {type: p|code|list|table, …} — p{text}, code{lang, caption, code}, list{items, ordered?}, table{head, rows}]
before_after [{title, before{lang, code}, after{lang, code}, why, chunk?}] — урок «было → стало» (только обучение)
verify       ["действие на 5 минут"] — «Проверь сам» в вердикте
lessons      [{title, text, step?}] — step: id куска, замечания или решения
quiz         [{q, a}]
glossary     {термин: пояснение}
meta.mr      url, ref («repo !iid»), branch («`src` → `dst`»), task (ссылка на Jira), stats («N файлов · M коммитов»), spec (URL спеки), state (opened|merged)
```

## Что строит скрипт

| На странице | Из чего |
|---|---|
| статус вердикта | `block` — переделать; `fix` в коде — после правок; `ask`+`merge` — «вопрос до мержа»; только `ci`-`fix` — «код готов, мерж держит процесс»; `ask` — «есть вопрос»; `merged` — «влит» |
| чек-лист | `area` замечаний, `know` → ℹ️; `scope` — требования без кусков; `tests` — требования без тестов |
| требования | `requirements` + `chunks.implements` + `tests.proves` + `findings.req` |
| риски, расхождения со спекой | `findings` по `when` |
| плашка под строкой | замечание с `at.line`; без строки — «слабое место» в карточке куска |
| часть 1 обучения «Картина MR» | `plan.task` — зачем; `picture` — было → стало; карта файлов по слоям (роль по пакету, ★ — файл первого шага `mechanism`); `example` |
| часть 2 «Один запрос насквозь» | `trace`, ветки, `mechanism` |
| задания в главах | `plan.rows[].check`: после файла куска `chunk`, поле для ответа хранится в браузере, ответ — под «Сверить» |
| часть 4 «Итог» | пересказ MR: образец из `mechanism.text` и пути по слоям; взгляд ревьюера — пробы, тесты, правки старого, лишние файлы; `before_after` |
| карточка файла (обучение) | роль слоя по пакету, `files[].note`, методы: объявление из диффа + `purpose`, метка замечания; код — под катом «Код с пояснениями», кнопки «Обзор · Код» в шапке |
| «Та же правка ещё в N файлах» | файлы, у всех кусков которых `same_as`: строка в карточке образца, код каждого — под катом |
| карточка куска над кодом | `purpose`, «зачем» (`why`), «кто зовёт / кого зовёт» (из `calls`), `how`, слабые места, ссылка на решение; на узле графа — `why` |
| граф вызовов | `entry` + `chunks.calls` + `outcomes`; роль слоя — по пакету файла |
| главы | `plan.rows`: решения, затем файлы кусков по порядку |
| «Что обещают тесты» | `tests` (требования — по id) + требования без тестов |
| «Контекст задачи», «Путь одного запроса» | `context`, `trace` |
| таблица слоёв | только роли кусков этого MR |
| «Файлы MR вне пути запроса» | файлы диффа, до которых не доходит граф от `entry`, кроме тестов; «зачем» — `files[].note` или `why` кусков |
| «Правки старого кода» | куски с `change: modified` в файлах, которые существовали до MR |
| левая колонка | граф вызовов строкой на узел (значок роли, глава, метка замечания) и главы с файлами и кусками; подсвечено место, которое читаешь |
| шапка обеих страниц | переключатель «Ревью · Обучение», вердикт, где я (глава › файл › кусок), прогресс по файлам, «Продолжить» с места прошлого чтения (localStorage) |
| ревью | первым экраном «До мержа» и «Расхождения со спекой»; чек-лист и требования ссылаются на замечание, а не повторяют его |
| ссылки к коду | имя куска и глава (`compute` гл. 3) вместо сквозных номеров шагов |

## Валидатор

Ошибка (рендер не рисует): лишнее поле, неизвестное значение шкалы, ссылка в пустоту, кусок вне плана,
пересечение кусков, строка замечания вне куска, якорь не найден, диапазон длиннее файла.
Проверка (рисует): пересказ замечания в куске или решении, похожие замечания, оценочное слово в описании,
кусок без `how`, больше одной `rule_line`, изменённые строки вне кусков, история или хэш в тексте.

«Текст на виду» — маршрут чтения: вердикт, картина MR, решения. Карточки кусков и плашки в диффе читаются
по главам и в лимит 2600 слов не входят.
