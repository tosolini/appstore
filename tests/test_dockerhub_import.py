import pytest

from src.dockerhub_import import DockerHubAppImporter, DockerHubImportError


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None):
        self.status_code = status_code
        self._json_data = json_data
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


PLANT_IT_DESCRIPTION = """<p align="center">Plant-it gardening companion app.</p>

## Quickstart

```
version: "3"
name: plant-it
services:
  server:
    image: msdeluise/plant-it-server:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "3000:3000"
  db:
    image: mysql:8.0
    restart: always
  cache:
    image: redis:7.2.1
    restart: always
```
"""


def _hub_meta(**overrides):
    meta = {
        "name": "plant-it-server",
        "description": "Self-hosted, open source gardening companion app",
        "full_description": PLANT_IT_DESCRIPTION,
        "star_count": 1,
        "pull_count": 330166,
        "categories": [{"name": "Web servers", "slug": "web-servers"}],
    }
    meta.update(overrides)
    return meta


def test_parse_repository_url_accepts_r_and_official_urls():
    assert DockerHubAppImporter.parse_repository_url(
        "https://hub.docker.com/r/msdeluise/plant-it-server"
    ) == ("msdeluise", "plant-it-server")
    assert DockerHubAppImporter.parse_repository_url(
        "https://hub.docker.com/_/nginx"
    ) == ("library", "nginx")
    assert DockerHubAppImporter.parse_repository_url(
        "https://www.hub.docker.com/r/MsDeluise/Plant-It-Server/"
    ) == ("msdeluise", "plant-it-server")


def test_parse_repository_url_rejects_non_hub_urls():
    with pytest.raises(DockerHubImportError):
        DockerHubAppImporter.parse_repository_url("https://github.com/owner/repo")
    with pytest.raises(DockerHubImportError):
        DockerHubAppImporter.parse_repository_url("https://hub.docker.com/r/only-namespace")
    with pytest.raises(DockerHubImportError):
        DockerHubAppImporter.parse_repository_url("not a url")


def test_normalize_repository_url_treats_variants_as_equivalent():
    canonical = "https://hub.docker.com/r/msdeluise/plant-it-server"
    for variant in [
        "https://hub.docker.com/r/msdeluise/plant-it-server",
        "https://hub.docker.com/r/msdeluise/plant-it-server/",
        "https://hub.docker.com/r/MsDeluise/Plant-It-Server",
        "https://www.hub.docker.com/r/msdeluise/plant-it-server",
    ]:
        assert DockerHubAppImporter.normalize_repository_url(variant) == canonical


def test_import_image_reuses_compose_from_description():
    url = "https://hub.docker.com/r/msdeluise/plant-it-server"
    session = FakeSession(
        {
            "https://hub.docker.com/v2/repositories/msdeluise/plant-it-server/": FakeResponse(
                json_data=_hub_meta()
            ),
        }
    )

    importer = DockerHubAppImporter(session=session)
    app, source = importer.import_image(url)

    assert app.app_id == "dockerhub-msdeluise-plant-it-server"
    assert app.title == "plant-it-server"
    assert app.description == "Self-hosted, open source gardening companion app"
    assert app.developer == "msdeluise"
    assert set(app.services) == {"server", "db", "cache"}
    assert app.port_map == "8080"
    assert app.source_url == url
    assert "dockerhub-import" in app.tags
    assert "github-import" not in app.tags
    assert app.source_type == "compose"
    assert app.import_debug["import_strategy"] == "dockerhub-description-compose"
    assert app.import_debug["image"] == "msdeluise/plant-it-server:latest"
    assert source["repo_full_name"] == "msdeluise/plant-it-server"
    assert source["compose_path"] == "description"


def test_import_image_generates_single_service_with_exposed_ports():
    url = "https://hub.docker.com/r/example/single"
    session = FakeSession(
        {
            "https://hub.docker.com/v2/repositories/example/single/": FakeResponse(
                json_data=_hub_meta(
                    name="single",
                    description="Single service demo",
                    full_description="Just a demo without compose docs.",
                    categories=[],
                )
            ),
            "https://registry-1.docker.io/v2/example/single/manifests/latest": FakeResponse(
                json_data={
                    "manifests": [
                        {
                            "digest": "sha256:arm64digest",
                            "platform": {"architecture": "arm64", "os": "linux"},
                        },
                        {
                            "digest": "sha256:amd64digest",
                            "platform": {"architecture": "amd64", "os": "linux"},
                        },
                    ]
                }
            ),
            "https://registry-1.docker.io/v2/example/single/manifests/sha256:amd64digest": FakeResponse(
                json_data={"config": {"digest": "sha256:configdigest"}}
            ),
            "https://registry-1.docker.io/v2/example/single/blobs/sha256:configdigest": FakeResponse(
                json_data={"config": {"ExposedPorts": {"8080/tcp": {}}}}
            ),
        }
    )

    importer = DockerHubAppImporter(session=session)
    app, source = importer.import_image(url)

    assert app.app_id == "dockerhub-example-single"
    assert set(app.services) == {"single"}
    assert app.services["single"].image == "example/single:latest"
    assert app.port_map == "8080"
    assert app.import_debug["import_strategy"] == "dockerhub-generated"
    assert app.import_debug["compose_path"] is None
    assert source["image"] == "example/single:latest"


def test_extract_compose_handles_list_indented_fences():
    # Fenced blocks nested in markdown list items share a 2-space indent;
    # naive strip() breaks the first line's indentation and YAML parsing.
    description = (
        "* Inside that folder, create `docker-compose.yml` with this content:\n"
        "  ```\n"
        '  version: "3"\n'
        "  name: plant-it\n"
        "  services:\n"
        "    server:\n"
        "      image: msdeluise/plant-it-server:latest\n"
        "      ports:\n"
        '        - "8080:8080"\n'
        "  ```\n"
    )
    extracted = DockerHubAppImporter._extract_compose_from_description(description)
    assert extracted is not None
    assert "server:" in extracted

    url = "https://hub.docker.com/r/msdeluise/plant-it-server"
    session = FakeSession(
        {
            "https://hub.docker.com/v2/repositories/msdeluise/plant-it-server/": FakeResponse(
                json_data=_hub_meta(full_description=description)
            ),
        }
    )
    importer = DockerHubAppImporter(session=session)
    app, _ = importer.import_image(url)
    assert app.import_debug["import_strategy"] == "dockerhub-description-compose"
    assert set(app.services) == {"server"}


def test_import_image_raises_for_missing_repo_and_tag():
    session = FakeSession(
        {
            "https://hub.docker.com/v2/repositories/example/missing/": FakeResponse(
                status_code=404, json_data={"detail": "not found"}
            ),
        }
    )
    importer = DockerHubAppImporter(session=session)
    with pytest.raises(DockerHubImportError):
        importer.import_image("https://hub.docker.com/r/example/missing")

    session = FakeSession(
        {
            "https://hub.docker.com/v2/repositories/example/single/": FakeResponse(
                json_data=_hub_meta(name="single", full_description="")
            ),
            "https://hub.docker.com/v2/repositories/example/single/tags/nonexistent/": FakeResponse(
                status_code=404, json_data={"detail": "not found"}
            ),
        }
    )
    importer = DockerHubAppImporter(session=session)
    with pytest.raises(DockerHubImportError):
        importer.import_image("https://hub.docker.com/r/example/single", tag="nonexistent")


def test_import_image_falls_back_to_generated_when_description_compose_invalid():
    url = "https://hub.docker.com/r/example/broken"
    session = FakeSession(
        {
            "https://hub.docker.com/v2/repositories/example/broken/": FakeResponse(
                json_data=_hub_meta(
                    name="broken",
                    description="Broken compose demo",
                    # Mentions services: but is not valid YAML mapping.
                    full_description="```\nservices: [unclosed\n```\n",
                    categories=[],
                )
            ),
            "https://registry-1.docker.io/v2/example/broken/manifests/latest": FakeResponse(
                json_data={"config": {"digest": "sha256:configdigest"}}
            ),
            "https://registry-1.docker.io/v2/example/broken/blobs/sha256:configdigest": FakeResponse(
                json_data={"config": {"ExposedPorts": {"3000/tcp": {}}}}
            ),
        }
    )

    importer = DockerHubAppImporter(session=session)
    app, _ = importer.import_image(url)

    assert app.import_debug["import_strategy"] == "dockerhub-generated"
    assert app.port_map == "3000"
