/**
 * Security utilities for XSS prevention and input validation
 * Centralized security functions used across the application
 */
class Security {
    /**
     * Sanitize text content to prevent XSS
     * @param {string} text - Text to sanitize
     * @returns {string} - Sanitized text
     */
    static sanitizeText(text) {
        if (!text || typeof text !== 'string') return '';

        // Create a temporary div element to escape HTML
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Escape HTML characters
     * @param {string} text - Text to escape
     * @returns {string} - Escaped HTML
     */
    static escapeHtml(text) {
        if (!text || typeof text !== 'string') return '';

        const div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    /**
     * Validate input length
     * @param {string} text - Text to validate
     * @param {number} maxLength - Maximum allowed length
     * @returns {boolean} - Whether text is valid
     */
    static validateLength(text, maxLength) {
        return text && typeof text === 'string' && text.length <= maxLength;
    }

    /**
     * Validate email format
     * @param {string} email - Email to validate
     * @returns {boolean} - Whether email is valid
     */
    static validateEmail(email) {
        if (!email || typeof email !== 'string') return false;

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    /**
     * Validate password strength
     * @param {string} password - Password to validate
     * @returns {Object} - Validation result with details
     */
    static validatePassword(password) {
        if (!password || typeof password !== 'string') {
            return { valid: false, message: 'Password is required' };
        }

        const issues = [];

        if (password.length < 8) {
            issues.push('at least 8 characters');
        }

        if (!/[A-Z]/.test(password)) {
            issues.push('one uppercase letter');
        }

        if (!/[a-z]/.test(password)) {
            issues.push('one lowercase letter');
        }

        if (!/\d/.test(password)) {
            issues.push('one number');
        }

        return {
            valid: issues.length === 0,
            message: issues.length > 0 ? `Password must contain ${issues.join(', ')}` : '',
            issues
        };
    }

    /**
     * Safe innerHTML setter with XSS prevention
     * @param {HTMLElement} element - Element to set HTML on
     * @param {string} html - HTML content to set
     */
    static safeSetHTML(element, html) {
        if (!element || !(element instanceof HTMLElement)) return;

        if (!html) {
            element.innerHTML = '';
            return;
        }

        if (typeof html !== 'string') {
            console.warn('safeSetHTML: html parameter must be a string');
            return;
        }

        // Basic XSS prevention - remove dangerous elements and attributes
        const cleanHTML = html
            // Remove script tags and their content
            .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
            // Remove javascript: protocol
            .replace(/javascript:/gi, '')
            // Remove on* event handlers (onclick, onload, etc.)
            .replace(/\bon\w+\s*=/gi, '')
            // Remove data: URLs that could execute scripts
            .replace(/data:(?!image\/)/gi, '')
            // Remove iframe, object, embed tags
            .replace(/<(iframe|object|embed|form|input|textarea)\b[^>]*>/gi, '')
            // Remove style tags with potential CSS expressions
            .replace(/<style\b[^<]*>.*?<\/style>/gi, '');

        element.innerHTML = cleanHTML;
    }

    /**
     * Create a safe DOM element with text content
     * @param {string} tagName - Tag name for element
     * @param {string} text - Text content (will be escaped)
     * @param {Object} attributes - Attributes to set
     * @param {string} className - CSS class name
     * @returns {HTMLElement} - Created element
     */
    static createElement(tagName, text = '', attributes = {}, className = '') {
        const element = document.createElement(tagName);

        if (text) {
            element.textContent = text; // Automatically escapes HTML
        }

        Object.entries(attributes).forEach(([key, value]) => {
            // Only set safe attributes
            const safeAttributes = ['id', 'class', 'data-*', 'aria-*', 'role', 'tabindex'];
            const isSafe = safeAttributes.some(attr => {
                if (attr.endsWith('*')) {
                    return key.startsWith(attr.slice(0, -1));
                }
                return key === attr;
            });

            if (isSafe && typeof value === 'string') {
                element.setAttribute(key, this.escapeHtml(value));
            }
        });

        if (className) {
            element.className = className;
        }

        return element;
    }

    /**
     * Validate CSRF token
     * @param {string} token - Token to validate
     * @returns {boolean} - Whether token appears valid
     */
    static validateCSRFToken(token) {
        if (!token || typeof token !== 'string') return false;

        // Basic validation - should be a reasonable length alphanumeric string
        return /^[a-zA-Z0-9_-]{20,}$/.test(token);
    }

    /**
     * Sanitize URL to prevent malicious redirects
     * @param {string} url - URL to validate
     * @returns {string} - Sanitized URL or empty string if invalid
     */
    static sanitizeURL(url) {
        if (!url || typeof url !== 'string') return '';

        try {
            const parsed = new URL(url, window.location.origin);

            // Only allow same-origin or specific safe protocols
            const allowedProtocols = ['http:', 'https:', 'mailto:', 'tel:'];
            if (!allowedProtocols.includes(parsed.protocol)) {
                return '';
            }

            // Prevent javascript: and data: URLs
            if (parsed.protocol === 'javascript:' || parsed.protocol.startsWith('data:')) {
                return '';
            }

            return parsed.toString();
        } catch (error) {
            console.warn('Invalid URL provided:', url);
            return '';
        }
    }

    /**
     * Rate limiter for preventing abuse
     */
    static createRateLimit(maxCalls = 5, windowMs = 60000) {
        const calls = [];

        return {
            check() {
                const now = Date.now();
                // Remove old calls outside the window
                while (calls.length > 0 && calls[0] <= now - windowMs) {
                    calls.shift();
                }

                if (calls.length >= maxCalls) {
                    return false;
                }

                calls.push(now);
                return true;
            },

            reset() {
                calls.length = 0;
            }
        };
    }

    /**
     * Content Security Policy helper for dynamic script loading
     * @param {string} scriptContent - Script content to validate
     * @returns {boolean} - Whether script content is safe
     */
    static validateScriptContent(scriptContent) {
        if (!scriptContent || typeof scriptContent !== 'string') return false;

        // Block dangerous patterns
        const dangerousPatterns = [
            /eval\s*\(/gi,
            /Function\s*\(/gi,
            /setTimeout\s*\(/gi,
            /setInterval\s*\(/gi,
            /document\.write/gi,
            /innerHTML\s*=/gi,
            /outerHTML\s*=/gi
        ];

        return !dangerousPatterns.some(pattern => pattern.test(scriptContent));
    }

    /**
     * Input validation for numeric values
     * @param {any} value - Value to validate
     * @param {Object} options - Validation options
     * @returns {boolean} - Whether value is valid
     */
    static validateNumber(value, options = {}) {
        const { min, max, integer = false, positive = false } = options;

        if (typeof value !== 'number' || isNaN(value)) {
            return false;
        }

        if (integer && !Number.isInteger(value)) {
            return false;
        }

        if (positive && value <= 0) {
            return false;
        }

        if (min !== undefined && value < min) {
            return false;
        }

        if (max !== undefined && value > max) {
            return false;
        }

        return true;
    }
}

// Export for use in modules
window.Security = Security;
export default Security;