"""PEFT/transformers LoRA 파인튜닝 파이프라인 (동기·CPU/GPU).

주의: 실제 학습은 잡 수신 시에만 실행된다(빌드/기동 시엔 모델 다운로드 없음).
dataset_ref는 'text' 컬럼을 가진 HF 데이터셋 이름 또는 로컬 경로를 가정 — 실제 데이터
형식에 맞게 반드시 조정할 것. target_modules는 모델 아키텍처마다 다르다(예: llama=q_proj,v_proj).
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("trainer")


def run_lora_training(job: dict, adapters_dir: str) -> str:
    # 무거운 의존성은 잡 처리 시 지연 임포트
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )

    base_model = job["base_model"]
    dataset_ref = job["dataset_ref"]
    epochs = int(job.get("epochs", 1))
    logger.info("LoRA 학습 시작 base=%s dataset=%s epochs=%s", base_model, dataset_ref, epochs)

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(base_model)

    lora = LoraConfig(
        r=8, lora_alpha=16, lora_dropout=0.05,
        target_modules=["q_proj", "v_proj"],  # TODO: 모델별 조정
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    ds = load_dataset(dataset_ref)
    train_split = ds["train"]

    def tokenize(batch: dict) -> dict:
        return tokenizer(batch["text"], truncation=True, max_length=512)

    tokenized = train_split.map(tokenize, batched=True, remove_columns=train_split.column_names)
    collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)

    out_dir = os.path.join(adapters_dir, base_model.replace("/", "_"))
    args = TrainingArguments(
        output_dir=out_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        logging_steps=10,
        save_strategy="no",
        report_to=[],
    )
    trainer = Trainer(model=model, args=args, train_dataset=tokenized, data_collator=collator)
    trainer.train()

    os.makedirs(out_dir, exist_ok=True)
    model.save_pretrained(out_dir)  # LoRA 어댑터(safetensors) 저장
    tokenizer.save_pretrained(out_dir)
    logger.info("LoRA 어댑터 저장: %s", out_dir)
    return out_dir
