const API_BASE = (window.API_GATEWAY_URL || '').replace(/\/$/, '');

function apiUrl(path) {
    return API_BASE ? `${API_BASE}${path}` : path;
}

// Global state
let currentPage = 1;
let currentSearch = '';
let currentSearchField = 'movie_name';
let totalPages = 1;
let charts = {}; // Store chart instances
let currentUser = null;
let authToken = localStorage.getItem('authToken') || '';

// DOM Elements
const moviesContainer = document.getElementById('moviesContainer');
const movieListView = document.getElementById('movieListView');
const movieDetailView = document.getElementById('movieDetailView');
const movieDetail = document.getElementById('movieDetail');
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const searchFieldSelect = document.getElementById('searchFieldSelect'); // new
const backBtn = document.getElementById('backBtn');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const pageInfo = document.getElementById('pageInfo');
const loadingSpinner = document.getElementById('loadingSpinner');
const visualizationView = document.getElementById('visualizationView');
const tabButtons = document.querySelectorAll('.tab-btn');
const trendingMoviesContainer = document.getElementById('trendingMoviesContainer');
const recommendedMoviesSection = document.getElementById('recommendedMoviesSection');
const recommendedMoviesContainer = document.getElementById('recommendedMoviesContainer');
const recommendedHomeSource = document.getElementById('recommendedHomeSource');
const similarMoviesSection = document.getElementById('similarMoviesSection');
const similarMoviesContainer = document.getElementById('similarMoviesContainer');
const guestActions = document.getElementById('guestActions');
const userActions = document.getElementById('userActions');
const openLoginBtn = document.getElementById('openLoginBtn');
const openRegisterBtn = document.getElementById('openRegisterBtn');
const profileBtn = document.getElementById('profileBtn');
const logoutBtn = document.getElementById('logoutBtn');
const userInitial = document.getElementById('userInitial');
const userNameLabel = document.getElementById('userNameLabel');
const authModal = document.getElementById('authModal');
const closeAuthModalBtn = document.getElementById('closeAuthModalBtn');
const loginTabBtn = document.getElementById('loginTabBtn');
const registerTabBtn = document.getElementById('registerTabBtn');
const profileTabBtn = document.getElementById('profileTabBtn');
const authModalTitle = document.getElementById('authModalTitle');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const profileForm = document.getElementById('profileForm');
const authMessage = document.getElementById('authMessage');
const adminTabBtn = document.getElementById('adminTabBtn');
const adminPanelBtn = document.getElementById('adminPanelBtn');
const adminView = document.getElementById('adminView');
const adminAddMovieBtn = document.getElementById('adminAddMovieBtn');
const adminFormPanel = document.getElementById('adminFormPanel');
const adminFormTitle = document.getElementById('adminFormTitle');
const adminMovieForm = document.getElementById('adminMovieForm');
const adminCancelFormBtn = document.getElementById('adminCancelFormBtn');
const adminMoviesTableBody = document.getElementById('adminMoviesTableBody');
const adminMessage = document.getElementById('adminMessage');

let adminMoviesCache = [];

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await initializeAuth();

    // set initial search field from select (in case default changed)
    if (searchFieldSelect && searchFieldSelect.value) {
        currentSearchField = searchFieldSelect.value;
    }

    const initialMovieId = getMovieIdFromPath();
    if (initialMovieId) {
        showMovieDetail(initialMovieId, false);
    } else {
        loadMovies();
        loadHomePageSections();
    }

    // Event listeners
    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });
    if (searchFieldSelect) {
        searchFieldSelect.addEventListener('change', () => {
            // Update placeholder optionally and keep selected field
            currentSearchField = searchFieldSelect.value;
            // If user wants immediate search when changing field, uncomment:
            // handleSearch();
        });
    }
    backBtn.addEventListener('click', showMovieList);
    prevBtn.addEventListener('click', () => changePage(-1));
    nextBtn.addEventListener('click', () => changePage(1));
    openLoginBtn?.addEventListener('click', () => openAuthModal('login'));
    openRegisterBtn?.addEventListener('click', () => openAuthModal('register'));
    profileBtn?.addEventListener('click', () => openAuthModal('profile'));
    logoutBtn?.addEventListener('click', logout);
    closeAuthModalBtn?.addEventListener('click', closeAuthModal);
    authModal?.addEventListener('click', (event) => {
        if (event.target.matches('[data-close-auth]')) {
            closeAuthModal();
        }
    });
    loginTabBtn?.addEventListener('click', () => setAuthMode('login'));
    registerTabBtn?.addEventListener('click', () => setAuthMode('register'));
    profileTabBtn?.addEventListener('click', () => setAuthMode('profile'));
    loginForm?.addEventListener('submit', handleLogin);
    registerForm?.addEventListener('submit', handleRegister);
    profileForm?.addEventListener('submit', handleProfileUpdate);
    adminPanelBtn?.addEventListener('click', () => switchTab('admin'));
    adminAddMovieBtn?.addEventListener('click', () => openAdminMovieForm('create'));
    adminCancelFormBtn?.addEventListener('click', closeAdminMovieForm);
    adminMovieForm?.addEventListener('submit', handleAdminMovieSubmit);
    adminMoviesTableBody?.addEventListener('click', handleAdminTableAction);

    // Tab switching
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
});

async function initializeAuth() {
    if (!authToken) {
        renderAuthState();
        return;
    }

    try {
        const data = await authRequest('/api/auth/verify', {
            method: 'POST',
            body: JSON.stringify({ token: authToken })
        });
        if (data.valid && data.user) {
            currentUser = data.user;
        } else {
            clearAuthState();
        }
    } catch (error) {
        console.warn('Token verification failed:', error);
        clearAuthState();
    }
    renderAuthState();
}

async function authRequest(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };

    if (authToken) {
        headers.Authorization = `Bearer ${authToken}`;
    }

    const response = await fetch(apiUrl(url), {
        ...options,
        headers
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.error || 'Yêu cầu không thành công');
    }
    return data;
}

function isAdminUser() {
    return currentUser?.role === 'admin';
}

function renderAuthState() {
    const adminVisible = isAdminUser();
    document.querySelectorAll('.admin-only-btn').forEach((button) => {
        button.style.display = adminVisible ? '' : 'none';
    });

    if (currentUser) {
        guestActions.style.display = 'none';
        userActions.style.display = 'flex';
        const displayName = currentUser.full_name || currentUser.username || currentUser.email || 'Tài khoản';
        userNameLabel.textContent = displayName;
        userInitial.textContent = displayName.charAt(0).toUpperCase();
    } else {
        guestActions.style.display = 'flex';
        userActions.style.display = 'none';
        userNameLabel.textContent = 'Tài khoản';
        userInitial.textContent = 'U';
        if (adminView?.classList.contains('active')) {
            switchTab('movies');
        }
    }
}

function openAuthModal(mode = 'login') {
    authModal.style.display = 'flex';
    authModal.setAttribute('aria-hidden', 'false');
    setAuthMode(mode);
}

function closeAuthModal() {
    authModal.style.display = 'none';
    authModal.setAttribute('aria-hidden', 'true');
    setAuthMessage('');
}

function setAuthMode(mode) {
    const modeTitles = {
        login: 'Đăng nhập',
        register: 'Đăng ký',
        profile: 'Thông tin người dùng'
    };

    authModalTitle.textContent = modeTitles[mode] || modeTitles.login;
    loginForm.style.display = mode === 'login' ? 'grid' : 'none';
    registerForm.style.display = mode === 'register' ? 'grid' : 'none';
    profileForm.style.display = mode === 'profile' ? 'grid' : 'none';
    profileTabBtn.style.display = currentUser ? 'block' : 'none';

    [loginTabBtn, registerTabBtn, profileTabBtn].forEach((button) => {
        button.classList.toggle('active', button.dataset.authMode === mode);
    });

    if (mode === 'profile' && currentUser) {
        document.getElementById('profileUsername').value = currentUser.username || '';
        document.getElementById('profileEmail').value = currentUser.email || '';
        document.getElementById('profileFullName').value = currentUser.full_name || '';
    }
    setAuthMessage('');
}

async function handleLogin(event) {
    event.preventDefault();
    setAuthMessage('Đang đăng nhập...');
    try {
        const data = await authRequest('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({
                identifier: document.getElementById('loginIdentifier').value.trim(),
                password: document.getElementById('loginPassword').value
            })
        });
        applyAuthenticatedUser(data);
        loginForm.reset();
        closeAuthModal();
    } catch (error) {
        setAuthMessage(error.message, true);
    }
}

async function handleRegister(event) {
    event.preventDefault();
    setAuthMessage('Đang tạo tài khoản...');
    try {
        const data = await authRequest('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({
                username: document.getElementById('registerUsername').value.trim(),
                email: document.getElementById('registerEmail').value.trim(),
                full_name: document.getElementById('registerFullName').value.trim(),
                password: document.getElementById('registerPassword').value
            })
        });
        applyAuthenticatedUser(data);
        registerForm.reset();
        closeAuthModal();
    } catch (error) {
        setAuthMessage(error.message, true);
    }
}

async function handleProfileUpdate(event) {
    event.preventDefault();
    setAuthMessage('Đang lưu...');
    try {
        const data = await authRequest('/api/users/me', {
            method: 'PUT',
            body: JSON.stringify({
                username: document.getElementById('profileUsername').value.trim(),
                email: document.getElementById('profileEmail').value.trim(),
                full_name: document.getElementById('profileFullName').value.trim()
            })
        });
        currentUser = data.user;
        renderAuthState();
        setAuthMessage('Đã lưu thay đổi.');
    } catch (error) {
        setAuthMessage(error.message, true);
    }
}

function applyAuthenticatedUser(data) {
    authToken = data.token;
    currentUser = data.user;
    localStorage.setItem('authToken', authToken);
    renderAuthState();
    if (!getMovieIdFromPath() && movieListView.style.display !== 'none') {
        loadHomeRecommendations();
    }
}

function logout() {
    clearAuthState();
    renderAuthState();
    closeAuthModal();
    if (!getMovieIdFromPath() && movieListView.style.display !== 'none') {
        loadHomeRecommendations();
    }
}

function clearAuthState() {
    authToken = '';
    currentUser = null;
    localStorage.removeItem('authToken');
}

function setAuthMessage(message, isError = false) {
    authMessage.textContent = message;
    authMessage.classList.toggle('error', isError);
}

function getTrackableMovieId(movie) {
    const rawId = movie.movie_id || movie.movieId || movie.id;
    if (rawId === undefined || rawId === null || String(rawId).trim() === '') {
        return null;
    }
    return String(rawId).trim();
}

function getMovieInteractionPayload(movie) {
    return {
        movieId: getTrackableMovieId(movie),
        movieName: movie.movie_name || '',
        genre: movie.genre || '',
        director: movie.director || '',
        star: movie.star || ''
    };
}

function setMovieTrackingMessage(message, isError = false) {
    const messageEl = document.getElementById('movieTrackingMessage');
    if (!messageEl) return;
    messageEl.textContent = message;
    messageEl.classList.toggle('error', isError);
}

function requireLoginForTracking() {
    if (currentUser && authToken) {
        return true;
    }
    setMovieTrackingMessage('Bạn cần đăng nhập để hệ thống lưu sở thích xem phim.', true);
    openAuthModal('login');
    return false;
}

async function trackMovieView(movie) {
    const button = document.getElementById('markWatchedBtn');
    const movieId = getTrackableMovieId(movie);
    if (!movieId) {
        setMovieTrackingMessage('Không xác định được mã phim.', true);
        return;
    }

    if (currentUser && authToken) {
        if (button) {
            button.disabled = true;
            button.textContent = 'Đang lưu...';
        }
        setMovieTrackingMessage('Đang lưu phim đã xem...');

        try {
            await authRequest('/api/users/me/interactions/watch', {
                method: 'POST',
                body: JSON.stringify({
                    ...getMovieInteractionPayload(movie),
                    watchedAt: new Date().toISOString()
                })
            });
            setMovieTrackingMessage('Đã lưu vào lịch sử xem và cập nhật sở thích của bạn.');
            if (button) {
                button.textContent = 'Đã xem';
            }
        } catch (error) {
            setMovieTrackingMessage(error.message, true);
            if (button) {
                button.disabled = false;
                button.textContent = 'Xem';
            }
        }
    } else {
        const watchedMovies = getLocalWatchedMovies();
        watchedMovies.push({
            ...getMovieInteractionPayload(movie),
            watchedAt: new Date().toISOString()
        });
        localStorage.setItem('watchedMovies', JSON.stringify(watchedMovies));
        setMovieTrackingMessage('Đã lưu lịch sử xem trên thiết bị.');
        if (button) {
            button.textContent = 'Đã xem';
        }
    }
}

async function rateMovie(movie, rating) {
    if (!requireLoginForTracking()) return;

    const movieId = getTrackableMovieId(movie);
    if (!movieId) {
        setMovieTrackingMessage('Không xác định được mã phim.', true);
        return;
    }

    const numericRating = Number(rating);
    if (!Number.isInteger(numericRating) || numericRating < 1 || numericRating > 5) {
        setMovieTrackingMessage('Vui lòng chọn rating từ 1 đến 5.', true);
        return;
    }

    setMovieTrackingMessage('Đang lưu đánh giá...');
    try {
        await authRequest('/api/users/me/interactions/rating', {
            method: 'POST',
            body: JSON.stringify({
                movieId,
                rating: numericRating,
                watchedAt: new Date().toISOString()
            })
        });
        setMovieTrackingMessage(`Đã lưu đánh giá ${numericRating}/5 cho phim này.`);
    } catch (error) {
        setMovieTrackingMessage(error.message, true);
    }
}

function bindMovieInteractionControls(movie) {
    document.getElementById('markWatchedBtn')?.addEventListener('click', () => trackMovieView(movie));
    document.getElementById('userRatingSelect')?.addEventListener('change', (event) => {
        if (event.target.value) {
            rateMovie(movie, event.target.value);
        }
    });
}

// Load movies
async function loadMovies(page = 1, search = '', field = 'movie_name') {
    showLoading();
    try {
        const url = `/api/movies?page=${page}&per_page=20${search ? `&search=${encodeURIComponent(search)}` : ''}&field=${encodeURIComponent(field)}`;
        const response = await fetch(apiUrl(url));
        const data = await response.json();

        currentPage = data.page;
        totalPages = data.total_pages;
        currentSearch = search;
        currentSearchField = field;

        displayMovies(data.movies || data.data || []);
        updatePagination();
    } catch (error) {
        console.error('Error loading movies:', error);
        moviesContainer.innerHTML = '<p style="color: red; text-align: center;">Có lỗi xảy ra khi tải dữ liệu. Vui lòng thử lại.</p>';
    } finally {
        hideLoading();
    }
}

// Display movies
function displayMovies(movies) {
    if (movies.length === 0) {
        moviesContainer.innerHTML = '<p style="color: var(--text-secondary); text-align: center; grid-column: 1 / -1;">Không tìm thấy phim nào.</p>';
        return;
    }

    moviesContainer.innerHTML = movies.map(movie => {
        const posterClasses = getPosterClasses('movie-poster', movie.poster);
        const posterAlt = escapeHtml(movie.movie_name || 'Poster');
        const posterImg = movie.poster ? `
            <img src="${escapeHtml(movie.poster)}" alt="Poster ${posterAlt}" loading="lazy" onerror="handlePosterError(event)">
        ` : '';

        return `
        <div class="movie-card" onclick="showMovieDetail('${movie.movie_id}')">
            <div class="${posterClasses}">
                ${posterImg}
                <span class="poster-placeholder">${getPosterPlaceholder(movie.movie_name)}</span>
            </div>
            <div class="movie-info">
                <div class="movie-title">${escapeHtml(movie.movie_name || 'N/A')}</div>
                <div class="movie-year">${movie.year || 'N/A'}</div>
                ${movie.rating ? `
                    <div class="movie-rating">
                        <span class="rating-value">⭐ ${movie.rating}</span>
                    </div>
                ` : ''}
                ${movie.genre ? `
                    <div class="movie-genre">${escapeHtml(movie.genre)}</div>
                ` : ''}
            </div>
        </div>
    `;
    }).join('');
}

// Show movie detail
async function showMovieDetail(movieId, updateUrl = true) {
    showLoading();
    try {
        const response = await fetch(apiUrl(`/api/movies/${movieId}`));
        const movie = await response.json();

        if (movie.error) {
            alert('Không tìm thấy thông tin phim');
            return;
        }

        // ⭐ Update URL without reload
        if (updateUrl) {
            history.pushState({ movieId }, "", `/movies/${movieId}`);
        }

        displayMovieDetail(movie);
        loadSimilarRecommendations(movie.movie_id);
        movieListView.style.display = 'none';
        movieDetailView.style.display = 'block';
        window.scrollTo(0, 0);

    } catch (error) {
        console.error('Error loading movie detail:', error);
        alert('Có lỗi xảy ra khi tải thông tin phim');
    } finally {
        hideLoading();
    }
}

// Display movie detail
function displayMovieDetail(movie) {
    const stars = movie.star ? movie.star.split(',').map(s => s.trim()).filter(s => s) : [];
    const posterClasses = getPosterClasses('detail-poster', movie.poster);
    const posterAlt = escapeHtml(movie.movie_name || 'Poster');
    const posterImg = movie.poster ? `
        <img src="${escapeHtml(movie.poster)}" alt="Poster ${posterAlt}" onerror="handlePosterError(event)">
    ` : '';

    movieDetail.innerHTML = `
        <div class="detail-header">
            <div class="${posterClasses}">
                ${posterImg}
                <span class="poster-placeholder">${getPosterPlaceholder(movie.movie_name)}</span>
            </div>
            <div class="detail-info">
                <h1 class="detail-title">${escapeHtml(movie.movie_name || 'N/A')}</h1>
                <div class="detail-meta">
                    ${movie.year ? `<div class="meta-item"><strong>Năm:</strong> ${movie.year}</div>` : ''}
                    ${movie.certificate ? `<div class="meta-item"><strong>Giấy chứng nhận:</strong> ${movie.certificate}</div>` : ''}
                    ${movie.runtime ? `<div class="meta-item"><strong>Thời lượng:</strong> ${movie.runtime}</div>` : ''}
                </div>
                ${movie.rating ? `
                    <div class="detail-rating">
                        ⭐ ${movie.rating}
                        ${movie.votes ? `<span style="font-size: 1rem; color: var(--text-secondary);">(${parseInt(movie.votes).toLocaleString()} lượt đánh giá)</span>` : ''}
                    </div>
                ` : ''}
                ${movie.genre ? `
                    <div class="detail-meta">
                        <div class="meta-item"><strong>Thể loại:</strong> ${escapeHtml(movie.genre)}</div>
                    </div>
                ` : ''}
                <div class="movie-actions-panel">
                    <button id="markWatchedBtn" class="watch-action-btn" type="button">Xem</button>
                    <label class="rating-control">
                        <span>Đánh giá của bạn</span>
                        <select id="userRatingSelect" aria-label="Đánh giá phim">
                            <option value="">Chọn rating</option>
                            <option value="5">5 - Rất hay</option>
                            <option value="4">4 - Hay</option>
                            <option value="3">3 - Bình thường</option>
                            <option value="2">2 - Không thích</option>
                            <option value="1">1 - Tệ</option>
                        </select>
                    </label>
                    <p id="movieTrackingMessage" class="movie-tracking-message" aria-live="polite"></p>
                </div>
            </div>
        </div>
        
        ${movie.description ? `
            <div class="detail-section">
                <h2 class="detail-section-title">Nội dung</h2>
                <p class="detail-section-content">${escapeHtml(movie.description)}</p>
            </div>
        ` : ''}
        
        ${movie.director ? `
            <div class="detail-section">
                <h2 class="detail-section-title">Đạo diễn</h2>
                <p class="detail-section-content">${escapeHtml(movie.director)}</p>
            </div>
        ` : ''}
        
        ${stars.length > 0 ? `
            <div class="detail-section">
                <h2 class="detail-section-title">Diễn viên</h2>
                <div class="detail-stars">
                    ${stars.map(star => `<span class="star-tag">${escapeHtml(star)}</span>`).join('')}
                </div>
            </div>
        ` : ''}
        
        ${movie.gross ? `
            <div class="detail-section">
                <h2 class="detail-section-title">Doanh thu</h2>
                <p class="detail-section-content">$${parseInt(movie.gross).toLocaleString()}</p>
            </div>
        ` : ''}
    `;
    bindMovieInteractionControls(movie);
}

// Show movie list
function showMovieList() {
    movieDetailView.style.display = 'none';
    movieListView.style.display = 'block';
    if (similarMoviesSection) {
        similarMoviesSection.style.display = 'none';
    }

    history.pushState({}, "", "/");
    loadHomeRecommendations();
}

function getMovieIdFromPath() {
    const match = window.location.pathname.match(/^\/movies\/(.+)$/);
    return match ? decodeURIComponent(match[1]) : null;
}

function getLocalWatchedMovies() {
    try {
        return JSON.parse(localStorage.getItem('watchedMovies')) || [];
    } catch {
        return [];
    }
}

function getLocalWatchedMovieIds() {
    const watched = getLocalWatchedMovies();
    const seen = new Set();
    const ids = [];
    for (let i = watched.length - 1; i >= 0; i -= 1) {
        const id = watched[i].movieId;
        if (id && !seen.has(id)) {
            seen.add(id);
            ids.push(id);
        }
    }
    return ids;
}

function loadHomePageSections() {
    loadTrendingMovies();
    loadHomeRecommendations();
}

async function loadTrendingMovies(topN = 8) {
    if (!trendingMoviesContainer) return;
    trendingMoviesContainer.innerHTML = '<p class="loading-inline">Đang tải phim nổi bật...</p>';
    try {
        const response = await fetch(apiUrl(`/api/recommendations/trending?top_k=${topN}`));
        const data = await response.json();
        renderSimilarMovies(data.recommendations || [], trendingMoviesContainer, { showScore: false });
    } catch (error) {
        console.error('Error loading trending movies:', error);
        trendingMoviesContainer.innerHTML = '<p style="color: var(--text-secondary);">Không thể tải phim nổi bật.</p>';
    }
}

async function loadRecommendationsByGenres(genres, topN = 8) {
    const seen = new Set();
    const results = [];
    const genresToUse = genres.slice(0, 3);

    for (const genre of genresToUse) {
        const response = await fetch(apiUrl(
            `/api/movies/search/by-genre?genre=${encodeURIComponent(genre)}&per_page=${topN + 5}`
        ));
        const data = await response.json();
        const movies = data.data || data.movies || [];
        for (const movie of movies) {
            if (movie.movie_id && !seen.has(movie.movie_id)) {
                seen.add(movie.movie_id);
                results.push(movie);
            }
        }
    }

    return results.slice(0, topN);
}

async function loadRecommendationsFromWatched(topN = 8) {
    const watchedIds = getLocalWatchedMovieIds();
    if (watchedIds.length === 0) {
        return [];
    }

    const response = await fetch(apiUrl('/api/recommendations/personalized'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            liked_movies: watchedIds,
            top_k: topN
        })
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || 'Không thể tải phim đề xuất');
    }
    return data.recommendations || [];
}

async function loadHomeRecommendations(topN = 8) {
    if (!recommendedMoviesSection || !recommendedMoviesContainer) return;

    try {
        let movies = [];
        let sourceText = '';

        if (currentUser && authToken) {
            const prefData = await authRequest('/api/users/me/preferences');
            const genres = prefData.preferences?.favoriteGenres || [];
            if (genres.length === 0) {
                recommendedMoviesSection.style.display = 'none';
                return;
            }

            recommendedMoviesSection.style.display = 'block';
            recommendedMoviesContainer.innerHTML = '<p class="loading-inline">Đang tải phim đề xuất...</p>';
            sourceText = `Dựa trên thể loại yêu thích: ${genres.slice(0, 3).join(', ')}`;
            movies = await loadRecommendationsByGenres(genres, topN);
        } else {
            const watchedIds = getLocalWatchedMovieIds();
            if (watchedIds.length === 0) {
                recommendedMoviesSection.style.display = 'none';
                return;
            }

            recommendedMoviesSection.style.display = 'block';
            recommendedMoviesContainer.innerHTML = '<p class="loading-inline">Đang tải phim đề xuất...</p>';
            sourceText = `Dựa trên ${watchedIds.length} phim bạn đã xem trên thiết bị`;
            movies = await loadRecommendationsFromWatched(topN);
        }

        if (recommendedHomeSource) {
            recommendedHomeSource.textContent = sourceText;
        }

        if (!movies.length) {
            recommendedMoviesSection.style.display = 'none';
            return;
        }

        renderSimilarMovies(movies, recommendedMoviesContainer, { showScore: Boolean(currentUser && authToken) });
    } catch (error) {
        console.error('Error loading home recommendations:', error);
        recommendedMoviesSection.style.display = 'none';
    }
}

async function loadSimilarRecommendations(movieId, topN = 10) {
    if (!similarMoviesContainer || !similarMoviesSection) return;
    similarMoviesSection.style.display = 'block';
    similarMoviesContainer.innerHTML = '<p class="loading-inline">Đang tải phim tương tự...</p>';
    try {
        const response = await fetch(apiUrl(`/api/recommendations/similar?movie_id=${encodeURIComponent(movieId)}&method=hybrid&top_k=${topN}`));
        const data = await response.json();
        if (data.error) {
            similarMoviesSection.style.display = 'none';
            return;
        }
        renderSimilarMovies(data.recommendations || [], similarMoviesContainer);
        if (!data.recommendations || data.recommendations.length === 0) {
            similarMoviesSection.style.display = 'none';
        }
    } catch (error) {
        console.error('Error loading similar movies:', error);
        similarMoviesContainer.innerHTML = '<p style="color: var(--text-secondary);">Không thể tải phim tương tự.</p>';
    }
}

function renderSimilarMovies(movies, container, options = {}) {
    const showScore = options.showScore !== false;
    if (!container) return;
    if (!movies || movies.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary);">Không có phim tương tự.</p>';
        return;
    }
    container.innerHTML = movies.map(movie => {
        const posterHtml = movie.poster
            ? `<img src="${escapeHtml(movie.poster)}" alt="Poster ${escapeHtml(movie.movie_name || '')}" loading="lazy" onerror="handlePosterError(event)">`
            : '';
        const similarityValue = (typeof movie.similarity_score === 'number') ? movie.similarity_score : movie.score;
        const scoreDisplay = showScore && typeof similarityValue === 'number'
            ? `Độ tương đồng: ${similarityValue.toFixed(2)}`
            : '';
        return `
            <div class="recommend-card" onclick="showMovieDetail('${movie.movie_id}')">
                <div class="recommend-poster poster-container ${movie.poster ? 'has-image' : ''}">
                    ${posterHtml}
                    <span class="poster-placeholder">${getPosterPlaceholder(movie.movie_name)}</span>
                </div>
                <div class="recommend-info">
                    <div class="recommend-title">${escapeHtml(movie.movie_name || 'N/A')}</div>
                    <div class="recommend-meta">
                        ${movie.year || ''}
                        ${movie.rating ? ` ⭐ ${movie.rating}` : ''}
                    </div>
                    ${movie.genre ? `<div class="recommend-genres">${escapeHtml(movie.genre)}</div>` : ''}
                    ${scoreDisplay ? `<div class="recommend-score">${scoreDisplay}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
}


// Handle search
function handleSearch() {
    const searchTerm = searchInput.value.trim();
    const field = (searchFieldSelect && searchFieldSelect.value) ? searchFieldSelect.value : 'movie_name';
    currentPage = 1;
    loadMovies(1, searchTerm, field);
}

// Change page
function changePage(delta) {
    const newPage = currentPage + delta;
    if (newPage >= 1 && newPage <= totalPages) {
        loadMovies(newPage, currentSearch, currentSearchField);
    }
}

// Update pagination
function updatePagination() {
    pageInfo.textContent = `Trang ${currentPage} / ${totalPages}`;
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === totalPages;
}

// Show/hide loading
function showLoading() {
    loadingSpinner.style.display = 'flex';
}

function hideLoading() {
    loadingSpinner.style.display = 'none';
}

// Poster helpers
function getPosterClasses(baseClass, poster) {
    return `${baseClass} poster-container${poster ? ' has-image' : ''}`;
}

function getPosterPlaceholder(name) {
    const fallback = '🎬';
    if (!name || typeof name !== 'string') {
        return fallback;
    }
    const trimmed = name.trim();
    if (!trimmed) {
        return fallback;
    }
    const firstChar = trimmed.charAt(0).toUpperCase();
    return escapeHtml(firstChar || fallback);
}

function handlePosterError(event) {
    const img = event.target;
    const container = img.closest('.poster-container');
    if (container) {
        container.classList.remove('has-image');
    }
    img.remove();
}

// Escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

window.addEventListener("popstate", (event) => {
    if (event.state && event.state.movieId) {
        // User pressed Back → show movie detail again
        showMovieDetail(event.state.movieId);
    } else {
        // User returned to main page
        showMovieList();
    }
});

// Tab switching
function switchTab(tabName) {
    tabButtons.forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-tab') === tabName);
    });

    movieListView.classList.remove('active');
    visualizationView.classList.remove('active');
    adminView?.classList.remove('active');
    movieListView.style.display = 'none';
    visualizationView.style.display = 'none';
    if (adminView) adminView.style.display = 'none';
    movieDetailView.style.display = 'none';

    if (tabName === 'movies') {
        movieListView.classList.add('active');
        movieListView.style.display = 'block';
    } else if (tabName === 'visualization') {
        visualizationView.classList.add('active');
        visualizationView.style.display = 'block';
        loadVisualizations();
    } else if (tabName === 'admin') {
        if (!isAdminUser()) {
            switchTab('movies');
            return;
        }
        adminView.classList.add('active');
        adminView.style.display = 'block';
        loadAdminMovies();
    }
}

function setAdminMessage(message, isError = false) {
    if (!adminMessage) return;
    adminMessage.textContent = message;
    adminMessage.classList.toggle('error', isError);
}

async function loadAdminMovies() {
    if (!isAdminUser()) return;

    adminMoviesTableBody.innerHTML = '<tr><td colspan="6">Đang tải...</td></tr>';
    try {
        const response = await authRequest('/api/movies?page=1&per_page=100');
        adminMoviesCache = response.movies || response.data || [];
        renderAdminMoviesTable();
    } catch (error) {
        adminMoviesTableBody.innerHTML = `<tr><td colspan="6">${escapeHtml(error.message)}</td></tr>`;
    }
}

function renderAdminMoviesTable() {
    if (!adminMoviesCache.length) {
        adminMoviesTableBody.innerHTML = '<tr><td colspan="6">Chưa có phim nào.</td></tr>';
        return;
    }

    adminMoviesTableBody.innerHTML = adminMoviesCache.map((movie) => `
        <tr>
            <td>${escapeHtml(movie.movie_id || '')}</td>
            <td>${escapeHtml(movie.movie_name || '')}</td>
            <td>${escapeHtml(movie.year || '')}</td>
            <td>${escapeHtml(movie.rating || '')}</td>
            <td>${escapeHtml(movie.genre || '')}</td>
            <td class="admin-actions">
                <button type="button" class="auth-btn secondary" data-admin-action="edit" data-movie-id="${escapeHtml(movie.movie_id || '')}">Sửa</button>
                <button type="button" class="auth-btn secondary danger" data-admin-action="delete" data-movie-id="${escapeHtml(movie.movie_id || '')}">Xóa</button>
            </td>
        </tr>
    `).join('');
}

function openAdminMovieForm(mode, movie = null) {
    adminFormPanel.style.display = 'block';
    adminFormTitle.textContent = mode === 'edit' ? 'Sửa thông tin phim' : 'Thêm phim mới';
    document.getElementById('adminEditingMovieId').value = mode === 'edit' ? (movie?.movie_id || '') : '';
    document.getElementById('adminMovieId').value = movie?.movie_id || '';
    document.getElementById('adminMovieId').readOnly = mode === 'edit';
    document.getElementById('adminMovieName').value = movie?.movie_name || '';
    document.getElementById('adminYear').value = movie?.year || '';
    document.getElementById('adminRating').value = movie?.rating || '';
    document.getElementById('adminGenre').value = movie?.genre || '';
    document.getElementById('adminCertificate').value = movie?.certificate || '';
    document.getElementById('adminRuntime').value = movie?.runtime || '';
    document.getElementById('adminVotes').value = movie?.votes || '';
    document.getElementById('adminDirector').value = movie?.director || '';
    document.getElementById('adminStar').value = movie?.star || '';
    document.getElementById('adminPoster').value = movie?.poster || '';
    document.getElementById('adminDescription').value = movie?.description || '';
    setAdminMessage('');
}

function closeAdminMovieForm() {
    adminFormPanel.style.display = 'none';
    adminMovieForm.reset();
    document.getElementById('adminMovieId').readOnly = false;
    document.getElementById('adminEditingMovieId').value = '';
}

function collectAdminMoviePayload() {
    return {
        movie_id: document.getElementById('adminMovieId').value.trim(),
        movie_name: document.getElementById('adminMovieName').value.trim(),
        year: document.getElementById('adminYear').value.trim(),
        rating: document.getElementById('adminRating').value.trim(),
        genre: document.getElementById('adminGenre').value.trim(),
        certificate: document.getElementById('adminCertificate').value.trim(),
        runtime: document.getElementById('adminRuntime').value.trim(),
        votes: document.getElementById('adminVotes').value.trim(),
        director: document.getElementById('adminDirector').value.trim(),
        star: document.getElementById('adminStar').value.trim(),
        poster: document.getElementById('adminPoster').value.trim(),
        description: document.getElementById('adminDescription').value.trim(),
    };
}

async function handleAdminMovieSubmit(event) {
    event.preventDefault();
    if (!isAdminUser()) return;

    const editingMovieId = document.getElementById('adminEditingMovieId').value.trim();
    const payload = collectAdminMoviePayload();

    try {
        if (editingMovieId) {
            await authRequest(`/api/movies/${encodeURIComponent(editingMovieId)}`, {
                method: 'PUT',
                body: JSON.stringify(payload),
            });
            setAdminMessage('Đã cập nhật phim.');
        } else {
            await authRequest('/api/movies', {
                method: 'POST',
                body: JSON.stringify(payload),
            });
            setAdminMessage('Đã thêm phim mới.');
        }

        closeAdminMovieForm();
        await loadAdminMovies();
        if (movieListView.style.display !== 'none') {
            loadMovies(currentPage, currentSearch, currentSearchField);
        }
    } catch (error) {
        setAdminMessage(error.message, true);
    }
}

async function handleAdminTableAction(event) {
    const button = event.target.closest('[data-admin-action]');
    if (!button || !isAdminUser()) return;

    const movieId = button.dataset.movieId;
    const action = button.dataset.adminAction;
    const movie = adminMoviesCache.find((item) => item.movie_id === movieId);

    if (action === 'edit' && movie) {
        openAdminMovieForm('edit', movie);
        return;
    }

    if (action === 'delete') {
        const confirmed = window.confirm(`Xóa phim "${movie?.movie_name || movieId}"?`);
        if (!confirmed) return;

        try {
            await authRequest(`/api/movies/${encodeURIComponent(movieId)}`, { method: 'DELETE' });
            setAdminMessage('Đã xóa phim.');
            await loadAdminMovies();
            if (movieListView.style.display !== 'none') {
                loadMovies(currentPage, currentSearch, currentSearchField);
            }
        } catch (error) {
            setAdminMessage(error.message, true);
        }
    }
}

// Load all visualizations
async function loadVisualizations() {
    showLoading();
    try {
        await Promise.all([
            loadRatingDistribution(),
            loadTopMovies(),
            loadTopGenres(),
            loadHeatmap(),
            loadBarChart(),
            loadHistogram(),
            loadWordCloud()
        ]);
    } catch (error) {
        console.error('Error loading visualizations:', error);
    } finally {
        hideLoading();
    }
}

// Rating Distribution Chart
async function loadRatingDistribution() {
    try {
        const response = await fetch(apiUrl('/api/visualization/rating-distribution'));
        const data = await response.json();

        const ctx = document.getElementById('ratingChart').getContext('2d');

        // Destroy existing chart if it exists
        if (charts.rating) {
            charts.rating.destroy();
        }

        charts.rating = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Number of Movies',
                    data: data.data,
                    backgroundColor: 'rgba(245, 197, 24, 0.6)',
                    borderColor: 'rgba(245, 197, 24, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 30, 30, 0.9)',
                        titleColor: '#f5c518',
                        bodyColor: '#ffffff',
                        borderColor: '#f5c518',
                        borderWidth: 1
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#b0b0b0'
                        },
                        grid: {
                            color: '#333333'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#b0b0b0',
                            maxRotation: 45,
                            minRotation: 45
                        },
                        grid: {
                            color: '#333333'
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading rating distribution:', error);
    }
}

// Top Movies Chart
async function loadTopMovies() {
    try {
        const response = await fetch(apiUrl('/api/visualization/top-movies'));
        const data = await response.json();

        const ctx = document.getElementById('topMoviesChart').getContext('2d');

        if (charts.topMovies) {
            charts.topMovies.destroy();
        }

        charts.topMovies = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.slice(0, 10).map(m => m.name.substring(0, 20) + (m.name.length > 20 ? '...' : '')),
                datasets: [{
                    label: 'Rating',
                    data: data.slice(0, 10).map(m => m.rating),
                    backgroundColor: 'rgba(245, 197, 24, 0.6)',
                    borderColor: 'rgba(245, 197, 24, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 30, 30, 0.9)',
                        titleColor: '#f5c518',
                        bodyColor: '#ffffff',
                        borderColor: '#f5c518',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 10,
                        ticks: {
                            color: '#b0b0b0'
                        },
                        grid: {
                            color: '#333333'
                        }
                    },
                    y: {
                        ticks: {
                            color: '#b0b0b0'
                        },
                        grid: {
                            color: '#333333'
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading top movies:', error);
    }
}

// Top Genres Chart
async function loadTopGenres() {
    try {
        const response = await fetch(apiUrl('/api/visualization/top-genres'));
        const data = await response.json();

        const ctx = document.getElementById('topGenresChart').getContext('2d');

        if (charts.topGenres) {
            charts.topGenres.destroy();
        }

        charts.topGenres = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(g => g.genre),
                datasets: [{
                    label: 'Number of Movies',
                    data: data.map(g => g.count),
                    backgroundColor: [
                        'rgba(245, 197, 24, 0.8)',
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)',
                        'rgba(255, 159, 64, 0.8)',
                        'rgba(199, 199, 199, 0.8)',
                        'rgba(83, 102, 255, 0.8)',
                        'rgba(255, 99, 255, 0.8)'
                    ],
                    borderWidth: 2,
                    borderColor: '#1e1e1e'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#b0b0b0',
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 30, 30, 0.9)',
                        titleColor: '#f5c518',
                        bodyColor: '#ffffff',
                        borderColor: '#f5c518',
                        borderWidth: 1
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading top genres:', error);
    }
}

// Heatmap Chart
async function loadHeatmap() {
    try {
        const response = await fetch(apiUrl('/api/visualization/heatmap-data'));
        const data = await response.json();

        const ctx = document.getElementById('heatmapChart').getContext('2d');

        if (charts.heatmap) {
            charts.heatmap.destroy();
        }

        // Sample data for better visualization (show last 30 years)
        const recentData = data.slice(-30);

        charts.heatmap = new Chart(ctx, {
            type: 'line',
            data: {
                labels: recentData.map(d => d.year),
                datasets: [{
                    label: 'Average Rating',
                    data: recentData.map(d => d.avg_rating),
                    borderColor: 'rgba(245, 197, 24, 1)',
                    backgroundColor: 'rgba(245, 197, 24, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        labels: {
                            color: '#b0b0b0'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 30, 30, 0.9)',
                        titleColor: '#f5c518',
                        bodyColor: '#ffffff',
                        borderColor: '#f5c518',
                        borderWidth: 1
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        min: 0,
                        max: 10,
                        ticks: {
                            color: '#b0b0b0'
                        },
                        grid: {
                            color: '#333333'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#b0b0b0',
                            maxRotation: 45,
                            minRotation: 45
                        },
                        grid: {
                            color: '#333333'
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading heatmap:', error);
    }
}

// Bar Chart
async function loadBarChart() {
    try {
        const response = await fetch(apiUrl('/api/visualization/bar-chart-data'));
        const data = await response.json();

        const ctx = document.getElementById('barChart').getContext('2d');

        if (charts.barChart) {
            charts.barChart.destroy();
        }

        charts.barChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Number of Movies',
                    data: data.data,
                    backgroundColor: 'rgba(245, 197, 24, 0.6)',
                    borderColor: 'rgba(245, 197, 24, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 30, 30, 0.9)',
                        titleColor: '#f5c518',
                        bodyColor: '#ffffff',
                        borderColor: '#f5c518',
                        borderWidth: 1
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#b0b0b0'
                        },
                        grid: {
                            color: '#333333'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#b0b0b0',
                            maxRotation: 45,
                            minRotation: 45
                        },
                        grid: {
                            color: '#333333'
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading bar chart:', error);
    }
}

// Histogram Chart
async function loadHistogram() {
    try {
        const response = await fetch(apiUrl('/api/visualization/histogram-data'));
        const data = await response.json();

        const ctx = document.getElementById('histogramChart').getContext('2d');

        if (charts.histogram) {
            charts.histogram.destroy();
        }

        charts.histogram = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Number of Movies',
                    data: data.data,
                    backgroundColor: 'rgba(245, 197, 24, 0.6)',
                    borderColor: 'rgba(245, 197, 24, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 30, 30, 0.9)',
                        titleColor: '#f5c518',
                        bodyColor: '#ffffff',
                        borderColor: '#f5c518',
                        borderWidth: 1
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#b0b0b0'
                        },
                        grid: {
                            color: '#333333'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#b0b0b0'
                        },
                        grid: {
                            color: '#333333'
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading histogram:', error);
    }
}

// Word Cloud
async function loadWordCloud() {
    try {
        const response = await fetch(apiUrl('/api/visualization/wordcloud-data'));
        const data = await response.json();

        const container = document.getElementById('wordcloudContainer');
        container.innerHTML = ''; // Clear previous word cloud

        if (typeof WordCloud !== 'undefined' && data.length > 0) {
            WordCloud(container, {
                list: data.map(item => [item.text, item.value]),
                gridSize: 8,
                weightFactor: function (size) {
                    return Math.pow(size, 0.6) * 8;
                },
                fontFamily: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
                color: function (word, weight, fontSize, distance, theta) {
                    return '#f5c518';
                },
                rotateRatio: 0.3,
                rotationSteps: 2,
                backgroundColor: 'transparent',
                minSize: 8
            });
        } else {
            container.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">Word cloud library not loaded</p>';
        }
    } catch (error) {
        console.error('Error loading word cloud:', error);
        const container = document.getElementById('wordcloudContainer');
        container.innerHTML = '<p style="color: red; text-align: center;">Error loading word cloud</p>';
    }
}
