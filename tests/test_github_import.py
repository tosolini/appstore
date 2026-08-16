from src.github_import import GitHubAppImporter, GitHubImportError


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
