# Video Loader

Утилита для macOS и Windows, которая скачивает видео с YouTube, ВКонтакте, Одноклассников и TikTok, а также изображения из Pinterest.

## Запуск

### Windows 10 и 11 (64-битные)

Скачай архив через **Code → Download ZIP**, распакуй его и дважды щёлкни **Запустить.cmd**. Для автоматической установки нужен WinGet из [App Installer](https://learn.microsoft.com/windows/package-manager/winget/).

### macOS

Для автоматической установки зависимостей нужен [Homebrew](https://brew.sh/).

```bash
git clone https://github.com/woyt1k/Video-Loader.git
cd Video-Loader
./Запустить.command
```

Файл **Запустить.command** также можно открыть двойным щелчком в Finder.

Оба файла запуска проверяют Python 3.10+, yt-dlp, FFmpeg, Deno и gallery-dl и устанавливают недостающие зависимости. Если всё уже установлено, программа сразу просит ссылку.

## Скачивание

1. Вставь ссылку на ролик или на Pinterest-пин. Поддерживаются короткие ссылки `pin.it`.
2. Для видео выбери номер качества. Можно выбрать 4K, если площадка отдаёт ролик в этом разрешении. Рядом с каждым вариантом указан размер файла, а `≈` обозначает оценку.
3. Во время загрузки видео Терминал показывает шкалу, процент и скорость в одной строке. Если видео и звук доступны отдельными дорожками, программа скачивает их и объединяет через FFmpeg.

| Что скачивается | macOS | Windows |
| --- | --- | --- |
| Видео | `~/Downloads/Video` | `%USERPROFILE%\Downloads\Video` |
| Фото из Pinterest | `~/Downloads/Pinterest` | `%USERPROFILE%\Downloads\Pinterest` |

Чтобы указать другую папку, запусти программу с параметром `--output-dir`. На macOS команда выглядит так.

```bash
./Запустить.command --output-dir "$HOME/Movies/Video Loader"
```

На Windows в PowerShell используй эту команду.

```powershell
.\Запустить.cmd --output-dir "$env:USERPROFILE\Videos\Video Loader"
```
