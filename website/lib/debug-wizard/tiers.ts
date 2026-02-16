/**
 * Debug Wizard Tier Management
 *
 * Defines access tiers for the debugging wizard with different
 * feature limits and capabilities. Enables freemium model for
 * website deployment while preserving full features for local use.
 */

// ============================================================================
// Access Tier Definitions
// ============================================================================

/**
 * Access tier enum - determines feature limits
 */
export enum AccessTier {
  /** Free website trial - limited features */
  FREE = 'free',
  /** Registered users - expanded features */
  REGISTERED = 'registered',
  /** Pro subscription - full web features */
  PRO = 'pro',
  /** Local installation - unlimited */
  LOCAL = 'local',
  /** Enterprise deployment */
  ENTERPRISE = 'enterprise',
}

/**
 * Tier limit configuration
 */
export interface TierLimits {
  /** Maximum files per analysis */
  maxFiles: number | null;
  /** Maximum file size in MB */
  maxFileSizeMB: number | null;
  /** Whether folder upload is enabled */
  folderUploadEnabled: boolean;
  /** Whether historical correlation is enabled */
  historicalCorrelationEnabled: boolean;
  /** Maximum historical matches to return */
  maxHistoricalMatches: number;
  /** Daily request limit */
  dailyRequestLimit: number | null;
  /** Pattern storage quota in MB */
  patternStorageMB: number | null;
  /** Whether to show upgrade prompts */
  showUpgradeCTA: boolean;
  /** Whether advanced predictions are enabled */
  advancedPredictionsEnabled: boolean;
  /** Whether resolution recording is enabled */
  resolutionRecordingEnabled: boolean;
  /** Whether code suggestions are enabled */
  codeSuggestionsEnabled: boolean;
  /** API priority level */
  apiPriority: 'low' | 'normal' | 'high';
}

// ============================================================================
// Tier Limit Configurations
// ============================================================================

/**
 * Tier limits mapped by AccessTier
 */
export const TIER_LIMITS: Record<AccessTier, TierLimits> = {
  [AccessTier.FREE]: {
    maxFiles: 3,
    maxFileSizeMB: 0.5,
    folderUploadEnabled: false,
    historicalCorrelationEnabled: true,
    maxHistoricalMatches: 3,
    dailyRequestLimit: 10,
    patternStorageMB: 5,
    showUpgradeCTA: true,
    advancedPredictionsEnabled: false,
    resolutionRecordingEnabled: false,
    codeSuggestionsEnabled: false,
    apiPriority: 'low',
  },

  [AccessTier.REGISTERED]: {
    maxFiles: 5,
    maxFileSizeMB: 1.0,
    folderUploadEnabled: false,
    historicalCorrelationEnabled: true,
    maxHistoricalMatches: 5,
    dailyRequestLimit: 50,
    patternStorageMB: 25,
    showUpgradeCTA: true,
    advancedPredictionsEnabled: true,
    resolutionRecordingEnabled: true,
    codeSuggestionsEnabled: false,
    apiPriority: 'normal',
  },

  [AccessTier.PRO]: {
    maxFiles: 20,
    maxFileSizeMB: 5.0,
    folderUploadEnabled: true,
    historicalCorrelationEnabled: true,
    maxHistoricalMatches: 20,
    dailyRequestLimit: 500,
    patternStorageMB: 500,
    showUpgradeCTA: false,
    advancedPredictionsEnabled: true,
    resolutionRecordingEnabled: true,
    codeSuggestionsEnabled: true,
    apiPriority: 'high',
  },

  [AccessTier.LOCAL]: {
    maxFiles: null, // Unlimited
    maxFileSizeMB: null, // Unlimited
    folderUploadEnabled: true,
    historicalCorrelationEnabled: true,
    maxHistoricalMatches: 100,
    dailyRequestLimit: null, // Unlimited
    patternStorageMB: null, // Unlimited
    showUpgradeCTA: false,
    advancedPredictionsEnabled: true,
    resolutionRecordingEnabled: true,
    codeSuggestionsEnabled: true,
    apiPriority: 'high',
  },

  [AccessTier.ENTERPRISE]: {
    maxFiles: null, // Unlimited
    maxFileSizeMB: null, // Unlimited
    folderUploadEnabled: true,
    historicalCorrelationEnabled: true,
    maxHistoricalMatches: 100,
    dailyRequestLimit: null, // Unlimited
    patternStorageMB: null, // Unlimited
    showUpgradeCTA: false,
    advancedPredictionsEnabled: true,
    resolutionRecordingEnabled: true,
    codeSuggestionsEnabled: true,
    apiPriority: 'high',
  },
};

// ============================================================================
// Tier Display Information
// ============================================================================

/**
 * User-facing tier information for display
 */
export interface TierDisplayInfo {
  name: string;
  description: string;
  price: string;
  features: string[];
  limitations: string[];
  ctaText: string;
  ctaLink: string;
}

/**
 * Display information for each tier
 */
export const TIER_DISPLAY: Record<AccessTier, TierDisplayInfo> = {
  [AccessTier.FREE]: {
    name: 'Free Trial',
    description: 'Try the debugging wizard with limited features',
    price: 'Free',
    features: [
      'Analyze up to 3 files',
      'Basic error classification',
      'Top 3 historical matches',
      '10 analyses per day',
    ],
    limitations: [
      'No folder uploads',
      'No resolution recording',
      'No code suggestions',
    ],
    ctaText: 'Get Started Free',
    ctaLink: '/tools/debug-wizard',
  },

  [AccessTier.REGISTERED]: {
    name: 'Registered',
    description: 'Create an account for expanded features',
    price: 'Free',
    features: [
      'Analyze up to 5 files',
      'Advanced predictions',
      'Top 5 historical matches',
      '50 analyses per day',
      'Resolution recording',
    ],
    limitations: [
      'No folder uploads',
      'No code suggestions',
    ],
    ctaText: 'Create Free Account',
    ctaLink: '/signup',
  },

  [AccessTier.PRO]: {
    name: 'Pro',
    description: 'Full web features for professional developers',
    price: '$19/month',
    features: [
      'Analyze up to 20 files',
      'Folder uploads',
      'AI code suggestions',
      '500 analyses per day',
      '500MB pattern storage',
      'Priority API access',
    ],
    limitations: [],
    ctaText: 'Upgrade to Pro',
    ctaLink: '/pricing',
  },

  [AccessTier.LOCAL]: {
    name: 'Local Installation',
    description: 'Install locally for unlimited features',
    price: 'Free (Open Source)',
    features: [
      'Unlimited files & folders',
      'Unlimited analyses',
      'Full historical database',
      'AI code suggestions',
      'Works offline',
      'Your data stays local',
    ],
    limitations: [],
    ctaText: 'Install Locally',
    ctaLink: '/docs/installation',
  },

  [AccessTier.ENTERPRISE]: {
    name: 'Enterprise',
    description: 'For teams and organizations',
    price: 'Contact Sales',
    features: [
      'Everything in Pro',
      'Team pattern sharing',
      'SSO integration',
      'Custom retention policies',
      'Dedicated support',
      'SLA guarantees',
    ],
    limitations: [],
    ctaText: 'Contact Sales',
    ctaLink: '/contact',
  },
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get tier limits for a given tier
 */
export function getTierLimits(tier: AccessTier): TierLimits {
  return TIER_LIMITS[tier];
}

/**
 * Get display info for a tier
 */
export function getTierDisplay(tier: AccessTier): TierDisplayInfo {
  return TIER_DISPLAY[tier];
}

/**
 * Check if a file count exceeds tier limits
 */
export function isFileCountExceeded(tier: AccessTier, fileCount: number): boolean {
  const limits = TIER_LIMITS[tier];
  return limits.maxFiles !== null && fileCount > limits.maxFiles;
}

/**
 * Check if a file size exceeds tier limits
 */
export function isFileSizeExceeded(tier: AccessTier, fileSizeBytes: number): boolean {
  const limits = TIER_LIMITS[tier];
  if (limits.maxFileSizeMB === null) return false;
  const fileSizeMB = fileSizeBytes / (1024 * 1024);
  return fileSizeMB > limits.maxFileSizeMB;
}

/**
 * Validate files against tier limits
 */
export function validateFilesForTier(
  tier: AccessTier,
  files: Array<{ path: string; size_bytes: number }>,
  isFolderUpload: boolean = false
): {
  valid: boolean;
  errors: string[];
  warnings: string[];
} {
  const limits = TIER_LIMITS[tier];
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check folder upload permission
  if (isFolderUpload && !limits.folderUploadEnabled) {
    errors.push(
      `Folder upload is not available on the ${TIER_DISPLAY[tier].name} tier. ` +
      `Upgrade to ${TIER_DISPLAY[AccessTier.PRO].name} or install locally.`
    );
  }

  // Check file count
  if (limits.maxFiles !== null && files.length > limits.maxFiles) {
    errors.push(
      `Too many files: ${files.length} provided, maximum ${limits.maxFiles} ` +
      `allowed on ${TIER_DISPLAY[tier].name} tier.`
    );
  }

  // Check individual file sizes
  if (limits.maxFileSizeMB !== null) {
    const maxBytes = limits.maxFileSizeMB * 1024 * 1024;
    for (const file of files) {
      if (file.size_bytes > maxBytes) {
        const fileSizeMB = (file.size_bytes / (1024 * 1024)).toFixed(2);
        errors.push(
          `File '${file.path}' exceeds size limit: ${fileSizeMB}MB > ${limits.maxFileSizeMB}MB`
        );
      }
    }
  }

  // Add upgrade CTA warning if there are errors
  if (limits.showUpgradeCTA && errors.length > 0) {
    warnings.push(
      `Upgrade to ${TIER_DISPLAY[AccessTier.PRO].name} for expanded limits, ` +
      `or install locally for unlimited features.`
    );
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * Get the next tier upgrade path
 */
export function getUpgradePath(currentTier: AccessTier): AccessTier | null {
  const upgradePaths: Record<AccessTier, AccessTier | null> = {
    [AccessTier.FREE]: AccessTier.REGISTERED,
    [AccessTier.REGISTERED]: AccessTier.PRO,
    [AccessTier.PRO]: AccessTier.LOCAL,
    [AccessTier.LOCAL]: AccessTier.ENTERPRISE,
    [AccessTier.ENTERPRISE]: null,
  };
  return upgradePaths[currentTier];
}

/**
 * Default tier for unauthenticated users
 */
export const DEFAULT_TIER = AccessTier.FREE;

/**
 * Default tier for web deployment
 */
export const WEB_DEFAULT_TIER = AccessTier.FREE;
