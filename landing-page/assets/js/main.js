// SmartGnosis Landing Page JavaScript

// ===========================
// Smooth Scrolling
// ===========================
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');

        // Skip if it's just a hash
        if (href === '#') {
            e.preventDefault();
            return;
        }

        const target = document.querySelector(href);
        if (target) {
            e.preventDefault();
            const offsetTop = target.offsetTop - 80; // Account for fixed navbar
            window.scrollTo({
                top: offsetTop,
                behavior: 'smooth'
            });
        }
    });
});

// ===========================
// Mobile Menu Toggle
// ===========================
const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
const navLinks = document.querySelector('.nav-links');

if (mobileMenuToggle) {
    mobileMenuToggle.addEventListener('click', () => {
        navLinks.classList.toggle('active');
        mobileMenuToggle.classList.toggle('active');
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.nav-wrapper')) {
            navLinks.classList.remove('active');
            mobileMenuToggle.classList.remove('active');
        }
    });

    // Close menu when clicking a link
    navLinks.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            navLinks.classList.remove('active');
            mobileMenuToggle.classList.remove('active');
        });
    });
}

// ===========================
// Navbar Background on Scroll
// ===========================
const navbar = document.querySelector('.navbar');
let lastScroll = 0;

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;

    // Add shadow on scroll
    if (currentScroll > 50) {
        navbar.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
    } else {
        navbar.style.boxShadow = 'none';
    }

    // Hide navbar on scroll down, show on scroll up
    if (currentScroll > lastScroll && currentScroll > 200) {
        navbar.style.transform = 'translateY(-100%)';
    } else {
        navbar.style.transform = 'translateY(0)';
    }

    lastScroll = currentScroll;
});

// ===========================
// Intersection Observer for Animations
// ===========================
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('fade-in-up');
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Observe elements for animation
const animatedElements = document.querySelectorAll(`
    .problem-card,
    .feature-card,
    .step,
    .pricing-card,
    .testimonial-card
`);

animatedElements.forEach(el => {
    observer.observe(el);
});

// ===========================
// Counter Animation
// ===========================
function animateCounter(element, target, duration = 2000) {
    let start = 0;
    const increment = target / (duration / 16); // 60fps
    const timer = setInterval(() => {
        start += increment;
        if (start >= target) {
            element.textContent = target;
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(start);
        }
    }, 16);
}

// Animate stats when they come into view
const statsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const statNumber = entry.target.querySelector('.stat-number');
            const text = statNumber.textContent;
            const numMatch = text.match(/\d+/);

            if (numMatch) {
                const target = parseInt(numMatch[0]);
                const suffix = text.replace(target, '').trim();
                statNumber.textContent = '0' + suffix;
                animateCounter(statNumber, target);
            }

            statsObserver.unobserve(entry.target);
        }
    });
}, observerOptions);

document.querySelectorAll('.stat').forEach(stat => {
    statsObserver.observe(stat);
});

// ===========================
// Form Handling (Demo/Contact)
// ===========================
const forms = document.querySelectorAll('form');

forms.forEach(form => {
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;

        // Show loading state
        submitBtn.textContent = 'Sending...';
        submitBtn.disabled = true;

        // Simulate form submission (replace with actual API call)
        try {
            // Replace this with your actual form submission logic
            await new Promise(resolve => setTimeout(resolve, 1500));

            // Success state
            submitBtn.textContent = 'Sent!';
            submitBtn.style.background = '#10B981';

            // Reset form
            form.reset();

            // Show success message
            showNotification('Thank you! We\'ll be in touch soon.', 'success');

            // Reset button after delay
            setTimeout(() => {
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                submitBtn.style.background = '';
            }, 3000);
        } catch (error) {
            // Error state
            submitBtn.textContent = 'Error - Try Again';
            submitBtn.style.background = '#EF4444';

            showNotification('Something went wrong. Please try again.', 'error');

            setTimeout(() => {
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                submitBtn.style.background = '';
            }, 3000);
        }
    });
});

// ===========================
// Notification System
// ===========================
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Style the notification
    Object.assign(notification.style, {
        position: 'fixed',
        top: '100px',
        right: '20px',
        padding: '1rem 1.5rem',
        background: type === 'success' ? '#10B981' : type === 'error' ? '#EF4444' : '#2563EB',
        color: 'white',
        borderRadius: '0.5rem',
        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
        zIndex: '9999',
        animation: 'slideInRight 0.3s ease-out',
        fontWeight: '600'
    });

    // Add to page
    document.body.appendChild(notification);

    // Remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Add notification animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }

    .nav-links.active {
        display: flex !important;
        flex-direction: column;
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        padding: 1rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        gap: 0.5rem;
    }

    .mobile-menu-toggle.active span:nth-child(1) {
        transform: rotate(45deg) translate(5px, 5px);
    }

    .mobile-menu-toggle.active span:nth-child(2) {
        opacity: 0;
    }

    .mobile-menu-toggle.active span:nth-child(3) {
        transform: rotate(-45deg) translate(7px, -6px);
    }

    .navbar {
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
`;
document.head.appendChild(style);

// ===========================
// Progress Ring Animation
// ===========================
function animateProgressRing(ring, percentage) {
    const circle = ring.querySelector('circle:last-child');
    const radius = circle.r.baseVal.value;
    const circumference = radius * 2 * Math.PI;

    circle.style.strokeDasharray = `${circumference} ${circumference}`;
    circle.style.strokeDashoffset = circumference;

    // Trigger animation
    setTimeout(() => {
        const offset = circumference - (percentage / 100) * circumference;
        circle.style.transition = 'stroke-dashoffset 1s ease-out';
        circle.style.strokeDashoffset = offset;
    }, 100);
}

// Animate progress rings when they come into view
const ringsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const rings = entry.target.querySelectorAll('.progress-ring');
            rings.forEach((ring, index) => {
                const percentage = [90, 100, 85][index]; // AC, AU, IA percentages
                setTimeout(() => {
                    animateProgressRing(ring.parentElement, percentage);
                }, index * 200);
            });
            ringsObserver.unobserve(entry.target);
        }
    });
}, observerOptions);

const dashboardPreview = document.querySelector('.dashboard-preview');
if (dashboardPreview) {
    ringsObserver.observe(dashboardPreview);
}

// ===========================
// Pricing Toggle (Annual/Monthly)
// ===========================
const pricingToggles = document.querySelectorAll('.pricing-toggle');

pricingToggles.forEach(toggle => {
    toggle.addEventListener('click', () => {
        const isAnnual = toggle.classList.toggle('annual');

        // Update pricing (if you want to add monthly/annual toggle)
        document.querySelectorAll('.price-amount').forEach(price => {
            const monthlyPrice = parseInt(price.dataset.monthly || price.textContent.replace(/,/g, ''));
            const annualPrice = Math.floor(monthlyPrice * 10); // 2 months free

            if (isAnnual) {
                price.textContent = annualPrice.toLocaleString();
                price.nextElementSibling.textContent = '/year';
            } else {
                price.textContent = monthlyPrice.toLocaleString();
                price.nextElementSibling.textContent = '/month';
            }
        });
    });
});

// ===========================
// Video Modal (for demo video)
// ===========================
const videoTriggers = document.querySelectorAll('[href="#demo-video"]');

videoTriggers.forEach(trigger => {
    trigger.addEventListener('click', (e) => {
        e.preventDefault();

        // Create modal
        const modal = document.createElement('div');
        modal.className = 'video-modal';
        modal.innerHTML = `
            <div class="video-modal-overlay"></div>
            <div class="video-modal-content">
                <button class="video-modal-close">&times;</button>
                <div class="video-container">
                    <iframe
                        width="100%"
                        height="100%"
                        src="https://www.youtube.com/embed/dQw4w9WgXcQ"
                        frameborder="0"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowfullscreen>
                    </iframe>
                </div>
            </div>
        `;

        // Style modal
        const modalStyle = document.createElement('style');
        modalStyle.textContent = `
            .video-modal {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 2rem;
            }

            .video-modal-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.9);
            }

            .video-modal-content {
                position: relative;
                width: 100%;
                max-width: 1000px;
                background: #000;
                border-radius: 1rem;
                overflow: hidden;
            }

            .video-container {
                position: relative;
                padding-bottom: 56.25%; /* 16:9 aspect ratio */
                height: 0;
                overflow: hidden;
            }

            .video-container iframe {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
            }

            .video-modal-close {
                position: absolute;
                top: -40px;
                right: 0;
                background: none;
                border: none;
                color: white;
                font-size: 40px;
                cursor: pointer;
                z-index: 10001;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.2s ease;
            }

            .video-modal-close:hover {
                transform: scale(1.1);
            }
        `;
        document.head.appendChild(modalStyle);

        // Add to page
        document.body.appendChild(modal);
        document.body.style.overflow = 'hidden';

        // Close handlers
        const closeModal = () => {
            modal.remove();
            modalStyle.remove();
            document.body.style.overflow = '';
        };

        modal.querySelector('.video-modal-close').addEventListener('click', closeModal);
        modal.querySelector('.video-modal-overlay').addEventListener('click', closeModal);

        // Close on escape key
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
    });
});

// ===========================
// Analytics Tracking (placeholder)
// ===========================
function trackEvent(eventName, eventData = {}) {
    // Replace with your analytics implementation
    // Example: Google Analytics, Mixpanel, Segment, etc.
    console.log('Event tracked:', eventName, eventData);

    // Example for Google Analytics
    // if (window.gtag) {
    //     gtag('event', eventName, eventData);
    // }
}

// Track CTA clicks
document.querySelectorAll('.btn-primary, .btn-secondary').forEach(btn => {
    btn.addEventListener('click', () => {
        trackEvent('cta_click', {
            button_text: btn.textContent.trim(),
            button_location: btn.closest('section')?.className || 'unknown'
        });
    });
});

// Track pricing card interactions
document.querySelectorAll('.pricing-card').forEach(card => {
    card.addEventListener('click', () => {
        const planName = card.querySelector('h3')?.textContent;
        trackEvent('pricing_card_click', {
            plan_name: planName
        });
    });
});

// ===========================
// Initialize on DOM Load
// ===========================
document.addEventListener('DOMContentLoaded', () => {
    console.log('SmartGnosis landing page loaded');

    // Track page view
    trackEvent('page_view', {
        page: 'landing',
        timestamp: new Date().toISOString()
    });

    // Add loaded class for CSS animations
    document.body.classList.add('loaded');
});

// ===========================
// Performance Monitoring
// ===========================
if ('performance' in window) {
    window.addEventListener('load', () => {
        setTimeout(() => {
            const perfData = performance.getEntriesByType('navigation')[0];
            console.log('Page load time:', perfData.loadEventEnd - perfData.fetchStart, 'ms');

            // Track performance metrics
            trackEvent('performance', {
                load_time: Math.round(perfData.loadEventEnd - perfData.fetchStart),
                dom_ready: Math.round(perfData.domContentLoadedEventEnd - perfData.fetchStart)
            });
        }, 0);
    });
}

// ===========================
// Accessibility Enhancements
// ===========================

// Keyboard navigation for cards
document.querySelectorAll('.feature-card, .pricing-card, .problem-card').forEach(card => {
    card.setAttribute('tabindex', '0');

    card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            const link = card.querySelector('a');
            if (link) {
                e.preventDefault();
                link.click();
            }
        }
    });
});

// Announce dynamic content changes to screen readers
function announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.className = 'sr-only';
    announcement.textContent = message;

    document.body.appendChild(announcement);

    setTimeout(() => {
        announcement.remove();
    }, 1000);
}

// Add screen reader only CSS
const srStyle = document.createElement('style');
srStyle.textContent = `
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border-width: 0;
    }
`;
document.head.appendChild(srStyle);

// ===========================
// Authentication Modals
// ===========================
const loginModal = document.getElementById('loginModal');
const signupModal = document.getElementById('signupModal');
const loginBtn = document.querySelector('.login-btn');
const getStartedBtns = document.querySelectorAll('[href="#demo"]');

// Open Login Modal
function openLoginModal() {
    loginModal.classList.add('active');
    document.body.style.overflow = 'hidden';
    trackEvent('modal_open', { modal: 'login' });
}

// Open Signup Modal
function openSignupModal() {
    signupModal.classList.add('active');
    document.body.style.overflow = 'hidden';
    trackEvent('modal_open', { modal: 'signup' });
}

// Close Modal
function closeModal(modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
    trackEvent('modal_close', { modal: modal.id });
}

// Login button click
if (loginBtn) {
    loginBtn.addEventListener('click', (e) => {
        e.preventDefault();
        openLoginModal();
    });
}

// Get Started buttons -> Open Signup
getStartedBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.preventDefault();
        openSignupModal();
    });
});

// Close button handlers
document.querySelectorAll('.auth-modal-close').forEach(closeBtn => {
    closeBtn.addEventListener('click', () => {
        const modal = closeBtn.closest('.auth-modal');
        closeModal(modal);
    });
});

// Close on overlay click
document.querySelectorAll('.auth-modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', () => {
        const modal = overlay.closest('.auth-modal');
        closeModal(modal);
    });
});

// Close on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (loginModal.classList.contains('active')) {
            closeModal(loginModal);
        }
        if (signupModal.classList.contains('active')) {
            closeModal(signupModal);
        }
    }
});

// Switch between login and signup
document.querySelectorAll('.switch-to-signup').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        closeModal(loginModal);
        setTimeout(() => openSignupModal(), 200);
    });
});

document.querySelectorAll('.switch-to-login').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        closeModal(signupModal);
        setTimeout(() => openLoginModal(), 200);
    });
});

// ===========================
// Password Toggle
// ===========================
document.querySelectorAll('.password-toggle').forEach(toggle => {
    toggle.addEventListener('click', () => {
        const input = toggle.previousElementSibling;
        const type = input.getAttribute('type');

        if (type === 'password') {
            input.setAttribute('type', 'text');
            toggle.setAttribute('aria-label', 'Hide password');
        } else {
            input.setAttribute('type', 'password');
            toggle.setAttribute('aria-label', 'Show password');
        }
    });
});

// ===========================
// Password Strength Indicator
// ===========================
const signupPassword = document.getElementById('signupPassword');
if (signupPassword) {
    signupPassword.addEventListener('input', (e) => {
        const password = e.target.value;
        const strengthFill = document.querySelector('.password-strength-fill');
        const strengthText = document.querySelector('.password-strength-text');

        const strength = calculatePasswordStrength(password);

        // Remove existing classes
        strengthFill.classList.remove('weak', 'medium', 'strong');

        if (password.length === 0) {
            strengthFill.style.width = '0%';
            strengthText.textContent = '';
            return;
        }

        if (strength < 40) {
            strengthFill.classList.add('weak');
            strengthText.textContent = 'Weak password';
        } else if (strength < 70) {
            strengthFill.classList.add('medium');
            strengthText.textContent = 'Medium strength';
        } else {
            strengthFill.classList.add('strong');
            strengthText.textContent = 'Strong password';
        }
    });
}

function calculatePasswordStrength(password) {
    let strength = 0;

    if (password.length >= 8) strength += 20;
    if (password.length >= 12) strength += 10;
    if (/[a-z]/.test(password)) strength += 15;
    if (/[A-Z]/.test(password)) strength += 15;
    if (/[0-9]/.test(password)) strength += 15;
    if (/[^A-Za-z0-9]/.test(password)) strength += 25;

    return strength;
}

// ===========================
// Form Validation
// ===========================
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validatePassword(password) {
    return password.length >= 8;
}

function showError(inputId, message) {
    const input = document.getElementById(inputId);
    const errorSpan = document.getElementById(inputId + 'Error');

    if (input && errorSpan) {
        input.classList.add('error');
        errorSpan.textContent = message;
        errorSpan.classList.add('visible');
    }
}

function clearError(inputId) {
    const input = document.getElementById(inputId);
    const errorSpan = document.getElementById(inputId + 'Error');

    if (input && errorSpan) {
        input.classList.remove('error');
        errorSpan.textContent = '';
        errorSpan.classList.remove('visible');
    }
}

// Clear errors on input
document.querySelectorAll('.auth-form input').forEach(input => {
    input.addEventListener('input', () => {
        clearError(input.id);
    });
});

// ===========================
// Login Form Submission
// ===========================
const loginForm = document.getElementById('loginForm');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        const submitBtn = loginForm.querySelector('button[type="submit"]');

        // Reset errors
        clearError('loginEmail');
        clearError('loginPassword');

        // Validation
        let hasError = false;

        if (!validateEmail(email)) {
            showError('loginEmail', 'Please enter a valid email address');
            hasError = true;
        }

        if (password.length === 0) {
            showError('loginPassword', 'Password is required');
            hasError = true;
        }

        if (hasError) return;

        // Show loading state
        submitBtn.classList.add('loading');
        submitBtn.disabled = true;

        try {
            // Replace with your actual API endpoint
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password }),
            });

            // Simulate API call for demo
            await new Promise(resolve => setTimeout(resolve, 1500));

            if (response.ok || true) { // Remove "|| true" in production
                // Success
                trackEvent('login_success', { method: 'email' });
                showNotification('Login successful! Redirecting...', 'success');

                // Redirect to dashboard
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1000);
            } else {
                throw new Error('Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            showError('loginPassword', 'Invalid email or password');
            trackEvent('login_failed', { method: 'email', error: error.message });
        } finally {
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
        }
    });
}

// ===========================
// Signup Form Submission
// ===========================
const signupForm = document.getElementById('signupForm');
if (signupForm) {
    signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const firstName = document.getElementById('signupFirstName').value.trim();
        const lastName = document.getElementById('signupLastName').value.trim();
        const company = document.getElementById('signupCompany').value.trim();
        const email = document.getElementById('signupEmail').value.trim();
        const password = document.getElementById('signupPassword').value;
        const termsAccepted = document.getElementById('acceptTerms').checked;
        const submitBtn = signupForm.querySelector('button[type="submit"]');

        // Reset errors
        clearError('signupFirstName');
        clearError('signupLastName');
        clearError('signupCompany');
        clearError('signupEmail');
        clearError('signupPassword');
        clearError('signupTerms');

        // Validation
        let hasError = false;

        if (firstName.length < 2) {
            showError('signupFirstName', 'First name is required');
            hasError = true;
        }

        if (lastName.length < 2) {
            showError('signupLastName', 'Last name is required');
            hasError = true;
        }

        if (company.length < 2) {
            showError('signupCompany', 'Company name is required');
            hasError = true;
        }

        if (!validateEmail(email)) {
            showError('signupEmail', 'Please enter a valid work email');
            hasError = true;
        }

        if (!validatePassword(password)) {
            showError('signupPassword', 'Password must be at least 8 characters');
            hasError = true;
        }

        if (!termsAccepted) {
            showError('signupTerms', 'You must accept the terms and conditions');
            hasError = true;
        }

        if (hasError) return;

        // Show loading state
        submitBtn.classList.add('loading');
        submitBtn.disabled = true;

        try {
            // Replace with your actual API endpoint
            const response = await fetch('/api/auth/signup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    firstName,
                    lastName,
                    company,
                    email,
                    password
                }),
            });

            // Simulate API call for demo
            await new Promise(resolve => setTimeout(resolve, 2000));

            if (response.ok || true) { // Remove "|| true" in production
                // Success
                trackEvent('signup_success', { method: 'email' });
                showNotification('Account created! Welcome to SmartGnosis!', 'success');

                // Redirect to onboarding or dashboard
                setTimeout(() => {
                    window.location.href = '/onboarding';
                }, 1500);
            } else {
                const data = await response.json();
                throw new Error(data.message || 'Signup failed');
            }
        } catch (error) {
            console.error('Signup error:', error);
            showError('signupEmail', error.message || 'An error occurred. Please try again.');
            trackEvent('signup_failed', { method: 'email', error: error.message });
        } finally {
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
        }
    });
}

// ===========================
// Social Authentication
// ===========================
document.querySelectorAll('.social-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const provider = btn.dataset.provider;
        trackEvent('social_auth_click', { provider });

        // Show loading notification
        showNotification(`Redirecting to ${provider}...`, 'info');

        // Redirect to OAuth endpoint
        setTimeout(() => {
            window.location.href = `/api/auth/${provider}`;
        }, 500);
    });
});

// ===========================
// Forgot Password Handler
// ===========================
document.querySelectorAll('.forgot-password').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();

        const email = document.getElementById('loginEmail').value;

        trackEvent('forgot_password_click');

        // In production, open a password reset modal or redirect
        const resetEmail = prompt('Enter your email address to reset your password:', email);

        if (resetEmail && validateEmail(resetEmail)) {
            showNotification('Password reset link sent to ' + resetEmail, 'success');
            trackEvent('password_reset_requested', { email: resetEmail });
        }
    });
});

console.log('SmartGnosis v1.0 - Ready to accelerate compliance!');
