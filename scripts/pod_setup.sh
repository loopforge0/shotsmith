#!/usr/bin/env bash
# Set up a RunPod GPU pod to render H3 Shot Studio's native-resolution takes: the same ComfyUI commit,
# PyTorch build, comfy-kitchen and model files as the local machine, all on /workspace so a stopped pod
# keeps them. Logs to /workspace/setup.log; the last line is "SETUP DONE" when ComfyUI is up on :8188.
#
#     scp -P <port> scripts/pod_setup.sh root@<ip>:/workspace/ && ssh ... 'nohup bash /workspace/pod_setup.sh &'
set -euo pipefail
exec >>/workspace/setup.log 2>&1
cd /workspace

COMFY_COMMIT=c06bf5f5
HF=https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main

if [ ! -d ComfyUI ]; then
  git clone https://github.com/comfyanonymous/ComfyUI.git
fi
git -C ComfyUI fetch --quiet origin
git -C ComfyUI checkout --quiet "$COMFY_COMMIT"

# Models download while Python packages install.
fetch() {
  local dir=ComfyUI/models/$1 name=$2
  mkdir -p "$dir"
  if [ ! -s "$dir/$name" ]; then
    curl -sSfL --retry 5 -C - -o "$dir/$name.part" "$HF/$1/$name"
    mv -f "$dir/$name.part" "$dir/$name"
  fi
  echo "model ready: $1/$name $(du -h "$dir/$name" | cut -f1)"
}
(
  fetch diffusion_models minimax_h3_ref2va_pruned_int8_convrot.safetensors &
  fetch text_encoders qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors &
  fetch vae minimax_h3_video_vae_fp16.safetensors &
  fetch vae minimax_h3_audio_vae_fp32.safetensors &
  wait
  echo "MODELS DONE"
) &
models=$!

if [ ! -x venv/bin/python ]; then
  uv venv --python 3.12 venv
fi
export VIRTUAL_ENV=/workspace/venv PATH=/workspace/venv/bin:$PATH
uv pip install --index-url https://download.pytorch.org/whl/cu130 \
  torch==2.11.0+cu130 torchvision==0.26.0+cu130 torchaudio==2.11.0+cu130
uv pip install -r ComfyUI/requirements.txt
python -c "import torch, comfy_kitchen; print('torch', torch.__version__, 'cuda', torch.version.cuda, torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0)); print('int8 attention', comfy_kitchen.int8_attention_is_available())"
echo "PACKAGES DONE"

wait $models
cd ComfyUI
nohup python main.py --listen 0.0.0.0 --port 8188 --use-ck-attention --fast fp16_accumulation \
  --preview-method none --disable-comfy-compiler >/workspace/comfyui.log 2>&1 &
until curl -sf http://127.0.0.1:8188/system_stats >/dev/null; do sleep 5; done
echo "SETUP DONE"
