// Use Config
const API_URL = window.APP_CONFIG.getApiUrl();
const BACKEND_URL = window.APP_CONFIG.getBackendUrl();

console.log('Using API URL:', API_URL);

// Helper to get full image URL
function getImageUrl(path) {
    if (!path) return null;
    if (path.startsWith('http') || path.startsWith('blob:') || path.startsWith('data:')) {
        return path;
    }
    // If it's a relative path starting with /, prepend backend URL
    if (path.startsWith('/')) {
        return `${BACKEND_URL}${path}`;
    }
    return path;
}

// Helper to construct Avatar URL with cache busting
function getAvatarUrl(user) {
    const defaultAvatar = `https://ui-avatars.com/api/?name=${user.username || 'User'}&background=random&color=fff`;
    if (!user.avatar) return defaultAvatar;

    let url = getImageUrl(user.avatar);

    // Add timestamp if it's a local upload to bust cache
    if (user.avatar.startsWith('/uploads/')) {
        url = url + (url.includes('?') ? '&' : '?') + 't=' + new Date().getTime();
    }

    return url;
}

// EMERGENCY BYPASS
// GUEST LOGIN
window.guestLogin = function () {
    const guestUser = {
        username: "guest",
        fullname: "Khách tham quan",
        email: "",
        role: "USER",
        id: "guest",
        user_id: "guest",
        avatar: "https://ui-avatars.com/api/?name=Guest&background=e9ecef&color=333"
    };
    localStorage.setItem('user', JSON.stringify(guestUser));
    window.location.href = 'index.html';
};

document.addEventListener('DOMContentLoaded', () => {

    // GLOBAL PORT ENFORCEMENT
    // 1. Check for PORT 5500 and Redirect
    // This is a safety measure to ensure users don't get stuck on the wrong port
    if (window.location.port === '5500') {
        let newPath = window.location.pathname;
        // Fix path: remove '/frontend' if present (common when using Live Server from root)
        newPath = newPath.replace('/frontend', '');
        window.location.href = 'http://localhost:8080' + newPath;
        return;
    }

    // Auth Check
    const isAuthPage = document.body.contains(document.getElementById('loginForm')) ||
        document.body.contains(document.getElementById('registerForm')) ||
        document.body.contains(document.getElementById('adminLoginForm'));

    if (!isAuthPage) {
        checkUserSession();
        initCarousel();
    }

    // Login Logic
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const loginInput = document.getElementById('login-input').value.trim();
            const password = document.getElementById('login-password').value.trim();

            try {
                console.log(`Sending login request to ${API_URL}/login`);
                const res = await fetch(`${API_URL}/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ login_input: loginInput, password: password })
                });

                console.log(`Response status: ${res.status}`);

                if (!res.ok) {
                    const data = await res.json().catch(() => ({ message: res.statusText })); // Fallback if not JSON
                    // Special handling for "Account not found" or auth errors
                    if (res.status === 404 || res.status === 401) {
                        alert(data.message || 'Login failed. Please check your credentials.');
                    } else {
                        alert(`Server Error (${res.status}): ${data.message || 'Unknown error'}`);
                    }
                    return;
                }

                const data = await res.json();

                // User portal: DO NOT allow Admin accounts to login here
                if (data.role === 'ADMIN') {
                    alert('Access Denied: Please use the Admin Login page.');
                    return;
                }
                alert('Login Success! Redirecting...');
                localStorage.setItem('user', JSON.stringify(data));
                window.location.href = 'index.html';

            } catch (err) {
                console.error(err);
                if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
                    alert("Connection Error: Unable to reach the server.\n\nPlease ensure the backend is running on port 8080.");
                } else {
                    alert(`An unexpected error occurred:\n${err.message}`);
                }
            }
        });
    }

    // Admin Login Logic
    const adminLoginForm = document.getElementById('adminLoginForm');
    if (adminLoginForm) {
        adminLoginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const loginInput = document.getElementById('admin-input').value;
            const password = document.getElementById('admin-password').value;

            try {
                console.log(`Sending ADMIN login request to ${API_URL}/login`);
                const res = await fetch(`${API_URL}/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ login_input: loginInput, password: password })
                });

                if (!res.ok) {
                    const data = await res.json().catch(() => ({ message: res.statusText }));
                    if (res.status === 404 || res.status === 401) {
                        alert(data.message || 'Login failed. Please check your credentials.');
                    } else {
                        alert(`Server Error (${res.status}): ${data.message || 'Unknown error'}`);
                    }
                    return;
                }

                const data = await res.json();

                if (data.role === 'ADMIN') {
                    alert('Admin Login Success! \nRedirecting to Dashboard...');
                    localStorage.setItem('user', JSON.stringify(data));
                    window.location.href = 'admin_index.html';
                } else {
                    // User trying to access Admin
                    alert('Access Denied: You are not an Admin. Please use User Login.');
                }
            } catch (err) {
                console.error(err);
                if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
                    alert("Connection Error: Unable to reach the server.\n\nPlease ensure the backend is running on port 8080.");
                } else {
                    alert(`An unexpected error occurred:\n${err.message}`);
                }
            }
        });
    }

    // Logout
    const logoutBtn = document.getElementById('nav-logout');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.removeItem('user');
            window.location.href = 'login.html';
        });
    }

    // User Menu Dropdown Toggle
    const navAvatar = document.getElementById('nav-avatar');
    if (navAvatar) {
        navAvatar.addEventListener('click', (e) => {
            const dropdown = document.getElementById('user-dropdown');
            if (dropdown) {
                dropdown.classList.toggle('show');
                e.stopPropagation();
            }
        });

        // Close on click outside
        document.addEventListener('click', () => {
            const dropdown = document.getElementById('user-dropdown');
            if (dropdown) dropdown.classList.remove('show');
        });
    }

    // Expose Global Functions for HTML OnClick
    window.logout = function () {
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    };

    window.toggleProfileView = function () {
        const homeView = document.getElementById('home-view');
        const profileView = document.getElementById('profile-view');
        const adminView = document.getElementById('admin-view');
        const heroSection = document.querySelector('.hero-carousel-section');

        // If we are on index.html, these should exist
        if (homeView && profileView) {
            homeView.classList.add('hidden');
            if (heroSection) heroSection.classList.add('hidden');
            if (adminView) adminView.classList.add('hidden');
            profileView.classList.remove('hidden');

            // Populate profile data if needed
            loadProfile();
        }
    };

    // loadProfileData removed in favor of loadProfile defined below
    // Register Logic - ADDED BACK
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('Registering...');

            const username = document.getElementById('reg-username').value.trim();
            const email = document.getElementById('reg-email').value.trim();
            const phone = document.getElementById('reg-phone').value.trim();
            const password = document.getElementById('reg-password').value.trim();
            const confirm = document.getElementById('reg-confirm-password').value.trim();

            if (password !== confirm) {
                alert("Passwords do not match!");
                return;
            }

            try {
                const res = await fetch(`${API_URL}/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, email, phone, password })
                });
                const data = await res.json();

                if (res.ok) {
                    alert('Registration Successful! \n\nPlease Login now.');
                    window.location.href = 'login.html';
                } else {
                    alert('Registration Failed: ' + data.message);
                }
            } catch (err) {
                console.error(err);
                if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
                    alert("Connection Error: Unable to reach the server.\n\nPlease ensure the backend is running on port 8080.");
                } else {
                    alert('Connection Error. Backend might be offline.');
                }
            }
        });
    }

    // Avatar upload preview
    const avatarInput = document.getElementById('avatar-upload');
    if (avatarInput) {
        avatarInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    document.getElementById('profile-avatar-main').src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Live Name Preview
    const pLastname = document.getElementById('p-lastname');
    const pFirstname = document.getElementById('p-firstname');
    const displayElement = document.getElementById('profile-name-display');

    function updateNamePreview() {
        if (pLastname && pFirstname && displayElement) {
            const full = `${pLastname.value} ${pFirstname.value}`.trim();
            if (full) displayElement.innerText = full;
        }
    }

    if (pLastname) pLastname.addEventListener('input', updateNamePreview);
    if (pFirstname) pFirstname.addEventListener('input', updateNamePreview);

    // Populate Date Dropdowns
    populateDateDropdowns();

    const toolRemove = document.getElementById('tool-remove-bg');
    const toolChangeBg = document.getElementById('tool-change-bg');
    const toolRecolor = document.getElementById('tool-recolor');
    const toolUpscale = document.getElementById('tool-upscale');
    const changeBgControls = document.getElementById('changebg-controls');
    const removeBgControls = document.getElementById('removebg-controls');
    const removeBgChoose = document.getElementById('removebg-choose');
    const recolorControls = document.getElementById('recolor-controls');
    const upscaleControls = document.getElementById('upscale-controls');
    const fileRemove = document.getElementById('removebg-file');
    const outRemove = document.getElementById('removebg-output');
    const recolorFile = document.getElementById('recolor-file');
    const recolorColor = document.getElementById('recolor-color');
    const recolorStrength = document.getElementById('recolor-strength');
    const recolorChoose = document.getElementById('recolor-choose');
    const recolorChooseImage = document.getElementById('recolor-choose-image');
    const recolorOut = document.getElementById('recolor-output');
    const recolorFilePanel = document.getElementById('recolor-file-panel');
    const recolorFileName = document.getElementById('recolor-file-name');
    const recolorConfirm = document.getElementById('recolor-confirm');
    const recolorCancel = document.getElementById('recolor-cancel');
    let pendingRecolorFile = null;
    const upscaleFile = document.getElementById('upscale-file');
    const upscaleScale = document.getElementById('upscale-scale');
    const upscaleChoose = document.getElementById('upscale-choose');
    const upscaleOut = document.getElementById('upscale-output');
    const changeBgFile = document.getElementById('changebg-file');
    const changeBgBgFile = document.getElementById('changebg-bg-file');
    const changeBgColor = document.getElementById('changebg-color');
    const changeBgBlur = document.getElementById('changebg-blur');
    const changeBgChooseImage = document.getElementById('changebg-choose-image');
    const changeBgChooseBg = document.getElementById('changebg-choose-bg');
    const changeBgOut = document.getElementById('changebg-output');
    const changeBgFilePanel = document.getElementById('changebg-file-panel');
    const changeBgFileName = document.getElementById('changebg-file-name');
    const changeBgBgFileName = document.getElementById('changebg-bg-file-name');
    const changeBgFileThumb = document.getElementById('changebg-file-thumb');
    const changeBgBgThumb = document.getElementById('changebg-bg-thumb');
    const changeBgConfirm = document.getElementById('changebg-confirm');
    const changeBgCancel = document.getElementById('changebg-cancel');
    let pendingChangeBgFile = null;
    let pendingBgFile = null;
    const navRemoveBg = document.getElementById('nav-remove-bg');
    const navChangeBg = document.getElementById('nav-change-bg');
    const navRecolor = document.getElementById('nav-recolor');
    const navUpscale = document.getElementById('nav-upscale');
    const navShopView = document.getElementById('nav-shop-view');
    const navShopBuy = document.getElementById('nav-shop-buy');
    // Tool view switcher (simulate separate pages via ?tool=)
    function getToolParam() {
        const params = new URLSearchParams(window.location.search);
        return params.get('tool');
    }
    function setToolParam(val) {
        const url = new URL(window.location.href);
        if (val) url.searchParams.set('tool', val);
        else url.searchParams.delete('tool');
        url.hash = 'tools';
        window.history.pushState({}, '', url.toString());
    }
    function showTool(tool) {
        const cards = {
            remove: document.getElementById('tool-remove-bg'),
            changebg: document.getElementById('tool-change-bg'),
            recolor: document.getElementById('tool-recolor'),
            upscale: document.getElementById('tool-upscale')
        };
        if (changeBgControls) changeBgControls.style.display = tool === 'changebg' ? 'flex' : 'none';
        if (removeBgControls) removeBgControls.style.display = tool === 'remove' ? 'flex' : 'none';
        if (recolorControls) recolorControls.style.display = tool === 'recolor' ? 'flex' : 'none';
        if (upscaleControls) upscaleControls.style.display = tool === 'upscale' ? 'flex' : 'none';
        // Clear outputs of other tools to avoid mixing UIs/results
        const outRemove = document.getElementById('removebg-output');
        const outChange = document.getElementById('changebg-output');
        const outRecolor = document.getElementById('recolor-output');
        const outUpscale = document.getElementById('upscale-output');
        const fRemove = document.getElementById('removebg-file');
        const fChange = document.getElementById('changebg-file');
        const fChangeBg = document.getElementById('changebg-bg-file');
        const fRecolor = document.getElementById('recolor-file');
        const fUpscale = document.getElementById('upscale-file');
        if (tool !== 'remove') {
            if (outRemove) outRemove.innerHTML = '';
            if (fRemove) fRemove.value = '';
        }
        if (tool !== 'changebg') {
            if (outChange) outChange.innerHTML = '';
            if (fChange) fChange.value = '';
            if (fChangeBg) fChangeBg.value = '';
            if (changeBgFilePanel) changeBgFilePanel.style.display = 'none';
            if (changeBgFileName) changeBgFileName.innerHTML = `<i class="fas fa-user"></i> Image`;
            if (changeBgBgFileName) changeBgBgFileName.innerHTML = `<i class="fas fa-image"></i> Background`;
            if (changeBgFileThumb) changeBgFileThumb.src = '';
            if (changeBgBgThumb) changeBgBgThumb.src = '';
        }
        if (tool !== 'recolor') {
            if (outRecolor) outRecolor.innerHTML = '';
            if (recolorFile) recolorFile.value = '';
            if (recolorFilePanel) recolorFilePanel.style.display = 'none';
            if (recolorFileName) recolorFileName.textContent = '';
            pendingRecolorFile = null;
        }
        if (tool !== 'upscale') {
            if (outUpscale) outUpscale.innerHTML = '';
            if (upscaleFile) upscaleFile.value = '';
        }
        const highlight = (el, active) => {
            if (!el) return;
            el.style.boxShadow = active ? '0 0 0 3px rgba(76,110,245,0.35)' : 'none';
            el.style.transform = active ? 'scale(1.02)' : 'scale(1)';
        };
        highlight(cards.remove, tool === 'remove');
        highlight(cards.changebg, tool === 'changebg');
        highlight(cards.recolor, tool === 'recolor');
        highlight(cards.upscale, tool === 'upscale');
        if (tool) document.getElementById('tools')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    // Initialize from URL
    const initialTool = getToolParam();
    if (initialTool) showTool(initialTool);

    // Nav dropdown bindings → open specific tool sections
    if (navRemoveBg) {
        navRemoveBg.addEventListener('click', (e) => {
            e.preventDefault();
            setToolParam('remove');
            showTool('remove');
        });
    }
    if (navChangeBg) {
        navChangeBg.addEventListener('click', (e) => {
            e.preventDefault();
            setToolParam('changebg');
            showTool('changebg');
        });
    }
    if (navRecolor) {
        navRecolor.addEventListener('click', (e) => {
            e.preventDefault();
            setToolParam('recolor');
            showTool('recolor');
        });
    }
    if (navUpscale && upscaleFile) {
        navUpscale.addEventListener('click', (e) => {
            e.preventDefault();
            setToolParam('upscale');
            showTool('upscale');
            // prompt file select for convenience
            upscaleFile.click();
        });
    }

    // Helpers for Shop dropdown
    async function ensureShopReady() {
        scrollToSection('shop');
        try { await loadShopItems(); } catch(e) {}
        return new Promise((resolve) => {
            let tries = 0;
            const timer = setInterval(() => {
                const grid = document.getElementById('shop-grid-container');
                const shopsRow = document.getElementById('shops-row');
                if (grid && shopsRow && shopsRow.children.length > 0) {
                    clearInterval(timer);
                    resolve({ grid, shopsRow });
                }
                if (++tries > 40) { // ~10s max
                    clearInterval(timer);
                    resolve({ grid, shopsRow });
                }
            }, 250);
        });
    }
    function clickAllShops(shopsRow) {
        if (!shopsRow) return;
        const btns = shopsRow.querySelectorAll('button.btn');
        for (const b of btns) {
            if ((b.textContent || '').trim().toLowerCase() === 'all shops') {
                b.click();
                return;
            }
        }
        // fallback: click first shop
        if (btns.length) btns[0].click();
    }
    if (navShopView) {
        navShopView.addEventListener('click', async (e) => {
            e.preventDefault();
            const { grid, shopsRow } = await ensureShopReady();
            clickAllShops(shopsRow);
            const st = document.getElementById('shop-title');
            if (st) st.innerText = 'View Price & Details';
            grid?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }
    if (navShopBuy) {
        navShopBuy.addEventListener('click', async (e) => {
            e.preventDefault();
            const { grid, shopsRow } = await ensureShopReady();
            clickAllShops(shopsRow);
            const st = document.getElementById('shop-title');
            if (st) st.innerText = 'Buy Now';
            setTimeout(() => {
                const buyLink = grid?.querySelector('a.btn.btn-secondary[href]');
                if (buyLink) {
                    window.open(buyLink.href, '_blank');
                } else {
                    grid?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 500);
        });
    }

    if (toolRemove && outRemove) {
        toolRemove.addEventListener('click', () => {
            setToolParam('remove');
            showTool('remove');
        });
        if (removeBgChoose && fileRemove) {
            removeBgChoose.addEventListener('click', () => fileRemove.click());
        }
        fileRemove.addEventListener('change', async (e) => {
            const f = e.target.files && e.target.files[0];
            if (!f) return;
            const origUrl = URL.createObjectURL(f);
            lastOriginalBlob = f;
            outRemove.innerHTML = '<div style="padding:12px; color:#666;">Processing...</div>';
            const fd = new FormData();
            fd.append('image', f);
            try {
                const res = await fetch(`${API_URL}/remove-bg`, { method: 'POST', body: fd });
                const ct = res.headers.get('content-type') || '';
                if (!res.ok) {
                    let msg = 'Image processing error';
                    if (ct.includes('application/json')) {
                        const j = await res.json().catch(() => ({}));
                        msg = j.message || msg;
                    } else {
                        msg = await res.text().catch(() => msg);
                    }
                    outRemove.innerHTML = `<div style="padding:12px; color:#e57373;">${msg}</div>`;
                    return;
                }
                if (ct.includes('image/')) {
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    outRemove.innerHTML = `
                        <div style="display:flex; gap:16px; flex-wrap:wrap;">
                            <div style="flex:1; min-width:240px;">
                                <div style="font-weight:600; margin-bottom:6px;">Original</div>
                                <img src="${origUrl}" alt="original" style="max-width:100%; border-radius:8px; border:1px solid #eee;">
                            </div>
                            <div style="flex:1; min-width:240px;">
                                <div style="font-weight:600; margin-bottom:6px;">Background Removed (PNG)</div>
                                <img src="${url}" alt="result" style="max-width:100%; border-radius:8px; border:1px solid #eee; background:checkerboard;">
                                <div style="margin-top:8px;">
                                    <a href="${url}" download="removed_bg.png" class="btn btn-secondary" style="width:auto;">Download</a>
                                </div>
                            </div>
                        </div>
                    `;
                } else {
                    const txt = await res.text();
                    outRemove.innerHTML = `<div style="padding:12px; color:#e57373;">${txt || 'Invalid response'}</div>`;
                }
            } catch (err) {
                outRemove.innerHTML = `<div style="padding:12px; color:#e57373;">${err.message || 'Server connection error'}</div>`;
            } finally {
                fileRemove.value = '';
            }
        });
    }

    async function runRecolorWithBlob(blob) {
        const origUrl = URL.createObjectURL(blob);
        recolorOut.innerHTML = '<div style="padding:12px; color:#666;">Processing...</div>';
        const fd = new FormData();
        fd.append('image', blob, 'input.png');
        fd.append('color', recolorColor.value || '#ff6b6b');
        fd.append('strength', recolorStrength.value || '0.8');
        const res = await fetch(`${API_URL}/recolor`, { method: 'POST', body: fd });
        if (!res.ok) {
            const txt = await res.text();
            recolorOut.innerHTML = `<div style="padding:12px; color:#e57373;">${txt}</div>`;
            return;
        }
        const outBlob = await res.blob();
        const url = URL.createObjectURL(outBlob);
        recolorOut.innerHTML = `
            <div style="display:flex; gap:16px; flex-wrap:wrap;">
                <div style="flex:1; min-width:240px;">
                    <div style="font-weight:600; margin-bottom:6px;">Original</div>
                    <img src="${origUrl}" style="max-width:100%; border-radius:8px; border:1px solid #eee;">
                </div>
                <div style="flex:1; min-width:240px;">
                    <div style="font-weight:600; margin-bottom:6px;">Recolored</div>
                    <img src="${url}" style="max-width:100%; border-radius:8px; border:1px solid #eee;">
                    <div style="margin-top:8px;"><a href="${url}" download="recolored.png" class="btn btn-secondary" style="width:auto;">Download</a></div>
                </div>
            </div>
        `;
    }

    async function runUpscaleWithBlob(blob) {
        const origUrl = URL.createObjectURL(blob);
        upscaleOut.innerHTML = '<div style="padding:12px; color:#666;">Upscaling...</div>';
        const fd = new FormData();
        fd.append('image', blob, 'input.png');
        fd.append('scale', upscaleScale.value || '2');
        const res = await fetch(`${API_URL}/upscale`, { method: 'POST', body: fd });
        if (!res.ok) {
            const txt = await res.text();
            upscaleOut.innerHTML = `<div style="padding:12px; color:#e57373;">${txt}</div>`;
            return;
        }
        const outBlob = await res.blob();
        const url = URL.createObjectURL(outBlob);
        upscaleOut.innerHTML = `
            <div style="display:flex; gap:16px; flex-wrap:wrap;">
                <div style="flex:1; min-width:240px;">
                    <div style="font-weight:600; margin-bottom:6px;">Original</div>
                    <img src="${origUrl}" style="max-width:100%; border-radius:8px; border:1px solid #eee;">
                </div>
                <div style="flex:1; min-width:240px;">
                    <div style="font-weight:600; margin-bottom:6px;">Upscaled</div>
                    <img src="${url}" style="max-width:100%; border-radius:8px; border:1px solid #eee;">
                    <div style="margin-top:8px;"><a href="${url}" download="upscaled.png" class="btn btn-secondary" style="width:auto;">Download</a></div>
                </div>
            </div>
        `;
    }

    async function runChangeBgWithFiles(subjectBlob, backgroundBlob) {
        const origUrl = URL.createObjectURL(subjectBlob);
        if (changeBgOut) changeBgOut.innerHTML = '<div style="padding:12px; color:#666;">Processing...</div>';
        const fd = new FormData();
        fd.append('image', subjectBlob, 'input.png');
        const blurVal = (changeBgBlur && changeBgBlur.value) ? changeBgBlur.value : '0';
        fd.append('blur', blurVal);
        if (backgroundBlob) {
            fd.append('bg_image', backgroundBlob, 'bg.png');
        } else {
            fd.append('bg_color', (changeBgColor && changeBgColor.value) ? changeBgColor.value : '#ffffff');
        }
        const res = await fetch(`${API_URL}/change-bg`, { method: 'POST', body: fd });
        if (!res.ok) {
            const txt = await res.text();
            if (changeBgOut) changeBgOut.innerHTML = `<div style="padding:12px; color:#e57373;">${txt}</div>`;
            return;
        }
        const outBlob = await res.blob();
        const url = URL.createObjectURL(outBlob);
        if (changeBgOut) {
            changeBgOut.innerHTML = `
                <div style="display:flex; gap:16px; flex-wrap:wrap;">
                    <div style="flex:1; min-width:240px;">
                        <div style="font-weight:600; margin-bottom:6px;">Original</div>
                        <img src="${origUrl}" style="max-width:100%; border-radius:8px; border:1px solid #eee;">
                    </div>
                    <div style="flex:1; min-width:240px;">
                        <div style="font-weight:600; margin-bottom:6px;">Background Changed</div>
                        <img src="${url}" style="max-width:100%; border-radius:8px; border:1px solid #eee;">
                        <div style="margin-top:8px;"><a href="${url}" download="changed_bg.png" class="btn btn-secondary" style="width:auto;">Download</a></div>
                    </div>
                </div>
            `;
        }
    }

    if (toolRecolor && recolorFile && recolorColor && recolorOut && recolorChoose) {
        toolRecolor.addEventListener('click', () => {
            setToolParam('recolor');
            showTool('recolor');
        });
        // open color picker
        recolorChoose.addEventListener('click', () => recolorColor && recolorColor.click());
        if (recolorChooseImage) {
            recolorChooseImage.addEventListener('click', () => recolorFile.click());
        }
        recolorFile.addEventListener('change', (e) => {
            const f = e.target.files && e.target.files[0];
            if (!f) return;
            pendingRecolorFile = f;
            if (recolorFilePanel) {
                recolorFilePanel.style.display = 'flex';
                if (recolorFileName) recolorFileName.textContent = `Selected: ${f.name}`;
            }
        });
        if (recolorConfirm) {
            recolorConfirm.addEventListener('click', async () => {
                if (!pendingRecolorFile) return;
                await runRecolorWithBlob(pendingRecolorFile);
                if (recolorFilePanel) recolorFilePanel.style.display = 'none';
                pendingRecolorFile = null;
                recolorFile.value = '';
            });
        }
        if (recolorCancel) {
            recolorCancel.addEventListener('click', () => {
                pendingRecolorFile = null;
                if (recolorFilePanel) recolorFilePanel.style.display = 'none';
                if (recolorFileName) recolorFileName.textContent = '';
                recolorFile.value = '';
            });
        }
    }

    if (toolChangeBg && changeBgControls) {
        toolChangeBg.addEventListener('click', () => {
            setToolParam('changebg');
            showTool('changebg');
        });
        if (changeBgChooseImage && changeBgFile) {
            changeBgChooseImage.addEventListener('click', () => changeBgFile.click());
        }
        if (changeBgChooseBg && changeBgBgFile) {
            changeBgChooseBg.addEventListener('click', () => changeBgBgFile.click());
        }
        if (changeBgFile) {
            changeBgFile.addEventListener('change', (e) => {
                const f = e.target.files && e.target.files[0];
                if (!f) return;
                pendingChangeBgFile = f;
                if (changeBgFilePanel) {
                    changeBgFilePanel.style.display = 'block';
                    if (changeBgFileName) changeBgFileName.innerHTML = `<i class="fas fa-user"></i> Image: ${f.name}`;
                    if (changeBgFileThumb) {
                        const url = URL.createObjectURL(f);
                        changeBgFileThumb.src = url;
                        changeBgFileThumb.onload = () => URL.revokeObjectURL(url);
                    }
                }
            });
        }
        if (changeBgBgFile) {
            changeBgBgFile.addEventListener('change', (e) => {
                const f = e.target.files && e.target.files[0];
                pendingBgFile = f || null;
                if (changeBgFilePanel && f) {
                    changeBgFilePanel.style.display = 'block';
                    if (changeBgBgFileName) changeBgBgFileName.innerHTML = `<i class="fas fa-image"></i> Background: ${f.name}`;
                    if (changeBgBgThumb) {
                        const url = URL.createObjectURL(f);
                        changeBgBgThumb.src = url;
                        changeBgBgThumb.onload = () => URL.revokeObjectURL(url);
                    }
                }
            });
        }
        if (changeBgConfirm) {
            changeBgConfirm.addEventListener('click', async () => {
                if (!pendingChangeBgFile) return;
                await runChangeBgWithFiles(pendingChangeBgFile, pendingBgFile);
                pendingChangeBgFile = null;
                pendingBgFile = null;
                if (changeBgFilePanel) changeBgFilePanel.style.display = 'none';
                if (changeBgFile) changeBgFile.value = '';
                if (changeBgBgFile) changeBgBgFile.value = '';
            });
        }
        if (changeBgCancel) {
            changeBgCancel.addEventListener('click', () => {
                pendingChangeBgFile = null;
                pendingBgFile = null;
                if (changeBgFilePanel) changeBgFilePanel.style.display = 'none';
                if (changeBgFileName) changeBgFileName.innerHTML = `<i class="fas fa-user"></i> Image`;
                if (changeBgBgFileName) changeBgBgFileName.innerHTML = `<i class="fas fa-image"></i> Background`;
                if (changeBgFile) changeBgFile.value = '';
                if (changeBgBgFile) changeBgBgFile.value = '';
                if (changeBgOut) changeBgOut.innerHTML = '';
                if (changeBgFileThumb) changeBgFileThumb.src = '';
                if (changeBgBgThumb) changeBgBgThumb.src = '';
            });
        }
    }

    if (toolUpscale && upscaleFile && upscaleOut && upscaleChoose) {
        toolUpscale.addEventListener('click', () => {
            setToolParam('upscale');
            showTool('upscale');
        });
        upscaleChoose.addEventListener('click', () => upscaleFile.click());
        upscaleFile.addEventListener('change', async (e) => {
            const f = e.target.files && e.target.files[0];
            if (!f) return;
            await runUpscaleWithBlob(f);
            upscaleFile.value = '';
        });
    }
});

function populateDateDropdowns() {
    const daySelect = document.getElementById('dob-day');
    const monthSelect = document.getElementById('dob-month');
    const yearSelect = document.getElementById('dob-year');

    if (!daySelect || !monthSelect || !yearSelect) return;

    // Helper to add options
    const addOps = (sel, start, end, reverse = false) => {
        sel.innerHTML = ''; // Clear default
        if (!reverse) {
            for (let i = start; i <= end; i++) {
                const opt = document.createElement('option');
                const val = i < 10 ? '0' + i : i; // Pad zero
                opt.value = val;
                opt.innerText = val;
                sel.appendChild(opt);
            }
        } else {
            for (let i = end; i >= start; i--) {
                const opt = document.createElement('option');
                const val = i;
                opt.value = val;
                opt.innerText = val;
                sel.appendChild(opt);
            }
        }
    };

    addOps(daySelect, 1, 31);
    addOps(monthSelect, 1, 12);
    // Years: 1920 to Current Year
    addOps(yearSelect, 1920, new Date().getFullYear(), true);
}

async function submitBodyAnalysis() {
    const input = document.getElementById('body-image');
    const out = document.getElementById('body-result');
    if (!input || !input.files || input.files.length === 0) {
        out.textContent = 'Please choose an image.';
        return;
    }
    const fd = new FormData();
    fd.append('image', input.files[0]);
    try {
        const res = await fetch(`${API_URL}/analyze-proportion`, { method: 'POST', body: fd, headers: { 'Accept': 'application/json' } });
        const ct = res.headers.get('content-type') || '';
        const data = ct.includes('application/json') ? await res.json() : { message: await res.text() };
        if (!res.ok) {
            out.textContent = data.message || 'Error';
            return;
        }
        out.innerText = '';
        out.innerHTML = formatAnalyzeHTML(data);
    } catch (e) {
        out.textContent = e.message;
    }
}

async function submitBodyShape() {
    const input = document.getElementById('body-image');
    const out = document.getElementById('body-result');
    if (!input || !input.files || input.files.length === 0) {
        out.textContent = 'Please choose an image.';
        return;
    }
    const fd = new FormData();
    fd.append('image', input.files[0]);
    try {
        const res = await fetch(`${API_URL}/identify-body-shape`, { method: 'POST', body: fd, headers: { 'Accept': 'application/json' } });
        const ct = res.headers.get('content-type') || '';
        const data = ct.includes('application/json') ? await res.json() : { message: await res.text() };
        if (!res.ok) {
            out.textContent = data.message || 'Error';
            return;
        }
        out.innerText = '';
        out.innerHTML = formatIdentifyHTML(data);
    } catch (e) {
        out.textContent = e.message;
    }
}
async function checkUserSession() {
    // Port check moved to global scope


    const userStr = localStorage.getItem('user');
    const userMenu = document.getElementById('user-menu');

    // 2. Logic for Guest or Not Logged In
    if (!userStr) {
        if (userMenu) {
            userMenu.innerHTML = '<a href="login.html" class="btn-bubble-pink">Login</a>';
        }
        // Don't redirect to login.html here so users can browse landing page if they want (optional, but good UX)
        // If strict login required: window.location.replace('login.html');
        // For now, let's strictly redirect if not on auth page (current logic expects login)
        window.location.replace('login.html');
        return;
    }

    const user = JSON.parse(userStr);

    // 3. Check if user is Guest
    if (user.id === 'guest' || user.username === 'guest') {
        if (userMenu) {
            // Show "Log In" button instead of Avatar for Guests
            userMenu.innerHTML = '<a href="login.html" class="btn-bubble-pink">Login</a>';
        }
        // Allow guest to stay on page
        loadShopItems();
        initCarousel();
        return;
    }

    // 4. Normal Authenticated User Verification
    const currentPage = window.location.pathname.split('/').pop();

    if (user.role !== 'ADMIN' && currentPage === 'admin_index.html') {
        alert('Access Denied: Admin Rights Required');
        window.location.replace('index.html');
        return;
    }

    // Fetch Profile to sync Avatar
    try {
        const userId = user.user_id || user.id;
        const res = await fetch(`${API_URL}/profile?user_id=${userId}&t=${new Date().getTime()}`, {
            headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' }
        });

        if (res.ok) {
            const data = await res.json();
            if (data.success && data.profile) {
                localStorage.setItem('user', JSON.stringify(data.profile));

                const navImg = document.getElementById('nav-avatar');
                if (navImg) {
                    navImg.src = getAvatarUrl(data.profile);
                    navImg.onerror = function () {
                        this.onerror = null;
                        this.src = `https://ui-avatars.com/api/?name=${data.profile.username || 'User'}&background=random&color=fff`;
                    };
                }
            }
        } else {
            updateNavbarFromLocalStorage(user);
        }
    } catch (error) {
        console.error('Error fetching profile:', error);
        updateNavbarFromLocalStorage(user);
    }

    loadShopItems();
}

// Helper function to update navbar from localStorage (fallback)
function updateNavbarFromLocalStorage(user) {
    const navImg = document.getElementById('nav-avatar');
    if (navImg) {
        navImg.src = getAvatarUrl(user);
        navImg.onerror = function () {
            this.onerror = null;
            this.src = `https://ui-avatars.com/api/?name=${user.username || 'User'}&background=random&color=fff`;
        };
    }
}

function _round(x) {
    return Math.round(x * 1000) / 1000;
}

function getPreferredGender(r) {
    const sel = document.getElementById('gender-select');
    if (sel) {
        const v = (sel.value || '').toLowerCase();
        if (v === 'male') return 'Male';
        if (v === 'female') return 'Female';
    }
    return guessGenderFromRatios(r);
}

function guessGenderFromRatios(r) {
    const s = r.shoulder_ratio || 0;
    const h = r.hip_ratio || 0;
    const w = r.waist_ratio || 0;
    // Conservative thresholds to avoid misclassification
    if ((s - h) > 0.05 && w >= (Math.min(s, h) * 0.80)) return 'Male';
    if ((h - s) > 0.05 && w <= (Math.min(s, h) * 0.95)) return 'Female';
    return 'Uncertain';
}

function guessShapeFromRatios(r) {
    const s = r.shoulder_ratio || 0;
    const h = r.hip_ratio || 0;
    const delta = s - h;
    if (Math.abs(delta) < 0.02) return 'H';
    if (delta >= 0.05) return 'V';
    if (delta <= -0.03) return 'A';
    return 'H';
}

function humanShapeName(shape) {
    if (shape === 'X') return 'Hourglass (X)';
    if (shape === 'V') return 'Inverted Triangle (V)';
    if (shape === 'A') return 'Triangle/Pear (A)';
    return 'Rectangle (H)';
}

function recsFor(shape, gender) {
    const male = {
        V: [
            'V-neck tops; darker colors on top',
            'Straight-leg trousers to balance broad shoulders',
            'Avoid heavy shoulder pads and tight shoulder fits'
        ],
        A: [
            'Structured jackets to add width to the upper body',
            'Light-colored shirts; details around shoulders/chest',
            'Avoid overly tight pants that emphasize hips'
        ],
        H: [
            'Layering with structured outerwear to create angles',
            'Straight-leg pants with mid rise',
            'Avoid skin-tight outfits head-to-toe'
        ],
        X: [
            'Well-fitted tops; define the waist with belts',
            'Straight or slim trousers (not too skinny)',
            'Avoid overly oversized silhouettes that hide the waist'
        ]
    };
    const female = {
        V: [
            'A-line and flared skirts to balance hips',
            'V-neck and raglan sleeves to soften shoulders',
            'Avoid large shoulder pads and stiff peplums'
        ],
        A: [
            'Shoulder/collar details; cropped jackets; structured blazers',
            'Darker, slightly straight skirts or trousers',
            'Avoid overly flared skirts at the hips'
        ],
        H: [
            'Wrap dresses; highlight the waist with belts',
            'Wide-leg or straight pants, mid/high rise',
            'Avoid full bodycon looks'
        ],
        X: [
            'Fitted dresses; light peplum; high-waist bottoms',
            'Pencil skirts; straight-leg trousers',
            'Avoid oversized items that hide the waist'
        ]
    };
    const bank = gender === 'Male' ? male : female;
    return bank[shape] || [];
}

function formatAnalyzeNarrative(r) {
    const s = _round(r.shoulder_ratio || 0);
    const w = _round(r.waist_ratio || 0);
    const h = _round(r.hip_ratio || 0);
    const l = _round(r.leg_ratio || 0);
    const gender = getPreferredGender(r);
    const shape = guessShapeFromRatios(r);
    const name = humanShapeName(shape);
    const notes = [];
    if (s > h + 0.02) notes.push('Shoulders are wider than hips');
    else if (h > s + 0.02) notes.push('Hips are wider than shoulders');
    else notes.push('Shoulders and hips are balanced');
    if (w < Math.min(s, h) * 0.85) notes.push('Defined waist');
    if (l > 0.5) notes.push('Long leg proportion');
    const rs = recsFor(shape, gender === 'Uncertain' ? 'Female' : gender);
    const gline = gender === 'Uncertain' ? 'Estimated gender: Uncertain (you can set it above)' : `Estimated gender: ${gender}`;
    const header = `Body Proportions Summary\nLikely shape: ${name}\n${gline}`;
    const ratios = `Key ratios:\n- Shoulder-to-Height: ${s}\n- Waist-to-Height: ${w}\n- Hip-to-Height: ${h}\n- Leg-to-Height: ${l}`;
    const obs = `Observations:\n- ${notes.join('\n- ')}`;
    const rec = rs.length ? `Recommended outfits:\n- ${rs.join('\n- ')}` : `Recommended outfits:\n- Choose well-fitted pieces, balance shoulder–hip, lightly define the waist`;
    return [header, ratios, obs, rec].join('\n\n');
}

function formatIdentifyNarrative(data) {
    const r = data.ratios || {};
    const s = _round(r.shoulder_ratio || 0);
    const w = _round(r.waist_ratio || 0);
    const h = _round(r.hip_ratio || 0);
    const l = _round(r.leg_ratio || 0);
    const shape = data.body_shape || guessShapeFromRatios(r);
    const name = humanShapeName(shape);
    const conf = typeof data.confidence === 'number' ? Math.round(data.confidence * 100) : null;
    const userPref = getPreferredGender(r);
    const gender = userPref !== 'Uncertain' ? userPref : (data.gender || 'Uncertain');
    const rs = recsFor(shape, gender === 'Uncertain' ? 'Female' : gender);
    const header = conf !== null ? `Body shape: ${name} (confidence ~${conf}%)` : `Body shape: ${name}`;
    const gconf = typeof data.gender_confidence === 'number' ? ` (~${Math.round(data.gender_confidence * 100)}%)` : '';
    const gline = gender === 'Uncertain'
        ? 'Estimated gender: Uncertain (you can set it above)'
        : `Estimated gender: ${gender}${userPref !== 'Uncertain' ? ' (selected)' : gconf}`;
    const ratios = `Key ratios:\n- Shoulder-to-Height: ${s}\n- Waist-to-Height: ${w}\n- Hip-to-Height: ${h}\n- Leg-to-Height: ${l}`;
    const rec = rs.length ? `Recommended outfits:\n- ${rs.join('\n- ')}` : `Recommended outfits:\n- Choose well-fitted pieces, balance shoulder–hip, lightly define the waist`;
    const src = data.source ? `Prediction source: ${data.source === 'ml' ? 'ML model' : data.source.replace('_', ' ')}` : '';
    return [header, gline, ratios, rec, src].filter(Boolean).join('\n\n');
}

function formatAnalyzeHTML(data) {
    const r = data.ratios || data || {};
    const s = _round(r.shoulder_ratio || 0);
    const w = _round(r.waist_ratio || 0);
    const h = _round(r.hip_ratio || 0);
    const l = _round(r.leg_ratio || 0);
    const userPref = getPreferredGender(r);
    const gender = userPref !== 'Uncertain' ? userPref : (data.gender || 'Uncertain');
    const gconf = userPref !== 'Uncertain'
        ? ' (selected)'
        : (typeof data.gender_confidence === 'number' ? ` (~${Math.round(data.gender_confidence * 100)}%)` : '');
    const shape = guessShapeFromRatios(r);
    const name = humanShapeName(shape);
    const notes = [];
    if (s > h + 0.02) notes.push('Shoulders are wider than hips');
    else if (h > s + 0.02) notes.push('Hips are wider than shoulders');
    else notes.push('Shoulders and hips are balanced');
    if (w < Math.min(s, h) * 0.85) notes.push('Defined waist');
    if (l > 0.5) notes.push('Long leg proportion');
    const rs = recsFor(shape, gender === 'Uncertain' ? 'Female' : gender);
    const recLis = rs.map(x => `<li>${x}</li>`).join('');
    const obsLis = notes.map(x => `<li>${x}</li>`).join('');
    return `
    <div style="background:#fff; border:1px solid #eee; border-radius:12px; padding:16px; text-align:left;">
      <div style="display:flex; gap:12px; flex-wrap:wrap;">
        <div style="flex:1; min-width:240px;">
          <div style="font-weight:600; margin-bottom:6px;">Body shape</div>
          <div>${name}</div>
        </div>
        <div style="flex:1; min-width:240px;">
          <div style="font-weight:600; margin-bottom:6px;">Estimated gender</div>
          <div>${gender}${gconf}</div>
        </div>
      </div>
      <hr style="border:none; border-top:1px solid #eee; margin:12px 0;">
      <div style="display:flex; gap:12px; flex-wrap:wrap;">
        <div style="flex:1; min-width:240px;">
          <div style="font-weight:600; margin-bottom:6px;">Key ratios</div>
          <ul style="margin:0; padding-left:18px;">
            <li>Shoulder-to-Height: ${s}</li>
            <li>Waist-to-Height: ${w}</li>
            <li>Hip-to-Height: ${h}</li>
            <li>Leg-to-Height: ${l}</li>
          </ul>
        </div>
        <div style="flex:1; min-width:240px;">
          <div style="font-weight:600; margin-bottom:6px;">Observations</div>
          <ul style="margin:0; padding-left:18px;">${obsLis}</ul>
        </div>
      </div>
      <hr style="border:none; border-top:1px solid #eee; margin:12px 0;">
      <div>
        <div style="font-weight:600; margin-bottom:6px;">Recommended outfits</div>
        <ul style="margin:0; padding-left:18px;">${recLis || '<li>Choose well-fitted pieces, balance shoulder–hip, lightly define the waist</li>'}</ul>
      </div>
    </div>`;
}

function formatIdentifyHTML(data) {
    const r = data.ratios || {};
    const s = _round(r.shoulder_ratio || 0);
    const w = _round(r.waist_ratio || 0);
    const h = _round(r.hip_ratio || 0);
    const l = _round(r.leg_ratio || 0);
    const shape = data.body_shape || guessShapeFromRatios(r);
    const name = humanShapeName(shape);
    const conf = typeof data.confidence === 'number' ? ` (~${Math.round(data.confidence * 100)}%)` : '';
    const userPref = getPreferredGender(r);
    const gender = userPref !== 'Uncertain' ? userPref : (data.gender || 'Uncertain');
    const gconf = userPref !== 'Uncertain'
        ? ' (selected)'
        : (typeof data.gender_confidence === 'number' ? ` (~${Math.round(data.gender_confidence * 100)}%)` : '');
    const rs = recsFor(shape, gender === 'Uncertain' ? 'Female' : gender);
    const recLis = rs.map(x => `<li>${x}</li>`).join('');
    return `
    <div style="background:#fff; border:1px solid #eee; border-radius:12px; padding:16px; text-align:left;">
      <div style="display:flex; gap:12px; flex-wrap:wrap;">
        <div style="flex:1; min-width:240px;">
          <div style="font-weight:600; margin-bottom:6px;">Body shape</div>
          <div>${name}${conf}</div>
        </div>
        <div style="flex:1; min-width:240px;">
          <div style="font-weight:600; margin-bottom:6px;">Estimated gender</div>
          <div>${gender}${gconf}</div>
        </div>
      </div>
      <hr style="border:none; border-top:1px solid #eee; margin:12px 0;">
      <div style="display:flex; gap:12px; flex-wrap:wrap;">
        <div style="flex:1; min-width:240px;">
          <div style="font-weight:600; margin-bottom:6px;">Key ratios</div>
          <ul style="margin:0; padding-left:18px;">
            <li>Shoulder-to-Height: ${s}</li>
            <li>Waist-to-Height: ${w}</li>
            <li>Hip-to-Height: ${h}</li>
            <li>Leg-to-Height: ${l}</li>
          </ul>
        </div>
        <div style="flex:1; min-width:240px;">
          <div style="font-weight:600; margin-bottom:6px;">Recommended outfits</div>
          <ul style="margin:0; padding-left:18px;">${recLis || '<li>Choose well-fitted pieces, balance shoulder–hip, lightly define the waist</li>'}</ul>
        </div>
      </div>
      ${data.source ? `<div style="margin-top:8px; color:#666;">Prediction source: ${data.source === 'ml' ? 'ML model' : data.source.replace('_', ' ')}</div>` : ''}
    </div>`;
}

// Carousel Logic
// Carousel Logic
// Carousel Logic
function initCarousel() {
    const track = document.getElementById('carousel-track');
    // Selector changed to hero-slide for new structure
    const slides = document.querySelectorAll('.hero-slide');

    if (!track || slides.length === 0) return;

    let index = 0;
    const totalSlides = slides.length;

    // Config
    const autoPlayDelay = 5000;
    let autoPlayTimer;

    const updateCarousel = () => {
        // Full width sliding
        track.style.transform = `translateX(-${index * 100}%)`;
    };

    const nextSlide = () => {
        index++;
        if (index >= totalSlides) index = 0;
        updateCarousel();
    };

    const prevSlide = () => {
        index--;
        if (index < 0) index = totalSlides - 1;
        updateCarousel();
    };

    const startAutoPlay = () => {
        clearInterval(autoPlayTimer);
        autoPlayTimer = setInterval(nextSlide, autoPlayDelay);
    };

    // Listeners
    const nextBtn = document.querySelector('.next-btn');
    const prevBtn = document.querySelector('.prev-btn');

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            nextSlide();
            startAutoPlay();
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            prevSlide();
            startAutoPlay();
        });
    }

    // Init
    updateCarousel();
    startAutoPlay();
}

function scrollToSection(id) {
    document.getElementById('home-view').classList.remove('hidden');
    document.getElementById('profile-view').classList.add('hidden');
    const el = document.getElementById(id);
    if (el) {
        // offset for fixed nav
        const y = el.getBoundingClientRect().top + window.scrollY - 80;
        window.scrollTo({ top: y, behavior: 'smooth' });
    }
}

function openProfile() {
    document.getElementById('home-view').classList.add('hidden');
    document.querySelector('.hero-carousel-section').classList.add('hidden');
    document.getElementById('profile-view').classList.remove('hidden');
    loadProfile();
}

function closeProfile() {
    document.getElementById('home-view').classList.remove('hidden');
    document.querySelector('.hero-carousel-section').classList.remove('hidden');
    document.getElementById('profile-view').classList.add('hidden');
}

// Load Profile - REFACTORED to fetch from API
async function loadProfile() {
    const localUser = JSON.parse(localStorage.getItem('user'));
    if (!localUser) return;

    try {
        // Fetch latest profile from server
        // Using user_id from local storage to query
        const userId = localUser.user_id || localUser.id;
        if (!userId) {
            console.error("No user ID found locally");
            return;
        }

        // Add timestamp to prevent caching
        const res = await fetch(`${API_URL}/profile?user_id=${userId}&t=${new Date().getTime()}`, {
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        const data = await res.json();

        // If success, update local storage with fresh data
        if (res.ok && data.success && data.profile) {
            localStorage.setItem('user', JSON.stringify(data.profile));
            // Proceed to render using the fresh data
            renderProfileUI(data.profile);

            // Also update navbar avatar directly
            const navImg = document.getElementById('nav-avatar');
            if (navImg) {
                navImg.src = getAvatarUrl(data.profile);
            }
        } else {
            console.warn("Failed to fetch fresh profile, using local data");
            renderProfileUI(localUser);
        }
    } catch (e) {
        console.error("Error fetching profile:", e);
        renderProfileUI(localUser); // Fallback
    }
}

function renderProfileUI(user) {
    if (!user) return;

    // Display header info
    document.getElementById('profile-name-display').innerText = user.fullname || user.username;

    // Profile Avatar
    const profileImg = document.getElementById('profile-avatar-main');
    if (profileImg) {
        profileImg.src = getAvatarUrl(user);
        profileImg.onerror = function () {
            this.onerror = null;
            this.src = `https://ui-avatars.com/api/?name=${user.username || 'User'}&background=random&color=fff`;
        };
    }

    // Also update nav avatar if it's visible while in profile view
    const navImg = document.getElementById('nav-avatar');
    if (navImg) {
        navImg.src = getAvatarUrl(user);
    }

    // Populate Form Fields
    // Handle Name Split
    let lastName = '';
    let firstName = '';

    if (user.fullname) {
        const parts = user.fullname.split(' ');
        if (parts.length > 0) lastName = parts[0];
        if (parts.length > 1) firstName = parts.slice(1).join(' ');
    } else if (user.username) {
        firstName = user.username;
    }

    document.getElementById('p-lastname').value = lastName;
    document.getElementById('p-firstname').value = firstName;
    document.getElementById('p-email').value = user.email || '';
    document.getElementById('p-phone').value = user.phone || '';
    document.getElementById('p-address').value = user.address || '';
    document.getElementById('p-gender').value = user.gender || 'Female';

    // DOB Split
    if (user.dob) {
        const parts = user.dob.split('/');
        if (parts.length === 3) {
            document.getElementById('dob-day').value = parts[0];
            document.getElementById('dob-month').value = parts[1];
            document.getElementById('dob-year').value = parts[2];
        }
    }
}

async function saveProfile() {
    const user = JSON.parse(localStorage.getItem('user'));

    if (!user || !user.user_id && !user.id) {
        alert('Error: User session not found. Please login again.');
        return;
    }

    // Create FormData for multipart/form-data
    const formData = new FormData();
    formData.append('user_id', user.user_id || user.id); // Handle id/user_id consistency
    formData.append('fullname', document.getElementById('p-lastname').value + ' ' + document.getElementById('p-firstname').value);
    // Or keep them separate if DB supports it, but standard user model has 'fullname'. 
    // Wait, the form has separate First/Last name but DB has 'fullname'. I should concat or update backend?
    // Backend has 'fullname'.
    // Let's assume user wants to save what is in the fields.
    // Ideally I should store split names or keep using fullname. 
    // The previous code used p-fullname. Now we have p-lastname and p-firstname.
    // I will concat them for now.

    const lastName = document.getElementById('p-lastname').value;
    const firstName = document.getElementById('p-firstname').value;
    formData.append('fullname', `${lastName} ${firstName}`.trim());

    formData.append('email', document.getElementById('p-email').value);
    formData.append('phone', document.getElementById('p-phone').value);
    formData.append('address', document.getElementById('p-address').value);
    formData.append('gender', document.getElementById('p-gender').value);

    const dob = `${document.getElementById('dob-day').value}/${document.getElementById('dob-month').value}/${document.getElementById('dob-year').value}`;
    formData.append('dob', dob);

    // Avatar
    const avatarInput = document.getElementById('avatar-upload');
    if (avatarInput && avatarInput.files[0]) {
        console.log('Avatar file selected:', avatarInput.files[0].name);
        formData.append('avatar_file', avatarInput.files[0]);
    }

    try {
        console.log('Sending profile update to:', `${API_URL}/profile`);
        const res = await fetch(`${API_URL}/profile`, {
            method: 'POST',
            // No Content-Type header! Browser sets it for FormData
            body: formData
        });

        console.log('Response status:', res.status);

        if (!res.ok) {
            const errorText = await res.text();
            console.error('Server error response:', errorText);
            alert(`Server Error (${res.status}): ${errorText}\n\nPlease check:\n1. Backend is running (port 5050)\n2. Check terminal for errors`);
            return;
        }

        const data = await res.json();

        console.log('=== PROFILE SAVE RESPONSE ===');
        console.log('Full response:', data);
        console.log('Avatar URL from server:', data.profile?.avatar || data.avatar);
        console.log('=============================');

        if (res.ok && data.success) {
            // Check if profile object is returned (as per new backend spec)
            if (data.profile) {
                // Update local storage with the FULL profile from server
                // This ensures UI matches backend state exactly
                console.log('Updating localStorage with profile:', data.profile);
                localStorage.setItem('user', JSON.stringify(data.profile));

                // IMMEDIATELY update navbar avatar using Helper
                const navImg = document.getElementById('nav-avatar');
                if (navImg) {
                    const newUrl = getAvatarUrl(data.profile);
                    console.log('Setting navbar avatar to:', newUrl);
                    navImg.src = newUrl;
                }

                // ALSO update profile page avatar
                const profileImg = document.getElementById('profile-avatar-main');
                if (profileImg) {
                    const newUrl = getAvatarUrl(data.profile);
                    console.log('Setting profile avatar to:', newUrl);
                    profileImg.src = newUrl;
                }
            } else {
                // Fallback block if no profile object
                const newUser = { ...user };
                if (data.avatar) newUser.avatar = data.avatar;
                newUser.fullname = `${lastName} ${firstName}`.trim();
                newUser.email = document.getElementById('p-email').value;
                newUser.phone = document.getElementById('p-phone').value;
                newUser.address = document.getElementById('p-address').value;
                newUser.gender = document.getElementById('p-gender').value;
                newUser.dob = dob;
                localStorage.setItem('user', JSON.stringify(newUser));

                const navImg = document.getElementById('nav-avatar');
                if (navImg) navImg.src = getAvatarUrl(newUser);

                const profileImg = document.getElementById('profile-avatar-main');
                if (profileImg) profileImg.src = getAvatarUrl(newUser);
            }

            alert('Profile Updated Successfully!');

            // DO NOT RELOAD - just close profile view
            // Avatar has already been updated in navbar above
            closeProfile();

            // Note: If avatar was uploaded, the src is already updated by preview, 
            // but for persistency we used the one from server response in localstorage.
        } else {
            alert('Update Failed: ' + (data.message || "Unknown error"));
        }
    } catch (e) {
        console.error('Error updating profile:', e);
        alert(`Error updating profile:\n${e.message}\n\nPlease check:\n1. Backend is running on port 8080\n2. Open console (F12) for more details`);
    }
}

async function loadShopItems() {
    const grid = document.getElementById('shop-grid-container');
    const filters = document.getElementById('shop-filters');
    const toggleBtn = document.getElementById('shop-toggle-btn');
    const shopsRow = document.getElementById('shops-row');
    if (!grid) return;
    try {
        // 1) Load distinct shops (with shop_url) and show as links
        const shopRes = await fetch(`${API_URL}/shops`);
        const shopList = await shopRes.json();
        // 2) Lazy load products only after user clicks a shop
        let productsCache = null;
        let currentShop = null;
        let expanded = false;
        const ensureProducts = async () => {
            if (productsCache) return productsCache;
            const res = await fetch(`${API_URL}/products`);
            productsCache = await res.json();
            return productsCache;
        };
        const renderProducts = async (shopName) => {
            currentShop = shopName;
            const products = await ensureProducts();
            grid.innerHTML = '';
            const full = shopName === 'ALL' ? products : products.filter(p => (p.shop_name || '').trim() === shopName);
            const items = expanded ? full : full.slice(0, Math.min(full.length, 4));
            if (items.length === 0) {
                grid.innerHTML = `<div style="padding:12px; color:#666;">No products available${shopName !== 'ALL' ? ' for this shop' : ''}.</div>`;
                return;
            }
            items.forEach(p => {
                const price = p.price && Number(p.price) > 0 ? `$${(Number(p.price)/100).toFixed(2)}` : '';
                grid.innerHTML += `
                  <div class="card">
                    <img src="${p.image}" alt="${p.name}">
                    <div class="card-body">
                      <h4 title="${p.name}">${p.name}</h4>
                      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                        <span class="badge" title="${p.shop_name}">${p.shop_name || 'Shop'}</span>
                        <div style="display:flex; gap:8px; align-items:center;">
                          ${price ? `<span class="badge" style="background:#eef;">${price}</span>` : ''}
                          <a href="${p.product_url}" target="_blank" class="btn btn-secondary" style="width:auto; padding:5px 10px; font-size:0.8rem;">Buy</a>
                        </div>
                      </div>
                    </div>
                  </div>
                `;
            });
            if (toggleBtn) {
                toggleBtn.style.display = 'inline-block';
                toggleBtn.textContent = expanded ? 'Collapse' : 'View All';
            }
        };
        // Initial message (no products yet)
        grid.innerHTML = `<div style="padding:12px; color:#666;">Choose a shop below to view products.</div>`;
        if (shopsRow) {
            shopsRow.innerHTML = '';
            // Build pills with external link
            const mkPill = (shop) => {
                const wrap = document.createElement('div');
                wrap.style = 'display:flex; align-items:center; gap:6px;';
                const btn = document.createElement('button');
                btn.className = 'btn';
                btn.style = 'width:auto; padding:6px 12px; font-size:0.85rem;';
                btn.textContent = shop.shop_name;
                btn.addEventListener('click', () => {
                    expanded = true;
                    if (filters) filters.style.display = 'flex';
                    renderProducts(shop.shop_name);
                });
                wrap.appendChild(btn);
                if (shop.shop_url) {
                    const a = document.createElement('a');
                    a.href = shop.shop_url;
                    a.target = '_blank';
                    a.title = 'Open shop';
                    a.textContent = '↗';
                    a.style = 'text-decoration:none; font-size:1rem;';
                    wrap.appendChild(a);
                }
                return wrap;
            };
            // Optional "All Shops"
            const allWrap = document.createElement('div');
            allWrap.style = 'display:flex; align-items:center; gap:6px;';
            const allBtn = document.createElement('button');
            allBtn.className = 'btn';
            allBtn.style = 'width:auto; padding:6px 12px; font-size:0.85rem;';
            allBtn.textContent = 'All Shops';
            allBtn.addEventListener('click', () => {
                expanded = true;
                if (filters) filters.style.display = 'flex';
                renderProducts('ALL');
            });
            allWrap.appendChild(allBtn);
            shopsRow.appendChild(allWrap);
            (shopList || []).forEach(s => shopsRow.appendChild(mkPill(s)));

            if ((shopList || []).length > 0) {
                expanded = false;
                if (filters) filters.style.display = 'flex';
                await renderProducts(shopList[0].shop_name);
            }
        }
        if (toggleBtn) {
            toggleBtn.style.display = 'none'; // hidden until a shop is selected
            toggleBtn.addEventListener('click', () => {
                expanded = !expanded;
                toggleBtn.textContent = expanded ? 'Collapse' : 'View All';
                if (filters) filters.style.display = expanded ? 'flex' : 'none';
                if (currentShop) renderProducts(currentShop);
            });
        }
        if (filters) {
            filters.innerHTML = ''; // will be filled after a shop is selected
            filters.style.display = 'none';
        }
    } catch (e) {
        console.error('Load products failed', e);
    }
}

async function loadShopRegistry() {
    const container = document.getElementById('shop-rename-container');
    if (!container) return;
    container.innerHTML = 'Loading...';
    try {
        const res = await fetch(`${API_URL}/shops`);
        let shops = await res.json();
        shops = (shops || []).filter(s => (s.shop_url || '').includes('shopee.vn'));
        container.innerHTML = '';
        if (!shops || shops.length === 0) {
            container.innerHTML = '<div style="color:#666;">No Shopee shops found.</div>';
            return;
        }
        shops.forEach(s => {
            const row = document.createElement('div');
            row.style = 'display:flex; gap:10px; align-items:center; margin-bottom:8px;';
            const label = document.createElement('span');
            label.textContent = s.shop_name;
            label.style = 'min-width:220px; font-weight:600;';
            const input = document.createElement('input');
            input.type = 'text';
            input.value = s.shop_name;
            input.style = 'flex:1; padding:6px 8px;';
            const btn = document.createElement('button');
            btn.className = 'btn btn-primary';
            btn.style = 'width:auto; padding:6px 12px;';
            btn.textContent = 'Save';
            btn.addEventListener('click', async () => {
                const newName = input.value.trim();
                if (!newName || newName === s.shop_name) return;
                const r = await fetch(`${API_URL}/admin/shops/rename`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ old_name: s.shop_name, new_name: newName })
                });
                const data = await r.json().catch(() => ({}));
                if (r.ok) {
                    await loadShopRegistry();
                    alert(`Updated ${data.updated || 0} products to "${newName}"`);
                } else {
                    alert(data.message || 'Rename failed');
                }
            });
            row.appendChild(label);
            row.appendChild(input);
            row.appendChild(btn);
            container.appendChild(row);
        });
    } catch (e) {
        container.innerHTML = '<div style="color:red;">Failed to load shops.</div>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const registry = document.getElementById('shop-rename-container');
    if (registry) loadShopRegistry();
});
