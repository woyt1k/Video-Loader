#!/usr/bin/env python3
"""Download videos at a selected resolution and images from Pinterest."""

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


VIDEO_DOMAINS = (
    "youtube.com", "youtu.be", "youtube-nocookie.com",
    "vk.com", "vk.ru", "vkvideo.ru", "vkontakte.ru",
    "ok.ru", "odnoklassniki.ru",
    "tiktok.com",
)
PINTEREST_DOMAIN = re.compile(r"(?:[a-z0-9-]+\.)*pinterest\.(?:com|[a-z]{2}|(?:co|com)\.[a-z]{2})")
IMAGE_FILTER = "extension.lower() in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'avif', 'bmp', 'tiff', 'tif', 'heic', 'heif')"
DOWNLOADS_DIRECTORY = Path.home() / "Downloads"
PROGRESS_PREFIX = "DOWNLOAD_PROGRESS\t"


@dataclass(frozen=True)
class VideoFormat:
    format_id: str
    width: int | None
    height: int | None
    fps: float | None
    video_only: bool
    size: int | None
    estimated_size: bool

    @property
    def label(self):
        if self.width and self.height:
            short_side, long_side = sorted((self.width, self.height))
            quality = f"{short_side}p"
            if short_side == 2160 and long_side in (3840, 4096):
                quality = "2160p / 4K"
            description = f"{quality} ({self.width}×{self.height})"
        elif self.height:
            description = f"{self.height}p"
        elif self.width:
            description = f"ширина {self.width} px"
        else:
            description = f"{self.format_id} (площадка не указала разрешение)"
        if self.fps:
            description += f" · {self.fps:g} FPS"
        return description

    @property
    def filename_quality(self):
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        if self.height:
            return f"{self.height}p"
        if self.width:
            return f"{self.width}w"
        return self.format_id

    @property
    def selector(self):
        video = f'bv*[format_id="{self.format_id}"]'
        if self.video_only:
            return f"{video}+ba[ext=m4a]/{video}+ba/{video}"
        return video

    @property
    def size_label(self):
        if self.size is None:
            return "размер неизвестен"
        prefix = "≈ " if self.estimated_size else ""
        return f"{prefix}{format_bytes(self.size)}"


def source_for_url(url):
    if any(character.isspace() for character in url):
        raise ValueError("Вставь одну ссылку.")
    parsed = urlsplit(url)
    host = (parsed.hostname or "").rstrip(".")
    if parsed.scheme in ("https", "http") and parsed.username is None:
        if host == "pin.it" or PINTEREST_DOMAIN.fullmatch(host):
            return "pinterest"
        if any(host == domain or host.endswith(f".{domain}") for domain in VIDEO_DOMAINS):
            return "video"
    raise ValueError("Вставь ссылку https:// или http:// из YouTube, ВК, ОК, TikTok или Pinterest.")


def require_programs(*names):
    missing = [name for name in names if shutil.which(name) is None]
    if missing:
        raise ValueError(f"Не хватает: {', '.join(missing)}. Открой «{launcher_name()}» для установки.")


def launcher_name():
    return "Запустить.cmd" if sys.platform == "win32" else "Запустить.command"


def read_video(command, url):
    result = subprocess.run(
        [*command, "--dump-single-json", "--skip-download", "--", url],
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise ValueError("Не удалось получить форматы. Проверь ссылку и сообщения yt-dlp выше.")
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("yt-dlp не вернул данные о видео.") from error
    if info.get("_type") in {"playlist", "multi_video"}:
        raise ValueError("Вставь ссылку на отдельный ролик.")
    return info


def format_bytes(size):
    for unit in ("Б", "КиБ", "МиБ", "ГиБ"):
        if size < 1024 or unit == "ГиБ":
            return f"{size:.2f} {unit}"
        size /= 1024


def stream_size(fmt, duration):
    if fmt.get("filesize"):
        return fmt["filesize"], False
    if fmt.get("filesize_approx"):
        return fmt["filesize_approx"], True
    bitrate = fmt.get("tbr")
    if not bitrate and fmt.get("vcodec") == "none":
        bitrate = fmt.get("abr")
    if not bitrate and fmt.get("acodec") == "none":
        bitrate = fmt.get("vbr")
    if bitrate and duration:
        return round(bitrate * 1000 / 8 * duration), True
    return None, False


def available_formats(info):
    formats = info.get("formats") or [info]
    duration = info.get("duration")
    # yt-dlp returns formats from least to most preferred.
    audio_formats = [
        fmt for fmt in formats
        if fmt.get("vcodec") == "none" and fmt.get("acodec") not in ("none", None)
        and fmt.get("has_drm") is not True
    ]
    audio = next((fmt for fmt in reversed(audio_formats) if fmt.get("ext") == "m4a"),
                 audio_formats[-1] if audio_formats else None)
    audio_size = stream_size(audio, duration)[0] if audio is not None else None

    choices = {}
    for fmt in formats:
        if fmt.get("vcodec") == "none" or fmt.get("has_drm") is True:
            continue
        format_id = fmt.get("format_id") or ""
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", format_id):
            continue
        width, height = fmt.get("width") or None, fmt.get("height") or None
        key = (width, height) if width or height else (format_id,)
        video_only = fmt.get("acodec") == "none"
        size, estimated_size = stream_size(fmt, duration)
        if video_only and audio is not None:
            size = size + audio_size if size is not None and audio_size is not None else None
            estimated_size = True
        choices[key] = VideoFormat(
            format_id, width, height, fmt.get("fps"), video_only, size, estimated_size,
        )
    return sorted(
        reversed(choices.values()),
        key=lambda fmt: (min(fmt.width, fmt.height) if fmt.width and fmt.height else fmt.height or 0,
                         (fmt.width or 0) * (fmt.height or 0), fmt.width or 0),
        reverse=True,
    )


def select_format(formats):
    for number, fmt in enumerate(formats, 1):
        print(f"  {number:2}. {fmt.label} · {fmt.size_label}")
    while True:
        answer = input("\nНомер качества (Enter — первое в списке): ").strip()
        try:
            number = int(answer or "1")
        except ValueError:
            number = 0
        if 1 <= number <= len(formats):
            return formats[number - 1]
        print(f"Введи число от 1 до {len(formats)}.")


def progress_line(progress, label):
    total = progress.get("total_bytes") or progress.get("total_bytes_estimate")
    downloaded = progress.get("downloaded_bytes")
    percent = None
    if progress.get("status") == "finished":
        percent = 100
    elif total and downloaded is not None:
        percent = min(99.9, 100 * downloaded / total)
    elif progress.get("fragment_count") and progress.get("fragment_index") is not None:
        percent = min(99.9, 100 * progress["fragment_index"] / progress["fragment_count"])

    filled = int((percent or 0) / 5)
    bar = "█" * filled + "░" * (20 - filled)
    percent_label = f"{percent:.1f}%" if percent is not None else "—%"
    speed = progress.get("speed")
    speed_label = f"{format_bytes(speed)}/с" if speed is not None else "—"
    return f"{label} [{bar}] {percent_label:>6}  {speed_label}"


def run_download(command):
    interactive = sys.stdout.isatty()
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    ) as process:
        progress_width = 0
        try:
            for raw_line in process.stdout:
                line = raw_line.rstrip("\r\n")
                if line.startswith(PROGRESS_PREFIX):
                    if interactive:
                        codec, _, payload = line[len(PROGRESS_PREFIX):].partition("\t")
                        try:
                            progress = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        label = "Аудио" if codec == "none" else "Видео"
                        progress_text = progress_line(progress, label)
                        progress_width = max(progress_width, len(progress_text))
                        print(f"\r{progress_text:<{progress_width}}", end="", flush=True)
                elif line:
                    if progress_width:
                        print(flush=True)
                        progress_width = 0
                    print(line, flush=True)
        finally:
            if progress_width:
                print(flush=True)
        return process.wait()


def download(command, url, quality, directory):
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"%(title).120B [%(extractor_key)s-%(id)s] [{quality.filename_quality}].%(ext)s"
    print(f"\nСкачиваю {quality.label} в {directory}\n", flush=True)
    exit_code = run_download([
        *command,
        "--no-simulate", "--quiet", "--progress", "--newline", "--no-overwrites",
        "--progress-delta", "0.25",
        "--progress-template", f"download:{PROGRESS_PREFIX}%(info.vcodec)s\t%(progress)j",
        "--format", quality.selector,
        "--merge-output-format", "mp4/mkv",
        "--paths", str(directory), "--output", filename,
        "--print", "after_move:Готово: %(filepath)s",
        "--", url,
    ])
    if exit_code:
        raise ValueError("Скачивание не завершилось. Причина указана в сообщениях yt-dlp выше.")


def download_pinterest(url, directory):
    directory.mkdir(parents=True, exist_ok=True)
    print(f"Скачиваю фото из Pinterest в {directory}\n", flush=True)
    result = subprocess.run([
        "gallery-dl", "--config-ignore", "--directory", str(directory),
        "--filter", IMAGE_FILTER,
        "--", url,
    ])
    if result.returncode:
        raise ValueError("Не удалось скачать фото. Проверь ссылку и сообщения gallery-dl выше.")


def main():
    parser = argparse.ArgumentParser(
        description="Скачать видео из YouTube, ВК, ОК и TikTok или фото из Pinterest.",
        epilog=f"Открой «{launcher_name()}», чтобы установить недостающие программы.",
    )
    parser.add_argument("url", nargs="?", help="ссылка, которую также можно ввести после запуска")
    parser.add_argument(
        "--output-dir", type=Path,
        help="папка для скачивания (по умолчанию ~/Downloads/Video или ~/Downloads/Pinterest)",
    )
    args = parser.parse_args()

    try:
        url = (args.url or input("Ссылка на видео или Pinterest: ")).strip()
        source = source_for_url(url)
        if source == "pinterest":
            require_programs("gallery-dl")
            directory = args.output_dir or DOWNLOADS_DIRECTORY / "Pinterest"
            download_pinterest(url, directory.expanduser().resolve())
            return 0

        require_programs("yt-dlp", "ffmpeg")
        directory = args.output_dir or DOWNLOADS_DIRECTORY / "Video"
        command = [
            "yt-dlp", "--ignore-config", "--encoding", "utf-8", "--no-playlist", "--playlist-items", "1",
        ]
        print("Получаю список форматов…", flush=True)
        info = read_video(command, url)
        formats = available_formats(info)
        if not formats:
            raise ValueError("yt-dlp не нашёл доступных видеоформатов для этого ролика.")
        print(f"\n{info.get('title') or 'Доступные форматы'}")
        quality = select_format(formats)
        download(command, url, quality, directory.expanduser().resolve())
    except (KeyboardInterrupt, EOFError):
        print("\nОтменено.", file=sys.stderr)
        return 130
    except (ValueError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
