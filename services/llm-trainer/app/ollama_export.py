"""학습된 LoRA 어댑터를 Ollama로 로드하기 위한 Modelfile 생성.

⚠️ 중요: Ollama의 `ADAPTER`는 **GGUF 포맷 어댑터**를 요구한다. PEFT는 safetensors로 저장하므로
llama.cpp의 변환이 필요하다:

    python llama.cpp/convert_lora_to_gguf.py <adapter_dir> --outfile adapter.gguf

그 후 아래 Modelfile로 등록:

    ollama create my-lora -f Modelfile
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("trainer")


def write_modelfile(adapter_dir: str, base_model: str, adapter_gguf: str = "adapter.gguf") -> str:
    modelfile = f"FROM {base_model}\nADAPTER ./{adapter_gguf}\n"
    path = os.path.join(adapter_dir, "Modelfile")
    with open(path, "w", encoding="utf-8") as f:
        f.write(modelfile)
    logger.info("Modelfile 작성: %s (GGUF 변환 후 `ollama create`)", path)
    return path
