import os
import json
import torch

DATASET_PATH = "dataset.jsonl"  # Your training data

# Model choices:
# 1 = Qwen2.5-1.5B (recommended, ~1GB)
# 2 = Qwen2.5-3B (~2GB)
# 3 = Llama-3.2-1B (~700MB)
# 4 = Llama-3.2-3B (~2GB)
# 5 = Gemma-2-2B (~1.5GB)
MODEL_CHOICE = 1

EPOCHS = 10
LEARNING_RATE = 2e-4
BATCH_SIZE = 4
MAX_SEQ_LENGTH = 2048
LORA_R = 32
LORA_ALPHA = 64

OUTPUT_DIR = "./output"

MODELS = {
    1: ("Qwen2.5-1.5B", "unsloth/Qwen2.5-1.5B-Instruct-bnb-4bit"),
    2: ("Qwen2.5-3B", "unsloth/Qwen2.5-3B-Instruct-bnb-4bit"),
    3: ("Llama-3.2-1B", "unsloth/Llama-3.2-1B-Instruct-bnb-4bit"),
    4: ("Llama-3.2-3B", "unsloth/Llama-3.2-3B-Instruct-bnb-4bit"),
    5: ("Gemma-2-2B", "unsloth/gemma-2-2b-it-bnb-4bit"),
}

def main():
    print("=" * 60)
    print(" LOCAL FINE-TUNING SCRIPT")
    print("=" * 60)
    
    # Check GPU
    if not torch.cuda.is_available():
        print(" No GPU detected! This script requires NVIDIA GPU.")
        return
    
    print(f" GPU: {torch.cuda.get_device_name(0)}")
    print(f" VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    print()
    
    # Check dataset
    if not os.path.exists(DATASET_PATH):
        print(f" Dataset not found: {DATASET_PATH}")
        print("   Run: python generate_dataset.py your_document.pdf")
        return
    
    # Import Unsloth
    print(" Loading Unsloth...")
    from unsloth import FastLanguageModel
    
    # Load model
    model_name, model_id = MODELS[MODEL_CHOICE]
    print(f" Loading model: {model_name}")
    
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_id,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,
        load_in_4bit=True,
    )
    print(" Model loaded!")
    
    # Add LoRA
    print(" Adding LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )
    model.print_trainable_parameters()
    
    # Load dataset
    print(f" Loading dataset: {DATASET_PATH}")
    from datasets import Dataset
    
    ROLE_MAP = {"human": "user", "gpt": "assistant", "system": "system"}
    conversations = []
    
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            msgs = obj.get("conversations") or obj.get("messages") or []
            chat = []
            for turn in msgs:
                role = ROLE_MAP.get(turn.get("from", turn.get("role", "")), "user")
                content = turn.get("value", turn.get("content", ""))
                chat.append({"role": role, "content": content})
            if chat:
                text = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=False)
                conversations.append({"text": text})
    
    ds = Dataset.from_list(conversations)
    split = ds.train_test_split(test_size=0.1, seed=42)
    train_ds, eval_ds = split["train"], split["test"]
    print(f" Train: {len(train_ds)}, Eval: {len(eval_ds)}")
    
    # Train
    print()
    print("=" * 60)
    print(f"TRAINING ({EPOCHS} epochs)")
    print("=" * 60)
    
    from trl import SFTTrainer
    from transformers import TrainingArguments
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_num_proc=2,
        packing=False,
        args=TrainingArguments(
            output_dir=OUTPUT_DIR,
            num_train_epochs=EPOCHS,
            per_device_train_batch_size=BATCH_SIZE,
            gradient_accumulation_steps=2,
            learning_rate=LEARNING_RATE,
            lr_scheduler_type="cosine",
            warmup_ratio=0.05,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=10,
            eval_strategy="epoch",
            save_strategy="epoch",
            save_total_limit=1,
            optim="adamw_8bit",
            seed=42,
            report_to="none",
        ),
    )
    
    trainer.train()
    print("\nTraining complete!")
    
    # Test
    print()
    print("=" * 60)
    print("TESTING")
    print("=" * 60)
    
    FastLanguageModel.for_inference(model)
    
    def ask(question):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question}
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=200,
            temperature=0.3,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        if "assistant" in response.lower():
            response = response[response.lower().rfind("assistant") + len("assistant"):]
        return response.strip()
    
    # Test questions - UPDATE THESE!
    questions = [
        "Where are MindMap Digital's offices located?",
        "What is CleverCruit?",
        "How many projects has MindMap Digital delivered?",
    ]
    
    for q in questions:
        print(f"\n {q}")
        print(f"💬 {ask(q)[:300]}")
    
    # Export GGUF
    print()
    print("=" * 60)
    print("EXPORTING TO GGUF")
    print("=" * 60)
    
    model.save_pretrained_gguf(
        OUTPUT_DIR,
        tokenizer,
        quantization_method="q4_K_M",
    )
    
    # Find GGUF file
    gguf_file = None
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(".gguf"):
            gguf_file = f
            break
    
    if not gguf_file:
        for f in os.listdir("."):
            if f.endswith(".gguf"):
                gguf_file = f
                os.rename(f, os.path.join(OUTPUT_DIR, f))
                break
    
    # Create Modelfile
    modelfile_path = os.path.join(OUTPUT_DIR, "Modelfile")
    with open(modelfile_path, "w") as f:
        f.write(f'FROM ./{gguf_file}\n')
        f.write('SYSTEM "You are a helpful assistant."\n')
        f.write('PARAMETER temperature 0.7\n')
    
    print(f" GGUF saved: {OUTPUT_DIR}/{gguf_file}")
    print(f"Modelfile saved: {modelfile_path}")
    
    # Done
    print()
    print("=" * 60)
    print(" COMPLETE!")
    print("=" * 60)
    print(f"""
Output files in: {OUTPUT_DIR}/
  - {gguf_file} (the model)
  - Modelfile (Ollama config)

To use with Ollama:
  cd {OUTPUT_DIR}
  ollama create my-assistant -f Modelfile
  ollama run my-assistant
""")


if __name__ == "__main__":
    main()
