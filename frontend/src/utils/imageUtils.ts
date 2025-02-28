/**
 * Utility functions for handling images in the application
 */

/**
 * Checks if a URL is an IPFS URL and returns a fallback if needed
 * @param url The original image URL
 * @param fallbackUrl The fallback URL to use if the original is an IPFS URL or invalid
 * @returns A safe URL to use for image loading
 */
export const getSafeImageUrl = (url: string | undefined | null, fallbackUrl: string = '/assets/pumpfun-logo.png'): string => {
  // If URL is undefined or null, return fallback
  if (!url) {
    return fallbackUrl;
  }

  // Check if it's an IPFS URL
  if (url.includes('ipfs.io/ipfs/') || url.includes('ipfs://')) {
    // For now, we'll just return the fallback for IPFS URLs
    // In the future, we could implement a proxy or gateway solution
    return fallbackUrl;
  }

  // Return the original URL if it's not IPFS
  return url;
};

/**
 * Handles image loading errors by setting the source to a fallback image
 * @param event The error event from the image
 * @param fallbackUrl The fallback URL to use
 */
export const handleImageError = (event: React.SyntheticEvent<HTMLImageElement, Event>, fallbackUrl: string = '/assets/pumpfun-logo.png') => {
  const img = event.target as HTMLImageElement;
  img.src = fallbackUrl;
};
