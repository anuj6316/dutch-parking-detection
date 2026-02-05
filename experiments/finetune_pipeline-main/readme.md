# 🚀 LLM Fine-Tuning Pipeline

Fine-tune a small LLM on your company documents and run it locally with Ollama.

---

## 📋 Overview

This pipeline:
1. **Extracts Q&A pairs** from your documents (PDF/DOCX/TXT)
2. **Fine-tunes** a small LLM (Qwen 1.5B) on your data
3. **Exports** to GGUF format for Ollama

---

## 🔧 Requirements

### For Dataset Generation (No GPU needed)
- Python 3.8+
- Ollama with `llama3.2` model

### For Training (GPU required)
- Python 3.10
- NVIDIA GPU with 8GB+ VRAM
- CUDA 11.8 or 12.1

---

## 📦 Installation

```bash
# Clone repo
git clone https://github.com/YOUR_USERNAME/llm-finetune.git
cd llm-finetune

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install PyTorch with CUDA
pip install torch --index-url https://download.pytorch.org/whl/cu121

# Install Unsloth
pip install "unsloth[cu121] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps trl peft accelerate bitsandbytes xformers

# Install dataset generation dependencies
pip install pypdf python-docx requests
```

---

## 🚀 Usage

### Step 1: Generate Training Dataset

```bash
# Start Ollama
ollama run llama3.2

# Generate dataset from your document
python generate_dataset.py your_document.pdf
```

**Output:** `dataset.jsonl`

---

### Step 2: Fine-Tune Model

```bash
python train_local.py
```

**Configuration** (edit `train_local.py`):
```python
DATASET_PATH = "dataset.jsonl"
MODEL_CHOICE = 1  # 1=Qwen-1.5B, 2=Qwen-3B, 3=Llama-1B
EPOCHS = 10
```

**Output:** `./output/` folder containing:
- `*.gguf` - The fine-tuned model
- `Modelfile` - Ollama configuration

**Time:** ~10-15 minutes on T4/RTX 3060

---

### Step 3: Run with Ollama

```bash
cd output
ollama create my-assistant -f Modelfile
ollama run my-assistant
```

---

## 📁 Project Structure

```
llm-finetune/
├── generate_dataset.py   # Creates training data from documents
├── train_local.py        # Fine-tunes model (requires GPU)
├── requirements.txt      # Python dependencies
├── README.md            
└── output/               # Generated after training
    ├── *.gguf           # Model file for Ollama
    └── Modelfile        # Ollama config
```

---

## ⚙️ Model Options

| Choice | Model | VRAM | Speed |
|--------|-------|------|-------|
| 1 | Qwen2.5-1.5B | ~6GB | ⭐ Recommended |
| 2 | Qwen2.5-3B | ~8GB | Better quality |
| 3 | Llama-3.2-1B | ~5GB | Fastest |
| 4 | Llama-3.2-3B | ~8GB | Good balance |
| 5 | Gemma-2-2B | ~6GB | Alternative |

---

## 🔧 Troubleshooting

### Unsloth import errors
```bash
pip uninstall unsloth unsloth-zoo -y
pip install "unsloth[cu121] @ git+https://github.com/unslothai/unsloth.git"
```

### Out of memory
- Use smaller model: `MODEL_CHOICE = 3`
- Reduce batch size: `BATCH_SIZE = 2`

### Model gives generic answers
- Increase epochs: `EPOCHS = 15`
- Add more training data (50+ examples recommended)

---
