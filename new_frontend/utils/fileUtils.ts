import { API_ENDPOINTS } from '../src/api/config';

export interface SaveImageResult {
  success: boolean;
  filePath?: string;
  error?: string;
}

/**
 * Generates a SHA-256 hash of a base64 image string for deduplication.
 */
export const generateImageHash = async (dataUrl: string): Promise<string> => {
  const base64Data = dataUrl.replace(/^data:image\/\w+;base64,/, '');
  const msgUint8 = new TextEncoder().encode(base64Data);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
};

export const saveMergedImage = async (
  dataUrl: string,
  municipality: string,
  index: number
): Promise<SaveImageResult> => {
  try {
    const base64Data = dataUrl.replace(/^data:image\/\w+;base64,/, '');
    const hash = await generateImageHash(dataUrl);

    const response = await fetch(API_ENDPOINTS.SAVE_IMAGES, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        images: [{ image_base64: base64Data, index, hash }],
        municipality
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to save image: ${response.status}`);
    }

    const result = await response.json();
    console.log(`[FileUtils] Saved image via backend: ${result.files?.[0]}`);

    return { success: true, filePath: result.files?.[0] };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`[FileUtils] Failed to save merged image:`, error);
    return { success: false, error: errorMessage };
  }
};

export const saveAllMergedImages = async (
  dataUrls: string[],
  municipality: string = 'unified'
): Promise<SaveImageResult> => {
  try {
    const images = await Promise.all(dataUrls.map(async (dataUrl, index) => {
      const base64Data = dataUrl.replace(/^data:image\/\w+;base64,/, '');
      const hash = await generateImageHash(dataUrl);
      return { image_base64: base64Data, index, hash };
    }));

    const response = await fetch(API_ENDPOINTS.SAVE_IMAGES, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ images, municipality })
    });

    if (!response.ok) {
      throw new Error(`Failed to save images: ${response.status}`);
    }

    const result = await response.json();
    console.log(`[FileUtils] Saved ${result.saved_count} images via backend (Unified Pool)`);

    return { success: true, filePath: `Saved ${result.saved_count} files` };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`[FileUtils] Failed to save merged images:`, error);
    return { success: false, error: errorMessage };
  }
};

export const base64ToBuffer = (dataUrl: string): Buffer => {
  const base64Data = dataUrl.replace(/^data:image\/\w+;base64,/, '');
  return Buffer.from(base64Data, 'base64');
};

/**
 * Triggers a browser download for a given content string.
 */
export const downloadFile = (content: string, fileName: string, contentType: string) => {
  const blob = new Blob([content], { type: contentType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
