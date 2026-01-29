#!/usr/bin/env python3
"""
MEMORY-EFFICIENT PARALLEL PROCESSING FOR KIMI-VL-A3B-THINKING-2506
For GPUs with limited VRAM (16GB or less)
Uses 4-bit quantization + smaller batch sizes
"""
import torch
from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig
from PIL import Image
import json
from pathlib import Path
from tqdm import tqdm
import multiprocessing as mp
import gc
import os


def extract_thinking_and_summary(text: str, bot: str = "◁think▷", eot: str = "◁/think▷"):
    """
    Extract thinking process and final summary from Kimi-VL-A3B-Thinking output
    Returns: (thinking_text, summary_text)
    """
    if bot in text and eot not in text:
        return "", text
    if eot in text:
        thinking = text[text.index(bot) + len(bot):text.index(eot)].strip()
        summary = text[text.index(eot) + len(eot):].strip()
        return thinking, summary
    return "", text


def init_worker_quantized(model_name, gpu_id):
    """
    Initialize worker with 4-bit quantized Kimi-VL model
    Uses much less VRAM per worker
    Each process gets its own CUDA context on the same GPU
    """
    global worker_model, worker_processor, my_gpu, my_worker_id
    
    # Use process ID as worker identifier (unique per process)
    my_worker_id = os.getpid() % 1000  # Modulo for readability
    my_gpu = gpu_id
    
    # CRITICAL: Each process must initialize its own CUDA context
    # This allows multiple processes to use the same GPU in parallel
    if torch.cuda.is_available():
        # Set device for this process
        torch.cuda.set_device(gpu_id)
        # Create a CUDA stream for this worker to enable parallel execution
        torch.cuda.current_stream(gpu_id).synchronize()
    
    print(f"[Worker PID {os.getpid()} (ID {my_worker_id}) on GPU {gpu_id}] Loading 4-bit quantized Kimi-VL model...")
    
    # 4-bit quantization config
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"
    )
    
    # Load model with quantization (uses ~3-4GB instead of ~14GB)
    # Each process loads its own copy of the model
    worker_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=quantization_config,
        device_map={"": gpu_id},  # All workers use same GPU but different contexts
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    worker_model.eval()
    
    worker_processor = AutoProcessor.from_pretrained(
        model_name,
        trust_remote_code=True
    )
    
    # Check VRAM usage for this process
    allocated = torch.cuda.memory_allocated(gpu_id) / 1024**3
    print(f"[Worker {my_worker_id}] Ready! Using {allocated:.2f} GB VRAM")


def process_image_quantized(args):
    """Process image with quantized Kimi-VL model"""
    global worker_model, worker_processor, my_gpu, my_worker_id
    
    image_path = args
    worker_id = my_worker_id
    
    try:
        # Load and resize image for memory efficiency
        image = Image.open(image_path).convert('RGB')
        
        # Resize large images to save memory
        # Kimi-VL-A3B-Thinking-2506 supports up to 1792x1792 (3.2M pixels)
        max_size = 1792
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        prompt = """Analyze this document and provide:
{
  "document_type": "string",
  "category": "string", 
  "summary": "string"
}"""
        
        # Kimi-VL message format
        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt}
            ]
        }]
        
        # Apply chat template
        text = worker_processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Process inputs
        inputs = worker_processor(
            text=[text],
            images=[image],
            return_tensors="pt"
        )
        inputs = inputs.to(my_gpu)
        
        # Generate with memory efficiency
        # Kimi-VL-A3B-Thinking benefits from higher temperature (0.2-0.5)
        with torch.inference_mode():
            generated_ids = worker_model.generate(
                **inputs,
                max_new_tokens=512,  # Thinking models may need more tokens
                do_sample=True,
                temperature=0.3,  # Higher temp for thinking model
            )
        
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        
        output = worker_processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True
        )[0]
        
        # Extract thinking and summary from output
        thinking, summary = extract_thinking_and_summary(output)
        
        # Parse JSON from summary
        cleaned = summary.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0]
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0]
        
        result = json.loads(cleaned.strip())
        result["filename"] = Path(image_path).name
        result["success"] = True
        result["worker"] = worker_id
        
        # Include thinking if present
        if thinking:
            result["thinking"] = thinking[:500]  # Truncate thinking for storage
        
        # Aggressive cleanup
        del inputs, image
        torch.cuda.empty_cache()
        gc.collect()
        
        return result
        
    except Exception as e:
        return {
            "filename": Path(image_path).name,
            "success": False,
            "error": str(e),
            "worker": worker_id
        }


def process_folder_memory_efficient(
    folder_path,
    output_json_path="document_analysis.json",
    model_name="moonshotai/Kimi-VL-A3B-Thinking-2506",
    num_workers=3,
    gpu_id=0
):
    """
    Memory-efficient parallel processing on SINGLE GPU with Kimi-VL-A3B-Thinking-2506
    
    With 4-bit quantization:
    - Each worker uses ~3-4 GB VRAM
    - Each worker process gets its own CUDA context
    - Multiple processes can run concurrently on the same GPU
    - 16GB GPU can handle 3-4 workers
    - 24GB GPU can handle 5-6 workers
    - 48GB GPU can handle 10-12 workers
    
    NOTE: All workers share the same GPU (gpu_id) but run in parallel through 
    separate processes with independent CUDA contexts.
    """
    print("="*80)
    print("MEMORY-EFFICIENT PARALLEL PROCESSING WITH KIMI-VL-A3B-THINKING-2506")
    print("="*80)
    print(f"Model: {model_name}")
    print(f"Features: Thinking model with reasoning capabilities")
    print(f"Resolution: Supports up to 1792x1792 (3.2M pixels)")
    print(f"Quantization: 4-bit (saves ~70% VRAM)")
    print(f"Workers: {num_workers}")
    print(f"GPU: {gpu_id}")
    print(f"Expected VRAM per worker: ~3-4 GB")
    print(f"Total expected VRAM: ~{num_workers * 3.5:.1f} GB")
    print("="*80 + "\n")
    
    # Get images
    image_folder = Path(folder_path)
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
    image_files = [
        str(f) for f in image_folder.iterdir() 
        if f.suffix.lower() in image_extensions
    ]
    
    print(f"📁 Found {len(image_files)} images\n")
    
    if not image_files:
        return []
    
    # Prepare tasks - just image paths (worker IDs handled in init)
    tasks = image_files
    
    # Initialize workers
    print(f"🚀 Starting {num_workers} workers with 4-bit quantization...\n")
    print("⏳ Loading models (this takes 30-60 seconds)...\n")
    
    # Create worker pool - each worker is a separate process
    # All workers will use the same GPU (gpu_id) but with independent CUDA contexts
    # This enables true parallel processing on a single GPU
    with mp.Pool(
        processes=num_workers,
        initializer=init_worker_quantized,
        initargs=(model_name, gpu_id)
    ) as pool:
        # Process in parallel - imap_unordered processes tasks as workers become available
        results = []
        with tqdm(total=len(tasks), desc="Processing images") as pbar:
            # imap_unordered allows parallel execution - results come in as they complete
            for result in pool.imap_unordered(process_image_quantized, tasks):
                results.append(result)
                pbar.update(1)
    
    # Save results
    output_path = Path(output_json_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Summary
    successful = sum(1 for r in results if r.get('success', False))
    failed = len(results) - successful
    
    print(f"\n{'='*80}")
    print("COMPLETE")
    print('='*80)
    print(f"📄 Output: {output_path}")
    print(f"📊 Total: {len(results)}")
    print(f"✓ Success: {successful} ({successful/len(results)*100:.1f}%)")
    print(f"✗ Failed: {failed}")
    
    # Worker stats
    worker_counts = {}
    for r in results:
        if 'worker' in r:
            w = r['worker']
            worker_counts[w] = worker_counts.get(w, 0) + 1
    
    print(f"\n📊 Images per worker:")
    for w, count in sorted(worker_counts.items()):
        print(f"  Worker {w}: {count} images")
    
    return results


if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Memory-efficient parallel processing with Kimi-VL-A3B-Thinking-2506"
    )
    parser.add_argument("--folder_path", 
                       default="/home/mindmap/Desktop/dutch-parking-detection/images")
    parser.add_argument("-o", "--output", 
                       default="document_analysis.json")
    parser.add_argument("--model", 
                       default="moonshotai/Kimi-VL-A3B-Thinking-2506",
                       help="Model name (default: moonshotai/Kimi-VL-A3B-Thinking-2506)")
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=1,
        help="Number of workers (default: 3 for 16GB GPU)"
    )
    parser.add_argument("--gpu",
                       type=int,
                       default=0,
                       help="GPU ID")
    
    args = parser.parse_args()
    
    # Recommend workers based on GPU
    if torch.cuda.is_available():
        gpu_mem = torch.cuda.get_device_properties(args.gpu).total_memory / 1024**3
        recommended = int(gpu_mem / 4)  # ~4GB per worker
        print(f"\n💡 GPU {args.gpu} has {gpu_mem:.1f} GB")
        print(f"💡 Recommended workers: {recommended}")
        if args.workers > recommended:
            print(f"⚠️  WARNING: You chose {args.workers} workers, might run out of memory!")
        print()
    
    results = process_folder_memory_efficient(
        args.folder_path,
        args.output,
        args.model,
        args.workers,
        args.gpu
    )
    
    # Samples
    successful = [r for r in results if r.get('success')]
    if successful:
        print(f"\n{'='*80}")
        print("SAMPLES:")
        print('='*80)
        for r in successful[:2]:
            print(json.dumps(r, indent=2, ensure_ascii=False))