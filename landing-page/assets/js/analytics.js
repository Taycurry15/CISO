// ComplianceFlow Analytics Integration
// This file handles all analytics tracking across different platforms

(function() {
    'use strict';

    // Get config
    const config = window.ComplianceFlowConfig || {};
    const analyticsConfig = config.analytics || {};

    // Analytics wrapper object
    window.CFAnalytics = {
        initialized: false,
        platforms: {
            ga: false,
            gtm: false,
            mixpanel: false,
            segment: false,
            hotjar: false,
        },

        // Initialize all analytics platforms
        init() {
            if (this.initialized) return;
            if (!analyticsConfig.enabled) {
                console.log('Analytics disabled');
                return;
            }

            this.initGoogleAnalytics();
            this.initGoogleTagManager();
            this.initMixpanel();
            this.initSegment();
            this.initHotjar();

            this.initialized = true;
            console.log('Analytics initialized:', this.platforms);
        },

        // Google Analytics 4
        initGoogleAnalytics() {
            const measurementId = analyticsConfig.google?.measurementId;
            if (!measurementId) return;

            try {
                // Load gtag.js
                const script = document.createElement('script');
                script.async = true;
                script.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
                document.head.appendChild(script);

                // Initialize gtag
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', measurementId, {
                    anonymize_ip: true,
                    cookie_flags: 'SameSite=None;Secure',
                });

                window.gtag = gtag;
                this.platforms.ga = true;
                console.log('Google Analytics initialized:', measurementId);
            } catch (error) {
                console.error('Google Analytics init failed:', error);
            }
        },

        // Google Tag Manager
        initGoogleTagManager() {
            const containerId = analyticsConfig.gtm?.containerId;
            if (!containerId) return;

            try {
                (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
                new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
                j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
                'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
                })(window,document,'script','dataLayer',containerId);

                this.platforms.gtm = true;
                console.log('Google Tag Manager initialized:', containerId);
            } catch (error) {
                console.error('GTM init failed:', error);
            }
        },

        // Mixpanel
        initMixpanel() {
            const token = analyticsConfig.mixpanel?.token;
            if (!token) return;

            try {
                (function(c,a){if(!a.__SV){var b=window;try{var d,m,j,k=b.location,f=k.hash;d=function(a,b){return(m=a.match(RegExp(b+"=([^&]*)")))?m[1]:null};f&&d(f,"state")&&(j=JSON.parse(decodeURIComponent(d(f,"state"))),"mpeditor"===j.action&&(b.sessionStorage.setItem("_mpcehash",f),history.replaceState(j.desiredHash||"",c.title,k.pathname+k.search)))}catch(n){}var l,h;window.mixpanel=a;a._i=[];a.init=function(b,d,g){function c(b,i){var a=i.split(".");2==a.length&&(b=b[a[0]],i=a[1]);b[i]=function(){b.push([i].concat(Array.prototype.slice.call(arguments,0)))}}var e=a;"undefined"!==typeof g?e=a[g]=[]:g="mixpanel";e.people=e.people||[];e.toString=function(b){var a="mixpanel";"mixpanel"!==g&&(a+="."+g);b||(a+=" (stub)");return a};e.people.toString=function(){return e.toString(1)+".people (stub)"};l="disable time_event track track_pageview track_links track_forms track_with_groups add_group set_group remove_group register register_once alias unregister identify name_tag set_config reset opt_in_tracking opt_out_tracking has_opted_in_tracking has_opted_out_tracking clear_opt_in_out_tracking people.set people.set_once people.unset people.increment people.append people.union people.track_charge people.clear_charges people.delete_user people.remove".split(" ");
                for(h=0;h<l.length;h++)c(e,l[h]);var f="set set_once union unset remove delete".split(" ");e.get_group=function(){function a(c){b[c]=function(){call2_args=arguments;call2=[c].concat(Array.prototype.slice.call(call2_args,0));e.push([d,call2])}}for(var b={},d=["get_group"].concat(Array.prototype.slice.call(arguments,0)),c=0;c<f.length;c++)a(f[c]);return b};a._i.push([b,d,g])};a.__SV=1.2;}})(document,window.mixpanel||[]);
                mixpanel.init(token);

                this.platforms.mixpanel = true;
                console.log('Mixpanel initialized:', token.substring(0, 10) + '...');
            } catch (error) {
                console.error('Mixpanel init failed:', error);
            }
        },

        // Segment
        initSegment() {
            const writeKey = analyticsConfig.segment?.writeKey;
            if (!writeKey) return;

            try {
                !function(){var analytics=window.analytics=window.analytics||[];if(!analytics.initialize)if(analytics.invoked)window.console&&console.error&&console.error("Segment snippet included twice.");else{analytics.invoked=!0;analytics.methods=["trackSubmit","trackClick","trackLink","trackForm","pageview","identify","reset","group","track","ready","alias","debug","page","once","off","on","addSourceMiddleware","addIntegrationMiddleware","setAnonymousId","addDestinationMiddleware"];analytics.factory=function(e){return function(){var t=Array.prototype.slice.call(arguments);t.unshift(e);analytics.push(t);return analytics}};for(var e=0;e<analytics.methods.length;e++){var key=analytics.methods[e];analytics[key]=analytics.factory(key)}analytics.load=function(key,e){var t=document.createElement("script");t.type="text/javascript";t.async=!0;t.src="https://cdn.segment.com/analytics.js/v1/" + key + "/analytics.min.js";var n=document.getElementsByTagName("script")[0];n.parentNode.insertBefore(t,n);analytics._loadOptions=e};analytics._writeKey=writeKey;analytics.SNIPPET_VERSION="4.15.3";
                analytics.load(writeKey);
                analytics.page();
                }}();

                this.platforms.segment = true;
                console.log('Segment initialized');
            } catch (error) {
                console.error('Segment init failed:', error);
            }
        },

        // Hotjar
        initHotjar() {
            const siteId = analyticsConfig.hotjar?.siteId;
            if (!siteId) return;

            try {
                (function(h,o,t,j,a,r){
                    h.hj=h.hj||function(){(h.hj.q=h.hj.q||[]).push(arguments)};
                    h._hjSettings={hjid:siteId,hjsv:6};
                    a=o.getElementsByTagName('head')[0];
                    r=o.createElement('script');r.async=1;
                    r.src=t+h._hjSettings.hjid+j+h._hjSettings.hjsv;
                    a.appendChild(r);
                })(window,document,'https://static.hotjar.com/c/hotjar-','.js?sv=');

                this.platforms.hotjar = true;
                console.log('Hotjar initialized:', siteId);
            } catch (error) {
                console.error('Hotjar init failed:', error);
            }
        },

        // Track page view
        pageView(pageName, properties = {}) {
            if (!this.initialized) return;

            const data = {
                page: pageName || window.location.pathname,
                ...properties,
                timestamp: new Date().toISOString(),
            };

            // Google Analytics
            if (this.platforms.ga && window.gtag) {
                gtag('event', 'page_view', data);
            }

            // Mixpanel
            if (this.platforms.mixpanel && window.mixpanel) {
                mixpanel.track('Page View', data);
            }

            // Segment
            if (this.platforms.segment && window.analytics) {
                analytics.page(pageName, data);
            }

            console.log('Page view tracked:', data);
        },

        // Track custom event
        track(eventName, properties = {}) {
            if (!this.initialized) return;

            const data = {
                ...properties,
                timestamp: new Date().toISOString(),
            };

            // Google Analytics
            if (this.platforms.ga && window.gtag) {
                gtag('event', eventName, data);
            }

            // Mixpanel
            if (this.platforms.mixpanel && window.mixpanel) {
                mixpanel.track(eventName, data);
            }

            // Segment
            if (this.platforms.segment && window.analytics) {
                analytics.track(eventName, data);
            }

            console.log('Event tracked:', eventName, data);
        },

        // Identify user
        identify(userId, traits = {}) {
            if (!this.initialized) return;

            // Google Analytics
            if (this.platforms.ga && window.gtag) {
                gtag('config', analyticsConfig.google.measurementId, {
                    user_id: userId,
                });
            }

            // Mixpanel
            if (this.platforms.mixpanel && window.mixpanel) {
                mixpanel.identify(userId);
                mixpanel.people.set(traits);
            }

            // Segment
            if (this.platforms.segment && window.analytics) {
                analytics.identify(userId, traits);
            }

            console.log('User identified:', userId, traits);
        },

        // Reset user (on logout)
        reset() {
            if (!this.initialized) return;

            // Mixpanel
            if (this.platforms.mixpanel && window.mixpanel) {
                mixpanel.reset();
            }

            // Segment
            if (this.platforms.segment && window.analytics) {
                analytics.reset();
            }

            console.log('Analytics reset');
        },
    };

    // Auto-initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.CFAnalytics.init();
        });
    } else {
        window.CFAnalytics.init();
    }
})();

// Export for use in main.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.CFAnalytics;
}
