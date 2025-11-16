// ComplianceFlow Landing Page JavaScript

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
    console.log('ComplianceFlow landing page loaded');

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

console.log('ComplianceFlow v1.0 - Ready to accelerate compliance!');
