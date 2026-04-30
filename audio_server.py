"""
Local AudioLDM2 FastAPI server — listens on :8189
Uses diffusers AudioLDM2Pipeline (no audioldm2 package needed).
Run: python audio_server.py
"""

import base64
import os
import uuid
from pathlib import Path

import soundfile as sf
import torch
import uvicorn
from diffusers import AudioLDM2Pipeline
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "C:/comfyuimcp/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Patch BEFORE any diffusers/pipeline import:
# transformers 4.40+ removed _update_model_kwargs_for_generation from GPT2Model
# but diffusers AudioLDM2Pipeline still calls it internally.
from transformers.models.gpt2 import modeling_gpt2 as _gpt2_mod
from transformers.generation.utils import GenerationMixin as _GenMixin
if not hasattr(_gpt2_mod.GPT2Model, "_update_model_kwargs_for_generation"):
    _gpt2_mod.GPT2Model._update_model_kwargs_for_generation = (
        _GenMixin._update_model_kwargs_for_generation
    )
if not hasattr(_gpt2_mod.GPT2LMHeadModel, "_update_model_kwargs_for_generation"):
    _gpt2_mod.GPT2LMHeadModel._update_model_kwargs_for_generation = (
        _GenMixin._update_model_kwargs_for_generation
    )

print("Loading AudioLDM2 pipeline via diffusers...")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
pipe = AudioLDM2Pipeline.from_pretrained(
    "cvssp/audioldm2",
    torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
)
pipe = pipe.to(DEVICE)
print(f"AudioLDM2 ready on {DEVICE}")

app = FastAPI(title="AudioLDM2 Local Server")


class AudioRequest(BaseModel):
    prompt: str
    negative_prompt: str = Field(default="low quality, noise, distortion")
    duration: float = Field(default=3.0, ge=1.0, le=10.0)
    steps: int = Field(default=25, ge=5, le=50)
    guidance_scale: float = Field(default=3.5, ge=1.0, le=10.0)


class AudioResponse(BaseModel):
    path: str
    audio_b64: str


@app.post("/generate", response_model=AudioResponse)
async def generate(req: AudioRequest):
    try:
        result = pipe(
            req.prompt,
            negative_prompt=req.negative_prompt,
            num_inference_steps=req.steps,
            audio_length_in_s=req.duration,
            guidance_scale=req.guidance_scale,
        )
        audio = result.audios[0]
        out_path = OUTPUT_DIR / f"sfx_{uuid.uuid4().hex[:8]}.wav"
        sf.write(str(out_path), audio, samplerate=16000)
        b64 = base64.b64encode(out_path.read_bytes()).decode()
        return AudioResponse(path=str(out_path), audio_b64=b64)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
async def health():
    return {"status": "ok", "device": DEVICE}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8189)
