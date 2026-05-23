// Global state
let currentPage = 1;
let currentSearch = '';
let currentSearchField = 'movie_name';
let totalPages = 1;
let charts = {}; // Store chart instances

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
const forYouContainer = document.getElementById('forYouContainer'); // new

// UID helper: create persistent anonymous id for recommendations
function getOrCreateUid() {
    let uid = localStorage.getItem('movie_uid');
    if (!uid) {
        uid = 'user_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8);
        localStorage.setItem('movie_uid', uid);
    }
    return uid;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // set initial search field from select (in case default changed)
    if (searchFieldSelect && searchFieldSelect.value) {
        currentSearchField = searchFieldSelect.value;
    }

    loadMovies();

    // load personalized recommendations ("For you")
    // small delay so movies load doesn't block rendering
    try {
        const uid = getOrCreateUid();
        loadForYou(uid);
    } catch (e) {
        console.warn('For you load skipped', e);
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

    // Tab switching
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
});

// Load movies
async function loadMovies(page = 1, search = '', field = 'movie_name') {
    showLoading();
    try {
        const url = `/api/movies?page=${page}&per_page=20${search ? `&search=${encodeURIComponent(search)}` : ''}&field=${encodeURIComponent(field)}`;
        const response = await fetch(url);
        const data = await response.json();

        currentPage = data.page;
        totalPages = data.total_pages;
        currentSearch = search;
        currentSearchField = field;

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
        const data = await response.json();

        if (data.error) {
            alert('Không tìm thấy thông tin phim');
            return;
        }

        // Normalize API response: some endpoints return { movie: {...}, recommendations: [...] }
        let movieObj;
        if (data.movie || data.recommendations) {
            movieObj = data.movie || {};
            movieObj.more_like_this = data.recommendations || [];
        } else {
            // backward compatibility: API returned movie object directly
            movieObj = data;
            movieObj.more_like_this = movieObj.more_like_this || [];
        }

        // ⭐ Update URL without reload
        history.pushState({ movieId }, "", `/movies/${movieId}`);

        displayMovieDetail(movieObj);
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
    // recommendations may be returned under more_like_this or recommendations
    const recommendations = movie.more_like_this || movie.recommendations || [];

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
                <p class="detail-section-content">$${isNaN(parseInt(movie.gross)) ? escapeHtml(movie.gross) : parseInt(movie.gross).toLocaleString()}</p>
            </div>
        ` : ''}
        ${recommendations.length > 0 ? `
        <div class="detail-section">
            <h2 class="detail-section-title">🎯 Phim đề xuất</h2>
            <div class="recommend-grid">
                ${recommendations.map(r => {
        const posterHtml = r.poster ? `<img src="${escapeHtml(r.poster)}" alt="Poster ${escapeHtml(r.movie_name)}" onerror="handlePosterError(event)">` : '';
        const scoreDisplay = (typeof r.score === 'number') ? `Similarity: ${r.score.toFixed(2)}` : (r.score ? `Similarity: ${escapeHtml(String(r.score))}` : '');
        const genreText = Array.isArray(r.genre)
            ? r.genre.join(', ')
            : (Array.isArray(r.genres)
                ? r.genres.join(', ')
                : (r.genre || r.genres || '')
            );

        return `
            <div class="recommend-card" onclick="showMovieDetail('${r.movie_id}')">
                <div class="recommend-poster poster-container ${r.poster ? 'has-image' : ''}">
                    ${posterHtml}
                    <span class="poster-placeholder">
                        ${getPosterPlaceholder(r.movie_name)}
                    </span>
                </div>
                <div class="recommend-info">
                    <div class="recommend-title">
                        ${escapeHtml(r.movie_name || 'N/A')}
                    </div>
                    <div class="recommend-meta">
                        ${r.year || ''} 
                        ${r.rating ? `⭐ ${r.rating}` : ''}
                    </div>
                    ${genreText ? `
            <div class="recommend-genres">
                ${escapeHtml(genreText)}
            </div>
            ` : ''}
                    ${scoreDisplay ? `
                        <div class="recommend-score">
                            ${scoreDisplay}
                        </div>
                    ` : ''}
                </div>
            </div>
        `}).join('')}
    </div>
</div>
` : ''}

    `;
}

// Show movie list
function showMovieList() {
    movieDetailView.style.display = 'none';
    movieListView.style.display = 'block';

    // ⭐ Restore URL back to homepage
    history.pushState({}, "", "/");
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
    // Update tab buttons
    tabButtons.forEach(btn => {
        if (btn.getAttribute('data-tab') === tabName) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Show/hide content
    if (tabName === 'movies') {
        movieListView.classList.add('active');
        visualizationView.classList.remove('active');
        visualizationView.style.display = 'none';
        movieDetailView.style.display = 'none';
    } else if (tabName === 'visualization') {
        movieListView.classList.remove('active');
        movieDetailView.style.display = 'none';
        visualizationView.classList.add('active');
        visualizationView.style.display = 'block';
        loadVisualizations();
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
        const response = await fetch('/api/visualization/rating-distribution');
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
        const response = await fetch('/api/visualization/top-movies');
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
        const response = await fetch('/api/visualization/top-genres');
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
                        'rgba(65, 161, 225, 0.8)',
                        'rgba(255, 170, 0, 1)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)',
                        'rgba(246, 242, 0, 1)',
                        'rgba(199, 199, 199, 0.8)',
                        'rgba(0, 28, 237, 1)',
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
        const response = await fetch('/api/visualization/heatmap-data');
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
        const response = await fetch('/api/visualization/bar-chart-data');
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
        const response = await fetch('/api/visualization/histogram-data');
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
        const response = await fetch('/api/visualization/wordcloud-data');
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

// New: fetch and render "For you"
async function loadForYou(uid, top_n = 6) {
    if (!forYouContainer) return;
    forYouContainer.innerHTML = '<p class="loading-inline">Đang tải đề xuất...</p>';
    try {
        const resp = await fetch(`/api/recommendations?uid=${encodeURIComponent(uid)}&top_n=${top_n}`);
        const data = await resp.json();
        if (!data || !data.recommendations) {
            forYouContainer.innerHTML = '<p style="color: var(--text-secondary);">Không có đề xuất.</p>';
            return;
        }
        displayForYou(data.recommendations);
    } catch (err) {
        console.error('Error fetching For You recommendations', err);
        forYouContainer.innerHTML = '<p style="color: var(--text-secondary);">Không thể tải đề xuất.</p>';
    }
}

function displayForYou(recs) {
    if (!forYouContainer) return;
    if (!recs || recs.length === 0) {
        forYouContainer.innerHTML = '<p style="color: var(--text-secondary);">Không có đề xuất.</p>';
        return;
    }
    forYouContainer.innerHTML = recs.map(r => {
        const posterHtml = r.poster ? `<img src="${escapeHtml(r.poster)}" alt="${escapeHtml(r.movie_name)}" loading="lazy" onerror="handlePosterError(event)">` : '';
        return `
            <div class="for-you-card" onclick="showMovieDetail('${escapeHtml(r.movie_id)}')">
                <div class="for-you-poster poster-container ${r.poster ? 'has-image' : ''}">
                    ${posterHtml}
                    <span class="poster-placeholder">${getPosterPlaceholder(r.movie_name)}</span>
                </div>
                <div class="for-you-info">
                    <div class="fy-title">${escapeHtml(r.movie_name || 'N/A')}</div>
                    <div class="fy-meta">${r.year ? r.year : ''} ${r.rating ? `⭐ ${r.rating}` : ''}</div>
                </div>
            </div>
        `;
    }).join('');
}

document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;

    // Nếu truy cập trực tiếp /movies/<id>
    const match = path.match(/^\/movies\/(.+)$/);
    if (match) {
        const movieId = match[1];

        // Load chi tiết phim thay vì list
        showMovieDetail(movieId);
    }
});
document.addEventListener('DOMContentLoaded', () => {
    const homeBtn = document.getElementById('homeBtn');

    if (homeBtn) {
        homeBtn.addEventListener('click', () => {
            // 1. Ẩn movie detail
            document.getElementById('movieDetailView').style.display = 'none';

            // 2. Hiện movie list
            document.getElementById('movieListView').style.display = 'block';

            // 3. Set tab active đúng
            document.querySelectorAll('.tab-btn').forEach(btn =>
                btn.classList.remove('active')
            );
            document.querySelector('[data-tab="movies"]').classList.add('active');

            // 4. (Optional) load lại danh sách phim nếu cần
            // loadMovies(currentPage);
        });
    }
});
