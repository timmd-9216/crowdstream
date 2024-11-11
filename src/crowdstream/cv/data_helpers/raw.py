import yt_dlp  # type: ignore
from tqdm import tqdm  # type: ignore


def download_video(url: str, file_name: str) -> None:
    """
    Descarga un video de YouTube a partir de su URL usando la librería yt_dlp.

    Args:
        url (str): URL del video.
        file_name (str): Nombre del archivo de salida.
    """
    
    ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": f"{file_name}.%(ext)s",
            "merge_output_format": "mp4",
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_raw_videos() -> None:
    """
    Esta función descarga los videos de demo utilizados para desarrollo.
    """
    urls = [
        "https://www.youtube.com/watch?v=ait5SPkmGME",
        "https://www.youtube.com/watch?v=TJ3lSLe9eWo",
        "https://www.youtube.com/watch?v=2RVnp_4C6Ug",
        "https://www.youtube.com/watch?v=wAEBK_HqbwQ"
    ]

    for i, url in tqdm(enumerate(urls)):
        
        file_name = f"data/raw/people_dancing_demo_{i}"
        
        download_video(url, file_name)
            
            
if __name__ == "__main__":
    download_raw_videos()