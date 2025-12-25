(function(){
  const STORAGE_KEY = 'quicklist-items-v1'
  const form = document.getElementById('item-form')
  const input = document.getElementById('item-input')
  const itemsEl = document.getElementById('items')
  const countEl = document.getElementById('count')
  const clearDoneBtn = document.getElementById('clear-done')
  const clearAllBtn = document.getElementById('clear-all')
  const filterButtons = document.querySelectorAll('.filters button')

  let items = []
  let filter = 'all'

  function save(){
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  }

  function load(){
    try{
      const raw = localStorage.getItem(STORAGE_KEY)
      items = raw ? JSON.parse(raw) : []
    }catch(e){ items = [] }
  }

  function uid(){ return Date.now().toString(36) + Math.random().toString(36).slice(2,7) }

  function addItem(name){
    if(!name || !name.trim()) return
    items.unshift({id:uid(),name:name.trim(),done:false})
    save()
    render()
  }

  function toggleDone(id){
    const it = items.find(x=>x.id===id)
    if(!it) return
    it.done = !it.done
    save(); render()
  }

  function deleteItem(id){
    items = items.filter(x=>x.id!==id)
    save(); render()
  }

  function clearDone(){
    items = items.filter(x=>!x.done)
    save(); render()
  }

  function clearAll(){
    if(!confirm('Clear all items?')) return
    items = []
    save(); render()
  }

  function setFilter(f){
    filter = f
    filterButtons.forEach(b=>b.classList.toggle('active', b.dataset.filter===f))
    render()
  }

  function render(){
    itemsEl.innerHTML = ''
    const shown = items.filter(i=>{
      if(filter==='active') return !i.done
      if(filter==='done') return i.done
      return true
    })

    if(shown.length===0){
      const li = document.createElement('li')
      li.className = 'item empty'
      li.textContent = 'No items yet.'
      itemsEl.appendChild(li)
    }else{
      for(const it of shown){
        const li = document.createElement('li')
        li.className = 'item' + (it.done? ' done':'')
        li.dataset.id = it.id

        const left = document.createElement('div')
        left.className = 'left'

        const cb = document.createElement('input')
        cb.type = 'checkbox'
        cb.checked = it.done
        cb.addEventListener('change', ()=> toggleDone(it.id))

        const name = document.createElement('div')
        name.className = 'name'
        name.textContent = it.name

        left.appendChild(cb)
        left.appendChild(name)

        const del = document.createElement('button')
        del.className = 'delete'
        del.textContent = 'Delete'
        del.addEventListener('click', ()=> deleteItem(it.id))

        li.appendChild(left)
        li.appendChild(del)
        itemsEl.appendChild(li)
      }
    }

    const total = items.length
    const remaining = items.filter(i=>!i.done).length
    countEl.textContent = remaining + ' / ' + total + ' items'
  }

  form.addEventListener('submit', e=>{
    e.preventDefault()
    addItem(input.value)
    input.value = ''
    input.focus()
  })

  clearDoneBtn.addEventListener('click', ()=>{
    clearDone()
  })

  clearAllBtn.addEventListener('click', ()=>{
    clearAll()
  })

  filterButtons.forEach(b=> b.addEventListener('click', ()=> setFilter(b.dataset.filter)))

  // init
  load()
  render()
})()
