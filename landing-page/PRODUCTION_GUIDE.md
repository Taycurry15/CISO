# SmartGnosis Landing Page - Production Deployment Guide

This guide walks you through deploying the SmartGnosis landing page to production.

## Table of Contents

- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Environment Setup](#environment-setup)
- [Deployment Options](#deployment-options)
- [Post-Deployment](#post-deployment)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Pre-Deployment Checklist

Before deploying to production, ensure you have completed the following:

### Backend Integration
- [ ] Backend authentication API is deployed and accessible
- [ ] API endpoints match the configuration in `config.js`
- [ ] CORS is properly configured to allow requests from your domain
- [ ] OAuth applications are created (Google, Microsoft)
- [ ] SSL/TLS certificates are configured for HTTPS

### Environment Configuration
- [ ] Copy `.env.example` to `.env`
- [ ] Fill in all required environment variables
- [ ] Test API connectivity from local environment
- [ ] Verify OAuth redirect URIs match your production domain

### Code Updates
- [ ] Remove demo mode from `main.js`:
  ```javascript
  // Find and remove "|| true" from lines 858 and 963
  if (response.ok) { // Remove || true
  ```
- [ ] Update `config.js` with production URLs
- [ ] Update contact information in legal pages
- [ ] Add your logo files to `assets/images/`
- [ ] Update Open Graph images and meta tags

### Analytics Setup
- [ ] Create Google Analytics 4 property
- [ ] Get GA measurement ID
- [ ] Set up Google Tag Manager (optional)
- [ ] Configure Mixpanel/Segment (optional)
- [ ] Set up Hotjar (optional)
- [ ] Test analytics tracking in staging

### Security
- [ ] Review and update Content Security Policy
- [ ] Configure rate limiting on backend
- [ ] Set up CSRF protection
- [ ] Review CORS settings
- [ ] Enable HTTPS only
- [ ] Configure security headers

### Legal & Compliance
- [ ] Review and customize privacy.html
- [ ] Review and customize terms.html
- [ ] Add your business address
- [ ] Add contact information
- [ ] Ensure GDPR/CCPA compliance
- [ ] Add cookie consent banner (if needed)

## Environment Setup

### 1. Configure Environment Variables

Create a `.env` file in the landing page directory:

```bash
cp .env.example .env
```

Edit `.env` with your production values:

```env
# API Configuration
API_BASE_URL=https://api.smartgnosis.com

# Google Analytics
GA_MEASUREMENT_ID=G-XXXXXXXXXX

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com

# Microsoft OAuth
MICROSOFT_CLIENT_ID=your-microsoft-client-id

# Enable features
FEATURE_GOOGLE_AUTH=true
FEATURE_MICROSOFT_AUTH=true
FEATURE_DEMO_MODE=false
FEATURE_ANALYTICS=true
```

### 2. Update config.js

The `config.js` file automatically loads environment variables. In a browser environment, you may need to use a build process to inject these values.

#### Option A: Build-time Replacement

Use a build tool to replace environment variables:

```bash
# Install envsubst or use a Node.js script
envsubst < config.js > config.prod.js
```

#### Option B: Server-side Injection

If using a server (nginx, Node.js), inject environment variables at runtime.

### 3. Update HTML References

Update `index.html` footer links to point to your actual pages:

```html
<a href="privacy.html">Privacy Policy</a>
<a href="terms.html">Terms of Service</a>
```

## Deployment Options

### Option 1: Netlify (Recommended for Static Sites)

1. **Connect Repository**
   ```bash
   # Install Netlify CLI
   npm install -g netlify-cli

   # Login
   netlify login

   # Deploy
   cd landing-page
   netlify deploy --prod
   ```

2. **Configure Environment Variables**
   - Go to Netlify Dashboard > Site Settings > Environment Variables
   - Add all variables from `.env`

3. **Set Custom Domain**
   - Go to Domain Settings
   - Add `complianceflow.app`
   - Configure DNS records

4. **Enable HTTPS**
   - Netlify automatically provisions Let's Encrypt SSL
   - Force HTTPS in settings

### Option 2: Vercel

1. **Deploy via CLI**
   ```bash
   # Install Vercel CLI
   npm install -g vercel

   # Login
   vercel login

   # Deploy
   cd landing-page
   vercel --prod
   ```

2. **Configure Environment Variables**
   ```bash
   vercel env add API_BASE_URL production
   vercel env add GA_MEASUREMENT_ID production
   # Add all other variables
   ```

3. **Custom Domain**
   ```bash
   vercel domains add complianceflow.app
   ```

### Option 3: AWS S3 + CloudFront

1. **Create S3 Bucket**
   ```bash
   aws s3 mb s3://complianceflow-landing --region us-east-1
   ```

2. **Configure Bucket for Static Hosting**
   ```bash
   aws s3 website s3://complianceflow-landing \
     --index-document index.html \
     --error-document index.html
   ```

3. **Upload Files**
   ```bash
   cd landing-page
   aws s3 sync . s3://complianceflow-landing \
     --exclude ".git/*" \
     --exclude ".env*" \
     --exclude "*.md" \
     --cache-control "public, max-age=31536000" \
     --exclude "*.html" \
     --exclude "*.json"

   # Upload HTML with different cache settings
   aws s3 sync . s3://complianceflow-landing \
     --exclude "*" \
     --include "*.html" \
     --cache-control "public, max-age=0, must-revalidate"
   ```

4. **Create CloudFront Distribution**
   - Origin: S3 bucket
   - Viewer Protocol: Redirect HTTP to HTTPS
   - Compress Objects: Yes
   - Add custom SSL certificate

5. **Configure DNS**
   - Point `complianceflow.app` to CloudFront distribution

### Option 4: Docker + Nginx

1. **Build Docker Image**
   ```bash
   cd landing-page
   docker build -t complianceflow-landing:latest .
   ```

2. **Run Container**
   ```bash
   docker run -d \
     -p 80:80 \
     --name complianceflow-landing \
     --restart unless-stopped \
     complianceflow-landing:latest
   ```

3. **Or Use Docker Compose**
   ```yaml
   version: '3.8'
   services:
     landing:
       build: .
       ports:
         - "80:80"
       restart: unless-stopped
       environment:
         - API_BASE_URL=${API_BASE_URL}
   ```

   Deploy:
   ```bash
   docker-compose up -d
   ```

### Option 5: Traditional Web Hosting (cPanel, etc.)

1. **Upload Files via FTP/SFTP**
   - Upload all files except `.git`, `.env.example`, `*.md`
   - Ensure proper file permissions (644 for files, 755 for directories)

2. **Configure .htaccess (for Apache)**
   ```apache
   # Force HTTPS
   RewriteEngine On
   RewriteCond %{HTTPS} off
   RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

   # Security Headers
   <IfModule mod_headers.c>
       Header set X-Frame-Options "DENY"
       Header set X-XSS-Protection "1; mode=block"
       Header set X-Content-Type-Options "nosniff"
   </IfModule>

   # Caching
   <FilesMatch "\.(css|js|jpg|jpeg|png|gif|svg|ico)$">
       Header set Cache-Control "public, max-age=31536000, immutable"
   </FilesMatch>
   ```

## Post-Deployment

### 1. Verify Deployment

```bash
# Check if site is accessible
curl -I https://complianceflow.app

# Test API proxy (if configured)
curl https://complianceflow.app/api/health

# Test analytics
# Open browser DevTools > Network tab
# Load page and verify GA requests
```

### 2. Test Functionality

- [ ] Landing page loads correctly
- [ ] All images and assets load
- [ ] Login modal opens
- [ ] Signup modal opens
- [ ] Password toggle works
- [ ] Password strength indicator works
- [ ] Form validation works
- [ ] Social auth buttons redirect correctly
- [ ] Analytics tracking fires (check Google Analytics Real-Time)
- [ ] Mobile responsiveness
- [ ] Cross-browser compatibility (Chrome, Firefox, Safari, Edge)

### 3. SEO Setup

```bash
# Create and submit sitemap
# Create robots.txt
# Verify Google Search Console
# Submit sitemap to Google
# Configure structured data
```

### 4. Performance Optimization

- [ ] Enable gzip/brotli compression
- [ ] Configure CDN (CloudFront, Cloudflare)
- [ ] Optimize images (use WebP format)
- [ ] Minify CSS and JavaScript
- [ ] Enable browser caching
- [ ] Test with PageSpeed Insights
- [ ] Achieve Lighthouse score >90

### 5. Security Hardening

- [ ] Force HTTPS
- [ ] Configure security headers
- [ ] Set up Content Security Policy
- [ ] Enable HSTS
- [ ] Configure CORS
- [ ] Set up rate limiting
- [ ] Enable DDoS protection (Cloudflare, AWS Shield)

## Monitoring

### Application Monitoring

1. **Set Up Error Tracking (Sentry)**
   ```javascript
   // Add to index.html head
   <script src="https://browser.sentry-cdn.com/7.x.x/bundle.min.js"></script>
   <script>
     Sentry.init({
       dsn: 'YOUR_SENTRY_DSN',
       environment: 'production',
     });
   </script>
   ```

2. **Set Up Uptime Monitoring**
   - Use UptimeRobot, Pingdom, or StatusCake
   - Monitor main page load
   - Monitor API health endpoint
   - Set up alerts (email, Slack, PagerDuty)

3. **Analytics Monitoring**
   - Google Analytics Dashboard
   - Conversion tracking
   - User flow analysis
   - Bounce rate monitoring

### Infrastructure Monitoring

1. **Server Monitoring** (if self-hosted)
   - CPU, Memory, Disk usage
   - Network traffic
   - Log aggregation (ELK stack, Datadog)

2. **CDN Monitoring**
   - Cache hit rate
   - Bandwidth usage
   - Edge location performance

## Troubleshooting

### Common Issues

**Issue: Login/Signup doesn't work**
- Check browser console for errors
- Verify API_BASE_URL is correct
- Check CORS settings on backend
- Verify network tab shows API requests

**Issue: Analytics not tracking**
- Check GA_MEASUREMENT_ID is correct
- Verify analytics.js loaded
- Check browser console for errors
- Disable ad blockers for testing

**Issue: OAuth redirect fails**
- Verify redirect URIs match in OAuth app settings
- Check that URIs use HTTPS in production
- Verify OAuth client IDs are correct

**Issue: Slow page load**
- Check image sizes (compress images)
- Enable CDN
- Check server response time
- Use browser DevTools Network tab

**Issue: SSL certificate errors**
- Verify certificate is valid and not expired
- Check certificate chain is complete
- Force HTTPS redirects

### Debug Mode

Enable debug logging:

```javascript
// In browser console
localStorage.setItem('debug', 'true');
// Reload page
```

### Support Channels

- **Documentation**: https://docs.complianceflow.app
- **Status Page**: https://status.complianceflow.app
- **Support**: support@complianceflow.app
- **Emergency**: [Emergency Contact]

## Rollback Procedure

If deployment fails:

### Netlify/Vercel
- Go to Deployments
- Select previous deployment
- Click "Publish deploy"

### Docker
```bash
# Revert to previous image
docker pull complianceflow-landing:previous
docker stop complianceflow-landing
docker rm complianceflow-landing
docker run -d -p 80:80 --name complianceflow-landing complianceflow-landing:previous
```

### S3 + CloudFront
```bash
# Sync previous version from backup
aws s3 sync s3://complianceflow-landing-backup s3://complianceflow-landing
# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

## Continuous Deployment

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Deploy to Netlify
        uses: netlify/actions/cli@master
        with:
          args: deploy --prod --dir=landing-page
        env:
          NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
          NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
```

## Production Checklist

Before going live:

- [ ] All environment variables configured
- [ ] Demo mode disabled in code
- [ ] Backend API accessible
- [ ] OAuth credentials configured
- [ ] HTTPS enabled
- [ ] Security headers configured
- [ ] Analytics tracking verified
- [ ] Legal pages updated
- [ ] Error tracking configured
- [ ] Uptime monitoring enabled
- [ ] Backups configured
- [ ] CDN configured
- [ ] DNS records propagated
- [ ] SSL certificate valid
- [ ] Performance tested (>90 PageSpeed score)
- [ ] Mobile responsiveness verified
- [ ] Cross-browser tested
- [ ] Accessibility tested
- [ ] SEO metadata configured
- [ ] Sitemap submitted
- [ ] Rollback plan documented
- [ ] Team trained on deployment process

## Post-Launch Tasks

Week 1:
- [ ] Monitor error rates
- [ ] Check conversion rates
- [ ] Review analytics data
- [ ] Address any bugs

Month 1:
- [ ] A/B testing setup
- [ ] Performance optimization
- [ ] User feedback collection
- [ ] Feature iteration

---

**Need Help?** Contact DevOps team at devops@complianceflow.app
