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

                if (data.role === 'ADMIN') {
                    // Admin logging in via User Form -> Redirect to Admin Dashboard
                    alert('Login Success! Welcome Admin. Redirecting to Dashboard...');
                    localStorage.setItem('user', JSON.stringify(data));
                    window.location.href = 'admin_index.html';
                } else {
                    alert('Login Success! Redirecting...');
                    localStorage.setItem('user', JSON.stringify(data));
                    window.location.href = 'index.html';
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
    if (!grid) return;

    try {
        const res = await fetch(`${API_URL}/outfits`);
        const data = await res.json();
        grid.innerHTML = '';
        data.forEach(item => {
            grid.innerHTML += `
               <div class="card">
                    <img src="${item.image}">
                    <div class="card-body">
                        <h4>${item.name}</h4>
                        <div style="display:flex; justify-content:space-between; margin-top:10px;">
                            <span class="badge">$49.99</span>
                            <a href="${item.shop_link}" target="_blank" class="btn btn-secondary" style="width:auto; padding:5px 10px; font-size:0.8rem;">Buy Now</a>
                        </div>
                    </div>
               </div>
            `;
        });
    } catch (e) { }
}
