#!/bin/zsh

export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/Current/bin:$PATH"

cd -- "${0:A:h}" || exit 1

install_dependencies() {
    local -a missing=()
    local package
    if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
        missing+=(python)
    fi
    for package in yt-dlp ffmpeg deno gallery-dl; do
        if ! command -v "$package" >/dev/null 2>&1; then
            missing+=("$package")
        fi
    done
    if (( ${#missing[@]} == 0 )); then
        return 0
    fi

    if ! command -v brew >/dev/null 2>&1; then
        printf 'Для автоматической установки нужен Homebrew: https://brew.sh/\n' >&2
        return 1
    fi

    printf 'Устанавливаю недостающие программы: %s\n\n' "${(j:, :)missing}"
    if ! brew install "${missing[@]}"; then
        printf '\nУстановка прервалась. После устранения ошибки снова открой этот файл.\n' >&2
        return 1
    fi
    rehash
}

if install_dependencies; then
    python3 ./video_downloader.py "$@"
    exit_code=$?
else
    exit_code=1
fi

if [[ $exit_code != 130 && -t 0 ]]; then
    printf '\nНажми Enter, чтобы завершить. '
    read -r
fi

exit "$exit_code"
