/**
 * Utility functions for script data compression and decompression
 */
import pako from 'pako';

/**
 * Decompresses base64 encoded script data
 * @param {string} compressedData - Base64 encoded compressed script data
 * @returns {Object} Decompressed script data object
 */
export default function decompressScriptData(compressedData) {
  if (!compressedData) {
    return null;
  }

  try {
    const binaryString = atob(compressedData);

    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    const decompressed = pako.inflate(bytes, { to: 'string' });

    return JSON.parse(decompressed);
  } catch (error) {
    console.error('Error decompressing script data:', error);
    return null;
  }
}
