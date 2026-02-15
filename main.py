from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
import yt_dlp
import os
import uuid

app = FastAPI()

@app.get("/download")
async def download_audio(url: str = Query(..., description="URL de YouTube")):
    # Creamos un nombre único para evitar conflictos entre usuarios
    file_id = str(uuid.uuid4())
    output_path = f"/tmp/{file_id}"
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_path}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = f"{output_path}.mp3"
        display_name = f"{info['title']}.mp3"

    # Devolvemos el archivo al usuario y lo borramos después (opcional)
    return FileResponse(
        path=filename, 
        filename=display_name, 
        media_type='audio/mpeg'
    )
  
