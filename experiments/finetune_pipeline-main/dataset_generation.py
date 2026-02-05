import json
import os
from typing import List, Dict
from pypdf import PdfReader
from docx import Document
import requests


class MaximumExtractor:
    """Extracts maximum training examples from document in ShareGPT format"""
    
    def __init__(self, model: str = "llama3.2", system_prompt: str = "You are a helpful assistant."):
        self.model = model
        self.system_prompt = system_prompt
        self.ollama_url = "http://localhost:11434"
        
        if not self._check_ollama():
            raise RuntimeError("Ollama is not running! Run: ollama run llama3.2")
    
    def _check_ollama(self) -> bool:
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _call_llm(self, prompt: str) -> str:
        """Call Ollama LLM"""
        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 4000
                }
            },
            timeout=240
        )
        
        return response.json()["response"]
    
    def process_file(self, file_path: str) -> Dict:
        """Process document and extract MAXIMUM training data"""
        
        print("📄 Extracting text from document...")
        raw_text = self._extract_text(file_path)
        
        print(f"   Extracted {len(raw_text)} characters")
        print()
        
        chunks = self._chunk_text(raw_text, chunk_size=1000)
        print(f"📝 Split into {len(chunks)} chunks for maximum extraction")
        print()
        
        all_training_data = []
        
        for i, chunk in enumerate(chunks, 1):
            print(f"🤖 Processing chunk {i}/{len(chunks)}...")
            print(f"   Length: {len(chunk)} chars")
            
            training_examples = self._extract_from_chunk(chunk)
            
            if training_examples:
                all_training_data.extend(training_examples)
                print(f"   ✓ Extracted {len(training_examples)} examples")
            else:
                print(f"   ⚠ No examples from this chunk")
            print()
        
        unique_data = self._remove_duplicates(all_training_data)
        print(f"✅ Total: {len(all_training_data)} examples ({len(unique_data)} unique)")
        
        return {
            "num_examples": len(unique_data),
            "training_data": unique_data
        }
    
    def _extract_text(self, file_path: str) -> str:
        """Extract text from PDF, DOCX, or TXT"""
        ext = file_path.lower().split('.')[-1]
        
        if ext == 'pdf':
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n\n"
            return text
        
        elif ext in ['docx', 'doc']:
            doc = Document(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        
        elif ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
    
    def _chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split text into smaller chunks for better extraction"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk.strip())
        
        return chunks
    
    def _extract_from_chunk(self, chunk: str) -> List[Dict]:
        """Extract training examples from a text chunk in ShareGPT format"""
        
        prompt = f"""Convert this text into question-answer training examples.

TEXT:
{chunk}

TASK:
Create 5-8 question-answer pairs from the text above.
Questions should be about the content in the text.
Answers should come directly from the text.

Format as JSON array with "question" and "answer" keys:
[
  {{"question": "question here", "answer": "answer from text"}},
  {{"question": "another question", "answer": "another answer"}}
]
 
Return ONLY the JSON array:"""

        response = self._call_llm(prompt)
        
        try:
            if "[" in response and "]" in response:
                start = response.find("[")
                end = response.rfind("]") + 1
                json_str = response[start:end]
                json_str = json_str.replace("```json", "").replace("```", "").strip()
                
                examples = json.loads(json_str)
                
                # Convert to ShareGPT format
                valid = []
                for ex in examples:
                    if isinstance(ex, dict):
                        # Handle both possible key formats from LLM
                        question = ex.get("question") or ex.get("input") or ""
                        answer = ex.get("answer") or ex.get("output") or ""
                        
                        if question.strip() and answer.strip() and len(answer) > 10:
                            sharegpt_example = {
                                "conversations": [
                                    {"from": "system", "value": self.system_prompt},
                                    {"from": "human", "value": question.strip()},
                                    {"from": "gpt", "value": answer.strip()}
                                ]
                            }
                            valid.append(sharegpt_example)
                
                return valid
            
            return []
                
        except Exception as e:
            print(f"   Error parsing: {e}")
            return []
    
    def _remove_duplicates(self, data: List[Dict]) -> List[Dict]:
        """Remove duplicate training examples"""
        seen = set()
        unique = []
        
        for item in data:
            # Extract question and answer from ShareGPT format
            conversations = item.get("conversations", [])
            question = ""
            answer = ""
            
            for conv in conversations:
                if conv["from"] == "human":
                    question = conv["value"]
                elif conv["from"] == "gpt":
                    answer = conv["value"]
            
            # Create a key from question + answer
            key = (question.lower().strip(), answer.lower().strip()[:100])
            
            if key not in seen:
                seen.add(key)
                unique.append(item)
        
        return unique
    
    def save_to_jsonl(self, training_data: List[Dict], output_path: str):
        """Save training data to JSONL format"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in training_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"\n✅ Saved {len(training_data)} examples to {output_path}")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python maximum_extractor_sharegpt.py <file_path> [system_prompt]")
        print()
        print("Examples:")
        print('  python maximum_extractor_sharegpt.py document.pdf')
        print('  python maximum_extractor_sharegpt.py document.pdf "You are a medical assistant."')
        sys.exit(1)
    
    file_path = sys.argv[1]
    system_prompt = sys.argv[2] if len(sys.argv) > 2 else "You are a helpful assistant."
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    print("=" * 70)
    print("🚀 MAXIMUM EXTRACTION MODE (ShareGPT Format)")
    print("=" * 70)
    print(f"System prompt: {system_prompt}")
    print()
    
    try:
        extractor = MaximumExtractor(system_prompt=system_prompt)
        result = extractor.process_file(file_path)
        
        if result['num_examples'] == 0:
            print("❌ No examples generated!")
            sys.exit(1)
        
        output_file = f"training_sharegpt_{os.path.basename(file_path).rsplit('.', 1)[0]}.jsonl"
        extractor.save_to_jsonl(result['training_data'], output_file)
        
        print()
        print("=" * 70)
        print("📊 RESULTS")
        print("=" * 70)
        print(f"Total examples: {result['num_examples']}")
        print(f"Output file: {output_file}")
        print()
        print("First 3 examples:")
        print("-" * 70)
        
        for i, ex in enumerate(result['training_data'][:3], 1):
            conversations = ex.get("conversations", [])
            question = ""
            answer = ""
            
            for conv in conversations:
                if conv["from"] == "human":
                    question = conv["value"]
                elif conv["from"] == "gpt":
                    answer = conv["value"]
            
            print(f"\n{i}. Human: {question[:80]}...")
            print(f"   GPT: {answer[:80]}...")
        
        print()
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
