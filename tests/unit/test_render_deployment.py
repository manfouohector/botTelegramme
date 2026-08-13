"""Tests — configuration déploiement Render."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


class TestRenderDeployment:
    def test_render_yaml_exists_and_valid(self):
        path = ROOT / "render.yaml"
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "football-bot-web" in content
        assert "football-bot-scheduler" in content
        assert "healthCheckPath: /health" in content
        assert "run_migrations.py" in content
        assert "type: web" in content
        assert "type: worker" in content

    def test_runtime_txt(self):
        runtime = (ROOT / "runtime.txt").read_text(encoding="utf-8").strip()
        assert runtime.startswith("python-3.12")

    def test_deploy_scripts_exist(self):
        assert (ROOT / "scripts" / "run_web.py").exists()
        assert (ROOT / "scripts" / "run_scheduler.py").exists()
        assert (ROOT / "scripts" / "run_migrations.py").exists()

    def test_web_app_module(self):
        from app.api.web_app import app

        assert app.title == "Football Prediction Bot"
