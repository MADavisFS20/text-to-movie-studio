"""LoRA fine-tune template (UNTESTED). See docs/FINETUNE.md.
Check the base model id exists on Hugging Face and that your unsloth/trl versions match the API below."""
import argparse
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig

p = argparse.ArgumentParser()
p.add_argument("--base", required=True)
p.add_argument("--data", required=True)
p.add_argument("--out", default="out/lora")
p.add_argument("--max-len", type=int, default=4096)
p.add_argument("--epochs", type=int, default=2)
a = p.parse_args()

model, tok = FastLanguageModel.from_pretrained(a.base, max_seq_length=a.max_len, load_in_4bit=True)
model = FastLanguageModel.get_peft_model(
    model, r=16, lora_alpha=32, lora_dropout=0,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
)
ds = load_dataset("json", data_files=a.data, split="train")
ds = ds.map(lambda r: {"text": tok.apply_chat_template(r["messages"], tokenize=False)})
SFTTrainer(
    model=model, tokenizer=tok, train_dataset=ds,
    args=SFTConfig(
        dataset_text_field="text", max_seq_length=a.max_len, per_device_train_batch_size=2,
        gradient_accumulation_steps=8, num_train_epochs=a.epochs, learning_rate=2e-4,
        logging_steps=10, output_dir=a.out, bf16=True,
    ),
).train()
model.save_pretrained(a.out)
tok.save_pretrained(a.out)
