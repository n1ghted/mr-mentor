# mr-mentor

Скилл Claude Code для аналитика или джуниора, за которого код пишет ИИ. Он разбирает GitLab merge request
и выдаёт две самодостаточные HTML-страницы:

- **Ревью** — самопроверка перед отправкой сеньору: вердикт, чек-лист, требования задачи, расхождения со
  спекой, что сломается на старых данных и кривых входах, не добавил ли ИИ лишнего.
- **Обучение** — как читать код этого MR: картина MR → один запрос насквозь по коду с реальными значениями →
  файлы по порядку с заданиями → пересказ со сверкой по образцу.

*English: a Claude Code skill that reviews a GitLab merge request for an analyst or junior whose code is
written by AI, and renders two self-contained HTML pages — a pre-review self-check and a code-reading lesson
built on worked examples, tracing and short exercises. Pages and prompts are in Russian.*

Пример готовых страниц — [`examples/shop-cancel/`](examples/shop-cancel/): вымышленный MR «покупатель
отменяет заказ».

## Как устроена страница обучения

Порядок взят из методик обучения чтению кода: сначала разобранный пример, потом самостоятельная работа.

1. **Картина MR** — зачем, было → стало, карта файлов по слоям с «сердцем MR».
2. **Один запрос насквозь** — запрос идёт по коду: что пришло, какой код сработал, что вышло.
3. **Файлы по порядку** — у файла роль и методы, код под катом; после файла — 1–3 задания:
   «предскажи», «объясни своими словами», «что сломается, если…», «где менять». Ответ пишется в поле
   и сверяется с образцом.
4. **Итог** — пересказ MR в трёх фразах, взгляд ревьюера.

## Что нужно

- Claude Code.
- Python 3.10 или новее, без сторонних библиотек.
- `git` и локальный клон репозитория MR.
- Доступ к MR: GitLab MCP-сервер или CLI [`glab`](https://gitlab.com/gitlab-org/cli). Без них описание MR
  можно вставить в чат.
- Лучше всего подходит для JVM-сервисов: Kotlin или Java, Spring, раскладка `application` / `core/ports` /
  `core/services` / `infrastructure`. На другом стеке разбор работает, но роли слоёв остаются пустыми.

## Установка

Скопируйте папку `mr-mentor` в `~/.claude/skills/` — для всех проектов, или в `.claude/skills/` проекта.

## Запуск

В Claude Code, из клона репозитория:

```
разбери MR https://gitlab.example.com/group/project/-/merge_requests/42
```

Скилл соберёт материал, запишет факты в JSON, запустит `scripts/render.py` и откроет страницу ревью.

## Как это работает

Модель пишет только факты — требования, куски кода, замечания, решения, тесты — каждый один раз и с id.
`scripts/render.py` проверяет JSON (`validate.py`), собирает из фактов всё, что видно на странице
(`project.py`), и рисует HTML. Вердикт, чек-лист, граф вызовов и таблицы строит скрипт, поэтому факт не
может разойтись сам с собой.

- `SKILL.md` — ход работы.
- `references/schema.md` — формат JSON, `references/fields.md` — что писать в каждом поле,
  `references/file-checklists.md` — где искать слабые места по роли файла.

## Перерисовать пример самому

```sh
git clone examples/shop-cancel/shop-orders.bundle /tmp/mr-mentor-shop
python3 scripts/render.py examples/shop-cancel/shop-orders-42.json
```

## Лицензия

[MIT](LICENSE)
