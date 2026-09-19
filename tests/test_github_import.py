import asyncio
import json
from io import BytesIO

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import UploadFile

from src.db.models import Base, GitHubImportedApp
from src.github_import import GitHubAppImporter, GitHubImportError, serialize_imported_app
from src.git_sync import GitSync
from src.models import App


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.headers = headers or {}

    def json(self):
        return self._json_data


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.headers = {}

    def get(self, url, **kwargs):
        params = kwargs.get("params")
        if params:
            query = "&".join(f"{key}={value}" for key, value in sorted(params.items()))
            lookup = f"{url}?{query}"
        else:
            lookup = url
        if lookup not in self.responses:
            raise AssertionError(f"Unexpected URL requested: {lookup}")
        return self.responses[lookup]


def test_parse_repository_url_accepts_git_suffix():
    owner, repo = GitHubAppImporter.parse_repository_url("https://github.com/example/demo.git")
    assert owner == "example"
    assert repo == "demo"


def test_parse_repository_url_rejects_non_github_and_invalid_urls():
    with pytest.raises(GitHubImportError):
        GitHubAppImporter.parse_repository_url("https://gitlab.com/owner/repo")
    with pytest.raises(GitHubImportError):
        GitHubAppImporter.parse_repository_url("https://github.com/onlyowner")


def test_normalize_repository_url_treats_url_variants_as_equivalent():
    variants = [
        "https://github.com/UnslothAI/Unsloth",
        "https://github.com/unslothai/unsloth.git",
        "https://github.com/unslothai/unsloth/",
        "https://github.com/unslothai/unsloth.git/",
        "https://github.com/unslothai/unsloth#readme",
        "https://github.com/unslothai/unsloth/tree/main",
        "https://github.com/unslothai/unsloth.git/",
    ]
    canonical = "https://github.com/unslothai/unsloth"
    for variant in variants:
        assert GitHubAppImporter.normalize_repository_url(variant) == canonical
    assert GitHubAppImporter.normalize_repository_url("https://github.com/unslothai/unsloth") == canonical


def test_select_compose_path_prefers_root_over_docs_and_tests():
    path = GitHubAppImporter._select_compose_path(
        [
            "docs/docker-compose.yml",
            "tests/docker-compose.yml",
            "docker-compose.yml",
            "docker/dev/docker-compose.yaml",
        ]
    )
    assert path == "docker-compose.yml"


def test_select_compose_path_accepts_nonstandard_compose_names():
    path = GitHubAppImporter._select_compose_path(
        [
            "deploy/stack.yaml",
            "docker-compose.dev.yaml",
            "docs/docker-compose.example.yaml",
        ]
    )
    assert path == "docker-compose.dev.yaml"


def test_select_compose_path_ignores_ci_workflows_and_substring_names():
    assert GitHubAppImporter._is_compose_candidate(".github/workflows/studio-composer-compatibility.yml") is False
    assert GitHubAppImporter._is_compose_candidate(".github/workflows/docker-build.yml") is False
    assert GitHubAppImporter._is_compose_candidate("studio/composer-settings.yml") is False

    path = GitHubAppImporter._select_compose_path(
        [
            "docker/Dockerfile",
            ".github/workflows/studio-composer-compatibility.yml",
            ".github/workflows/docker-build.yml",
        ]
    )
    assert path is None


def test_select_compose_path_falls_back_to_dockerfile_for_docker_only_repos():
    path = GitHubAppImporter._select_compose_path(["docker/Dockerfile"])
    assert path is None
    dockerfile_path = GitHubAppImporter._select_dockerfile_path(["docker/Dockerfile"])
    assert dockerfile_path == "docker/Dockerfile"


def test_normalize_asset_url_handles_relative_and_blob_urls():
    relative = GitHubAppImporter._normalize_asset_url(
        "./assets/app.png",
        "owner",
        "repo",
        "main",
        "docs",
    )
    blob = GitHubAppImporter._normalize_asset_url(
        "https://github.com/owner/repo/blob/main/assets/app.png",
        "owner",
        "repo",
        "main",
        "",
    )
    backslash_path = GitHubAppImporter._normalize_asset_url(
        r".\frontend\public\logo.svg",
        "owner",
        "repo",
        "main",
        "",
    )

    assert relative == "https://raw.githubusercontent.com/owner/repo/main/docs/assets/app.png"
    assert blob == "https://raw.githubusercontent.com/owner/repo/main/assets/app.png"
    assert backslash_path == "https://raw.githubusercontent.com/owner/repo/main/frontend/public/logo.svg"


def test_import_repository_builds_app_from_compose_and_detects_architecture():
    repo_url = "https://github.com/example/demo-app"
    session = FakeSession(
        {
            "https://api.github.com/repos/example/demo-app": FakeResponse(
                json_data={
                    "name": "demo-app",
                    "full_name": "example/demo-app",
                    "default_branch": "main",
                    "description": "Self-hosted demo application",
                    "homepage": "https://demo.example.com",
                    "topics": ["self-hosted", "monitoring"],
                    "owner": {"login": "example", "avatar_url": "https://avatars.example.com/u/1"},
                }
            ),
            "https://api.github.com/repos/example/demo-app/git/trees/main?recursive=1": FakeResponse(
                json_data={
                    "tree": [
                        {"type": "blob", "path": "README.md"},
                        {"type": "blob", "path": "docker-compose.yml"},
                        {"type": "blob", "path": "assets/logo.svg"},
                    ]
                }
            ),
            "https://raw.githubusercontent.com/example/demo-app/main/README.md": FakeResponse(
                text="# Demo\n\n![Screenshot](./docs/demo.png)\n"
            ),
            "https://raw.githubusercontent.com/example/demo-app/main/docker-compose.yml": FakeResponse(
                text=(
                    "services:\n"
                    "  app:\n"
                    "    image: ghcr.io/example/demo-app:latest\n"
                    "    ports:\n"
                    "      - \"8080:8080\"\n"
                )
            ),
            "https://ghcr.io/v2/example/demo-app/manifests/latest": FakeResponse(
                json_data={
                    "manifests": [
                        {"platform": {"architecture": "amd64", "os": "linux"}},
                        {"platform": {"architecture": "arm64", "os": "linux"}},
                    ]
                }
            ),
        }
    )

    importer = GitHubAppImporter(session=session)
    app, source = importer.import_repository(repo_url)

    assert app.app_id == "github-example-demo-app"
    assert app.title == "demo-app"
    assert app.description == "Self-hosted demo application"
    assert app.category == "Monitoring"
    assert app.port_map == "8080"
    assert app.source_url == repo_url
    assert app.homepage == "https://demo.example.com"
    assert app.icon == "https://raw.githubusercontent.com/example/demo-app/main/assets/logo.svg"
    assert "github-import" in app.tags
    assert app.source_type == "compose"
    assert app.architectures == ["amd64", "arm64"]
    assert app.compatibility_status in {"compatible", "warning"}
    assert app.services["app"].architectures == ["amd64", "arm64"]
    assert source["compose_path"] == "docker-compose.yml"


def test_import_repository_marks_missing_host_architecture():
    repo_url = "https://github.com/example/amd64-only"
    session = FakeSession(
        {
            "https://api.github.com/repos/example/amd64-only": FakeResponse(
                json_data={
                    "name": "amd64-only",
                    "full_name": "example/amd64-only",
                    "default_branch": "main",
                    "description": "AMD64 only demo",
                    "homepage": "",
                    "topics": ["self-hosted"],
                    "owner": {"login": "example", "avatar_url": "https://avatars.example.com/u/1"},
                }
            ),
            "https://api.github.com/repos/example/amd64-only/git/trees/main?recursive=1": FakeResponse(
                json_data={
                    "tree": [
                        {"type": "blob", "path": "docker-compose.yml"},
                    ]
                }
            ),
            "https://raw.githubusercontent.com/example/amd64-only/main/docker-compose.yml": FakeResponse(
                text=(
                    "services:\n"
                    "  app:\n"
                    "    image: ghcr.io/example/amd64-only:latest\n"
                )
            ),
            "https://ghcr.io/v2/example/amd64-only/manifests/latest": FakeResponse(
                json_data={
                    "manifests": [
                        {"platform": {"architecture": "amd64", "os": "linux"}},
                    ]
                }
            ),
        }
    )

    importer = GitHubAppImporter(session=session)
    app, _ = importer.import_repository(repo_url)

    if app.host_architecture == "amd64":
        assert app.compatibility_status == "compatible"
    else:
        assert app.compatibility_status == "warning"
        assert app.compatibility_warning is not None
        assert app.unsupported_services == ["app"]


def test_import_repository_requires_docker_assets():
    repo_url = "https://github.com/example/no-docker"
    session = FakeSession(
        {
            "https://api.github.com/repos/example/no-docker": FakeResponse(
                json_data={
                    "name": "no-docker",
                    "full_name": "example/no-docker",
                    "default_branch": "main",
                    "description": "Missing compose and Dockerfile",
                    "homepage": "",
                    "topics": [],
                    "owner": {"login": "example", "avatar_url": "https://avatars.example.com/u/1"},
                }
            ),
            "https://api.github.com/repos/example/no-docker/git/trees/main?recursive=1": FakeResponse(
                json_data={"tree": [{"type": "blob", "path": "README.md"}]}
            ),
            "https://raw.githubusercontent.com/example/no-docker/main/README.md": FakeResponse(text="# README"),
        }
    )

    importer = GitHubAppImporter(session=session)

    try:
        importer.import_repository(repo_url)
    except GitHubImportError as exc:
        assert str(exc) == "No docker-compose file or Dockerfile found"
    else:
        raise AssertionError("Expected GitHubImportError")


def _make_test_app(app_id="github-unslothai-unsloth", title="unsloth"):
    return App(
        app_id=app_id,
        title=title,
        description="Unsloth",
        developer="unslothai",
        category="Utilities",
        main_service="unsloth",
        repository_source="GitHub Imports",
        source_url="https://github.com/unslothai/unsloth",
        compose_content="services:\n  unsloth:\n    image: unsloth/unsloth\n",
        services={},
    )


def test_export_full_and_restore_roundtrip(tmp_path, monkeypatch):
    import src.main as main

    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    session.add(
        GitHubImportedApp(
            source_url="https://github.com/unslothai/unsloth",
            repo_full_name="unslothai/unsloth",
            app_id="github-unslothai-unsloth",
            payload_json=serialize_imported_app(_make_test_app()),
            enabled=True,
        )
    )
    session.commit()

    monkeypatch.setattr(main, "git_sync", GitSync(str(tmp_path / "cache")))

    resp = asyncio.run(main.export_github_imports(format="full", db=session))
    data = json.loads(resp.body)
    assert data["format"] == "container-appstore-imports-v1"
    assert data["count"] == 1
    assert data["imports"][0]["source_url"] == "https://github.com/unslothai/unsloth"
    assert data["imports"][0]["app"]["title"] == "unsloth"

    session.query(GitHubImportedApp).delete()
    session.commit()

    upload = UploadFile(file=BytesIO(json.dumps(data).encode("utf-8")), filename="backup.json")
    result = asyncio.run(main.restore_github_imports(file=upload, db=session))
    assert result["restored"] == 1
    assert result["skipped"] == 0

    restored = session.query(GitHubImportedApp).first()
    assert restored.app_id == "github-unslothai-unsloth"
    assert restored.source_url == "https://github.com/unslothai/unsloth"
    assert restored.enabled is True

    assert "github-unslothai-unsloth" in main.git_sync.imported_apps
    session.close()


def test_restore_updates_existing_record_by_canonical_url(tmp_path, monkeypatch):
    import src.main as main

    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Pre-existing record stored with a raw variant of the URL
    session.add(
        GitHubImportedApp(
            source_url="https://github.com/unslothai/unsloth.git",
            repo_full_name="unslothai/unsloth",
            app_id="github-unslothai-unsloth",
            payload_json=serialize_imported_app(_make_test_app(title="old-title")),
            enabled=True,
        )
    )
    session.commit()

    monkeypatch.setattr(main, "git_sync", GitSync(str(tmp_path / "cache")))

    backup = {
        "format": "container-appstore-imports-v1",
        "generated_at": "2026-09-19T00:00:00",
        "count": 1,
        "imports": [
            {
                "source_url": "https://github.com/unslothai/unsloth",
                "repo_full_name": "unslothai/unsloth",
                "app_id": "github-unslothai-unsloth",
                "enabled": True,
                "last_imported_at": "2026-09-19T12:00:00",
                "app": _make_test_app(title="new-title").model_dump(),
            }
        ],
    }
    upload = UploadFile(file=BytesIO(json.dumps(backup).encode("utf-8")), filename="backup.json")
    result = asyncio.run(main.restore_github_imports(file=upload, db=session))
    assert result["restored"] == 0
    assert result["updated"] == 1

    restored = session.query(GitHubImportedApp).first()
    assert restored.source_url == "https://github.com/unslothai/unsloth"
    app = App.model_validate(json.loads(restored.payload_json))
    assert app.title == "new-title"
    session.close()
