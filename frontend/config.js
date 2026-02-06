// configuration.js
window.APP_CONFIG = {
    // If backend is on port 5050 and we are serving frontend from there (or via proxy)
    // We can use relative path or absolute path.
    // For local dev with separate servers: http://localhost:5050
    // For production/integrated: /api
    getApiUrl: function () {
        const port = window.location.port;
        let hostname = window.location.hostname;

        if (!hostname) {
            hostname = 'localhost';
        }

        // If served from backend (port 8080), use relative path
        if (port === '8080') {
            return '/api';
        }

        // Fix for localhost IPv6 issues: force 127.0.0.1 if currently on localhost
        if (hostname === 'localhost') hostname = '127.0.0.1';

        // For VSCode Live Server (5500) or others, point to backend port 8080
        return `http://${hostname}:8080/api`;
    },

    getBackendUrl: function () {
        const port = window.location.port;
        let hostname = window.location.hostname;

        if (!hostname) {
            hostname = 'localhost';
        }

        if (port === '8080') {
            return '';
        }

        // Fix for localhost IPv6 issues
        if (hostname === 'localhost') hostname = '127.0.0.1';

        return `http://${hostname}:8080`;
    }
};

console.log('App Config Loaded:', window.APP_CONFIG.getApiUrl());
