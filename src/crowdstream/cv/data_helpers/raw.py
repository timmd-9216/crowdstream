import yt_dlp  # type: ignore


def download_raw_videos() -> None:
    urls = [
        "https://www.youtube.com/watch?v=ait5SPkmGME",
        "https://www.youtube.com/watch?v=TJ3lSLe9eWo",
        "https://www.youtube.com/watch?v=2RVnp_4C6Ug",
        "https://www.youtube.com/watch?v=wAEBK_HqbwQ"
    ]

    for i, url in enumerate(urls):

        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": f"people_dancing_demo_{i}.%(ext)s",
            "merge_output_format": "mp4",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])