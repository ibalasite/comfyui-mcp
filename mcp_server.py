"""
Local Media Generation MCP Server
Exposes ComfyUI (image/img2img) and AudioLDM2 (audio) as Claude MCP tools.
Supports: SDXL, Flux.1-schnell (GGUF), LoRA, batch, img2img, audio Base64.
"""

import asyncio
import base64
import os
import time
import uuid
from pathlib import Path

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import ImageContent, TextContent, Tool

# ── Config ─────────────────────────────────────────────────────────────────────
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
AUDIO_URL   = os.getenv("AUDIO_URL",   "http://127.0.0.1:8189")
OUTPUT_DIR  = Path(os.getenv("OUTPUT_DIR", "C:/comfyuimcp/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
POLL_TIMEOUT = int(os.getenv("COMFYUI_POLL_TIMEOUT", "180"))

FLUX_GGUF   = "flux1-schnell-Q4_K_S.gguf"   # in models/unet/
SDXL_CKPT   = "sd_xl_base_1.0.safetensors"  # in models/checkpoints/

# ── Workflow builders ──────────────────────────────────────────────────────────

def _sdxl_workflow(prompt: str, negative: str, width: int, height: int,
                   steps: int, seed: int, batch: int, lora: str | None) -> dict:
    model_ref = ["4", 0]
    clip_ref  = ["4", 1]
    nodes: dict = {
        "4": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": SDXL_CKPT}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"width": width, "height": height, "batch_size": batch}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"text": prompt, "clip": clip_ref}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"text": negative, "clip": clip_ref}},
        "3": {"class_type": "KSampler",
              "inputs": {"seed": seed, "steps": steps, "cfg": 7.0,
                         "sampler_name": "euler", "scheduler": "normal",
                         "denoise": 1.0, "model": model_ref,
                         "positive": ["6", 0], "negative": ["7", 0],
                         "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": "mcp_sdxl"}},
    }
    if lora:
        nodes["10"] = {"class_type": "LoraLoader",
                       "inputs": {"model": ["4", 0], "clip": ["4", 1],
                                  "lora_name": lora,
                                  "strength_model": 0.8, "strength_clip": 0.8}}
        nodes["3"]["inputs"]["model"] = ["10", 0]
        nodes["6"]["inputs"]["clip"]  = ["10", 1]
        nodes["7"]["inputs"]["clip"]  = ["10", 1]
    return nodes


def _flux_workflow(prompt: str, width: int, height: int,
                   steps: int, seed: int, batch: int) -> dict:
    return {
        "1": {"class_type": "UnetLoaderGGUF",
              "inputs": {"unet_name": FLUX_GGUF}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "clip_l.safetensors", "type": "flux"}},
        "3": {"class_type": "CLIPTextEncode",
              "inputs": {"text": prompt, "clip": ["2", 0]}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": width, "height": height, "batch_size": batch}},
        "5": {"class_type": "KSampler",
              "inputs": {"seed": seed, "steps": steps, "cfg": 1.0,
                         "sampler_name": "euler", "scheduler": "simple",
                         "denoise": 1.0, "model": ["1", 0],
                         "positive": ["3", 0], "negative": ["3", 0],
                         "latent_image": ["4", 0]}},
        "6": {"class_type": "VAELoader",
              "inputs": {"vae_name": "flux_ae.safetensors"}},
        "7": {"class_type": "VAEDecode",
              "inputs": {"samples": ["5", 0], "vae": ["6", 0]}},
        "8": {"class_type": "SaveImage",
              "inputs": {"images": ["7", 0], "filename_prefix": "mcp_flux"}},
    }


def _img2img_workflow(prompt: str, negative: str, image_b64: str,
                      denoise: float, steps: int, seed: int) -> dict:
    return {
        "4":  {"class_type": "CheckpointLoaderSimple",
               "inputs": {"ckpt_name": SDXL_CKPT}},
        "10": {"class_type": "ETN_LoadImageBase64",
               "inputs": {"image": image_b64}},
        "11": {"class_type": "VAEEncode",
               "inputs": {"pixels": ["10", 0], "vae": ["4", 2]}},
        "6":  {"class_type": "CLIPTextEncode",
               "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7":  {"class_type": "CLIPTextEncode",
               "inputs": {"text": negative, "clip": ["4", 1]}},
        "3":  {"class_type": "KSampler",
               "inputs": {"seed": seed, "steps": steps, "cfg": 7.0,
                          "sampler_name": "euler", "scheduler": "normal",
                          "denoise": denoise, "model": ["4", 0],
                          "positive": ["6", 0], "negative": ["7", 0],
                          "latent_image": ["11", 0]}},
        "8":  {"class_type": "VAEDecode",
               "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9":  {"class_type": "SaveImage",
               "inputs": {"images": ["8", 0], "filename_prefix": "mcp_i2i"}},
    }


# ── ComfyUI submit + poll ──────────────────────────────────────────────────────

async def _comfyui_run(workflow: dict) -> list[Path]:
    client_id = str(uuid.uuid4())
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{COMFYUI_URL}/prompt",
                         json={"prompt": workflow, "client_id": client_id})
        r.raise_for_status()
        prompt_id = r.json()["prompt_id"]

    deadline = time.time() + POLL_TIMEOUT
    async with httpx.AsyncClient(timeout=10) as c:
        while time.time() < deadline:
            await asyncio.sleep(2)
            hist = (await c.get(f"{COMFYUI_URL}/history/{prompt_id}")).json()
            if prompt_id not in hist:
                continue
            results = []
            for node_out in hist[prompt_id]["outputs"].values():
                for img in node_out.get("images", []):
                    raw = (await c.get(f"{COMFYUI_URL}/view",
                                       params={"filename": img["filename"],
                                               "subfolder": img.get("subfolder", ""),
                                               "type": img.get("type", "output")})).content
                    p = OUTPUT_DIR / f"img_{uuid.uuid4().hex[:8]}.png"
                    p.write_bytes(raw)
                    results.append(p)
            if results:
                return results
    raise TimeoutError(f"ComfyUI timed out after {POLL_TIMEOUT}s")


# ── AudioLDM2 ─────────────────────────────────────────────────────────────────

async def _audio_run(prompt: str, negative: str, duration: float, steps: int) -> tuple[Path, str]:
    async with httpx.AsyncClient(timeout=180) as c:
        r = await c.post(f"{AUDIO_URL}/generate",
                         json={"prompt": prompt, "negative_prompt": negative,
                               "duration": duration, "steps": steps})
        r.raise_for_status()
        data = r.json()
    audio_path = Path(data["path"])
    if audio_path.exists():
        b64 = base64.b64encode(audio_path.read_bytes()).decode()
        return audio_path, b64
    out = OUTPUT_DIR / f"sfx_{uuid.uuid4().hex[:8]}.wav"
    b64 = data["audio_b64"]
    out.write_bytes(base64.b64decode(b64))
    return out, b64


# ── MCP Server ────────────────────────────────────────────────────────────────

app = Server("local-media-gen")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_image",
            description=(
                "Generate images locally on RTX 5090 via ComfyUI. "
                "Supports SDXL (default) or Flux.1-schnell, LoRA, and batch generation. "
                "Returns images inline."
            ),
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt":   {"type": "string", "description": "Positive prompt"},
                    "negative": {"type": "string", "default": "ugly, blurry, low quality, watermark",
                                 "description": "Negative prompt"},
                    "model":    {"type": "string", "enum": ["sdxl", "flux"],
                                 "default": "sdxl", "description": "Model to use"},
                    "width":    {"type": "integer", "default": 1024},
                    "height":   {"type": "integer", "default": 1024},
                    "steps":    {"type": "integer", "default": 20},
                    "batch":    {"type": "integer", "default": 1, "description": "Number of images (1–4)"},
                    "lora":     {"type": "string", "description": "LoRA filename (SDXL only, optional)"},
                },
            },
        ),
        Tool(
            name="img2img",
            description=(
                "Image-to-image: provide a base64-encoded PNG and a prompt, "
                "ComfyUI will transform it via SDXL on the RTX 5090."
            ),
            inputSchema={
                "type": "object",
                "required": ["prompt", "image_b64"],
                "properties": {
                    "prompt":    {"type": "string"},
                    "image_b64": {"type": "string", "description": "Base64-encoded source PNG"},
                    "negative":  {"type": "string", "default": "ugly, blurry, low quality"},
                    "denoise":   {"type": "number", "default": 0.75,
                                  "description": "Denoising strength 0.0–1.0"},
                    "steps":     {"type": "integer", "default": 20},
                },
            },
        ),
        Tool(
            name="generate_audio",
            description=(
                "Generate a sound effect or music clip locally via AudioLDM2 on RTX 5090. "
                "Returns file path AND base64 audio data."
            ),
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt":    {"type": "string", "description": "Sound description"},
                    "negative":  {"type": "string", "default": "low quality, noise, distortion"},
                    "duration":  {"type": "number",  "default": 3.0},
                    "steps":     {"type": "integer", "default": 25},
                },
            },
        ),
        Tool(
            name="list_outputs",
            description="List recently generated files in the output folder.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent]:

    if name == "generate_image":
        prompt   = arguments["prompt"]
        negative = arguments.get("negative", "ugly, blurry, low quality, watermark")
        model    = arguments.get("model", "sdxl")
        width    = min(max(int(arguments.get("width",  1024)), 256), 2048) // 64 * 64
        height   = min(max(int(arguments.get("height", 1024)), 256), 2048) // 64 * 64
        steps    = min(max(int(arguments.get("steps",  20)),   5),   50)
        batch    = min(max(int(arguments.get("batch",  1)),    1),   4)
        lora     = arguments.get("lora")
        seed     = int(time.time()) % 2**31

        try:
            if model == "flux":
                wf = _flux_workflow(prompt, width, height, steps, seed, batch)
            else:
                wf = _sdxl_workflow(prompt, negative, width, height, steps, seed, batch, lora)
            paths = await _comfyui_run(wf)
            out: list[TextContent | ImageContent] = [
                TextContent(type="text", text=f"Generated {len(paths)} image(s) via {model.upper()}:")
            ]
            for p in paths:
                b64 = base64.b64encode(p.read_bytes()).decode()
                out.append(ImageContent(type="image", data=b64, mimeType="image/png"))
            return out
        except Exception as e:
            return [TextContent(type="text", text=f"Image generation failed: {e}")]

    if name == "img2img":
        prompt    = arguments["prompt"]
        image_b64 = arguments["image_b64"]
        negative  = arguments.get("negative", "ugly, blurry, low quality")
        denoise   = float(arguments.get("denoise", 0.75))
        steps     = min(max(int(arguments.get("steps", 20)), 5), 50)
        seed      = int(time.time()) % 2**31
        try:
            wf    = _img2img_workflow(prompt, negative, image_b64, denoise, steps, seed)
            paths = await _comfyui_run(wf)
            out: list[TextContent | ImageContent] = [
                TextContent(type="text", text=f"img2img complete ({len(paths)} image(s)):")
            ]
            for p in paths:
                b64 = base64.b64encode(p.read_bytes()).decode()
                out.append(ImageContent(type="image", data=b64, mimeType="image/png"))
            return out
        except Exception as e:
            return [TextContent(type="text", text=f"img2img failed: {e}")]

    if name == "generate_audio":
        prompt   = arguments["prompt"]
        negative = arguments.get("negative", "low quality, noise, distortion")
        duration = min(max(float(arguments.get("duration", 3.0)), 1.0), 10.0)
        steps    = min(max(int(arguments.get("steps", 25)), 5), 50)
        try:
            path, b64 = await _audio_run(prompt, negative, duration, steps)
            return [
                TextContent(type="text", text=f"Audio saved: {path}"),
                TextContent(type="text", text=f"data:audio/wav;base64,{b64}"),
            ]
        except Exception as e:
            return [TextContent(type="text", text=f"Audio generation failed: {e}")]

    if name == "list_outputs":
        files = sorted(OUTPUT_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        lines = [f"{f.name} ({f.stat().st_size // 1024} KB)" for f in files[:20]]
        return [TextContent(type="text",
                            text=f"Output dir: {OUTPUT_DIR}\n\n" + ("\n".join(lines) or "Empty"))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
