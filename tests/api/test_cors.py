from fastapi.testclient import TestClient


def test_cors_allowed_origin(client: TestClient) -> None:
    # Default ALLOWED_ORIGINS in main.py is http://localhost:3000 if not set in env
    # But conftest.py might have already loaded the app.
    # Let's see what happens.
    response = client.options(
        '/api/v1/health',
        headers={
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'GET',
        },
    )
    assert response.status_code == 200
    assert (
        response.headers.get('access-control-allow-origin') == 'http://localhost:3000'
    )


def test_cors_disallowed_origin(client: TestClient) -> None:
    response = client.options(
        '/api/v1/health',
        headers={
            'Origin': 'http://malicious.com',
            'Access-Control-Request-Method': 'GET',
        },
    )
    # FastAPI CORSMiddleware returns 400 for disallowed origins in preflight requests
    assert response.status_code == 400
    assert 'access-control-allow-origin' not in response.headers
