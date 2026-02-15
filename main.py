import os
import uuid
import shutil
import asyncio
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
import yt_dlp

app = FastAPI(title="YouTube MP3 Downloader")

# --- INTERFAZ HTML (Modern & Dark Mode) ---
html_content = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YT Downloader Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style> body { font-family: 'Inter', sans-serif; } </style>
</head>
<body class="bg-[#0f172a] text-slate-200 flex items-center justify-center min-h-screen p-4">
    <div class="bg-[#1e293b] p-8 rounded-3xl shadow-2xl w-full max-w-md border border-slate-700/50">
        <div class="text-center mb-8">
            <div class="bg-blue-500/10 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"></path>
                </svg>
            </div>
            <h1 class="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">YT to MP3</h1>
            <p class="text-slate-400 mt-2">Descarga audio en alta calidad</p>
        </div>
        
        <form action="/download" method="get" id="dlForm" class="space-y-6">
            <div>
                <input type="url" name="url" id="url" required 
                    placeholder="Pega el enlace de YouTube aquí..." 
                    class="w-full p-4 rounded-xl bg-[#0f172a] border border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all text-white placeholder-slate-500">
            </div>
            
            <button type="submit" id="btn"
                class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 rounded-xl transition-all duration-300 transform active:scale-95 shadow-lg shadow-blue-900/20 flex items-center justify-center gap-2">
                <span>Preparar Descarga</span>
            </button>
        </form>

        <div id="loader" class="hidden mt-8 text-center animate-pulse">
            <div class="flex justify-center space-x-2 mb-3">
                <div class="w-2 h-2 bg-blue-400 rounded-full"></div>
                <div class="w-2 h-2 bg-blue-400 rounded-full"></div>
                <div class="w-2 h-2 bg-blue-400 rounded-full"></div>
            </div>
            <p class="text-sm text-blue-400 font-medium italic">Procesando audio... por favor espera.</p>
        </div>
    </div>

    <script>
        const form = document.getElementById('dlForm');
        const btn = document.getElementById('btn');
        const loader = document.getElementById('loader');

        form.onsubmit = () => {
            btn.disabled = true;
            btn.innerText = "Procesando...";
            btn.classList.add('opacity-50', 'cursor-not-allowed');
            loader.classList.remove('hidden');
            
            // Re-habilitar después de 20 segundos por si falla algo
            setTimeout(() => {
                btn.disabled = false;
                btn.innerText = "Preparar Descarga";
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
                loader.classList.add('hidden');
            }, 20000);
        };
    </script>
</body>
</html>
"""

# --- LÓGICA DE LIMPIEZA ---
def remove_file(path: str):
    """Borra el archivo después de enviarlo para no agotar el disco de Railway."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error borrando archivo: {e}")

# --- RUTAS DE LA API ---
@app.get("/", response_class=HTMLResponse)
async def index():
    return html_content

@app.get("/download")
async def download_audio(background_tasks: BackgroundTasks, url: str = Query(...)):
    # Identificador único para esta sesión de descarga
    file_id = str(uuid.uuid4())
    temp_path = f"/tmp/{file_id}"
    
    # Opciones de yt-dlp optimizadas para MP3
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{temp_path}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }

    try:
        # Ejecutar la descarga de forma síncrona (pero dentro de una ruta async de FastAPI)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extraer info para obtener el título real
            info = ydl.extract_info(url, download=True)
            real_filename = f"{temp_path}.mp3"
            clean_title = "".join([c for c in info['title'] if c.isalnum() or c in (' ', '-', '_')]).rstrip()
            download_name = f"{clean_title}.mp3"

        # Programar la eliminación del archivo para después de que se envíe la respuesta
        background_tasks.add_task(remove_file, real_filename)

        return FileResponse(
            path=real_filename, 
            filename=download_name, 
            media_type='audio/mpeg'
        )

    except Exception as e:
        # Limpiar si falla antes de terminar
        if os.path.exists(f"{temp_path}.mp3"):
            os.remove(f"{temp_path}.mp3")
        raise HTTPException(status_code=400, detail=f"Error en la descarga: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Railway inyecta el puerto automáticamente en la variable de entorno $PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
