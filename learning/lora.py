import logging
import os
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.learning.lora")


class LoRATrainer:
    def __init__(self, model_dir: str | Path, base_model: str = "microsoft/phi-2") -> None:
        self._model_dir = Path(model_dir)
        self._model_dir.mkdir(parents=True, exist_ok=True)
        self._base_model = base_model
        self._trained = False

    @property
    def available(self) -> bool:
        try:
            import peft
            import torch
            import transformers
            return True
        except ImportError:
            return False

    def train(self, examples: list[dict[str, str]],
              output_name: str = "lora_adapter",
              num_epochs: int = 3) -> dict[str, Any]:
        if not self.available:
            return {"success": False, "error": "Dependencies not installed"}

        try:
            import torch
            from datasets import Dataset
            from peft import LoraConfig, get_peft_model
            from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments

            logger.info(f"Starting LoRA training on {len(examples)} examples")

            texts = [f"{ex.get('input', '')} {ex.get('output', '')}" for ex in examples]
            dataset = Dataset.from_dict({"text": texts})

            tokenizer = AutoTokenizer.from_pretrained(self._base_model)
            tokenizer.pad_token = tokenizer.eos_token

            def tokenize(batch):
                return tokenizer(batch["text"], truncation=True, padding=True, max_length=512)

            tokenized = dataset.map(tokenize, batched=True)

            model = AutoModelForCausalLM.from_pretrained(
                self._base_model,
                torch_dtype=torch.float16,
                device_map="auto"
            )

            lora_cfg = LoraConfig(
                r=8,
                lora_alpha=32,
                target_modules=["q_proj", "v_proj"],
                lora_dropout=0.1,
                bias="none",
                task_type="CAUSAL_LM"
            )
            model = get_peft_model(model, lora_cfg)

            output_path = self._model_dir / output_name
            args = TrainingArguments(
                output_dir=str(output_path),
                num_train_epochs=num_epochs,
                per_device_train_batch_size=4,
                save_steps=500,
                logging_steps=10,
                save_total_limit=2,
                remove_unused_columns=False
            )

            import transformers
            trainer = transformers.Trainer(
                model=model,
                args=args,
                train_dataset=tokenized,
            )
            trainer.train()
            trainer.save_model(str(output_path))
            tokenizer.save_pretrained(str(output_path))

            self._trained = True
            report = {
                "success": True,
                "model_path": str(output_path),
                "epochs": num_epochs,
                "examples": len(examples)
            }
            logger.info(f"LoRA training complete: {output_path}")
            return report

        except Exception as e:
            logger.error(f"LoRA training failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def predict(self, text: str, adapter_path: str | None = None) -> str:
        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer

            path = adapter_path or str(self._model_dir / "lora_adapter")
            if not os.path.exists(path):
                return ""

            tokenizer = AutoTokenizer.from_pretrained(self._base_model)
            model = AutoModelForCausalLM.from_pretrained(
                self._base_model,
                torch_dtype=torch.float16,
                device_map="auto"
            )
            model = PeftModel.from_pretrained(model, path)

            inputs = tokenizer(text, return_tensors="pt")
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=100)

            return tokenizer.decode(outputs[0], skip_special_tokens=True)

        except Exception as e:
            logger.error(f"LoRA prediction failed: {e}")
            return ""

    def list_adapters(self) -> list[str]:
        return [d.name for d in self._model_dir.iterdir() if d.is_dir()]

    def remove_adapter(self, name: str) -> bool:
        path = self._model_dir / name
        if path.exists():
            shutil.rmtree(path)
            logger.info(f"Removed adapter: {name}")
            return True
        return False
