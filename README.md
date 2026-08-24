# postman-echo-allure

Автотесты публичного REST-сервиса [postman-echo.com](https://postman-echo.com)
на `requests` + `pytest` с отчётом **Allure**, который собирается в GitHub Actions
и публикуется на GitHub Pages.

**Отчёт:** https://petrovasochi2019.github.io/postman-echo-allure/

## Что покрыто

13 тестов (9 функций, одна параметризована на 5 кейсов), сгруппированы в отчёте
по epic → feature → story:

| Feature | Тест | Что проверяет |
| --- | --- | --- |
| `GET /get` | `test_get_query_params_are_echoed` | квери-параметры возвращаются в `args`, повторяющийся — списком |
| `GET /get` | `test_get_echoes_custom_headers` | пользовательские заголовки эхо-нятся в нижнем регистре |
| `GET /get` | `test_head_get_returns_headers_without_body` | `HEAD /get` — `200` с пустым телом |
| `POST /post` | `test_post_form_urlencoded` | form-urlencoded тело попадает в `form`, `data` пустая |
| `POST /post` | `test_post_json_body` | JSON-тело возвращается в `json` и `data`, `Content-Length` совпадает |
| `POST /post` | `test_post_raw_text_body` | `text/plain` тело кладётся в `data` строкой, `json = null` |
| `POST /post` | `test_post_multipart_file_upload` | multipart: файл в `files`, поле в `form` |
| `POST /post` | `test_post_url_accepts_query_params_too` | квери-параметры и тело обрабатываются независимо |
| Негативные | `test_wrong_method_for_endpoint_returns_404` | чужой HTTP-метод даёт `404` (5 кейсов) |

## Allure-аннотации

- `@allure.epic` / `@allure.feature` / `@allure.story` — группировка в отчёте;
- `@allure.title` — человекочитаемое имя теста (у параметризованного — шаблон
  `{method} {url} возвращает 404`);
- `@allure.description` — что именно проверяется и почему;
- `@allure.severity` — приоритет;
- `@allure.link` — ссылка на тестируемый эндпоинт;
- `allure.step` — шаги «Отправить запрос» → «Получен ответ» → шаги проверок;
- `allure.attach` — параметры запроса, заголовки и тело ответа приложены к каждому шагу.

## Запуск локально

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

pytest -v --alluredir=allure-results        # прогон с результатами Allure
allure serve allure-results                 # открыть отчёт (нужен Allure CLI)
```

Тестам нужен интернет — они ходят в реальный сервис.

## CI

[`.github/workflows/tests.yml`](.github/workflows/tests.yml) на каждый push в `main`,
на pull request и по кнопке:

1. ставит зависимости и гоняет `pytest -v --alluredir=allure-results`;
2. добавляет `environment.properties` (сервис, версия Python, ветка, коммит);
3. подтягивает ветку `gh-pages`, чтобы в отчёте сохранялась история прогонов
   (последние 20 отчётов, тренды);
4. собирает Allure-отчёт и публикует его в `gh-pages` → GitHub Pages;
5. кладёт `allure-results` артефактом к запуску;
6. падает, если тесты красные (отчёт при этом всё равно публикуется).
