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
        console.error('Błąd pobierania:', error);
    }
};

fetchItems();

let catalog = [];

document.addEventListener('DOMContentLoaded', async () => {
    const response = await fetch('/api/catalog');
    catalog = await response.json();
    console.log(catalog);
});

const input = document.getElementById('input');
const suggestionsUl = document.getElementById('suggestions');

input.addEventListener('input', (e) => {
    const value = e.target.value.toLowerCase();

    if (value.length < 1) {
        suggestionsUl.innerHTML = '';
        return;
    }

    const matches = catalog.filter(item =>
        item.name.toLowerCase().includes(value)
    ).slice(0, 5);

    renderSuggestions(matches);
});

function renderSuggestions(matches) {
    matches.forEach(item => {
        const li = document.createElement('li');
        suggestionsUl.appendChild(li);
    })
}
