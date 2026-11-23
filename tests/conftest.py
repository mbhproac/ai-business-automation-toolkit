import pytest

from ai_business_automation.config import Settings


@pytest.fixture
def settings(tmp_path):
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "lead_intake.json").write_text(
        '{"id":"lead_intake","actions":[{"type":"record","name":"a","message":"Hello ${company}"}]}',
        encoding="utf-8",
    )
    return Settings(api_key="a" * 48, database_path=tmp_path / "jobs.sqlite3",
                    workflows_dir=workflow_dir)
