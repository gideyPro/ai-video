import sys
import os
import json
import glob
import subprocess
import shutil
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="AI Video Studio")

# Setup directories
os.makedirs("static", exist_ok=True)
os.makedirs("assets", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("config", exist_ok=True)
os.makedirs("scenes", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

os.makedirs("logs", exist_ok=True)
LOG_FILE = "logs/app.log"

def run_with_log(cmd, background=False):
    with open(LOG_FILE, "a") as f:
        f.write(f"\n--- Running: {' '.join(cmd)} ---\n")
    if background:
        f = open(LOG_FILE, "a")
        subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
    else:
        with open(LOG_FILE, "a") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)

@app.get("/api/logs")
def get_logs():
    if not os.path.exists(LOG_FILE):
        return {"logs": ""}
    with open(LOG_FILE, "r") as f:
        return {"logs": "".join(f.readlines()[-200:])}


@app.get("/")
def index():
    return FileResponse("static/index.html")

# Config API
@app.get("/api/config")
def get_config():
    if not os.path.exists("config/config.json"):
        return {}
    with open("config/config.json") as f:
        return json.load(f)

@app.post("/api/config")
def save_config(config: dict):
    with open("config/config.json", "w") as f:
        json.dump(config, f, indent=2)
    return {"status": "ok"}

# Assets API
@app.post("/api/upload")
async def upload_asset(file: UploadFile = File(...)):
    file_path = f"assets/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "ok", "filename": file.filename, "path": file_path}

@app.get("/api/assets")
def list_assets():
    assets = []
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.mp4", "*.mp3", "*.wav"]:
        for f in glob.glob(f"assets/{ext}"):
            assets.append(os.path.basename(f))
    return {"assets": sorted(assets)}

# Scenes API
@app.get("/api/scenes")
def list_scenes():
    scenes = [os.path.basename(f) for f in glob.glob("scenes/*.json")]
    return {"scenes": sorted(scenes)}

@app.get("/api/scenes/{filename}")
def get_scene(filename: str):
    if not os.path.exists(f"scenes/{filename}"):
        raise HTTPException(status_code=404)
    with open(f"scenes/{filename}") as f:
        return json.load(f)

@app.post("/api/scenes/{filename}")
def save_scene(filename: str, scene_data: dict):
    with open(f"scenes/{filename}", "w") as f:
        json.dump(scene_data, f, indent=2)
    return {"status": "ok"}

@app.delete("/api/scenes/{filename}")
def delete_scene(filename: str):
    if os.path.exists(f"scenes/{filename}"):
        os.remove(f"scenes/{filename}")
    return {"status": "ok"}


@app.get("/api/fonts")
def list_fonts():
    import os
    fonts = []
    for d in ["/usr/share/fonts", "/data/data/com.termux/files/usr/share/fonts"]:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith((".ttf", ".otf")):
                        fonts.append(os.path.join(root, f))
    return {"fonts": sorted(fonts)}

# Actions
class GenerateScriptReq(BaseModel):
    topic: str
    duration: int
    filename: str

@app.post("/api/generate-script")
def generate_script(req: GenerateScriptReq):
    out_path = f"scenes/{req.filename}"
    cmd = [sys.executable, "scripts/script_generator.py", req.topic, "--duration", str(req.duration), "--output", out_path]
    run_with_log(cmd, background=False)
    if os.path.exists(out_path):
        return {"status": "ok"}
    raise HTTPException(status_code=500)

class GenerateTTSReq(BaseModel):
    filename: str
    voice: str = "en-US-AriaNeural"

@app.post("/api/generate-tts")
def generate_tts(req: GenerateTTSReq):
    scene_path = f"scenes/{req.filename}"
    audio_path = f"scenes/{req.filename.replace('.json', '.mp3')}"
    cmd = [sys.executable, "scripts/tts_generator.py", scene_path, audio_path, "--voice", req.voice]
    run_with_log(cmd, background=False)
    if os.path.exists(audio_path):
        return {"status": "ok", "audio_path": audio_path}
    raise HTTPException(status_code=500)

class RenderReq(BaseModel):
    filename: str

@app.post("/api/render")
def render_video(req: RenderReq):
    scene_path = f"scenes/{req.filename}"
    audio_path = f"scenes/{req.filename.replace('.json', '.mp3')}"
    cmd = [sys.executable, "renderer/renderer.py", scene_path]
    if os.path.exists(audio_path):
        cmd.extend(["-a", audio_path])
    out_file = f"output/{req.filename.replace('.json', '.mp4')}"
    cmd.extend(["-o", out_file])
    run_with_log(cmd, background=True)
    return {"status": "started", "output": out_file}

# Preview API
@app.post("/api/preview")
def preview_scene(scene_data: dict):
    # Create a temporary JSON with just this scene for rendering one frame
    tmp_path = "output/preview_temp.json"
    preview_data = {
        "video": {"width": 1920, "height": 1080, "fps": 30},
        "scenes": [scene_data]
    }
    with open(tmp_path, "w") as f:
        json.dump(preview_data, f)
        
    cmd = [sys.executable, "renderer/renderer.py", tmp_path, "--preview-only"]
    subprocess.run(cmd)
    return {"status": "ok", "url": f"/output/preview.png?t={os.path.getmtime('output/preview.png') if os.path.exists('output/preview.png') else 0}"}

@app.get("/api/videos")
def list_videos():
    videos = [os.path.basename(f) for f in glob.glob("output/*.mp4")]
    return {"videos": sorted(videos)}

@app.get("/video/{filename}")
def serve_video(filename: str):
    return FileResponse(f"output/{filename}")

@app.get("/output/{filename}")
def serve_output(filename: str):
    return FileResponse(f"output/{filename}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
