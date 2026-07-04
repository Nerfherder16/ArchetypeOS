from app.main import app


def test_app_has_health_route():
    routes = {route.path for route in app.routes}
    assert "/health" in routes
