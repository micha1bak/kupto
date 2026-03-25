let products = [];
let categories = [];
let shoppingList = [];
let lists = [];
const input = document.getElementById('input');
const inputQuant = document.getElementById('inputQuant');
const addToListButton = document.getElementById('add-button');
const shoppingListUl = document.getElementById('shopping-ul');
const suggestionsUl = document.getElementById('suggestions');
const newProductModal = document.getElementById('new-product-modal');
const btnOpenModal = document.getElementById('btn-open-modal');
const newProductName = document.getElementById('new-product-name');
const newProductCategory = document.getElementById('new-product-category');
const btnCancel = document.getElementById('btn-cancel');
const btnSaveProduct = document.getElementById('btn-save-product')
const listSelect = document.getElementById('list-select');



/* --- RENDER --- */
function renderLoginPage() {

    if (document.getElementById('login-container')) {
        return;
    }

    const appElementsToHide = [
        document.querySelector('.search-container'),
        document.getElementById('shopping-ul'),
        document.getElementById('btn-open-modal')
    ];

    appElementsToHide.forEach(el => {
        if (el) el.style.display = 'none';
    });

    const loginContainer = document.createElement('div');
    loginContainer.id = 'login-container';
    loginContainer.className = 'login-container';

    const form = document.createElement('form');
    form.id = 'login-form';
    form.className = 'login-form';

    const title = document.createElement('h2');
    title.textContent = 'Zaloguj się';
    title.className = 'login-title';

    const emailGroup = document.createElement('div');
    emailGroup.className = 'input-group';
    const emailLabel = document.createElement('label');
    emailLabel.htmlFor = 'login-email';
    emailLabel.textContent = 'Email';
    const emailInput = document.createElement('input');
    emailInput.id = 'login-email';
    emailInput.required = true;
    emailInput.placeholder = 'Wprowadź adres email';
    emailGroup.appendChild(emailLabel);
    emailGroup.appendChild(emailInput);

    const passwordGroup = document.createElement('div');
    passwordGroup.className = 'input-group';
    const passwordLabel = document.createElement('label');
    passwordLabel.htmlFor = 'login-password';
    passwordLabel.textContent = 'Hasło';
    const passwordInput = document.createElement('input');
    passwordInput.type = 'password';
    passwordInput.id = 'login-password';
    passwordInput.required = true;
    passwordInput.placeholder = 'Wprowadź hasło';
    passwordGroup.appendChild(passwordLabel);
    passwordGroup.appendChild(passwordInput);

    const errorMsg = document.createElement('p');
    errorMsg.id = 'login-error';
    errorMsg.className = 'login-error hidden';
    errorMsg.textContent = 'Nieprawidłowy email lub hasło.';

    const submitBtn = document.createElement('button');
    submitBtn.type = 'submit';
    submitBtn.className = 'btn-login';
    submitBtn.textContent = 'Zaloguj';

    form.appendChild(title);
    form.appendChild(emailGroup);
    form.appendChild(passwordGroup);
    form.appendChild(errorMsg);
    form.appendChild(submitBtn);
    loginContainer.appendChild(form);

    document.body.appendChild(loginContainer);

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = emailInput.value;
        const password = passwordInput.value;

        try {

            const response = await fetch('api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    login: email,
                    password: password
                })
            })

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();
            localStorage.setItem('jwt_token', data.token);

            await fetchShoppingList();
            await fetchProducts();
            await fetchCategories();

            errorMsg.classList.add('hidden');
            document.body.removeChild(loginContainer);

            appElementsToHide.forEach(el => {
                if (el) el.style.display = '';
            });
        }
        catch (error) {
            errorMsg.classList.remove('hidden');
            console.error('[ERROR] logowanie:', error);
        }
    });
}

function renderShoppingList() {
    shoppingListUl.innerHTML = '';
    shoppingList.forEach(category => {
        const h4 = document.createElement('h4');
        h4.className = 'category-header';
        h4.textContent = category.category;
        shoppingListUl.appendChild(h4);

        let i = 0;
        category.items.forEach(product => {
            const name = document.createElement('span');
            const quantity = document.createElement('span');
            const X = document.createElement('span');
            const div = document.createElement('div');

            name.className = 'item-name';
            quantity.className = 'quantity';
            X.className = 'rm-button';
            if (i % 2 === 0){
                div.className = 'prod-container green-list-row';
                i = 1;
            } else {
                div.className = 'prod-container';
                i = 0;
            }

            name.textContent = product.name;
            quantity.textContent = product.quantity;
            X.textContent = '🗑️';
            div.appendChild(name);
            div.appendChild(quantity);
            div.appendChild(X);
            shoppingListUl.appendChild(div);

            X.addEventListener("click", () => deleteItemFromList(product.id));
        });
    });
}

function renderCategory() {
    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category.name;
        option.textContent = category.name;
        newProductCategory.appendChild(option);
    })
}

function renderLists() {
    lists.lists.forEach(list => {
        const option = document.createElement('option');
        option.value = list.list_id;
        option.textContent = list.name;
        listSelect.appendChild(option);
    })
}

function renderSuggestions() {
    console.log('render suggestions');
    const value = input.value.toLowerCase();
    suggestionsUl.innerHTML = '';
    if (value.length < 1) {
        return;
    }

    const matches = products.filter(item =>
        item.name.toLowerCase().includes(value)
    ).slice(0, 5);

    matches.forEach(item => {
        const li = document.createElement('li');
        li.textContent = item.name;
        li.dataset.id = item.id;
        suggestionsUl.appendChild(li);
        li.addEventListener("click", () => {
            input.value = item.name;
            suggestionsUl.innerHTML = ''
        });
    })
}



/* --- FETCH --- */
async function fetchShoppingList() {
    try {
        const response = await fetch('/api/list', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`
            }
        });
        if (!response.ok) {
            throw new Error('list');
        }
        shoppingList = await response.json();
        renderShoppingList();
    } catch (error) {
        console.error(error);
        renderLoginPage();
    }
}

async function fetchProducts() {
    try {
        const response = await fetch('/api/products', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`
            }
        });
        products = await response.json();
    }
    catch (err){
        console.error(err);
    }
}

async function fetchCategories() {
    try {
        const response = await fetch('/api/categories', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`
            }
        });
        categories = await response.json();

        renderCategory();
    }
    catch (err){
        console.error(err);
    }
}

async function fetchIdsOfListsWithAccess() {
    try {
        const res = await fetch('/api/lists', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`
            }
        });
        if (!res.ok) {
            throw new Error(`Server error: ${res.status}`);
        }
        lists = await res.json();
        renderLists();
    } catch (err) {
        console.error(err);
    }
}



/* --- ACTIONS --- */
const addItemToList = async (productId) => {
    try {
        const response = await fetch('/api/list', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`
            },
            body: JSON.stringify({
                productId: productId,
                quantity: getQuantity()
            })
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        await fetchShoppingList();

        input.value = '';
        inputQuant. value = '';
        suggestionsUl.innerHTML = '';
    }
    catch (error) {
        console.error('[ERROR] add item to list', error);
    }
};

const deleteItemFromList = async (productId) => {
    try {
        const response = await fetch(`/api/list/${productId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`
            },
            body: JSON.stringify({
                productId: productId
            })
        });
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        await fetchShoppingList();
    } catch (error) {
            console.error(error);
    }
}

function getQuantity() {
    return document.getElementById('inputQuant').value;
}

function getFormatedProductName(s) {
    if (!s) return '';
    return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

const addNewProductToDB = async (categoryId, name) => {
    try {
        const res = await fetch('/api/products', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`
            },
            body: JSON.stringify({
                categoryId: categoryId,
                name: name
            })
        });
        if (!res.ok) {
            throw new Error(`Server error: ${res.status}`);
        }
        await fetchProducts();
    } catch (err) {
        console.error(err);
    }
}


// --- EVENTS --- //

// render suggestions
input.addEventListener('input', () => {
    renderSuggestions()
});

addToListButton.addEventListener('click', () => {
    let selectedProduct;
    for (let i = 0; i < products.length; i++) {
        if (input.value === products[i].name) {
            selectedProduct = products[i];
            break;
        }
    }
    if (!selectedProduct){
        alert('Nieznana nazwa produktu. Dodaj nowy produkt do bazy.');
        return;
    }

    addItemToList(selectedProduct.id);
})



/* --- MODAL --- */
btnOpenModal.addEventListener('click', () => {
    newProductModal.className = 'modal' // remove class 'hidden'
})

btnCancel.addEventListener('click', () => {
    newProductModal.className = 'modal hidden' // add class 'hidden'
})

btnSaveProduct.addEventListener('click', () => {
    const categoryName = newProductCategory.value;
    const name = newProductName.value;
    let categoryId = 0;
    categories.forEach(category => {
        if (category.name === categoryName){
            categoryId = category.category_id;
        }
    })
    if (categoryId === 0) {
        alert('Zła kategoria.');
        newProductModal.className = 'modal hidden' // add class 'hidden'
        return;
    }

    addNewProductToDB(categoryId, name);
    newProductModal.className = 'modal hidden' // add class 'hidden'

})

async function initApp() {
    const token = localStorage.getItem('jwt_token');

    if (!token) {
        renderLoginPage();
        return;
    }

    try {
        await fetchShoppingList();
        await fetchCategories();
        await fetchProducts();
        await fetchIdsOfListsWithAccess();
    }
    catch (err) {
        console.warn('Wymagane logowanie', err);
    }
}

initApp();