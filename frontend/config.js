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

        // If served from backend (port 5050), use relative path
        if (port === '5050') {
            return '/api';
        }

        // For VSCode Live Server (5500) or others, point to backend port 5050
        return `http://${hostname}:5050/api`;
    },

    getBackendUrl: function () {
        const port = window.location.port;
        let hostname = window.location.hostname;

        if (!hostname) {
            hostname = 'localhost';
        }

        if (port === '5050') {
            return '';
        }

        return `http://${hostname}:5050`;
    }
};

console.log('App Config Loaded:', window.APP_CONFIG.getApiUrl());
