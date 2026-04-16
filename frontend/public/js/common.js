const API_ROOT = '/api';

function getAuthToken() {
    return localStorage.getItem('token');
}

function getCurrentRole() {
    return localStorage.getItem('role');
}

function getDisplayName() {
    return localStorage.getItem('display_name') || localStorage.getItem('username') || 'User';
}

async function fetchAPI(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };

    const token = getAuthToken();
    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${API_ROOT}${endpoint}`, {
        method: options.method || 'GET',
        headers,
        body: options.body,
    });

    if (response.status === 401) {
        localStorage.clear();
        if (!window.location.pathname.endsWith('login.html')) {
            window.location.href = 'login.html';
        }
    }

    return response;
}

async function handleLogin(role, username, password) {
    const response = await fetchAPI('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ role, username, password })
    });

    if (!response.ok) {
        return false;
    }

    const data = await response.json();
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('role', data.role);
    localStorage.setItem('username', data.user_id || data.username);
    localStorage.setItem('display_name', data.display_name || data.username);
    return true;
}

function checkRole(role) {
    const currentRole = getCurrentRole();
    const onLoginPage = window.location.pathname.endsWith('login.html');
    if (!currentRole && !onLoginPage) {
        window.location.href = 'login.html';
        return;
    }
    if (currentRole && currentRole !== role && !onLoginPage) {
        window.location.href = `${currentRole}_portal.html`;
    }
}

function logout() {
    localStorage.clear();
    window.location.href = 'login.html';
}
