// Global state
let currentPage = 1;
let currentSearch = '';
let totalPages = 1;

// DOM Elements
const moviesContainer = document.getElementById('moviesContainer');
const movieListView = document.getElementById('movieListView');
const movieDetailView = document.getElementById('movieDetailView');
const movieDetail = document.getElementById('movieDetail');
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const backBtn = document.getElementById('backBtn');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const pageInfo = document.getElementById('pageInfo');
const loadingSpinner = document.getElementById('loadingSpinner');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadMovies();
    
    // Event listeners
    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });
    backBtn.addEventListener('click', showMovieList);
    prevBtn.addEventListener('click', () => changePage(-1));
    nextBtn.addEventListener('click', () => changePage(1));
});

// Load movies
async function loadMovies(page = 1, search = '') {
    showLoading();
    try {
        const url = `/api/movies?page=${page}&per_page=20${search ? `&search=${encodeURIComponent(search)}` : ''}`;
        const response = await fetch(url);
        const data = await response.json();
        
        currentPage = data.page;
        totalPages = data.total_pages;
        currentSearch = search;
        
        displayMovies(data.movies);
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
async function showMovieDetail(movieId) {
    showLoading();
    try {
        const response = await fetch(`/api/movies/${movieId}`);
        const movie = await response.json();
        
        if (movie.error) {
            alert('Không tìm thấy thông tin phim');
            return;
        }
        
        displayMovieDetail(movie);
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
}

// Show movie list
function showMovieList() {
    movieDetailView.style.display = 'none';
    movieListView.style.display = 'block';
}

// Handle search
function handleSearch() {
    const searchTerm = searchInput.value.trim();
    currentPage = 1;
    loadMovies(1, searchTerm);
}

// Change page
function changePage(delta) {
    const newPage = currentPage + delta;
    if (newPage >= 1 && newPage <= totalPages) {
        loadMovies(newPage, currentSearch);
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

