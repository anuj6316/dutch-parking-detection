    #!/bin/bash
# Complete fix for Kimi-VL transformers compatibility issue

echo "=========================================="
echo "Kimi-VL Transformers Fix Script"
echo "=========================================="
echo ""

# Step 1: Check current transformers version
echo "Step 1: Checking current transformers version..."
CURRENT_VERSION=$(python -c "import transformers; print(transformers.__version__)" 2>/dev/null)
echo "Current transformers version: $CURRENT_VERSION"

if [ "$CURRENT_VERSION" != "4.51.3" ]; then
    echo "❌ Wrong version detected. Need 4.51.3"
    echo ""
    echo "Step 2: Installing correct transformers version..."
    uv pip install --upgrade transformers==4.51.3
    
    if [ $? -eq 0 ]; then
        echo "✅ Transformers 4.51.3 installed"
    else
        echo "❌ Failed to install transformers"
        exit 1
    fi
else
    echo "✅ Correct version already installed"
fi

echo ""
echo "Step 3: Clearing Hugging Face cache (fixes cached incompatible files)..."

# Clear the specific Kimi-VL cached model files
CACHE_DIR="$HOME/.cache/huggingface/modules/transformers_modules/moonshotai"
if [ -d "$CACHE_DIR" ]; then
    echo "Found cached Kimi-VL files at: $CACHE_DIR"
    rm -rf "$CACHE_DIR"
    echo "✅ Cleared cached model files"
else
    echo "No cached files found (this is fine)"
fi

echo ""
echo "Step 4: Verifying installation..."
python3 << 'PYEOF'
import sys
try:
    import transformers
    print(f"✅ Transformers version: {transformers.__version__}")
    
    # Test the specific import that was failing
    from transformers.utils.import_utils import is_torch_fx_available
    print("✅ is_torch_fx_available import successful")
    
    import torch
    print(f"✅ PyTorch version: {torch.__version__}")
    print(f"✅ CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"✅ GPU Memory: {gpu_mem:.1f} GB")
    
    print("\n✅✅✅ All checks passed! ✅✅✅")
    print("\nYou can now run:")
    print("  uv run lightOnOcr.py --workers 2")
    
except ImportError as e:
    print(f"❌ Error: {e}")
    print("\nSomething is still wrong. Try:")
    print("  uv pip uninstall transformers")
    print("  uv pip install transformers==4.51.3")
    sys.exit(1)
PYEOF

echo ""
echo "=========================================="
echo "Fix Complete!"
echo "=========================================="