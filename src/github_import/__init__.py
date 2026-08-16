import json
import logging
import platform
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import requests
import yaml

from src.db.models import GitHubImportedApp
from src.models import App
from src.parsers import DockerComposeParser


logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
RAW_GITHUB_BASE = "https://raw.githubusercontent.com"
IMPORT_SOURCE_NAME = "GitHub Imports"


class GitHubImportError(ValueError):
    """Raised when a repository cannot be imported."""


class GitHubAppImporter:
    """Imports GitHub repositories into App objects."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self._manifest_cache: Dict[str, List[str]] = {}
        token = self.session.headers.get("Authorization")
        if not token:
            import os

            github_token = os.getenv("GITHUB_TOKEN")
            if github_token:
                self.session.headers["Authorization"] = "Bearer " + github_token
        self.session.headers.setdefault("Accept", "application/vnd.github+json")
        self.session.headers.setdefault("User-Agent", "container-appstore-importer")

    def import_repository(self, repository_url: str) -> Tuple[App, Dict[str, Any]]:
        owner, repo = self.parse_repository_url(repository_url)
        repo_meta, metadata_source = self._get_repo_metadata_with_fallback(repository_url, owner, repo)
        default_branch = repo_meta["default_branch"]
        file_listing_source = "github-api"
        file_read_source = "raw-github"

        checkout_dir = None
        try:
            try:
                tree = self._get_json(f"/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1")
                file_paths = [
                    item["path"]
                    for item in tree.get("tree", [])
                    if item.get("type") == "blob" and isinstance(item.get("path"), str)
                ]

                def read_file(path: str) -> str:
                    return self._fetch_raw_file(owner, repo, default_branch, path)

            except GitHubImportError:
                checkout_dir = self._clone_repository_snapshot(repository_url, default_branch)
                file_paths = self._list_repository_files(checkout_dir)
                file_listing_source = "git-fallback"
                file_read_source = "git-fallback"

                def read_file(path: str) -> str:
                    return (checkout_dir / path).read_text(encoding="utf-8")

            compose_path = self._select_compose_path(file_paths)
            dockerfile_path = self._select_dockerfile_path(file_paths) if not compose_path else None
            readme_path = self._select_readme_path(file_paths)

            if not compose_path and not dockerfile_path:
                raise GitHubImportError("No docker-compose file or Dockerfile found")

            readme_content = read_file(readme_path) if readme_path else ""
            readme_images = self._extract_readme_images(readme_content, owner, repo, default_branch, readme_path)
            tree_images = self._extract_tree_images(file_paths, owner, repo, default_branch)
            image_links = self._merge_image_candidates(readme_images, tree_images)

            metadata = self._build_metadata(repository_url, repo_meta, image_links)

            if compose_path:
                compose_content = read_file(compose_path)
                compose_content = self._enrich_compose_metadata(compose_content, metadata)
            else:
                dockerfile_content = read_file(dockerfile_path)
                compose_content = self._build_compose_from_dockerfile(
                    repo_meta=repo_meta,
                    repository_url=repository_url,
                    dockerfile_path=dockerfile_path,
                    dockerfile_content=dockerfile_content,
                    metadata=metadata,
                )

            app_id = self._build_app_id(owner, repo)
            app = DockerComposeParser.parse_compose_content(
                compose_content=compose_content,
                app_id=app_id,
                repository_source=IMPORT_SOURCE_NAME,
                source_url=repository_url,
                homepage=repo_meta.get("homepage") or None,
            )
            if not app:
                raise GitHubImportError("Generated compose file could not be parsed")

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
            app.source_url = repository_url
            app.homepage = repo_meta.get("homepage") or None
            app.source_type = "dockerfile" if dockerfile_path and not compose_path else "compose"
            app.import_debug = {
                "metadata_source": metadata_source,
                "file_listing_source": file_listing_source,
                "file_read_source": file_read_source,
                "compose_path": compose_path,
                "dockerfile_path": dockerfile_path,
                "import_strategy": (
                    "dockerfile-fallback" if dockerfile_path and not compose_path
                    else ("git-fallback" if file_listing_source == "git-fallback" else "github-api")
                ),
            }
            self._populate_architecture_metadata(app)

            return app, {
                "source_url": repository_url,
                "repo_full_name": repo_meta["full_name"],
                "default_branch": default_branch,
                "compose_path": compose_path,
                "dockerfile_path": dockerfile_path,
            }
        finally:
            if checkout_dir:
                shutil.rmtree(checkout_dir, ignore_errors=True)

    @staticmethod
    def parse_repository_url(repository_url: str) -> Tuple[str, str]:
        parsed = urlparse(repository_url.strip())
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
            raise GitHubImportError("Only GitHub repository URLs are supported")

        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) < 2:
            raise GitHubImportError("Invalid GitHub repository URL")

        owner = parts[0]
        repo = parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]

        return owner, repo

    @staticmethod
    def _build_app_id(owner: str, repo: str) -> str:
        raw = f"github-{owner}-{repo}".lower()
        return re.sub(r"[^a-z0-9-]+", "-", raw).strip("-")

    @staticmethod
    def normalize_architecture(raw_architecture: Optional[str], variant: Optional[str] = None) -> Optional[str]:
        if not raw_architecture:
            return None

        arch = raw_architecture.lower().strip()
        variant_value = (variant or "").lower().strip()

        if arch in {"unknown", "n/a"}:
            return None

        if arch in {"x86_64", "amd64"}:
            return "amd64"
        if arch in {"aarch64", "arm64"}:
            return "arm64"
        if arch == "arm":
            if variant_value in {"v7", "7"}:
                return "arm/v7"
            if variant_value in {"v6", "6"}:
                return "arm/v6"
            return "arm"
        if arch in {"386", "i386"}:
            return "386"

        return arch

    @classmethod
    def host_architecture(cls) -> str:
        return cls.normalize_architecture(platform.machine()) or "amd64"

    def _get_json(self, path: str) -> Dict[str, Any]:
        response = self.session.get(f"{GITHUB_API_BASE}{path}", timeout=20)
        if response.status_code == 404:
            raise GitHubImportError("GitHub repository or file metadata not found")
        if response.status_code >= 400:
            raise GitHubImportError(f"GitHub API request failed with status {response.status_code}")
        return response.json()

    def _get_repo_metadata_with_fallback(self, repository_url: str, owner: str, repo: str) -> Tuple[Dict[str, Any], str]:
        try:
            return self._get_json(f"/repos/{owner}/{repo}"), "github-api"
        except GitHubImportError as exc:
            logger.info(f"Falling back to git/html metadata for {repository_url}: {exc}")

        default_branch = self._git_default_branch(repository_url)
        html_metadata = self._scrape_repository_metadata(repository_url)
        return ({
            "name": repo,
            "full_name": f"{owner}/{repo}",
            "default_branch": default_branch,
            "description": html_metadata.get("description") or f"Imported from {owner}/{repo}",
            "homepage": html_metadata.get("homepage") or "",
            "topics": html_metadata.get("topics") or [],
            "owner": {
                "login": owner,
                "avatar_url": html_metadata.get("avatar_url"),
            },
        }, "html-fallback")

    @staticmethod
    def _git_default_branch(repository_url: str) -> str:
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--symref", repository_url, "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
        except Exception:
            return "main"

        for line in result.stdout.splitlines():
            if line.startswith("ref: ") and "\tHEAD" in line:
                ref = line.split()[1]
                return ref.rsplit("/", 1)[-1]
        return "main"

    def _scrape_repository_metadata(self, repository_url: str) -> Dict[str, Any]:
        try:
            response = self.session.get(repository_url, timeout=20)
        except Exception:
            return {}

        if response.status_code >= 400:
            return {}

        html = response.text
        description = self._extract_meta_content(html, "og:description") or self._extract_meta_name(html, "description")
        title = self._extract_meta_content(html, "og:title")
        image = self._extract_meta_content(html, "og:image")

        return {
            "title": title,
            "description": description,
            "avatar_url": image,
            "homepage": "",
            "topics": [],
        }

    @staticmethod
    def _extract_meta_content(html: str, property_name: str) -> Optional[str]:
        pattern = rf'<meta[^>]+property=["\']{re.escape(property_name)}["\'][^>]+content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, flags=re.IGNORECASE)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_meta_name(html: str, name: str) -> Optional[str]:
        pattern = rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, flags=re.IGNORECASE)
        return match.group(1).strip() if match else None

    @staticmethod
    def _clone_repository_snapshot(repository_url: str, branch: str):
        checkout_dir = tempfile.mkdtemp(prefix="appstore-github-import-")
        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    branch,
                    repository_url,
                    checkout_dir,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            shutil.rmtree(checkout_dir, ignore_errors=True)
            stderr = exc.stderr.strip() or exc.stdout.strip()
            raise GitHubImportError(f"Could not clone repository snapshot: {stderr}")

        from pathlib import Path

        return Path(checkout_dir)

    @staticmethod
    def _list_repository_files(checkout_dir) -> List[str]:
        files = []
        for entry in checkout_dir.rglob("*"):
            if entry.is_file():
                files.append(entry.relative_to(checkout_dir).as_posix())
        return files

    def _fetch_raw_file(self, owner: str, repo: str, branch: str, path: str) -> str:
        response = self.session.get(
            f"{RAW_GITHUB_BASE}/{owner}/{repo}/{branch}/{path}",
            timeout=20,
        )
        if response.status_code == 404:
            raise GitHubImportError(f"File not found: {path}")
        if response.status_code >= 400:
            raise GitHubImportError(f"Could not fetch {path} (status {response.status_code})")
        return response.text

    @staticmethod
    def _select_readme_path(file_paths: List[str]) -> Optional[str]:
        root_candidates = [path for path in file_paths if path.lower() in {"readme.md", "readme.mdx"}]
        if root_candidates:
            return sorted(root_candidates)[0]

        candidates = [path for path in file_paths if path.split("/")[-1].lower() in {"readme.md", "readme.mdx"}]
        if not candidates:
            return None

        return sorted(candidates, key=lambda path: (path.count("/"), path.lower()))[0]

    @staticmethod
    def _select_compose_path(file_paths: List[str]) -> Optional[str]:
        candidates = [path for path in file_paths if GitHubAppImporter._is_compose_candidate(path)]
        if not candidates:
            return None

        def score(path: str) -> Tuple[int, int, str]:
            lowered = path.lower()
            penalty = 0
            noisy_segments = ("test", "tests", "dev", "docs", "example", "examples", ".github")
            if any(segment in lowered.split("/") for segment in noisy_segments):
                penalty += 10
            basename = path.split("/")[-1].lower()
            preferred_names = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
            if basename in preferred_names:
                name_penalty = preferred_names.index(basename)
            elif "compose" in basename and basename.endswith((".yml", ".yaml")):
                name_penalty = 10
            elif basename.endswith((".yml", ".yaml")) and "docker" in basename:
                name_penalty = 20
            else:
                name_penalty = 30
            return (penalty, name_penalty, path.count("/"), lowered)

        return sorted(candidates, key=score)[0]

    @staticmethod
    def _is_compose_candidate(path: str) -> bool:
        basename = path.split("/")[-1].lower()
        if basename in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}:
            return True
        if basename.endswith((".yml", ".yaml")) and "compose" in basename:
            return True
        if basename.endswith((".yml", ".yaml")) and ("docker" in basename or "stack" in basename):
            return True
        return False

    @staticmethod
    def _select_dockerfile_path(file_paths: List[str]) -> Optional[str]:
        candidates = [
            path
            for path in file_paths
            if path.split("/")[-1] in {"Dockerfile", "Containerfile"}
        ]
        if not candidates:
            return None

        def score(path: str) -> Tuple[int, int, str]:
            lowered = path.lower()
            penalty = 0
            noisy_segments = ("test", "tests", "dev", "docs", "example", "examples", ".github")
            if any(segment in lowered.split("/") for segment in noisy_segments):
                penalty += 10
            containerfile_penalty = 1 if path.endswith("Containerfile") else 0
            return (penalty, containerfile_penalty, path.count("/"), lowered)

        return sorted(candidates, key=score)[0]

    @staticmethod
    def _extract_readme_images(
        readme_content: str,
        owner: str,
        repo: str,
        branch: str,
        readme_path: Optional[str],
    ) -> List[str]:
        if not readme_content:
            return []

        markdown_images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme_content)
        html_images = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', readme_content, flags=re.IGNORECASE)
        base_dir = ""
        if readme_path and "/" in readme_path:
            base_dir = readme_path.rsplit("/", 1)[0]

        normalized = []
        ignored_fragments = (
            "shields.io",
            "badge",
            "star-history",
            "contrib.rocks",
            "run-button",
            "railway.com/button",
        )
        for image_url in markdown_images + html_images:
            cleaned = GitHubAppImporter._normalize_asset_url(image_url, owner, repo, branch, base_dir)
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if any(fragment in lowered for fragment in ignored_fragments):
                continue
            normalized.append(cleaned)

        return list(dict.fromkeys(normalized))

    @staticmethod
    def _extract_tree_images(
        file_paths: List[str],
        owner: str,
        repo: str,
        branch: str,
    ) -> List[str]:
        candidates = []
        ignored_segments = {"node_modules", ".github", "vendor", "dist", "build"}
        image_extensions = (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif")

        for path in file_paths:
            lowered = path.lower()
            if not lowered.endswith(image_extensions):
                continue
            if any(segment in ignored_segments for segment in lowered.split("/")):
                continue
            if any(fragment in lowered for fragment in ("badge", "star-history", "contrib", "button", "favicon", "icons.")):
                continue

            score = 100
            if any(keyword in lowered for keyword in ("logo", "icon", "banner", "cover")):
                score -= 40
            if any(keyword in lowered for keyword in ("screenshot", "screen", "preview", "dashboard")):
                score -= 25
            if lowered.endswith(".svg"):
                score -= 5
            score += path.count("/")

            candidates.append(
                (
                    score,
                    f"{RAW_GITHUB_BASE}/{owner}/{repo}/{branch}/{path}",
                )
            )

        return [url for _, url in sorted(candidates, key=lambda item: (item[0], item[1]))[:8]]

    @staticmethod
    def _merge_image_candidates(readme_images: List[str], tree_images: List[str]) -> List[str]:
        merged = []
        for image_url in tree_images + readme_images:
            if image_url not in merged:
                merged.append(image_url)
        return merged

    @staticmethod
    def _normalize_asset_url(
        image_url: str,
        owner: str,
        repo: str,
        branch: str,
        base_dir: str,
    ) -> Optional[str]:
        cleaned = image_url.strip().strip("<>").strip().replace("\\", "/")
        if not cleaned:
            return None

        parsed = urlparse(cleaned)
        if parsed.scheme in {"http", "https"}:
            if parsed.netloc.lower() == "github.com" and "/blob/" in parsed.path:
                path_parts = parsed.path.strip("/").split("/")
                if len(path_parts) >= 5:
                    return f"{RAW_GITHUB_BASE}/{path_parts[0]}/{path_parts[1]}/{path_parts[3]}/{'/'.join(path_parts[4:])}"
            return cleaned

        relative_path = cleaned.lstrip("./")
        if relative_path.startswith("/"):
            relative_path = relative_path.lstrip("/")
            return f"{RAW_GITHUB_BASE}/{owner}/{repo}/{branch}/{relative_path}"

        if base_dir:
            relative_path = f"{base_dir}/{relative_path}"

        return f"{RAW_GITHUB_BASE}/{owner}/{repo}/{branch}/{relative_path}"

    @staticmethod
    def _build_metadata(repository_url: str, repo_meta: Dict[str, Any], image_links: List[str]) -> Dict[str, Any]:
        title = repo_meta["name"]
        description = repo_meta.get("description") or f"Imported from {repo_meta['full_name']}"
        icon = image_links[0] if image_links else repo_meta["owner"].get("avatar_url")
        screenshot_links = image_links[1:] if len(image_links) > 1 else []
        category = GitHubAppImporter._infer_category(repo_meta.get("topics", []), description)
        tags = list(dict.fromkeys((repo_meta.get("topics") or []) + ["github-import"]))

        return {
            "title": title,
            "description": description,
            "developer": repo_meta["owner"]["login"],
            "icon": icon,
            "thumbnail": icon,
            "category": category,
            "tags": tags,
            "screenshot_links": screenshot_links,
            "source_url": repository_url,
            "homepage": repo_meta.get("homepage") or None,
        }

    @staticmethod
    def _infer_category(topics: List[str], description: str) -> str:
        topics_lower = {topic.lower() for topic in topics}
        description_lower = description.lower()

        if {"monitoring", "uptime", "statuspage", "server-monitoring", "incident", "observability"} & topics_lower:
            return "Monitoring"
        if {"network", "networking", "dns", "reverse-proxy"} & topics_lower or "port monitoring" in description_lower:
            return "Networking"
        if {"note", "note-taking", "knowledge-base", "zettelkasten", "markdown"} & topics_lower:
            return "Productivity"
        if {"gallery", "images", "share-image"} & topics_lower:
            return "Media"
        if {"database", "postgres", "mysql", "mongodb", "redis"} & topics_lower:
            return "Databases"
        if {"personal-cloud", "cloud", "home-server", "self-hosted", "homelab"} & topics_lower:
            return "Self-hosting"
        if {"finance", "trading", "charting-library"} & topics_lower:
            return "Finance"
        if {"security", "mtls", "oidc"} & topics_lower or "certificate" in description_lower:
            return "Security"
        if {"api", "developer-tools", "sdk"} & topics_lower:
            return "Developer Tools"

        return "Utilities"

    @staticmethod
    def _enrich_compose_metadata(compose_content: str, metadata: Dict[str, Any]) -> str:
        compose = yaml.safe_load(compose_content)
        if not isinstance(compose, dict):
            raise GitHubImportError("Compose file is not a valid object")

        services = compose.get("services")
        if not isinstance(services, dict) or not services:
            raise GitHubImportError("Compose file does not declare any services")

        main_service = next(iter(services.keys()))
        port_map = GitHubAppImporter._extract_port_map(services.get(main_service, {}))

        x_casaos = compose.get("x-casaos") or {}
        defaults = {
            "main": main_service,
            "title": metadata["title"],
            "description": metadata["description"],
            "developer": metadata["developer"],
            "category": metadata["category"],
            "icon": metadata["icon"],
            "thumbnail": metadata["thumbnail"],
            "port_map": port_map,
            "index": "/",
            "architectures": ["amd64"],
            "tags": metadata["tags"],
            "source_url": metadata["source_url"],
        }
        if metadata.get("homepage"):
            defaults["homepage"] = metadata["homepage"]
        if metadata["screenshot_links"]:
            defaults["screenshot_link"] = metadata["screenshot_links"]

        for key, value in defaults.items():
            if not x_casaos.get(key):
                x_casaos[key] = value

        compose["x-casaos"] = x_casaos
        return yaml.safe_dump(compose, sort_keys=False, allow_unicode=False)

    @staticmethod
    def _extract_port_map(service_config: Dict[str, Any]) -> str:
        ports = service_config.get("ports", [])
        if not ports:
            return "80"

        first_port = ports[0]
        if isinstance(first_port, int):
            return str(first_port)
        if isinstance(first_port, str):
            cleaned = first_port.split("/")[0]
            if ":" in cleaned:
                return cleaned.split(":", 1)[0]
            return cleaned
        if isinstance(first_port, dict):
            published = first_port.get("published") or first_port.get("target")
            if published:
                return str(published)
        return "80"

    @staticmethod
    def _build_compose_from_dockerfile(
        repo_meta: Dict[str, Any],
        repository_url: str,
        dockerfile_path: str,
        dockerfile_content: str,
        metadata: Dict[str, Any],
    ) -> str:
        service_name = re.sub(r"[^a-z0-9-]+", "-", repo_meta["name"].lower()).strip("-") or "app"
        ports = GitHubAppImporter._extract_exposed_ports(dockerfile_content)
        main_port = ports[0] if ports else "80"

        build_config: Dict[str, Any] = {
            "context": f"{repository_url}.git#{repo_meta['default_branch']}",
        }
        if dockerfile_path not in {"Dockerfile", "./Dockerfile"}:
            build_config["dockerfile"] = dockerfile_path

        compose: Dict[str, Any] = {
            "services": {
                service_name: {
                    "build": build_config,
                    "container_name": service_name,
                    "restart": "unless-stopped",
                }
            },
            "x-casaos": {
                "main": service_name,
                "title": metadata["title"],
                "description": metadata["description"],
                "developer": metadata["developer"],
                "category": metadata["category"],
                "icon": metadata["icon"],
                "thumbnail": metadata["thumbnail"],
                "port_map": main_port,
                "index": "/",
                "architectures": ["amd64"],
                "tags": metadata["tags"],
                "source_url": metadata["source_url"],
            },
        }
        if metadata.get("homepage"):
            compose["x-casaos"]["homepage"] = metadata["homepage"]
        if metadata["screenshot_links"]:
            compose["x-casaos"]["screenshot_link"] = metadata["screenshot_links"]
        if ports:
            compose["services"][service_name]["ports"] = [f"{port}:{port}" for port in ports]

        return yaml.safe_dump(compose, sort_keys=False, allow_unicode=False)

    @staticmethod
    def _extract_exposed_ports(dockerfile_content: str) -> List[str]:
        ports: List[str] = []
        for match in re.findall(r"^EXPOSE\s+(.+)$", dockerfile_content, flags=re.IGNORECASE | re.MULTILINE):
            for token in match.split():
                port = token.split("/")[0].strip()
                if port.isdigit():
                    ports.append(port)
        return list(dict.fromkeys(ports))

    def _populate_architecture_metadata(self, app: App) -> None:
        host_architecture = self.host_architecture()
        app.host_architecture = host_architecture

        if app.source_type == "dockerfile":
            app.compatible_with_host = True
            app.compatibility_status = "buildable"
            app.compatibility_warning = None
            app.unsupported_services = []
            return

        service_architectures: Dict[str, List[str]] = {}
        supported_sets: List[Set[str]] = []

        for service_name, service in app.services.items():
            if not service.image:
                continue
            architectures = self._detect_image_architectures(service.image)
            if architectures:
                service.architectures = architectures
                service_architectures[service_name] = architectures
                supported_sets.append(set(architectures))

        if supported_sets:
            shared_architectures = sorted(set.intersection(*supported_sets))
            if shared_architectures:
                app.architectures = shared_architectures

        unsupported_services = [
            service_name
            for service_name, architectures in service_architectures.items()
            if host_architecture not in architectures
        ]
        app.unsupported_services = unsupported_services

        if unsupported_services:
            app.compatible_with_host = False
            app.compatibility_status = "warning"
            app.compatibility_warning = (
                f"Some container images do not publish {host_architecture} builds: "
                f"{', '.join(unsupported_services)}."
            )
            return

        if service_architectures:
            app.compatible_with_host = True
            app.compatibility_status = "compatible"
            app.compatibility_warning = None
            return

        app.compatible_with_host = None
        app.compatibility_status = "unknown"
        app.compatibility_warning = "Image architecture could not be detected automatically."

    def _detect_image_architectures(self, image_reference: str) -> List[str]:
        if image_reference in self._manifest_cache:
            return self._manifest_cache[image_reference]

        try:
            registry, repository, reference = self._parse_image_reference(image_reference)
            manifest = self._fetch_registry_manifest(registry, repository, reference)
            architectures = self._extract_architectures_from_manifest(manifest)
        except Exception as exc:
            logger.info(f"Could not detect architectures for image {image_reference}: {exc}")
            architectures = []

        self._manifest_cache[image_reference] = architectures
        return architectures

    @staticmethod
    def _parse_image_reference(image_reference: str) -> Tuple[str, str, str]:
        raw = image_reference.strip()
        digest = None
        if "@" in raw:
            raw, digest = raw.rsplit("@", 1)

        tag = "latest"
        last_segment = raw.rsplit("/", 1)[-1]
        if ":" in last_segment:
            raw, tag = raw.rsplit(":", 1)

        parts = raw.split("/")
        if len(parts) > 1 and ("." in parts[0] or ":" in parts[0] or parts[0] == "localhost"):
            registry = parts[0]
            repository = "/".join(parts[1:])
        else:
            registry = "registry-1.docker.io"
            repository = raw if "/" in raw else f"library/{raw}"

        if registry in {"docker.io", "index.docker.io"}:
            registry = "registry-1.docker.io"

        reference = digest or tag
        return registry, repository, reference

    def _fetch_registry_manifest(self, registry: str, repository: str, reference: str) -> Dict[str, Any]:
        url = f"https://{registry}/v2/{repository}/manifests/{reference}"
        headers = {
            "Accept": ", ".join(
                [
                    "application/vnd.oci.image.index.v1+json",
                    "application/vnd.docker.distribution.manifest.list.v2+json",
                    "application/vnd.oci.image.manifest.v1+json",
                    "application/vnd.docker.distribution.manifest.v2+json",
                ]
            )
        }

        response = self.session.get(url, headers=headers, timeout=20)
        if response.status_code == 401:
            token = self._registry_bearer_token(response.headers.get("WWW-Authenticate", ""))
            if not token:
                raise GitHubImportError(f"Unauthorized to inspect image manifest for {repository}")
            headers["Authorization"] = f"Bearer {token}"
            response = self.session.get(url, headers=headers, timeout=20)

        if response.status_code >= 400:
            raise GitHubImportError(f"Manifest lookup failed for {repository}:{reference}")

        return response.json()

    def _registry_bearer_token(self, challenge_header: str) -> Optional[str]:
        if not challenge_header.startswith("Bearer "):
            return None

        attributes = {}
        for part in challenge_header[len("Bearer "):].split(","):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            attributes[key.strip()] = value.strip().strip('"')

        realm = attributes.get("realm")
        if not realm:
            return None

        params = {}
        if attributes.get("service"):
            params["service"] = attributes["service"]
        if attributes.get("scope"):
            params["scope"] = attributes["scope"]

        response = self.session.get(realm, params=params, timeout=20)
        if response.status_code >= 400:
            return None

        data = response.json()
        return data.get("token") or data.get("access_token")

    @classmethod
    def _extract_architectures_from_manifest(cls, manifest: Dict[str, Any]) -> List[str]:
        architectures = []
        manifests = manifest.get("manifests")
        if isinstance(manifests, list):
            for entry in manifests:
                platform_data = entry.get("platform", {})
                normalized = cls.normalize_architecture(
                    platform_data.get("architecture"),
                    platform_data.get("variant"),
                )
                if normalized:
                    architectures.append(normalized)
        else:
            normalized = cls.normalize_architecture(
                manifest.get("architecture"),
                manifest.get("variant"),
            )
            if normalized:
                architectures.append(normalized)

        return sorted(dict.fromkeys(architectures))


def serialize_imported_app(app: App) -> str:
    return app.model_dump_json()


def deserialize_imported_app(payload_json: str) -> App:
    return App.model_validate(json.loads(payload_json))


def load_persisted_imported_apps(db) -> List[GitHubImportedApp]:
    return (
        db.query(GitHubImportedApp)
        .filter(GitHubImportedApp.enabled == True)
        .order_by(GitHubImportedApp.updated_at.desc())
        .all()
    )
