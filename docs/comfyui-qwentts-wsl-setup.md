# ComfyUI-QwenTTS setup for Reddit automation on WSL

This setup is for Kelvin's local machine:

- WSL2 Ubuntu 24.04
- AMD Radeon RX 7900 XT
- Reddit automation project: `/home/kel/projects/postmortem`
- ComfyUI target URL: `http://127.0.0.1:8188`

The correct path is AMD ROCm on WSL plus a manual ComfyUI install. Do not use the NVIDIA ComfyUI setup path.

## 1. Install ROCm for AMD WSL

Run in WSL:

```bash
cd ~

sudo apt update
sudo apt install -y wget git python3-venv python3-pip ffmpeg

wget https://repo.radeon.com/amdgpu-install/6.4.2.1/ubuntu/noble/amdgpu-install_6.4.60402-1_all.deb
sudo apt install -y ./amdgpu-install_6.4.60402-1_all.deb

sudo amdgpu-install -y --usecase=wsl,rocm --no-dkms

sudo usermod -a -G render,video "$USER"
```

Then restart WSL from Windows PowerShell:

```powershell
wsl --shutdown
```

Open WSL again.

## 2. Verify ROCm sees the GPU

```bash
rocminfo | grep -E "Name:|Marketing Name" | head -40
```

Expected: output should include something like `gfx1100` and Radeon RX 7900 XT.

If `rocminfo` fails, stop. The likely fix is updating AMD Adrenalin on Windows to a WSL-compatible version.

## 3. Install ComfyUI

```bash
mkdir -p ~/ai
cd ~/ai

git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip wheel setuptools
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.4

# Avoid replacing ROCm torch with CPU/CUDA torch from ComfyUI requirements.
grep -v -E '^(torch|torchvision|torchaudio)' requirements.txt > /tmp/comfyui-requirements-no-torch.txt
pip install -r /tmp/comfyui-requirements-no-torch.txt
```

Verify PyTorch ROCm:

```bash
python - <<'PY'
import torch
print("torch:", torch.__version__)
print("hip:", torch.version.hip)
print("gpu available:", torch.cuda.is_available())
print("device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO_GPU")
PY
```

Expected: `gpu available: True`.

If it says false, try:

```bash
export HSA_OVERRIDE_GFX_VERSION=11.0.0
```

Then rerun the Python check.

## 4. Install ComfyUI-QwenTTS

```bash
cd ~/ai/ComfyUI/custom_nodes

git clone https://github.com/1038lab/ComfyUI-QwenTTS.git
cd ComfyUI-QwenTTS

# Avoid replacing ROCm torch with CPU/CUDA torch from QwenTTS requirements.
grep -v -E '^(torch|torchvision|torchaudio)' requirements.txt > /tmp/qwentts-requirements-no-torch.txt
pip install -r /tmp/qwentts-requirements-no-torch.txt
```

## 5. Start ComfyUI

Run this from a terminal you can leave open:

```bash
cd ~/ai/ComfyUI
source .venv/bin/activate

export HSA_OVERRIDE_GFX_VERSION=11.0.0

python main.py --listen 127.0.0.1 --port 8188 --use-pytorch-cross-attention
```

Leave that terminal running.

## 6. Verify ComfyUI from another WSL terminal

```bash
curl -s http://127.0.0.1:8188/system_stats | python3 -m json.tool
```

Then check the QwenTTS nodes:

```bash
python3 - <<'PY'
import json
from urllib.request import urlopen

with urlopen("http://127.0.0.1:8188/object_info", timeout=10) as r:
    info = json.load(r)

for name in sorted(info):
    if "Qwen" in name or "TTS" in name or "Audio" in name:
        print(name)
PY
```

Required nodes for the Reddit integration:

```text
AILab_Qwen3TTSCustomVoice_Advanced
SaveAudioMP3
```

If these names are missing, ComfyUI-QwenTTS did not load correctly or an audio save node dependency is missing.

## 7. Switch the Reddit project to QwenTTS

Edit:

```text
/home/kel/projects/postmortem/config/config.yaml
```

Change:

```yaml
tts:
  provider: edge_tts
```

to:

```yaml
tts:
  provider: comfy_qwen_tts
```

Keep:

```yaml
tts:
  comfy_qwen_tts:
    base_url: http://127.0.0.1:8188
```

Suggested host voices:

```yaml
hosts:
  host_1:
    qwen_voice_id: Ryan
    voice_instruct: A dry, confident male host voice with crisp podcast pacing.
  host_2:
    qwen_voice_id: Serena
    voice_instruct: A skeptical, expressive female co-host voice with sharp comedic timing.
```

## 8. Notes and caveats

- First QwenTTS generation may be slow because models can download on first use.
- Keep `tts.provider: edge_tts` until ComfyUI is running and `/object_info` confirms the required nodes.
- The Reddit project treats ComfyUI-QwenTTS as an external HTTP service. Do not vendor or copy ComfyUI-QwenTTS code into the MIT project because that repository is GPL-3.0.
- The integration preserves the existing pipeline shape: one script line becomes one MP3 clip, then ffmpeg stitches the episode audio.
- Keep `unload_models: false` during episode generation to avoid reloading the model for every line.

## 9. Quick smoke check after ComfyUI is running

From the Reddit project:

```bash
cd /home/kel/projects/postmortem
source .venv/bin/activate

python - <<'PY'
from reddit_automation.clients.comfy_qwen_tts_client import ComfyQwenTTSClient
from reddit_automation.utils.config import load_config

config = load_config("config/config.yaml")
config["tts"]["provider"] = "comfy_qwen_tts"
client = ComfyQwenTTSClient(config)
path = client.generate("host_1", "This is a short Qwen TTS smoke test.")
print(path)
PY
```

Expected: prints a local `.mp3` path.
