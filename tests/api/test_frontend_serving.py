from fastapi.testclient import TestClient

from football_platform.api.app import create_app


def test_built_frontend_is_served_with_spa_fallback(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('ok')")
    (tmp_path / "index.html").write_text("<html>app</html>")
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path))
    client = TestClient(create_app("postgresql://unused/unused"))
    assert client.get("/").text == "<html>app</html>"
    assert client.get("/players/x/seasons/y").text == "<html>app</html>"  # client-side route
    assert client.get("/assets/app.js").text == "console.log('ok')"
    assert client.get("/api/unknown-endpoint").status_code == 404  # API paths never fall back to the app
    assert client.get("/api/metrics").status_code == 200  # API routes take precedence


def test_without_frontend_dist_only_the_api_is_served(monkeypatch):
    monkeypatch.delenv("FRONTEND_DIST", raising=False)
    client = TestClient(create_app("postgresql://unused/unused"))
    assert client.get("/").status_code == 404
