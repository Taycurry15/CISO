// ComplianceFlow Landing Page Configuration
// This file loads environment variables and provides a centralized config object

const config = {
    // API Configuration
    api: {
        baseUrl: process.env.API_BASE_URL || 'https://api.complianceflow.app',
        endpoints: {
            login: process.env.API_LOGIN_ENDPOINT || '/api/v1/auth/login',
            signup: process.env.API_SIGNUP_ENDPOINT || '/api/v1/auth/signup',
            logout: process.env.API_LOGOUT_ENDPOINT || '/api/v1/auth/logout',
            refresh: process.env.API_REFRESH_ENDPOINT || '/api/v1/auth/refresh',
            forgotPassword: process.env.API_FORGOT_PASSWORD_ENDPOINT || '/api/v1/auth/forgot-password',
            resetPassword: process.env.API_RESET_PASSWORD_ENDPOINT || '/api/v1/auth/reset-password',
            oauth: {
                google: process.env.API_OAUTH_GOOGLE || '/api/v1/auth/oauth/google',
                microsoft: process.env.API_OAUTH_MICROSOFT || '/api/v1/auth/oauth/microsoft',
            }
        },
        timeout: 30000, // 30 seconds
        retries: 3,
    },

    // OAuth Configuration
    oauth: {
        google: {
            clientId: process.env.GOOGLE_CLIENT_ID || '',
            redirectUri: process.env.GOOGLE_REDIRECT_URI || '',
        },
        microsoft: {
            clientId: process.env.MICROSOFT_CLIENT_ID || '',
            redirectUri: process.env.MICROSOFT_REDIRECT_URI || '',
            tenantId: process.env.MICROSOFT_TENANT_ID || 'common',
        },
    },

    // Analytics
    analytics: {
        enabled: process.env.FEATURE_ANALYTICS === 'true',
        google: {
            measurementId: process.env.GA_MEASUREMENT_ID || '',
        },
        gtm: {
            containerId: process.env.GTM_CONTAINER_ID || '',
        },
        mixpanel: {
            token: process.env.MIXPANEL_TOKEN || '',
        },
        segment: {
            writeKey: process.env.SEGMENT_WRITE_KEY || '',
        },
        hotjar: {
            siteId: process.env.HOTJAR_SITE_ID || '',
        },
    },

    // Site Information
    site: {
        url: process.env.SITE_URL || 'https://complianceflow.app',
        name: process.env.SITE_NAME || 'ComplianceFlow',
        description: process.env.SITE_DESCRIPTION || 'CMMC Compliance in Days, Not Months',
        keywords: process.env.SITE_KEYWORDS || 'CMMC,compliance,automation,AI,defense contractors,DIB',
    },

    // Social Media
    social: {
        twitter: process.env.TWITTER_HANDLE || '@complianceflow',
        facebook: process.env.FACEBOOK_PAGE || 'complianceflow',
        linkedin: process.env.LINKEDIN_PAGE || 'company/complianceflow',
    },

    // Security
    security: {
        csrf: {
            tokenName: process.env.CSRF_TOKEN_NAME || '_csrf',
            headerName: process.env.CSRF_HEADER_NAME || 'X-CSRF-Token',
        },
        session: {
            cookieName: process.env.SESSION_COOKIE_NAME || 'cf_session',
            timeout: parseInt(process.env.SESSION_TIMEOUT || '86400', 10),
        },
        rateLimit: {
            loginAttempts: parseInt(process.env.RATE_LIMIT_LOGIN_ATTEMPTS || '5', 10),
            signupAttempts: parseInt(process.env.RATE_LIMIT_SIGNUP_ATTEMPTS || '3', 10),
            window: parseInt(process.env.RATE_LIMIT_WINDOW || '900', 10), // 15 minutes
        },
    },

    // Feature Flags
    features: {
        googleAuth: process.env.FEATURE_GOOGLE_AUTH === 'true',
        microsoftAuth: process.env.FEATURE_MICROSOFT_AUTH === 'true',
        demoMode: process.env.FEATURE_DEMO_MODE === 'true',
        analytics: process.env.FEATURE_ANALYTICS === 'true',
        chatWidget: process.env.FEATURE_CHAT_WIDGET === 'false',
    },

    // Error Tracking
    errorTracking: {
        sentry: {
            dsn: process.env.SENTRY_DSN || '',
            environment: process.env.SENTRY_ENVIRONMENT || 'production',
        },
    },

    // Third-Party Services
    services: {
        intercom: {
            appId: process.env.INTERCOM_APP_ID || '',
        },
        hubspot: {
            portalId: process.env.HUBSPOT_PORTAL_ID || '',
        },
        stripe: {
            publishableKey: process.env.STRIPE_PUBLISHABLE_KEY || '',
        },
        recaptcha: {
            siteKey: process.env.RECAPTCHA_SITE_KEY || '',
        },
    },

    // CDN & Assets
    cdn: {
        url: process.env.CDN_URL || '',
        assetVersion: process.env.ASSET_VERSION || '1.0.0',
    },

    // Redirects
    redirects: {
        afterLogin: '/dashboard',
        afterSignup: '/onboarding',
        afterLogout: '/',
    },

    // Validation Rules
    validation: {
        password: {
            minLength: 8,
            maxLength: 128,
            requireUppercase: true,
            requireLowercase: true,
            requireNumbers: true,
            requireSpecialChars: true,
        },
        email: {
            maxLength: 254,
        },
        name: {
            minLength: 2,
            maxLength: 50,
        },
        company: {
            minLength: 2,
            maxLength: 100,
        },
    },
};

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = config;
}

// Make available globally for browser
if (typeof window !== 'undefined') {
    window.ComplianceFlowConfig = config;
}
