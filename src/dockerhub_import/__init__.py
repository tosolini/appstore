import json
import logging
import re
import textwrap
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
import yaml

from src.db.models import GitHubImportedApp
from src.github_import import GitHubAppImporter, GitHubImportError
from src.models import App
from src.parsers import DockerComposeParser


logger = logging.getLogger(__name__)

DOCKERHUB_API_BASE = "https://hub.docker.com/v2/repositories"
DOCKERHUB_URL_BASE = "https://hub.docker.com"
IMPORT_SOURCE_NAME = "Docker Hub Imports"

_FENCED_BLOCK_RE = re.compile(r"```(?:[a-zA-Z0-9_+\-]*\n)?(.*?)```", re.DOTALL)
# NOTE: the image/tag patterns below intentionally avoid `[^>]+` / `[^\]]*`
# style classes: those allow `<` / `[` / `(` inside the match, which makes
# the engine backtrack quadratically on inputs like `<<<<...` or
# `![![![...` (CodeQL py/polynomial-redos). Excluding the delimiter chars
# (`[^<>]`, `[^[\]]`, `[^()\s]`) keeps matching linear while covering
# real-world markdown/HTML images.
_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\[\]]*\]\(([^()\s]+)\)")
_HTML_IMAGE_RE = re.compile(
    r'<img\b[^<>]*?\bsrc\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE
)
_HTML_TAG_RE = re.compile(r"<[^<>]+>")
# Bound how much uncontrolled upstream text (Docker Hub descriptions can be
# arbitrarily large) is fed to the regexes above, as defense-in-depth
# against ReDoS (see CodeQL py/polynomial-redos recommendation).
_MAX_SCAN_CHARS = 50000
_IGNORED_IMAGE_FRAGMENTS = (
    "shields.io",
    "badge",
    "star-history",
    "contrib.rocks",
    "buymeacoffee",
    "bmc-button",
)


class DockerHubImportError(ValueError):
    """Raised when a Docker Hub image cannot be imported."""


class DockerHubAppImporter:
    """Imports Docker Hub repository pages into App objects.

    The importer reads public metadata from the Docker Hub API
    (description, full description, categories) and builds a compose file:
    either reusing a compose snippet embedded in the repository's full
    description (e.g. plant-it documents its 3-service stack there) or
    generating a single-service compose file for the image, with ports
    inferred from the image config ``ExposedPorts``.
    """

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.setdefault("Accept", "application/json")
        self.session.headers.setdefault("User-Agent", "container-appstore-importer")
        authorization = self.session.headers.get("Authorization")
        # Reuse the registry inspection logic (manifest auth, architecture
        # detection) from the GitHub importer on the same session.
        self._gh = GitHubAppImporter(session=self.session)
        if authorization is None:
            self.session.headers.pop("Authorization", None)
        else:
            self.session.headers["Authorization"] = authorization
        self.session.headers["Accept"] = "application/json"

    def import_image(self, image_url: str, tag: str = "latest") -> Tuple[App, Dict[str, Any]]:
        namespace, repo = self.parse_repository_url(image_url)
        canonical_url = self.normalize_repository_url(image_url)
        tag = (tag or "latest").strip() or "latest"

        meta = self._get_repository_metadata(namespace, repo)
        if tag != "latest":
            self._ensure_tag_exists(namespace, repo, tag)

        if namespace == "library":
            image_ref = f"{repo}:{tag}"
        else:
            image_ref = f"{namespace}/{repo}:{tag}"

        full_description = meta.get("full_description") or ""
        short_description = self._short_description(meta, full_description)
        topics = self._topics_from_metadata(meta)
        image_links = self._extract_description_images(full_description)

        repo_meta = {
            "name": meta.get("name") or repo,
            "full_name": f"{namespace}/{repo}",
            "description": short_description,
            "homepage": "",
            "topics": topics,
            "owner": {"login": namespace, "avatar_url": None},
        }
        metadata = GitHubAppImporter._build_metadata(canonical_url, repo_meta, image_links)
        metadata["tags"] = [t for t in metadata["tags"] if t != "github-import"] + ["dockerhub-import"]

        compose_path: Optional[str] = None
        import_strategy = "dockerhub-generated"
        compose_content: Optional[str] = None

        extracted = self._extract_compose_from_description(full_description)
        if extracted is not None:
            try:
                compose_content = GitHubAppImporter._enrich_compose_metadata(extracted, metadata)
                compose_path = "description"
                import_strategy = "dockerhub-description-compose"
            except (GitHubImportError, yaml.YAMLError) as exc:
                logger.info(f"Ignoring embedded compose for {canonical_url}: {exc}")

        if compose_content is None:
            ports = self._get_exposed_ports(image_ref)
            generated = self._build_single_service_compose(
                repo=repo,
                image_ref=image_ref,
                ports=ports,
                metadata=metadata,
            )
            compose_content = GitHubAppImporter._enrich_compose_metadata(generated, metadata)

        app_id = self._build_app_id(namespace, repo)
        app = DockerComposeParser.parse_compose_content(
            compose_content=compose_content,
            app_id=app_id,
            repository_source=IMPORT_SOURCE_NAME,
            source_url=canonical_url,
            homepage=None,
        )
        if not app:
            raise DockerHubImportError("Generated compose file could not be parsed")

        if not app.title:
            app.title = metadata["title"]
        if not app.description:
            app.description = metadata["description"]
        if not app.icon:
            app.icon = metadata["icon"]
        if not app.thumbnail:
            app.thumbnail = metadata["thumbnail"]
        if not app.developer or app.developer == "Unknown":
            app.developer = metadata["developer"]
        if not app.category or app.category == "Other":
            app.category = metadata["category"]
        if not app.screenshot_links:
            app.screenshot_links = metadata["screenshot_links"]
        app.tags = list(dict.fromkeys((app.tags or []) + metadata["tags"]))
        app.source_url = canonical_url
        app.source_type = "compose"
        app.import_debug = {
            "metadata_source": "dockerhub-api",
            "file_listing_source": "dockerhub-api",
            "file_read_source": "dockerhub-api",
            "compose_path": compose_path,
            "dockerfile_path": None,
            "docker_dir_fallback": False,
            "import_strategy": import_strategy,
            "image": image_ref,
            "tag": tag,
        }
        self._gh._populate_architecture_metadata(app)

        return app, {
            "source_url": canonical_url,
            "repo_full_name": f"{namespace}/{repo}",
            "tag": tag,
            "image": image_ref,
            "compose_path": compose_path,
            "dockerfile_path": None,
        }

    @staticmethod
    def parse_repository_url(image_url: str) -> Tuple[str, str]:
        """Parse ``namespace`` and ``repository`` from a Docker Hub page URL.

        Accepts ``https://hub.docker.com/r/{namespace}/{repository}`` and
        official images ``https://hub.docker.com/_/{repository}``
        (mapped to the ``library`` namespace).
        """
        parsed = urlparse(image_url.strip())
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {
            "hub.docker.com",
            "www.hub.docker.com",
        }:
            raise DockerHubImportError("Only Docker Hub URLs are supported (hub.docker.com)")

        parts = [part for part in parsed.path.strip("/").split("/") if part]
        namespace: Optional[str] = None
        repo: Optional[str] = None
        if len(parts) >= 3 and parts[0] == "r":
            namespace, repo = parts[1], parts[2]
        elif len(parts) >= 2 and parts[0] == "_":
            namespace, repo = "library", parts[1]

        if not namespace or not repo:
            raise DockerHubImportError(
                "Invalid Docker Hub URL. Expected https://hub.docker.com/r/{namespace}/{repository}"
            )

        namespace = namespace.lower()
        repo = repo.lower()
        if not re.fullmatch(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", namespace):
            raise DockerHubImportError(f"Invalid Docker Hub namespace: {namespace}")
        if not re.fullmatch(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", repo):
            raise DockerHubImportError(f"Invalid Docker Hub repository: {repo}")

        return namespace, repo

    @staticmethod
    def normalize_repository_url(image_url: str) -> str:
        """Return a canonical Docker Hub repository URL for duplicate detection."""
        namespace, repo = DockerHubAppImporter.parse_repository_url(image_url)
        return f"{DOCKERHUB_URL_BASE}/r/{namespace}/{repo}"

    @staticmethod
    def _build_app_id(namespace: str, repo: str) -> str:
        raw = f"dockerhub-{namespace}-{repo}".lower()
        return re.sub(r"[^a-z0-9-]+", "-", raw).strip("-")

    def _get_repository_metadata(self, namespace: str, repo: str) -> Dict[str, Any]:
        response = self.session.get(f"{DOCKERHUB_API_BASE}/{namespace}/{repo}/", timeout=20)
        if response.status_code == 404:
            raise DockerHubImportError(f"Docker Hub repository not found: {namespace}/{repo}")
        if response.status_code >= 400:
            raise DockerHubImportError(
                f"Docker Hub API request failed with status {response.status_code}"
            )
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise DockerHubImportError("Docker Hub API returned an invalid response") from exc
        if not isinstance(data, dict):
            raise DockerHubImportError("Docker Hub API returned an invalid response")
        return data

    def _ensure_tag_exists(self, namespace: str, repo: str, tag: str) -> None:
        response = self.session.get(f"{DOCKERHUB_API_BASE}/{namespace}/{repo}/tags/{tag}/", timeout=20)
        if response.status_code == 404:
            raise DockerHubImportError(f"Tag '{tag}' not found for {namespace}/{repo}")
        if response.status_code >= 400:
            raise DockerHubImportError(
                f"Docker Hub tag lookup failed with status {response.status_code}"
            )

    @staticmethod
    def _topics_from_metadata(meta: Dict[str, Any]) -> List[str]:
        topics: List[str] = []
        for category in meta.get("categories") or []:
            if not isinstance(category, dict):
                continue
            for candidate in (category.get("slug"), category.get("name")):
                if not candidate:
                    continue
                slug = re.sub(r"[^a-z0-9]+", "-", str(candidate).lower()).strip("-")
                if slug and slug not in topics:
                    topics.append(slug)
        return topics

    @staticmethod
    def _short_description(meta: Dict[str, Any], full_description: str) -> str:
        short = (meta.get("description") or "").strip()
        if short:
            return short
        # Truncate uncontrolled upstream text before regex matching
        # (ReDoS defense-in-depth; see py/polynomial-redos).
        text = (full_description or "")[:_MAX_SCAN_CHARS]
        for line in text.splitlines():
            # Bound individual line length as well; a single very long
            # line without newlines would otherwise still be expensive.
            cleaned = _HTML_TAG_RE.sub("", line[:5000]).strip().lstrip("#*>- ").strip()
            if len(cleaned) >= 20:
                return cleaned[:300]
        name = meta.get("name") or "Docker Hub image"
        return f"{name} (imported from Docker Hub)"

    @classmethod
    def _extract_description_images(cls, full_description: str) -> List[str]:
        if not full_description:
            return []
        # Truncate uncontrolled upstream text before regex matching
        # (ReDoS defense-in-depth; see py/polynomial-redos).
        text = full_description[:_MAX_SCAN_CHARS]
        candidates: List[str] = []
        for image_url in _MARKDOWN_IMAGE_RE.findall(text) + _HTML_IMAGE_RE.findall(text):
            cleaned = image_url.strip().strip("<>").strip()
            parsed = urlparse(cleaned)
            if parsed.scheme not in {"http", "https"}:
                continue
            lowered = cleaned.lower()
            if any(fragment in lowered for fragment in _IGNORED_IMAGE_FRAGMENTS):
                continue
            candidates.append(cleaned)
        candidates = list(dict.fromkeys(candidates))

        def score(url: str) -> Tuple[int, str]:
            lowered = url.lower()
            bonus = 0
            if "logo" in lowered or "icon" in lowered:
                bonus -= 10
            if lowered.endswith(".svg"):
                bonus -= 2
            return (bonus, url)

        return [url for _, url in sorted(((score(url), url) for url in candidates))][:8]

    @staticmethod
    def _extract_compose_from_description(full_description: str) -> Optional[str]:
        """Return the first fenced code block that parses as a compose file."""
        if not full_description:
            return None
        # Truncate uncontrolled upstream text before regex matching
        # (ReDoS defense-in-depth; see py/polynomial-redos).
        text = full_description[:_MAX_SCAN_CHARS]
        for match in _FENCED_BLOCK_RE.finditer(text):
            # Dedent before stripping: fenced blocks nested in markdown list
            # items share a common indent that strip() alone would break on
            # the first line only.
            block = textwrap.dedent(match.group(1)).strip()
            if "services:" not in block:
                continue
            try:
                parsed = yaml.safe_load(block)
            except yaml.YAMLError:
                continue
            if (
                isinstance(parsed, dict)
                and isinstance(parsed.get("services"), dict)
                and parsed["services"]
            ):
                return block
        return None

    @staticmethod
    def _build_single_service_compose(
        repo: str,
        image_ref: str,
        ports: List[str],
        metadata: Dict[str, Any],
    ) -> str:
        service_name = re.sub(r"[^a-z0-9-]+", "-", repo.lower()).strip("-") or "app"
        service: Dict[str, Any] = {
            "image": image_ref,
            "container_name": service_name,
            "restart": "unless-stopped",
        }
        if ports:
            service["ports"] = [f"{port}:{port}" for port in ports]
        compose: Dict[str, Any] = {
            "services": {service_name: service},
            "x-casaos": {
                "main": service_name,
                "title": metadata["title"],
                "description": metadata["description"],
                "developer": metadata["developer"],
                "category": metadata["category"],
                "icon": metadata["icon"],
                "thumbnail": metadata["thumbnail"],
                "port_map": ports[0] if ports else "80",
                "index": "/",
                "architectures": ["amd64"],
                "tags": metadata["tags"],
                "source_url": metadata["source_url"],
            },
        }
        if metadata.get("screenshot_links"):
            compose["x-casaos"]["screenshot_link"] = metadata["screenshot_links"]
        return yaml.safe_dump(compose, sort_keys=False, allow_unicode=False)

    def _get_exposed_ports(self, image_reference: str) -> List[str]:
        """Infer container ports from the image config ``ExposedPorts``."""
        try:
            registry, repository, reference = GitHubAppImporter._parse_image_reference(
                image_reference
            )
            manifest = self._gh._fetch_registry_manifest(registry, repository, reference)
            config_digest = self._manifest_config_digest(
                manifest, registry, repository, reference
            )
            if not config_digest:
                return []
            blob = self._fetch_registry_blob(registry, repository, config_digest)
            exposed = ((blob.get("config") or {}).get("ExposedPorts")) or {}
            ports = []
            for key in exposed:
                port = str(key).split("/")[0].strip()
                if port.isdigit():
                    ports.append(port)
            return list(dict.fromkeys(ports))
        except Exception as exc:
            logger.info(f"Could not detect exposed ports for image {image_reference}: {exc}")
            return []

    def _manifest_config_digest(
        self,
        manifest: Dict[str, Any],
        registry: str,
        repository: str,
        reference: str,
    ) -> Optional[str]:
        config = manifest.get("config")
        if isinstance(config, dict) and config.get("digest"):
            return config["digest"]
        entries = manifest.get("manifests")
        if not isinstance(entries, list) or not entries:
            return None

        def rank(entry: Dict[str, Any]) -> Tuple[int, int, str]:
            platform = entry.get("platform", {}) if isinstance(entry, dict) else {}
            arch = GitHubAppImporter.normalize_architecture(
                platform.get("architecture"), platform.get("variant")
            )
            os_name = (platform.get("os") or "").lower()
            arch_rank = {"amd64": 0, "arm64": 1}.get(arch or "", 2)
            os_rank = 0 if os_name in {"linux", ""} else 1
            return (os_rank, arch_rank, str(entry.get("digest") or ""))

        ranked = sorted([e for e in entries if isinstance(e, dict)], key=rank)
        if not ranked or not ranked[0].get("digest"):
            return None
        sub_manifest = self._gh._fetch_registry_manifest(
            registry, repository, ranked[0]["digest"]
        )
        sub_config = sub_manifest.get("config")
        if isinstance(sub_config, dict) and sub_config.get("digest"):
            return sub_config["digest"]
        return None

    def _fetch_registry_blob(
        self, registry: str, repository: str, digest: str
    ) -> Dict[str, Any]:
        url = f"https://{registry}/v2/{repository}/blobs/{digest}"
        response = self.session.get(url, timeout=30)
        if response.status_code == 401:
            token = self._gh._registry_bearer_token(
                response.headers.get("WWW-Authenticate", "")
            )
            if not token:
                raise DockerHubImportError(
                    f"Unauthorized to inspect image config for {repository}"
                )
            response = self.session.get(
                url, headers={"Authorization": f"Bearer {token}"}, timeout=30
            )
        if response.status_code >= 400:
            raise DockerHubImportError(f"Image config lookup failed for {repository}")
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise DockerHubImportError("Image config response was not valid JSON") from exc
        if not isinstance(data, dict):
            raise DockerHubImportError("Image config response was not valid JSON")
        return data


def load_persisted_dockerhub_apps(db) -> List[GitHubImportedApp]:
    """Persisted imports whose source URL is a Docker Hub page."""
    records = (
        db.query(GitHubImportedApp)
        .filter(GitHubImportedApp.enabled == True)
        .order_by(GitHubImportedApp.updated_at.desc())
        .all()
    )
    hub_records = []
    for record in records:
        try:
            DockerHubAppImporter.normalize_repository_url(record.source_url)
        except DockerHubImportError:
            continue
        hub_records.append(record)
    return hub_records
