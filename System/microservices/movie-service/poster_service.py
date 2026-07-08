"""Poster upload and IMDb image lookup helpers."""
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import requests
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
MAX_POSTER_SIZE = 5 * 1024 * 1024
IMDB_IMAGES_API = os.getenv(
    'IMDB_IMAGES_API',
    'https://api.imdbapi.dev/titles/{movie_id}/images',
)


def get_posters_dir() -> Path:
    env_dir = os.getenv('POSTERS_DIR')
    if env_dir:
        target = Path(env_dir)
    else:
        candidates = [
            Path('/app/data/static/posters'),
            Path(__file__).resolve().parents[3] / 'web' / 'static' / 'posters',
        ]
        target = next((path for path in candidates if path.parent.exists()), candidates[-1])

    target.mkdir(parents=True, exist_ok=True)
    return target


def _allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _sanitize_movie_id(movie_id: Optional[str]) -> str:
    if not movie_id:
        return ''
    cleaned = re.sub(r'[^a-zA-Z0-9_-]', '', movie_id.strip())
    return cleaned


def save_poster_upload(file: FileStorage, movie_id: Optional[str] = None) -> Dict[str, str]:
    if not file or not file.filename:
        raise ValueError('Poster file is required')

    if not _allowed_file(file.filename):
        raise ValueError('Allowed poster formats: png, jpg, jpeg, webp, gif')

    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_POSTER_SIZE:
        raise ValueError('Poster file must be smaller than 5MB')

    extension = file.filename.rsplit('.', 1)[1].lower()
    safe_movie_id = _sanitize_movie_id(movie_id)
    if safe_movie_id:
        filename = f'{safe_movie_id}.{extension}'
    else:
        filename = f'{uuid.uuid4().hex}.{extension}'

    filename = secure_filename(filename)
    posters_dir = get_posters_dir()
    destination = posters_dir / filename
    file.save(destination)

    poster_url = f'/static/posters/{filename}'
    return {
        'poster_url': poster_url,
        'filename': filename,
    }


def _pick_best_poster(images: List[dict]) -> Optional[dict]:
    posters = [image for image in images if image.get('type') == 'poster' and image.get('url')]
    if not posters:
        return None
    return max(posters, key=lambda image: int(image.get('width') or 0) * int(image.get('height') or 0))


def fetch_imdb_posters(movie_id: str) -> Dict:
    safe_movie_id = _sanitize_movie_id(movie_id)
    if not safe_movie_id:
        raise ValueError('movie_id is required')

    url = IMDB_IMAGES_API.format(movie_id=safe_movie_id)
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    payload = response.json()

    images = payload.get('images') or []
    poster_images = [
        {
            'url': image.get('url'),
            'width': image.get('width'),
            'height': image.get('height'),
            'type': image.get('type'),
        }
        for image in images
        if image.get('type') == 'poster' and image.get('url')
    ]

    if not poster_images:
        raise ValueError('No poster images found for this movie')

    selected = _pick_best_poster(poster_images)
    return {
        'movie_id': safe_movie_id,
        'posters': poster_images,
        'selected_poster': selected,
        'poster_url': selected['url'],
        'total_count': payload.get('totalCount', len(poster_images)),
    }
