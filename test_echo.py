"""
Автотесты публичного сервиса https://postman-echo.com с Allure-отчётом.

Проверяется поведение эндпоинтов
  GET  https://postman-echo.com/get
  POST https://postman-echo.com/post

Эхо-сервис возвращает JSON с разобранным запросом, поэтому каждый тест
сравнивает отправленное с тем, что сервис отразил обратно.
"""

import json

import allure
import pytest
import requests

BASE_URL = "https://postman-echo.com"
GET_URL = f"{BASE_URL}/get"
POST_URL = f"{BASE_URL}/post"
TIMEOUT = 15


@pytest.fixture(scope="session")
def session():
    with requests.Session() as s:
        s.headers.update({"User-Agent": "postman-echo-tests/1.0"})
        yield s


def send(session, method, url, **kwargs):
    """Отправляет запрос и прикладывает запрос/ответ к Allure-отчёту."""
    with allure.step(f"Отправить {method} {url}"):
        allure.attach(
            json.dumps(kwargs, ensure_ascii=False, default=str, indent=2),
            name="Параметры запроса",
            attachment_type=allure.attachment_type.JSON,
        )
        response = session.request(method, url, timeout=TIMEOUT, **kwargs)

    with allure.step(f"Получен ответ {response.status_code}"):
        allure.attach(
            json.dumps(dict(response.headers), ensure_ascii=False, indent=2),
            name="Заголовки ответа",
            attachment_type=allure.attachment_type.JSON,
        )
        allure.attach(
            response.text or "<пустое тело>",
            name="Тело ответа",
            attachment_type=allure.attachment_type.JSON
            if response.text.startswith("{")
            else allure.attachment_type.TEXT,
        )
    return response


@allure.epic("postman-echo.com")
@allure.feature("GET /get")
class TestGetEndpoint:
    @allure.title("GET /get возвращает квери-параметры в поле args")
    @allure.description(
        "Отправляем три квери-параметра, один из них повторяется дважды. "
        "Сервис обязан вернуть их в args, повторяющийся — списком значений, "
        "а также отразить полный URL запроса. Полей тела (form/data) в ответе GET нет."
    )
    @allure.story("Квери-параметры")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.link(GET_URL, name="Эндпоинт")
    def test_get_query_params_are_echoed(self, session):
        params = {"foo": "bar", "lang": "ru", "x": ["1", "2"]}

        response = send(session, "GET", GET_URL, params=params)

        with allure.step("Статус 200 и JSON в Content-Type"):
            assert response.status_code == 200
            assert response.headers["Content-Type"].startswith("application/json")
        body = response.json()
        with allure.step("Все параметры вернулись в args, повторяющийся — списком"):
            assert body["args"]["foo"] == "bar"
            assert body["args"]["lang"] == "ru"
            assert body["args"]["x"] == ["1", "2"]
        with allure.step("URL отражён, полей тела запроса нет"):
            assert body["url"].startswith(GET_URL)
            assert "form" not in body
            assert "data" not in body

    @allure.title("GET /get отражает пользовательские заголовки в нижнем регистре")
    @allure.description(
        "Сервис возвращает полученные заголовки в объекте headers, приводя имена "
        "к нижнему регистру. Заголовок X-Request-Id съедается edge-прокси сервиса "
        "и в эхо не попадает, поэтому проверяем на X-Trace-Id."
    )
    @allure.story("Заголовки")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_echoes_custom_headers(self, session):
        headers = {"X-Trace-Id": "abc-123", "X-Client": "pytest"}

        response = send(session, "GET", GET_URL, headers=headers)

        assert response.status_code == 200
        echoed = response.json()["headers"]
        with allure.step("Пользовательские заголовки вернулись в нижнем регистре"):
            assert echoed["x-trace-id"] == "abc-123"
            assert echoed["x-client"] == "pytest"
            assert "X-Trace-Id" not in echoed
        with allure.step("Служебные заголовки заполнены сервисом"):
            assert echoed["host"] == "postman-echo.com"
            assert echoed["user-agent"] == "postman-echo-tests/1.0"
            assert echoed["x-forwarded-proto"] == "https"

    @allure.title("HEAD /get отвечает 200 без тела")
    @allure.description(
        "На HEAD сервис отдаёт те же заголовки, что и на GET, но тело ответа пустое."
    )
    @allure.story("Методы")
    @allure.severity(allure.severity_level.MINOR)
    def test_head_get_returns_headers_without_body(self, session):
        response = send(session, "HEAD", GET_URL)

        assert response.status_code == 200
        with allure.step("Тело пустое, Content-Type сохранён"):
            assert response.text == ""
            assert response.headers["Content-Type"].startswith("application/json")


@allure.epic("postman-echo.com")
@allure.feature("POST /post")
class TestPostEndpoint:
    @allure.title("POST /post кладёт form-urlencoded тело в поле form")
    @allure.description(
        "Тело application/x-www-form-urlencoded разбирается сервисом в объект form, "
        "при этом data остаётся пустой строкой, а files и args — пустыми объектами."
    )
    @allure.story("Тело запроса")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_post_form_urlencoded(self, session):
        payload = {"login": "user", "password": "secret"}

        response = send(session, "POST", POST_URL, data=payload)

        assert response.status_code == 200
        body = response.json()
        with allure.step("Тело разобрано в form"):
            assert body["form"] == payload
            assert body["headers"]["content-type"] == "application/x-www-form-urlencoded"
        with allure.step("Остальные секции пустые"):
            assert body["data"] == ""
            assert body["files"] == {}
            assert body["args"] == {}

    @allure.title("POST /post возвращает JSON-тело в полях json и data")
    @allure.description(
        "JSON-тело со вложенным объектом и массивом возвращается дважды — в json и в "
        "data — без искажений, а Content-Length совпадает с длиной отправленного тела."
    )
    @allure.story("Тело запроса")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_post_json_body(self, session):
        payload = {"id": 42, "tags": ["qa", "api"], "nested": {"ok": True}}

        response = send(session, "POST", POST_URL, json=payload)

        assert response.status_code == 200
        body = response.json()
        with allure.step("Тело вернулось без искажений в json и data"):
            assert body["json"] == payload
            assert body["data"] == payload
            assert body["form"] == {}
        with allure.step("Заголовки соответствуют отправленному телу"):
            assert body["headers"]["content-type"] == "application/json"
            assert body["headers"]["content-length"] == str(len(response.request.body))

    @allure.title("POST /post кладёт text/plain тело в data строкой")
    @allure.description(
        "Для не-JSON тела сервис возвращает его строкой в data, поле json равно null, "
        "form пустой. Проверяем на кириллице, чтобы поймать проблемы с кодировкой."
    )
    @allure.story("Тело запроса")
    @allure.severity(allure.severity_level.NORMAL)
    def test_post_raw_text_body(self, session):
        text = "просто текст"

        response = send(
            session,
            "POST",
            POST_URL,
            data=text.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

        assert response.status_code == 200
        body = response.json()
        with allure.step("Текст вернулся строкой, json = null"):
            assert body["data"] == text
            assert body["json"] is None
            assert body["form"] == {}

    @allure.title("POST /post разбирает multipart: файл в files, поле в form")
    @allure.description(
        "Загружаем файл report.txt вместе с обычным текстовым полем. Имя файла должно "
        "оказаться в files, поле — в form, а Content-Type запроса — multipart с boundary."
    )
    @allure.story("Загрузка файлов")
    @allure.severity(allure.severity_level.NORMAL)
    def test_post_multipart_file_upload(self, session):
        files = {"report": ("report.txt", b"line1\nline2", "text/plain")}

        response = send(
            session, "POST", POST_URL, files=files, data={"comment": "upload"}
        )

        assert response.status_code == 200
        body = response.json()
        with allure.step("Файл попал в files, поле — в form"):
            assert "report.txt" in body["files"]
            assert body["form"]["comment"] == "upload"
        with allure.step("Content-Type запроса — multipart/form-data с boundary"):
            assert body["headers"]["content-type"].startswith(
                "multipart/form-data; boundary="
            )

    @allure.title("POST /post отражает квери-параметры и тело одновременно")
    @allure.description(
        "Квери-строка и тело обрабатываются независимо: параметры попадают в args, "
        "тело — в json, а url содержит исходную квери-строку."
    )
    @allure.story("Квери-параметры")
    @allure.severity(allure.severity_level.NORMAL)
    def test_post_url_accepts_query_params_too(self, session):
        response = send(
            session, "POST", POST_URL, params={"source": "ci"}, json={"value": 1}
        )

        assert response.status_code == 200
        body = response.json()
        with allure.step("args и json заполнены независимо друг от друга"):
            assert body["args"] == {"source": "ci"}
            assert body["json"] == {"value": 1}
            assert body["url"] == f"{POST_URL}?source=ci"


@allure.epic("postman-echo.com")
@allure.feature("Негативные проверки")
@allure.story("Чужой HTTP-метод")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("{method} {url} возвращает 404")
@allure.description(
    "Каждый эндпоинт эхо-сервиса отвечает только на свой HTTP-метод: /get — на GET и "
    "HEAD, /post — на POST. Любой другой метод должен приводить к 404, а не к 405."
)
@pytest.mark.parametrize(
    "method,url",
    [
        ("POST", GET_URL),
        ("PUT", GET_URL),
        ("DELETE", GET_URL),
        ("GET", POST_URL),
        ("PATCH", POST_URL),
    ],
)
def test_wrong_method_for_endpoint_returns_404(session, method, url):
    response = send(session, method, url)

    with allure.step("Сервис отвечает 404"):
        assert response.status_code == 404
