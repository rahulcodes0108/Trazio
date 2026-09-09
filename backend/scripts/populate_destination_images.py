"""Discover Wikimedia Commons images and upload destination images to Cloudinary.

Usage:
    python scripts/populate_destination_images.py discover
    python scripts/populate_destination_images.py upload
    python scripts/populate_destination_images.py all

Discovery:
    - Reads active destinations from PostgreSQL.
    - Searches Wikimedia Commons with destination-specific queries.
    - Scores multiple image candidates for semantic relevance.
    - Accepts only freely licensed images.
    - Downloads Wikimedia thumbnail images.
    - Records attribution/source metadata in a manifest.

Upload:
    - Uploads discovered images to Cloudinary.
    - Stores the resulting secure URL in destinations.image_url.
    - Uses a stable Cloudinary public ID.
    - Skips destinations that already have an image URL.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import cloudinary
import cloudinary.uploader
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.destination import Destination


LOGGER = logging.getLogger("destination-images")

# /app/scripts/populate_destination_images.py
# parents[1] -> /app
PROJECT_ROOT = Path(__file__).resolve().parents[1]

IMAGE_DIR = PROJECT_ROOT / "scripts" / "destination_images"
MANIFEST_PATH = PROJECT_ROOT / "scripts" / "destination_image_sources.json"

WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"

ALLOWED_LICENSE_PATTERNS = (
    "CC0",
    "CC BY",
    "CC BY-SA",
    "Public domain",
    "Public Domain",
)

USER_AGENT = (
    "Trazio/0.1 "
    "(destination image importer; "
    "contact: trazio-development)"
)

SEARCH_LIMIT = 20
THUMBNAIL_WIDTH = 1200
REQUEST_TIMEOUT = 45

# Keep requests polite to Wikimedia.
REQUEST_DELAY_SECONDS = 2.0
RATE_LIMIT_DELAY_SECONDS = 15.0

# The importer is intentionally conservative. These are extra search
# phrases for destinations where the database name is not always the
# wording used on Wikimedia Commons.
DESTINATION_SEARCH_TERMS: dict[str, list[str]] = {
    "Chennai Rail Museum": [
        '"Chennai Rail Museum"',
        '"Chennai Railway Museum"',
        '"Rail Museum Chennai"',
        '"ICF Museum Chennai"',
        '"Integral Coach Factory Museum"',
    ],
    "Santhome Cathedral Basilica": [
        '"Santhome Cathedral Basilica"',
        '"San Thome Cathedral Basilica"',
        '"Santhome Basilica Chennai"',
        '"San Thome Basilica Chennai"',
        '"Santhome Church Chennai"',
    ],
    "Kalikambal Kamadeswarar Temple": [
        '"Kalikambal Kamadeswarar Temple"',
        '"Kalikambal Temple Chennai"',
        '"Kalikambal Kamakshi Temple"',
        '"Kalikambal Temple"',
    ],
    "Express Avenue": [
        '"Express Avenue" Chennai',
        '"Express Avenue Mall" Chennai',
        '"Express Avenue Mall Chennai"',
    ],
    "Phoenix Marketcity Chennai": [
        '"Phoenix Marketcity Chennai"',
        '"Phoenix Marketcity" Chennai',
        '"Phoenix Mall Chennai"',
        '"Phoenix Mall" Chennai',
    ],
    "Dakshinachitra Craft Village": [
    '"Dakshinchitra (1).jpg"',
    '"Amphitheatre at DakshinaChitra.jpg"',
    '"Crafts Bazar Dakshinachitra.jpg"',
    '"DakshinaChitra" Chennai',
    '"Dakshinachitra Museum" Chennai',
    ],
    "Marina Beach Food Zone": [
        '"Marina Beach" Chennai food',
        '"Marina Beach" Chennai street food',
        '"Marina Beach" Chennai vendors',
        '"Marina Beach" Chennai',
    ],
    "Besant Nagar Food Street": [
        '"Besant Nagar" Chennai food',
        '"Besant Nagar Beach" Chennai food',
        '"Besant Nagar" street food Chennai',
        '"Elliot Beach" Chennai food',
        '"Besant Nagar" Chennai',
    ],
    "Koyambedu Market": [
    '"Koyambedu Market.jpg"',
    '"Koyambedu Market A View.jpg"',
    '"India - Koyambedu Market - Market 01"',
    '"Koyambedu Market" Chennai',
    '"Koyambedu Wholesale Market"',
    ],
}


def get_database_url() -> str:
    """Return the configured database URL."""
    return settings.DATABASE_URL


def get_session() -> Session:
    """Create a database session."""
    engine = create_engine(get_database_url())
    return Session(engine)


def normalize_filename(value: str) -> str:
    """Create a safe local filename from a destination slug."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def normalize_text(value: str) -> str:
    """Normalize text for candidate relevance scoring."""
    value = value.lower()
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[^a-z0-9\s]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def license_is_acceptable(license_text: str) -> bool:
    """Return whether a Wikimedia license is suitable for Trazio."""
    normalized = license_text.lower()

    if "noncommercial" in normalized:
        return False

    if "no derivatives" in normalized:
        return False

    return any(
        pattern.lower() in normalized
        for pattern in ALLOWED_LICENSE_PATTERNS
    )


def extract_metadata(info: dict[str, Any]) -> dict[str, str]:
    """Extract useful attribution metadata from Wikimedia metadata."""
    metadata = info.get("extmetadata", {})

    def value(name: str) -> str:
        item = metadata.get(name, {})
        return str(item.get("value", "")).strip()

    return {
        "author": value("Artist"),
        "license": value("LicenseShortName"),
        "license_url": value("LicenseUrl"),
        "description": value("ImageDescription"),
    }


def get_wikimedia(
    params: dict[str, Any],
    *,
    max_retries: int = 3,
) -> requests.Response:
    """Call the Wikimedia API with polite retry handling."""
    headers = {
        "User-Agent": USER_AGENT,
    }

    for attempt in range(1, max_retries + 1):
        response = requests.get(
            WIKIMEDIA_API,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 429:
            response.raise_for_status()
            return response

        retry_after = response.headers.get("Retry-After")

        if retry_after:
            try:
                delay = min(float(retry_after), 60.0)
            except ValueError:
                delay = RATE_LIMIT_DELAY_SECONDS
        else:
            delay = RATE_LIMIT_DELAY_SECONDS * attempt

        if attempt < max_retries:
            LOGGER.warning(
                "Wikimedia API rate limit reached (429). "
                "Retrying in %.0f seconds (%s/%s).",
                delay,
                attempt,
                max_retries,
            )
            time.sleep(delay)

    response.raise_for_status()
    return response


def get_search_terms(destination: Destination) -> list[str]:
    """Return destination-specific search terms."""
    custom_terms = DESTINATION_SEARCH_TERMS.get(destination.name)

    if custom_terms:
        return custom_terms

    return [
        f'"{destination.name}" Chennai',
        destination.name,
    ]


def candidate_search_text(
    destination: Destination,
    page: dict[str, Any],
    metadata: dict[str, str],
) -> str:
    """Build searchable text for candidate scoring."""
    parts = [
        destination.name,
        destination.slug,
        destination.category or "",
        destination.city or "",
        destination.state_province or "",
        page.get("title", ""),
        metadata.get("description", ""),
    ]

    return normalize_text(" ".join(str(part) for part in parts))


def destination_tokens(destination: Destination) -> set[str]:
    """Return useful semantic tokens for a destination."""
    source = " ".join(
        [
            destination.name,
            destination.slug or "",
            destination.category or "",
            destination.city or "",
        ]
    )

    tokens = set(normalize_text(source).split())

    # Generic terms are not useful for image relevance.
    ignored = {
        "the",
        "and",
        "of",
        "in",
        "at",
        "on",
        "chennai",
        "tamil",
        "nadu",
        "india",
        "city",
        "district",
        "zone",
        "area",
        "food",
        "street",
        "village",
        "centre",
        "center",
    }

    return {
        token
        for token in tokens
        if len(token) >= 3 and token not in ignored
    }


def score_candidate(
    destination: Destination,
    page: dict[str, Any],
    metadata: dict[str, str],
) -> int:
    """Score a Wikimedia candidate for semantic relevance."""
    title = normalize_text(str(page.get("title", "")))
    description = normalize_text(metadata.get("description", ""))

    full_text = f"{title} {description}"

    score = 0
    tokens = destination_tokens(destination)

    # Strongest signal: destination-specific tokens in the title.
    for token in tokens:
        if token in title:
            score += 12

        if token in description:
            score += 4

    # Exact destination name.
    destination_name = normalize_text(destination.name)

    if destination_name in title:
        score += 60

    if destination_name in description:
        score += 30

    # Chennai is useful contextual evidence, but should never be enough
    # on its own to make an unrelated image acceptable.
    if "chennai" in full_text:
        score += 8

    # Destination category hints.
    category = normalize_text(destination.category or "")

    category_terms: dict[str, set[str]] = {
        "beach": {
            "beach",
            "coast",
            "shore",
            "sea",
            "seaside",
        },
        "temple": {
            "temple",
            "kovil",
            "shrine",
        },
        "church": {
            "church",
            "cathedral",
            "basilica",
        },
        "museum": {
            "museum",
            "gallery",
        },
        "park": {
            "park",
            "garden",
        },
        "market": {
            "market",
            "bazaar",
            "vegetable",
            "wholesale",
        },
        "shopping": {
            "mall",
            "shopping",
            "market",
        },
        "food": {
            "food",
            "restaurant",
            "street",
            "market",
            "vendor",
        },
    }

    for term in category_terms.get(category, set()):
        if term in title:
            score += 7
        elif term in description:
            score += 3

    # Penalize obviously generic/unrelated images.
    negative_terms = {
        "army",
        "weapon",
        "petard",
        "military",
        "soldier",
        "war",
        "aircraft",
        "football",
        "cricket",
        "politician",
        "map",
        "logo",
        "flag",
    }

    for term in negative_terms:
        if term in title:
            score -= 40

    return score


def search_wikimedia(destination: Destination) -> dict[str, Any] | None:
    """Find the most relevant acceptable Wikimedia image."""
    search_terms = get_search_terms(destination)

    candidates: list[dict[str, Any]] = []
    seen_page_ids: set[int] = set()

    for search_term in search_terms:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": search_term,
            "gsrnamespace": "6",
            "gsrlimit": SEARCH_LIMIT,
            "prop": "imageinfo",
            "iiprop": "url|mime|size|extmetadata",
            "iiurlwidth": THUMBNAIL_WIDTH,
        }

        response = get_wikimedia(params)
        data = response.json()

        pages = data.get("query", {}).get("pages", {})

        for page in pages.values():
            page_id = page.get("pageid")

            if page_id in seen_page_ids:
                continue

            seen_page_ids.add(page_id)

            imageinfo = page.get("imageinfo", [])

            if not imageinfo:
                continue

            info = imageinfo[0]

            mime = info.get("mime", "")

            if not mime.startswith("image/"):
                continue

            metadata = extract_metadata(info)

            if not license_is_acceptable(metadata["license"]):
                continue

            title = str(page.get("title", ""))

            # Wikimedia file titles should normally contain File:.
            # Keep only actual image files.
            if not title.lower().startswith("file:"):
                continue

            score = score_candidate(
                destination,
                page,
                metadata,
            )

            candidates.append(
                {
                    "title": title,
                    "pageid": page_id,
                    "url": info.get("url"),
                    "thumb_url": info.get("thumburl"),
                    "mime": mime,
                    "metadata": metadata,
                    "score": score,
                }
            )

        # One strong search result is enough to avoid unnecessary API
        # requests and CDN traffic.
        if candidates and max(
            candidate["score"] for candidate in candidates
        ) >= 70:
            break

        time.sleep(REQUEST_DELAY_SECONDS)

    if not candidates:
        return None

    candidates.sort(
        key=lambda candidate: candidate["score"],
        reverse=True,
    )

    best = candidates[0]

    # Do not accept a merely licensed image if it has essentially no
    # evidence that it represents the requested destination.
    if best["score"] < 15:
        LOGGER.warning(
            "  Wikimedia candidates found, but none were sufficiently "
            "relevant. Best score=%s | %s",
            best["score"],
            best["title"],
        )
        return None

    LOGGER.info(
        "  Selected candidate: %s | relevance=%s",
        best["title"],
        best["score"],
    )

    return best


def extension_for_mime(mime: str) -> str:
    """Return a safe local extension for a MIME type."""
    if mime == "image/png":
        return ".png"

    if mime == "image/webp":
        return ".webp"

    if mime == "image/jpeg":
        return ".jpg"

    return ".jpg"


def download_image(
    result: dict[str, Any],
    local_path: Path,
) -> None:
    """Download a Wikimedia thumbnail with limited retry handling."""
    image_url = result.get("thumb_url") or result.get("url")

    if not image_url:
        raise RuntimeError(
            f"No downloadable image URL for {result['title']}"
        )

    headers = {
        "User-Agent": USER_AGENT,
    }

    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        response = requests.get(
            image_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 429:
            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type",
                "",
            ).lower()

            if not content_type.startswith("image/"):
                raise RuntimeError(
                    "Wikimedia returned a non-image response "
                    f"for {result['title']}: {content_type}"
                )

            local_path.write_bytes(response.content)
            return

        if attempt < max_attempts:
            retry_after = response.headers.get("Retry-After")

            try:
                delay = (
                    min(float(retry_after), 60.0)
                    if retry_after
                    else RATE_LIMIT_DELAY_SECONDS * attempt
                )
            except ValueError:
                delay = RATE_LIMIT_DELAY_SECONDS * attempt

            LOGGER.warning(
                "  Wikimedia image CDN rate limit reached (429). "
                "Retrying in %.0f seconds (%s/%s).",
                delay,
                attempt,
                max_attempts,
            )

            time.sleep(delay)

    response.raise_for_status()


def write_manifest(manifest: dict[str, Any]) -> None:
    """Atomically write the image source manifest."""
    MANIFEST_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = MANIFEST_PATH.with_suffix(".json.tmp")

    temp_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    temp_path.replace(MANIFEST_PATH)


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}

    return json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8-sig")
    )

def discover_images() -> None:
    """Discover and download Wikimedia images."""
    IMAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with get_session() as db:
        destinations = (
            db.query(Destination)
            .filter(Destination.is_active.is_(True))
            .order_by(Destination.id)
            .all()
        )

    manifest = load_manifest()

    total = len(destinations)

    LOGGER.info(
        "Found %s active destinations.",
        total,
    )

    for index, destination in enumerate(
        destinations,
        start=1,
    ):
        slug = normalize_filename(destination.slug)

        LOGGER.info(
            "[%s/%s] Searching Wikimedia Commons: %s",
            index,
            total,
            destination.name,
        )

        existing = manifest.get(slug)

        if existing and existing.get("local_file"):
            local_path = PROJECT_ROOT / existing["local_file"]

            if local_path.exists():
                LOGGER.info(
                    "  Existing local image found; skipping search."
                )
                continue

        try:
            result = search_wikimedia(destination)

            if result is None:
                LOGGER.warning(
                    "  No sufficiently relevant Wikimedia image found "
                    "for %s",
                    destination.name,
                )

                manifest[slug] = {
                    "destination_id": destination.id,
                    "destination_name": destination.name,
                    "slug": destination.slug,
                    "status": "not_found",
                }

                write_manifest(manifest)
                continue

            extension = extension_for_mime(
                result["mime"],
            )

            filename = f"{slug}{extension}"
            local_path = IMAGE_DIR / filename

            download_image(
                result,
                local_path,
            )

            relative_path = local_path.relative_to(
                PROJECT_ROOT,
            )

            manifest[slug] = {
                "destination_id": destination.id,
                "destination_name": destination.name,
                "slug": destination.slug,
                "status": "downloaded",
                "local_file": str(relative_path).replace(
                    "\\",
                    "/",
                ),
                "wikimedia_title": result["title"],
                "wikimedia_page_id": result["pageid"],
                "source_url": (
                    "https://commons.wikimedia.org/wiki/"
                    + result["title"].replace(
                        " ",
                        "_",
                    )
                ),
                "original_url": result["url"],
                "download_url": result["thumb_url"],
                "author": result["metadata"]["author"],
                "license": result["metadata"]["license"],
                "license_url": result["metadata"]["license_url"],
                "description": result["metadata"]["description"],
                "relevance_score": result["score"],
            }

            write_manifest(manifest)

            LOGGER.info(
                "  Downloaded: %s | %s | relevance=%s",
                filename,
                result["metadata"]["license"],
                result["score"],
            )

        except Exception as exc:
            LOGGER.error(
                "  Failed to process %s: %s",
                destination.name,
                exc,
            )

            manifest[slug] = {
                "destination_id": destination.id,
                "destination_name": destination.name,
                "slug": destination.slug,
                "status": "error",
                "error": str(exc),
            }

            write_manifest(manifest)

        time.sleep(REQUEST_DELAY_SECONDS)

    write_manifest(manifest)

    LOGGER.info("Discovery complete.")
    LOGGER.info(
        "Manifest: %s",
        MANIFEST_PATH,
    )


def configure_cloudinary() -> None:
    """Configure Cloudinary from application settings."""
    missing = []

    if not settings.CLOUDINARY_CLOUD_NAME:
        missing.append("CLOUDINARY_CLOUD_NAME")

    if not settings.CLOUDINARY_API_KEY:
        missing.append("CLOUDINARY_API_KEY")

    if not settings.CLOUDINARY_API_SECRET:
        missing.append("CLOUDINARY_API_SECRET")

    if missing:
        raise RuntimeError(
            "Missing Cloudinary configuration: "
            + ", ".join(missing)
        )

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def upload_images() -> None:
    """Upload discovered images to Cloudinary and update PostgreSQL."""
    configure_cloudinary()

    if not MANIFEST_PATH.exists():
        raise RuntimeError(
            "Image manifest does not exist. "
            "Run the discover command first."
        )

    manifest = load_manifest()

    with get_session() as db:
        for slug, item in manifest.items():
            if item.get("status") != "downloaded":
                continue

            destination = (
                db.query(Destination)
                .filter(
                    Destination.id == item["destination_id"],
                )
                .first()
            )

            if destination is None:
                LOGGER.warning(
                    "Destination %s no longer exists; skipping.",
                    item["destination_name"],
                )
                continue

            if destination.image_url:
                LOGGER.info(
                    "Skipping %s: image_url already exists.",
                    destination.name,
                )
                continue

            local_file = PROJECT_ROOT / item["local_file"]

            if not local_file.exists():
                LOGGER.warning(
                    "Missing local file for %s: %s",
                    destination.name,
                    local_file,
                )
                continue

            public_id = f"trazio/destinations/{slug}"

            LOGGER.info(
                "Uploading %s -> %s",
                destination.name,
                public_id,
            )

            result = cloudinary.uploader.upload(
                str(local_file),
                public_id=public_id,
                overwrite=False,
                resource_type="image",
            )

            secure_url = result.get("secure_url")

            if not secure_url:
                raise RuntimeError(
                    "Cloudinary returned no secure_url for "
                    f"{destination.name}"
                )

            destination.image_url = secure_url

            item["cloudinary_public_id"] = result.get(
                "public_id",
            )
            item["cloudinary_url"] = secure_url
            item["status"] = "uploaded"

            db.commit()

            LOGGER.info(
                "  Uploaded successfully: %s",
                destination.name,
            )

    write_manifest(manifest)

    LOGGER.info("Cloudinary upload complete.")


def main() -> None:
    """Run the requested image pipeline operation."""
    parser = argparse.ArgumentParser(
        description="Trazio destination image pipeline",
    )

    parser.add_argument(
        "command",
        choices=(
            "discover",
            "upload",
            "all",
        ),
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.command in (
        "discover",
        "all",
    ):
        discover_images()

    if args.command in (
        "upload",
        "all",
    ):
        upload_images()


if __name__ == "__main__":
    main()