"""
Local AudioLDM2 FastAPI server — listens on :8189
Uses diffusers AudioLDM2Pipeline (no audioldm2 package needed).
Run: python audio_server.py

Compatibility patch for transformers 4.40+:
  - _update_model_kwargs_for_generation removed from GPT2Model
  - _get_initial_cache_position API changed (cache_position KeyError)
  Both fixed by replacing generate_language_model with a version that
  manages past_key_values directly without calling either broken method.
"""

import base64
import os
import types
import uuid
from pathlib import Path

import soundfile as sf
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


def _patch_audioldm2_pipeline():
    """
    Patch diffusers AudioLDM2Pipeline.generate_language_model to work with
    transformers >= 4.40 which removed internal generation helper methods.
    Must be called before the pipeline is instantiated.
    """
    from diffusers import AudioLDM2Pipeline

    def generate_language_model(self, inputs_embeds=None, max_new_tokens=8, **model_kwargs):
        max_new_tokens = (
            max_new_tokens
            if max_new_tokens is not None
            else self.language_model.config.max_new_tokens
        )
        # Drop keys that no longer exist in newer transformers
        model_kwargs.pop("cache_position", None)
        model_kwargs.pop("attention_mask", None)

        for _ in range(max_new_tokens):
            model_inputs = {"inputs_embeds": inputs_embeds}
            if model_kwargs.get("past_key_values") is not None:
                model_inputs["past_key_values"] = model_kwargs["past_key_values"]

            output = self.language_model(
                **model_inputs, output_hidden_states=True, return_dict=True
            )
            next_hidden = output.hidden_states[-1]
            inputs_embeds = torch.cat([inputs_embeds, next_hidden[:, -1:, :]], dim=1)

            if getattr(output, "past_key_values", None) is not None:
                model_kwargs["past_key_values"] = output.past_key_values

        return inputs_embeds[:, -max_new_tokens:, :]

    AudioLDM2Pipeline.generate_language_model = generate_language_model


_patch_audioldm2_pipeline()

from diffusers import AudioLDM2Pipeline  # noqa: E402 (import after patch)

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "C:/Projects/comfyuimcp/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading AudioLDM2 pipeline...")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
pipe = AudioLDM2Pipeline.from_pretrained(
    "cvssp/audioldm2",
    torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
).to(DEVICE)
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
        audio = pipe(
            req.prompt,
            negative_prompt=req.negative_prompt,
            num_inference_steps=req.steps,
            audio_length_in_s=req.duration,
            guidance_scale=req.guidance_scale,
        ).audios[0]
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
