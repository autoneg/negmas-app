/**
 * Composable for consistent negotiator color palette across all panels.
 * Supports up to 20 negotiators with distinct, visually pleasing colors.
 * Provides both standard and colorblind-friendly (Okabe-Ito based) palettes.
 */

/**
 * Standard color palette - 20 visually distinct colors
 * Designed for good contrast in both light and dark modes.
 * First 8 colors are primary/vibrant, remaining are more muted but still distinct.
 */
const STANDARD_COLORS = [
  '#3b82f6', // Blue
  '#ef4444', // Red
  '#10b981', // Emerald/Green
  '#f59e0b', // Amber/Orange
  '#8b5cf6', // Purple
  '#06b6d4', // Cyan
  '#f97316', // Orange
  '#ec4899', // Pink
  '#84cc16', // Lime
  '#14b8a6', // Teal
  '#a855f7', // Violet
  '#f43f5e', // Rose
  '#0ea5e9', // Sky
  '#22c55e', // Green
  '#eab308', // Yellow
  '#6366f1', // Indigo
  '#d946ef', // Fuchsia
  '#64748b', // Slate
  '#78716c', // Stone
  '#0d9488', // Teal-dark
]

/**
 * Colorblind-friendly palette based on Okabe-Ito and other research.
 * Extended to 20 colors while maintaining distinguishability.
 * https://jfly.uni-koeln.de/color/
 */
const COLORBLIND_COLORS = [
  '#0173b2', // Blue
  '#de8f05', // Orange
  '#029e73', // Green
  '#cc78bc', // Pink
  '#ca9161', // Brown
  '#fbafe4', // Light pink
  '#949494', // Gray
  '#ece133', // Yellow
  '#56b4e9', // Sky blue (lighter)
  '#009e73', // Bluish green
  '#f0e442', // Yellow (brighter)
  '#d55e00', // Vermillion
  '#cc79a7', // Reddish purple
  '#0072b2', // Blue (darker)
  '#e69f00', // Orange (brighter)
  '#666666', // Dark gray
  '#aa4499', // Purple
  '#44aa99', // Teal
  '#999933', // Olive
  '#882255', // Wine
]

/**
 * Check if colorblind mode is enabled
 */
function isColorBlindMode() {
  return document.documentElement.classList.contains('color-blind-mode')
}

/**
 * Get the color palette based on current mode
 * @returns {string[]} Array of hex color strings
 */
export function getNegotiatorColorPalette() {
  return isColorBlindMode() ? COLORBLIND_COLORS : STANDARD_COLORS
}

/**
 * Get color for a specific negotiator by index
 * @param {number} index - Negotiator index (0-based)
 * @param {string[]} [customColors] - Optional custom colors array (e.g., from negotiation.negotiator_colors)
 * @returns {string} Hex color string
 */
export function getNegotiatorColor(index, customColors = null) {
  // If custom colors provided and valid for this index, use them
  if (customColors && customColors.length > 0 && index < customColors.length) {
    return customColors[index]
  }
  
  const palette = getNegotiatorColorPalette()
  // Wrap around if more negotiators than colors
  return palette[index % palette.length]
}

/**
 * Get array of colors for N negotiators
 * @param {number} count - Number of negotiators
 * @param {string[]} [customColors] - Optional custom colors array
 * @returns {string[]} Array of hex color strings
 */
export function getNegotiatorColors(count, customColors = null) {
  // If custom colors provided with enough colors, use them
  if (customColors && customColors.length >= count) {
    return customColors.slice(0, count)
  }
  
  const palette = getNegotiatorColorPalette()
  const colors = []
  for (let i = 0; i < count; i++) {
    colors.push(palette[i % palette.length])
  }
  return colors
}

/**
 * Generate colors for negotiators, preferring passed colors but falling back to palette
 * This is the main function panels should use.
 * @param {Object} negotiation - Negotiation object with negotiator_names and optionally negotiator_colors
 * @returns {string[]} Array of hex color strings matching the number of negotiators
 */
export function getColorsForNegotiation(negotiation) {
  if (!negotiation) return []
  
  const count = negotiation.negotiator_names?.length || 2
  const customColors = negotiation.negotiator_colors
  
  return getNegotiatorColors(count, customColors)
}

/**
 * Vue composable hook for negotiator colors
 * Provides reactive functions that respond to colorblind mode changes
 */
export function useNegotiatorColors() {
  return {
    getNegotiatorColorPalette,
    getNegotiatorColor,
    getNegotiatorColors,
    getColorsForNegotiation,
    STANDARD_COLORS,
    COLORBLIND_COLORS,
  }
}

export default useNegotiatorColors
