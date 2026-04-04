/**
 * Kupto - Modern SPA Frontend
 */

// --- STATE ---
const state = {
    user: null,
    shoppingList: [],
    products: [],
    categories: [],
    availableLists: [],
    activeView: 'loading', // loading, auth, main
    isMenuOpen: false,
    isModalOpen: false,
    isListModalOpen: false,
    searchQuery: '',
    suggestions: []
};

const appRoot = document.getElementById('app');

// --- API CLIENT ---
async function apiFetch(url, options = {}) {
    const defaultOptions = {
        headers: { 'Content-Type': 'application/json' },
        ...options
    };

    const response = await fetch(url, defaultOptions);

    if (response.status === 401 && state.activeView !== 'auth') {
        state.activeView = 'auth';
        render();
        throw new Error('Unauthorized');
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(error.error || `HTTP error ${response.status}`);
    }

    return response.status === 204 ? null : response.json();
}

// --- ACTIONS ---
const actions = {
    async init() {
        try {
            state.user = await apiFetch('/api/users/me');
            await Promise.all([
                actions.fetchShoppingList(),
                actions.fetchProducts(),
                actions.fetchCategories(),
                actions.fetchAvailableLists()
            ]);
            state.activeView = 'main';
        } catch (err) {
            state.activeView = 'auth';
        }
        render();
    },

    async login(login, password) {
        await apiFetch('/api/login', {
            method: 'POST',
            body: JSON.stringify({ login, password })
        });
        await actions.init();
    },

    async register(login, password) {
        await apiFetch('/api/register', {
            method: 'POST',
            body: JSON.stringify({ login, password })
        });
        await actions.login(login, password);
    },

    async logout() {
        await apiFetch('/api/logout', { method: 'POST' });
        state.user = null;
        state.activeView = 'auth';
        render();
    },

    async fetchShoppingList() {
        state.shoppingList = await apiFetch('/api/list');
    },

    async fetchProducts() {
        state.products = await apiFetch('/api/products');
    },

    async fetchCategories() {
        state.categories = await apiFetch('/api/categories');
    },

    async fetchAvailableLists() {
        state.availableLists = await apiFetch('/api/lists');
    },

    async addItem(productId, quantity) {
        await apiFetch('/api/list/item', {
            method: 'POST',
            body: JSON.stringify({ productId, quantity })
        });
        await actions.fetchShoppingList();
        state.searchQuery = '';
        state.suggestions = [];
        render();
    },

    async deleteItem(productId) {
        await apiFetch(`/api/list/item/${productId}`, { method: 'DELETE' });
        await actions.fetchShoppingList();
        render();
    },

    async changeDefaultList(listId) {
        await apiFetch('/api/users/default-list', {
            method: 'PUT',
            body: JSON.stringify({ listId })
        });
        state.isMenuOpen = false;
        await actions.fetchShoppingList();
        state.user.default_list_id = listId;
        render();
    },

    async addNewProduct(categoryId, name) {
        await apiFetch('/api/products', {
            method: 'POST',
            body: JSON.stringify({ categoryId, name })
        });
        await actions.fetchProducts();
        state.isModalOpen = false;
        render();
    },

    async createList(name) {
        await apiFetch('/api/lists', {
            method: 'POST',
            body: JSON.stringify({ name })
        });
        await actions.fetchAvailableLists();
        state.isListModalOpen = false;
        render();
    }
};

// --- UI COMPONENTS ---
const components = {
    Header: () => `
        <header class="main-header">
            <button class="menu-toggle" id="menu-toggle">☰</button>
            <h1 class="logo">Kupto</h1>
            <div class="header-spacer"></div>
        </header>
    `,

    Menu: () => `
        <div class="side-menu ${state.isMenuOpen ? 'open' : ''}">
            <div class="menu-content">
                <button class="menu-close" id="menu-close">×</button>
                <div class="user-profile">
                    <div class="avatar">${state.user?.login[0].toUpperCase()}</div>
                    <span class="username">${state.user?.login}</span>
                </div>
                
                <nav class="menu-nav">
                    <div class="menu-nav-header">
                        <h3>Twoje Listy</h3>
                        <button class="btn-add-list" id="btn-add-list">+</button>
                    </div>
                    <ul>
                        ${state.availableLists.map(list => `
                            <li class="${state.user?.default_list_id === list.list_id ? 'active' : ''}" 
                                onclick="actions.changeDefaultList(${list.list_id})">
                                ${list.name}
                            </li>
                        `).join('')}
                    </ul>
                    <hr>
                    <button class="btn-logout" id="logout-btn">Wyloguj się</button>
                </nav>
            </div>
            <div class="menu-overlay" id="menu-overlay"></div>
        </div>
    `,

    AuthView: () => `
        <div class="auth-container">
            <form class="auth-form" id="auth-form">
                <h2>${state.authMode === 'register' ? 'Stwórz konto' : 'Zaloguj się'}</h2>
                <div class="input-group">
                    <label>Login</label>
                    <input type="text" id="auth-login" required minlength="3">
                </div>
                <div class="input-group">
                    <label>Hasło</label>
                    <input type="password" id="auth-password" required minlength="8">
                </div>
                <div id="auth-error" class="error-msg hidden"></div>
                <button type="submit" class="btn-primary">
                    ${state.authMode === 'register' ? 'Zarejestruj' : 'Zaloguj'}
                </button>
                <p class="auth-switch">
                    ${state.authMode === 'register' ? 'Masz już konto?' : 'Nie masz konta?'}
                    <a href="#" id="switch-auth-mode">
                        ${state.authMode === 'register' ? 'Zaloguj się' : 'Zarejestruj się'}
                    </a>
                </p>
            </form>
        </div>
    `,

    MainView: () => `
        <div class="app-container">
            ${components.Header()}
            ${components.Menu()}
            
            <main class="content">
                <div class="search-section">
                    <div class="search-bar">
                        <input type="text" id="product-search" placeholder="Szukaj produktu..." value="${state.searchQuery}">
                        <input type="text" id="product-qty" placeholder="Ile?" class="qty-input">
                        <button id="btn-add-item" class="btn-add">Dodaj</button>
                    </div>
                    <ul class="suggestions ${state.suggestions.length ? '' : 'hidden'}">
                        ${state.suggestions.map(p => `
                            <li data-id="${p.id}">${p.name}</li>
                        `).join('')}
                    </ul>
                </div>

                <div class="list-section">
                    ${state.shoppingList.length === 0 ? '<p class="empty-msg">Twoja lista jest pusta</p>' : ''}
                    ${state.shoppingList.map(cat => `
                        <div class="category-group">
                            <h3>${cat.category}</h3>
                            <ul>
                                ${cat.items.map(item => `
                                    <li class="list-item">
                                        <span class="item-name">${item.name}</span>
                                        <span class="item-qty">${item.quantity || ''}</span>
                                        <button class="btn-rm" onclick="actions.deleteItem(${item.id})">🗑️</button>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    `).join('')}
                </div>
            </main>

            <button class="fab" id="btn-open-modal">+</button>

            ${state.isModalOpen ? components.NewProductModal() : ''}
            ${state.isListModalOpen ? components.NewListModal() : ''}
        </div>
    `,

    NewProductModal: () => `
        <div class="modal-overlay">
            <div class="modal">
                <h3>Dodaj nowy produkt</h3>
                <div class="input-group">
                    <label>Nazwa produktu</label>
                    <input type="text" id="new-prod-name">
                </div>
                <div class="input-group">
                    <label>Kategoria</label>
                    <select id="new-prod-cat">
                        ${state.categories.map(c => `<option value="${c.category_id}">${c.name}</option>`).join('')}
                    </select>
                </div>
                <div class="modal-actions">
                    <button class="btn-text" id="modal-cancel">Anuluj</button>
                    <button class="btn-primary" id="modal-save">Zapisz</button>
                </div>
            </div>
        </div>
    `,

    NewListModal: () => `
        <div class="modal-overlay">
            <div class="modal">
                <h3>Utwórz nową listę</h3>
                <div class="input-group">
                    <label>Nazwa listy</label>
                    <input type="text" id="new-list-name" placeholder="np. Zakupy domowe">
                </div>
                <div class="modal-actions">
                    <button class="btn-text" id="list-modal-cancel">Anuluj</button>
                    <button class="btn-primary" id="list-modal-save">Utwórz</button>
                </div>
            </div>
        </div>
    `
};

// --- RENDERING ENGINE ---
function render() {
    if (state.activeView === 'loading') {
        appRoot.innerHTML = '<div class="loading-screen">Ładowanie aplikacji...</div>';
        return;
    }

    if (state.activeView === 'auth') {
        appRoot.innerHTML = components.AuthView();
        setupAuthListeners();
        return;
    }

    appRoot.innerHTML = components.MainView();
    setupMainListeners();
}

// --- EVENT LISTENERS ---
function setupAuthListeners() {
    const form = document.getElementById('auth-form');
    const switchBtn = document.getElementById('switch-auth-mode');

    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const login = document.getElementById('auth-login').value;
        const password = document.getElementById('auth-password').value;
        const errorEl = document.getElementById('auth-error');

        try {
            if (state.authMode === 'register') {
                await actions.register(login, password);
            } else {
                await actions.login(login, password);
            }
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        }
    });

    switchBtn?.addEventListener('click', (e) => {
        e.preventDefault();
        state.authMode = state.authMode === 'register' ? 'login' : 'register';
        render();
    });
}

function setupMainListeners() {
    // Menu
    document.getElementById('menu-toggle')?.addEventListener('click', () => {
        state.isMenuOpen = true;
        render();
    });
    document.getElementById('menu-close')?.addEventListener('click', () => {
        state.isMenuOpen = false;
        render();
    });
    document.getElementById('menu-overlay')?.addEventListener('click', () => {
        state.isMenuOpen = false;
        render();
    });
    document.getElementById('logout-btn')?.addEventListener('click', () => actions.logout());

    // Search & Suggestions
    const searchInput = document.getElementById('product-search');
    searchInput?.addEventListener('input', (e) => {
        state.searchQuery = e.target.value;
        const val = state.searchQuery.toLowerCase();
        if (val.length > 0) {
            state.suggestions = state.products
                .filter(p => p.name.toLowerCase().includes(val))
                .slice(0, 5);
        } else {
            state.suggestions = [];
        }
        renderSuggestionsOnly(); // Optymalizacja: renderujemy tylko listę sugestii
    });

    document.querySelector('.suggestions')?.addEventListener('click', (e) => {
        const li = e.target.closest('li');
        if (li) {
            searchInput.value = li.textContent;
            state.searchQuery = li.textContent;
            state.selectedProductId = parseInt(li.dataset.id);
            state.suggestions = [];
            render();
        }
    });

    document.getElementById('btn-add-item')?.addEventListener('click', () => {
        const qty = document.getElementById('product-qty').value;
        const productName = searchInput.value;
        const product = state.products.find(p => p.name === productName);
        
        if (product) {
            actions.addItem(product.id, qty || '1');
        } else {
            alert('Wybierz produkt z listy lub dodaj nowy przyciskiem +');
        }
    });

    // Modal
    document.getElementById('btn-open-modal')?.addEventListener('click', () => {
        state.isModalOpen = true;
        render();
    });
    document.getElementById('modal-cancel')?.addEventListener('click', () => {
        state.isModalOpen = false;
        render();
    });
    document.getElementById('modal-save')?.addEventListener('click', () => {
        const name = document.getElementById('new-prod-name').value;
        const catId = parseInt(document.getElementById('new-prod-cat').value);
        actions.addNewProduct(catId, name);
    });

    // List Modal
    document.getElementById('btn-add-list')?.addEventListener('click', () => {
        state.isListModalOpen = true;
        render();
    });
    document.getElementById('list-modal-cancel')?.addEventListener('click', () => {
        state.isListModalOpen = false;
        render();
    });
    document.getElementById('list-modal-save')?.addEventListener('click', () => {
        const name = document.getElementById('new-list-name').value;
        if (name) {
            actions.createList(name);
        } else {
            alert('Podaj nazwę listy');
        }
    });
}

function renderSuggestionsOnly() {
    const sugUl = document.querySelector('.suggestions');
    if (!sugUl) return;
    if (state.suggestions.length === 0) {
        sugUl.classList.add('hidden');
        return;
    }
    sugUl.innerHTML = state.suggestions.map(p => `<li data-id="${p.id}">${p.name}</li>`).join('');
    sugUl.classList.remove('hidden');
}

// Global expose for onclick handlers (temporary simplicity)
window.actions = actions;

// --- START APP ---
actions.init();
