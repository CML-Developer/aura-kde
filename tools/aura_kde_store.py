"""Local Aura Store video catalog. Never writes to Steam or Guardian."""
import hashlib
import json
import os
from pathlib import Path
import subprocess


def download_dir():
    config = os.environ.get('XDG_CONFIG_HOME')
    return (Path(config) if config else Path.home() / '.config') / 'aura-kde-lab/wallpapers_online_dir'


def inspect_video(path, probe=False):
    root = download_dir().resolve()
    path = path.resolve()
    if not path.is_relative_to(root) or path.suffix.lower() != '.mp4' or not path.is_file():
        raise ValueError('Select a completed MP4 from Aura Store downloads')
    with path.open('rb') as stream:
        header = stream.read(12)
    if len(header) != 12 or header[4:8] != b'ftyp':
        raise ValueError('Download is not an MP4 container')
    if probe:
        result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                 '-show_entries', 'stream=codec_type,width,height', '-of', 'json', str(path)],
                                capture_output=True, text=True, timeout=15, check=True)
        streams = json.loads(result.stdout).get('streams', [])
        if not streams or streams[0].get('codec_type') != 'video' or streams[0].get('width', 0) <= 0 or streams[0].get('height', 0) <= 0:
            raise ValueError('Download has no playable video stream')
    stat = path.stat()
    identity = 'aura-video-' + hashlib.sha256(str(path).encode()).hexdigest()[:24]
    return dict(id=identity, project=str(path), title=path.stem, type='video', usable=True,
                provider='aura-store', downloaded=True, modified=int(stat.st_mtime),
                source=path.as_uri() + '+video',
                fingerprint=[stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns])


def inspect_media(path, probe=False):
    path = path.resolve()
    if path.suffix.lower() == '.mp4':
        return inspect_video(path, probe)
    if not path.is_relative_to(download_dir().resolve()) or path.suffix.lower() not in ('.jpg','.jpeg','.png','.webp') or not path.is_file():
        raise ValueError('Select an image from Aura Store downloads')
    from PIL import Image
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', Image.DecompressionBombWarning)
        with Image.open(path) as image:
            if image.format not in ('JPEG','PNG','WEBP') or image.width <= 0 or image.height <= 0 or image.width * image.height > 40_000_000:
                raise ValueError('Unsupported image format or dimensions')
            image.verify()
        if probe:
            with Image.open(path) as image:
                image.load()
    stat = path.stat()
    identity = 'aura-image-' + hashlib.sha256(str(path).encode()).hexdigest()[:24]
    return dict(id=identity, project=str(path), title=path.stem, type='image', usable=True,
                provider='aura-store', downloaded=True, modified=int(stat.st_mtime),
                fingerprint=[stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns])


def items():
    root = download_dir()
    if not root.is_dir():
        return []
    output = []
    for path in sorted(root.iterdir()):
        try:
            output.append(inspect_media(path))
        except (ValueError, OSError):
            continue
    return output


def video_plan(path, before):
    from aura_kde_catalog import validate_snapshot
    from aura_kde_apply import restore_value
    validate_snapshot(before)
    item = inspect_video(path, probe=True)
    libraries = {restore_value('SteamLibraryPath', t['values']['SteamLibraryPath']['value'])
                 for t in before['targets']}
    if len(libraries) != 1:
        raise ValueError('Store video requires the same Steam library on both screens')
    return dict(item=item, proposed=dict(SteamLibraryPath=libraries.pop(),
                WallpaperWorkShopId=item['id'], WallpaperSource=item['source']))
