import path from 'path';

const BASE_PATH = '/home/mindmap/Documents/dutch-parking-detection/new_frontend/public/merged-images';

export const getMergedImagesBasePath = (): string => {
  return BASE_PATH;
};

export const getMunicipalityDirectory = (municipality: string): string => {
  return path.join(BASE_PATH, municipality);
};

export const getMergedImagePath = (municipality: string, index: number): string => {
  const fileName = `merged-${municipality}-${index.toString().padStart(3, '0')}.jpg`;
  return path.join(getMunicipalityDirectory(municipality), fileName);
};

export const ensureDirectory = async (dirPath: string): Promise<void> => {
  try {
    const fs = await import('fs/promises');
    await fs.mkdir(dirPath, { recursive: true });
  } catch (error) {
    console.error(`Failed to create directory ${dirPath}:`, error);
    throw error;
  }
};
