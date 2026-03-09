let products = [];
const input = document.getElementById('input');
const suggestionsUl = document.getElementById('suggestions');

// fetch items that are currently on a list
const fetchItems = async () => {
    try {
        const response = await fetch('/api/list');
        const data = await response.json();

        const ul = document.getElementById('shopping-ul');
        ul.innerHTML = '';

        data.forEach(item => {
            const li = document.createElement('li');
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.id = `item-${item.id}`;

            const label = document.createElement('label');
            label.setAttribute('for', `item-${item.id}`);
            label.textContent = item.product_name;

            li.appendChild(cb);
            li.appendChild(label);
            ul.appendChild(li);
        });
    } catch (error) {
        console.error('[ERROR] fetchItems: ', error);
    }
};

// fetch items on load
fetchItems();

// load all products
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/catalog');
        products = await response.json();
    }
    catch (err){
        console.error('[ERROR]: api/catalog', err);
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
        suggestionsUl.appendChild(li);
    })
});
