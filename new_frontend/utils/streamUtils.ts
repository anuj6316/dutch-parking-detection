export interface StreamUpdate {
  type: 'log' | 'progress' | 'final_result' | 'error';
  message?: string;
  value?: number;
  data?: any;
}

export async function parseStreamResponse(
  response: Response,
  onUpdate: (update: StreamUpdate) => void
): Promise<void> {
  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  if (!reader) return;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const update = JSON.parse(line);
        onUpdate(update);
      } catch (e) {
        console.error("Error parsing stream line:", e, line);
      }
    }
  }
}
