let products = [];
let categories = [];
let shoppingList = [];
const input = document.getElementById('input');
const addButton = document.getElementById('add-button');
const shoppingListUl = document.getElementById('shopping-ul');
const suggestionsUl = document.getElementById('suggestions');
const newProductModal = document.getElementById('new-product-modal');
const btnOpenModal = document.getElementById('btn-open-modal');
const btnCancel = document.getElementById('btn-cancel');
const userId = 1;

function renderShoppingList() {
    shoppingListUl.innerHTML = '';
    shoppingList.forEach(category => {
        const h4 = document.createElement('h4');
        h4.className = 'category-header';
        h4.textContent = category.category;
        shoppingListUl.appendChild(h4);

        category.items.forEach(product => {
            const name = document.createElement('span');
            const quantity = document.createElement('span');
            const X = document.createElement('span');
            const div = document.createElement('div');

            name.className = 'item-name';
            quantity.className = 'quantity';
            X.className = 'rm-button';
            div.className = 'prod-container';

            name.textContent = product.name;
            quantity.textContent = product.quantity;
            X.textContent = 'X';
            div.appendChild(name);
            div.appendChild(quantity);
            div.appendChild(X);
            shoppingListUl.appendChild(div);

            X.addEventListener("click", () => deleteItemFromList(product.id));
        });
    });
}

const fetchShoppingList = async () => {
    try {
        const response = await fetch('/api/list');
        shoppingList = await response.json();
        renderShoppingList();
    } catch (error) {
        console.error('[ERROR] fetch shopping list: ', error);
    }
};

const addItemToList = async (productId) => {
    try {
        const response = await fetch('/api/list', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                productId: productId,
                addedByUserId: userId,
                quantity: getQuantity()
            })
        });
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        await fetchShoppingList();
    } catch (error) {
        console.error('[ERROR] add item to list', error);
    }
};

const deleteItemFromList = async (productId) => {
    try {
        const response = await fetch(`/api/list/${productId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                productId: productId
            })
        })
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        fetchShoppingList();
    } catch (error) {
            console.error(error);
    }
}

function getQuantity() {
    return document.getElementById('inputQuant').value;
}

// load all products and categories
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/products');
        products = await response.json();
    }
    catch (err){
        console.error('[ERROR] fetch all products', err);
    }
    try {
        const response = await fetch('/api/categories');
        categories = await response.json();
    }
    catch (err){
        console.error('[ERROR] fetch all categories', err);
    }
});

// render suggestions
input.addEventListener('input', (e) => {
    const value = e.target.value.toLowerCase();
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
});

addButton.addEventListener('click', () => {
    let selectedProduct = null;
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

btnOpenModal.addEventListener('click', () => {
    newProductModal.className = 'modal' // remove class 'hidden'
})

btnCancel.addEventListener('click', () => {
    newProductModal.className = 'modal hidden' // add class 'hidden'
})


fetchShoppingList();
