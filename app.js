let products = [];
let categories = [];
let shopping_list = [];
const input = document.getElementById('input');
const addButton = document.getElementById('add-button');
const shopping_list_ul = document.getElementById('shopping-ul');
const suggestionsUl = document.getElementById('suggestions');
const userId = 1;

function renderShoppingList() {
    shopping_list_ul.innerHTML = '';
    shopping_list.forEach(item => {
        const li = document.createElement('li');
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.id = `item-${item.id}`;

        const label = document.createElement('label');
        label.setAttribute('for', `item-${item.id}`);
        label.textContent = item.name;

        li.appendChild(cb);
        li.appendChild(label);
        shopping_list_ul.appendChild(li);

        li.addEventListener("click", () => deleteItemFromList(item.id));
    });
}

const fetchShoppingList = async () => {
    try {
        const response = await fetch('/api/list');
        shopping_list = await response.json();
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

        const data = await response.json();
        fetchShoppingList();

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
        const data = await response.json();
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

fetchShoppingList();
