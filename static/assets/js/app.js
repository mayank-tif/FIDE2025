// ========== Utility Functions ==========
const qs = (selector, parent = document) => parent.querySelector(selector);
const qsa = (selector, parent = document) => Array.from(parent.querySelectorAll(selector));

const delegate = (parent, event, selector, handler) => {
  parent.addEventListener(event, (e) => {
    const target = e.target.closest(selector);
    if (target) handler(e, target);
  });
};

const formToObject = (form) => {
  const data = new FormData(form);
  const obj = {};
  for (const [key, value] of data.entries()) {
    obj[key] = value;
  }
  return obj;
};

const toInitials = (name) => {
  if (!name) return '??';
  return name
    .split(' ')
    .map(word => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
};

const showToast = (message, type = 'success') => {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
};

// ========== Modal Management ==========
class ModalManager {
  constructor() {
    this.init();
  }

  init() {
    document.addEventListener('click', (e) => {
      const openBtn = e.target.closest('[data-modal-open]');
      if (openBtn) {
        const modalId = openBtn.dataset.modalOpen;
        this.open(modalId);
      }

      const closeBtn = e.target.closest('[data-modal-close]');
      if (closeBtn) {
        const modal = closeBtn.closest('.modal');
        if (modal) this.close(modal.id);
      }

      if (e.target.classList.contains('modal')) {
        this.close(e.target.id);
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const activeModal = qs('.modal.active');
        if (activeModal) this.close(activeModal.id);
      }
    });
  }

  open(modalId) {
    const modal = qs(`#${modalId}`);
    if (modal) {
      modal.classList.add('active');
      const firstInput = qs('input, textarea, select', modal);
      if (firstInput) firstInput.focus();
    }
  }

  close(modalId) {
    const modal = qs(`#${modalId}`);
    if (modal) {
      modal.classList.remove('active');
      const form = qs('form', modal);
      if (form) form.reset();
    }
  }
}

// ========== Pagination ==========
class Pagination {
  constructor(tableId, pageSize = 10) {
    this.table = qs(`#${tableId}`);
    if (!this.table) return;
    
    this.tbody = qs('tbody', this.table);
    this.pageSize = parseInt(this.table.dataset.pageSize) || pageSize;
    this.currentPage = 1;
    this.rows = qsa('tr', this.tbody);
    this.filteredRows = [...this.rows];
    
    this.paginationId = `${tableId.replace('-table', '')}-pagination`;
    this.pagination = qs(`#${this.paginationId}`);
    
    this.render();
  }

  filter(searchTerm) {
    searchTerm = searchTerm.toLowerCase().trim();
    
    if (!searchTerm) {
      this.filteredRows = [...this.rows];
    } else {
      this.filteredRows = this.rows.filter(row => {
        const text = row.textContent.toLowerCase();
        return text.includes(searchTerm);
      });
    }
    
    this.currentPage = 1;
    this.render();
  }

  render() {
    const totalPages = Math.ceil(this.filteredRows.length / this.pageSize);
    const start = (this.currentPage - 1) * this.pageSize;
    const end = start + this.pageSize;

    this.rows.forEach(row => row.style.display = 'none');
    this.filteredRows.slice(start, end).forEach(row => row.style.display = '');

    if (this.pagination) {
      this.renderPagination(totalPages);
    }
  }

  renderPagination(totalPages) {
    const buttons = [];
    
    buttons.push(`<button ${this.currentPage === 1 ? 'disabled' : ''} data-page="prev">‹</button>`);
    
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) {
        buttons.push(`<button class="${i === this.currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`);
      }
    } else {
      buttons.push(`<button class="${1 === this.currentPage ? 'active' : ''}" data-page="1">1</button>`);
      
      if (this.currentPage > 3) {
        buttons.push(`<span>…</span>`);
      }
      
      const start = Math.max(2, this.currentPage - 1);
      const end = Math.min(totalPages - 1, this.currentPage + 1);
      
      for (let i = start; i <= end; i++) {
        buttons.push(`<button class="${i === this.currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`);
      }
      
      if (this.currentPage < totalPages - 2) {
        buttons.push(`<span>…</span>`);
      }
      
      buttons.push(`<button class="${totalPages === this.currentPage ? 'active' : ''}" data-page="${totalPages}">${totalPages}</button>`);
    }
    
    buttons.push(`<button ${this.currentPage === totalPages ? 'disabled' : ''} data-page="next">›</button>`);
    buttons.push(`<span>Page ${this.currentPage} of ${totalPages}</span>`);
    
    this.pagination.innerHTML = buttons.join('');
    
    this.pagination.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => {
        const page = btn.dataset.page;
        if (page === 'prev' && this.currentPage > 1) {
          this.currentPage--;
        } else if (page === 'next' && this.currentPage < totalPages) {
          this.currentPage++;
        } else if (!isNaN(page)) {
          this.currentPage = parseInt(page);
        }
        this.render();
      });
    });
  }

  addRow(rowHtml) {
    this.tbody.insertAdjacentHTML('afterbegin', rowHtml);
    this.rows = qsa('tr', this.tbody);
    this.filteredRows = [...this.rows];
    this.render();
  }

  updateRow(rowId, data) {
    const row = qs(`tr[data-id="${rowId}"]`, this.tbody);
    if (row) {
      Object.keys(data).forEach(key => {
        row.dataset[key] = data[key];
        const cell = qs(`.${key}`, row);
        if (cell) cell.textContent = data[key];
      });
    }
  }

  deleteRow(rowId) {
    const row = qs(`tr[data-id="${rowId}"]`, this.tbody);
    if (row) {
      row.remove();
      this.rows = qsa('tr', this.tbody);
      this.filteredRows = [...this.rows];
      this.render();
    }
  }
}

// ========== Login Handler ==========
const initLogin = () => {
  const form = qs('#login-form');
  if (!form) return;

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const data = formToObject(form);
    
    if (data.username && data.password) {
      window.location.href = 'dashboard.html';
    } else {
      showToast('Please enter username and password', 'error');
    }
  });
};

// ========== Logout Handler ==========
const initLogout = () => {
  const logoutBtns = qsa('[data-logout]');
  logoutBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      if (confirm('Are you sure you want to logout?')) {
        window.location.href = 'login.html';
      }
    });
  });
};

// ========== Players Page ==========
const initPlayersPage = () => {
  const table = qs('#players-table');
  if (!table) return;

  const pagination = new Pagination('players-table', 10);
  
  const searchInput = qs('#player-search');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      pagination.filter(e.target.value);
    });
  }

  // Add Player
  const addForm = qs('#add-player-form');
  if (addForm) {
    addForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const data = formToObject(addForm);
      
      const id = Date.now();
      const initials = toInitials(data.name);
      const statusClass = 'active';
      
      const template = qs('#tpl-player-row');
      const clone = template.content.cloneNode(true);
      const row = qs('tr', clone);
      
      row.dataset.id = id;
      row.dataset.name = data.name;
      row.dataset.age = data.age;
      row.dataset.gender = data.gender;
      row.dataset.country = data.country;
      row.dataset.email = data.email;
      row.dataset.status = 'Active';
      
      qs('.avatar', row).textContent = initials;
      qs('.avatar', row).dataset.initials = initials;
      qs('.name', row).textContent = data.name;
      qs('.age', row).textContent = data.age;
      qs('.gender', row).textContent = data.gender;
      qs('.country', row).textContent = data.country;
      qs('.email', row).textContent = data.email;
      qs('.badge', row).textContent = 'Active';
      qs('.badge', row).className = 'badge badge--active';
      
      qs('tbody', table).insertBefore(row, qs('tbody tr', table));
      
      pagination.rows = qsa('tr', qs('tbody', table));
      pagination.filteredRows = [...pagination.rows];
      pagination.render();
      
      modalManager.close('add-player-modal');
      showToast('Player added successfully');
    });
  }

  // Edit/Delete/View Players
  delegate(table, 'click', '[data-action]', (e, btn) => {
    const action = btn.dataset.action;
    const row = btn.closest('tr');
    const id = row.dataset.id;

    if (action === 'view') {
      window.location.href = `player-profile.html?id=${id}&name=${encodeURIComponent(row.dataset.name)}`;
    } else if (action === 'edit') {
      const editModal = qs('#edit-player-modal');
      if (editModal) {
        qs('#edit-player-id').value = id;
        qs('#edit-player-name').value = row.dataset.name;
        qs('#edit-player-age').value = row.dataset.age;
        qs('#edit-player-gender').value = row.dataset.gender;
        qs('#edit-player-country').value = row.dataset.country;
        qs('#edit-player-email').value = row.dataset.email;
        qs('#edit-player-status').value = row.dataset.status;
        modalManager.open('edit-player-modal');
      }
    } else if (action === 'delete') {
      if (confirm('Are you sure you want to delete this player?')) {
        pagination.deleteRow(id);
        showToast('Player deleted successfully');
      }
    }
  });

  // Edit Player Submit
  const editForm = qs('#edit-player-form');
  if (editForm) {
    editForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const data = formToObject(editForm);
      const row = qs(`tr[data-id="${data.id}"]`);
      
      if (row) {
        row.dataset.name = data.name;
        row.dataset.age = data.age;
        row.dataset.gender = data.gender;
        row.dataset.country = data.country;
        row.dataset.email = data.email;
        row.dataset.status = data.status;
        
        qs('.name', row).textContent = data.name;
        qs('.age', row).textContent = data.age;
        qs('.gender', row).textContent = data.gender;
        qs('.country', row).textContent = data.country;
        qs('.email', row).textContent = data.email;
        
        const badge = qs('.badge', row);
        badge.textContent = data.status;
        badge.className = `badge badge--${data.status.toLowerCase().replace(' ', '-')}`;
        
        qs('.avatar', row).textContent = toInitials(data.name);
        
        modalManager.close('edit-player-modal');
        showToast('Player updated successfully');
      }
    });
  }
};

// ========== Player Profile Page ==========
const initProfilePage = () => {
  const profilePage = qs('.profile-page');
  if (!profilePage) return;

  // Get player name from URL
  const params = new URLSearchParams(window.location.search);
  const playerName = params.get('name') || 'Player Name';
  const nameEl = qs('#profile-player-name');
  if (nameEl) nameEl.textContent = playerName;

  // Tab Management
  const tabBtns = qsa('.tab-btn');
  const tabContents = qsa('.tab-content');
  
  const showTab = (tabName) => {
    tabBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    tabContents.forEach(content => {
      content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
    window.location.hash = tabName;
  };

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      showTab(btn.dataset.tab);
    });
  });

  // Load tab from URL hash
  const hash = window.location.hash.slice(1);
  if (hash && qsa('.tab-btn').some(btn => btn.dataset.tab === hash)) {
    showTab(hash);
  }

  // Photo Upload
  const uploadBtn = qs('#upload-photo-btn');
  const uploadInput = qs('#upload-photo-input');
  const avatar = qs('#profile-avatar');
  
  if (uploadBtn && uploadInput && avatar) {
    uploadBtn.addEventListener('click', () => uploadInput.click());
    
    uploadInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          avatar.style.backgroundImage = `url(${e.target.result})`;
          avatar.style.backgroundSize = 'cover';
          avatar.textContent = '';
        };
        reader.readAsDataURL(file);
        showToast('Photo uploaded successfully');
      }
    });
  }

  // Profile Form
  const profileForm = qs('#profile-form');
  if (profileForm) {
    profileForm.addEventListener('submit', (e) => {
      e.preventDefault();
      showToast('Profile updated successfully');
    });
  }

  // Transportation Form
  const transportForm = qs('#transport-form');
  const transportLog = qs('#transport-log');
  const transportTemplate = qs('#tpl-transport-item');
  let editingTransportItem = null;

  const getTransportTitle = (type) => {
    const titles = {
      'Airport': 'Airport Details',
      'Hotel': 'Hotel Details',
      'Match': 'Match Details',
      'Other': 'Other Details'
    };
    return titles[type] || 'Transportation Details';
  };

  if (transportForm && transportLog && transportTemplate) {
    transportForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const data = formToObject(transportForm);

      if (editingTransportItem) {
        // Update existing item
        editingTransportItem.dataset.pickup = data.pickup;
        editingTransportItem.dataset.dropoff = data.dropoff;
        editingTransportItem.dataset.type = data.type;
        editingTransportItem.dataset.details = data.details;
        editingTransportItem.dataset.remarks = data.remarks;

        const strong = qs('strong', editingTransportItem);
        strong.textContent = getTransportTitle(data.type) + ':';

        const details = qs('.details', editingTransportItem);
        details.textContent = data.details;

        const route = qs('.route', editingTransportItem);
        route.textContent = `${data.pickup} → ${data.dropoff}`;

        const datetime = qs('.datetime', editingTransportItem);
        const now = new Date();
        datetime.textContent = now.toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit', hour12: true}) + ', ' + now.toLocaleDateString('en-US', {day: 'numeric', month: 'short', year: 'numeric'});

        editingTransportItem = null;
        showToast('Transportation details updated');
      } else {
        // Add new item
        const clone = transportTemplate.content.cloneNode(true);
        const item = qs('.item-entry', clone);

        item.dataset.pickup = data.pickup;
        item.dataset.dropoff = data.dropoff;
        item.dataset.type = data.type;
        item.dataset.details = data.details;
        item.dataset.remarks = data.remarks;
        item.dataset.status = 'Completed';

        const strong = qs('strong', item);
        strong.textContent = getTransportTitle(data.type) + ':';

        const details = qs('.details', item);
        details.textContent = data.details;

        const route = qs('.route', item);
        route.textContent = `${data.pickup} → ${data.dropoff}`;

        const datetime = qs('.datetime', item);
        const now = new Date();
        datetime.textContent = now.toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit', hour12: true}) + ', ' + now.toLocaleDateString('en-US', {day: 'numeric', month: 'short', year: 'numeric'});

        transportLog.insertBefore(item, transportLog.firstChild);
        showToast('Transportation details added');
      }

      transportForm.reset();
    });
  }

  // Edit Transport Item
  delegate(transportLog, 'click', '[data-action="edit-transport"]', (e, btn) => {
    const item = btn.closest('.item-entry');
    editingTransportItem = item;

    qs('#transport-pickup').value = item.dataset.pickup;
    qs('#transport-dropoff').value = item.dataset.dropoff;
    qs('#transport-type').value = item.dataset.type;
    qs('#transport-details').value = item.dataset.details;
    qs('#transport-remarks').value = item.dataset.remarks;

    window.scrollTo({top: 0, behavior: 'smooth'});
    showToast('Edit mode: Update the form and save', 'info');
  });

  // Hotel Form
  const hotelForm = qs('#hotel-form');
  const hotelLog = qs('#hotel-log');
  const hotelTemplate = qs('#tpl-hotel-item');
  let editingHotelItem = null;

  if (hotelForm && hotelLog && hotelTemplate) {
    hotelForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const data = formToObject(hotelForm);

      if (editingHotelItem) {
        // Update existing item
        editingHotelItem.dataset.pickup = data.pickup;
        editingHotelItem.dataset.dropoff = data.dropoff;
        editingHotelItem.dataset.type = data.type;
        editingHotelItem.dataset.details = data.details;
        editingHotelItem.dataset.remarks = data.remarks;

        const strong = qs('strong', editingHotelItem);
        strong.textContent = getTransportTitle(data.type) + ':';

        const details = qs('.details', editingHotelItem);
        details.textContent = data.details;

        const route = qs('.route', editingHotelItem);
        route.textContent = `${data.pickup} → ${data.dropoff}`;

        const datetime = qs('.datetime', editingHotelItem);
        const now = new Date();
        datetime.textContent = now.toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit', hour12: true}) + ', ' + now.toLocaleDateString('en-US', {day: 'numeric', month: 'short', year: 'numeric'});

        editingHotelItem = null;
        showToast('Hotel details updated');
      } else {
        // Add new item
        const clone = hotelTemplate.content.cloneNode(true);
        const item = qs('.item-entry', clone);

        item.dataset.pickup = data.pickup;
        item.dataset.dropoff = data.dropoff;
        item.dataset.type = data.type;
        item.dataset.details = data.details;
        item.dataset.remarks = data.remarks;
        item.dataset.status = 'Completed';

        const strong = qs('strong', item);
        strong.textContent = getTransportTitle(data.type) + ':';

        const details = qs('.details', item);
        details.textContent = data.details;

        const route = qs('.route', item);
        route.textContent = `${data.pickup} → ${data.dropoff}`;

        const datetime = qs('.datetime', item);
        const now = new Date();
        datetime.textContent = now.toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit', hour12: true}) + ', ' + now.toLocaleDateString('en-US', {day: 'numeric', month: 'short', year: 'numeric'});

        hotelLog.insertBefore(item, hotelLog.firstChild);
        showToast('Hotel details added');
      }

      hotelForm.reset();
    });
  }

  // Edit Hotel Item
  delegate(hotelLog, 'click', '[data-action="edit-hotel"]', (e, btn) => {
    const item = btn.closest('.item-entry');
    editingHotelItem = item;

    qs('#hotel-pickup').value = item.dataset.pickup;
    qs('#hotel-dropoff').value = item.dataset.dropoff;
    qs('#hotel-type').value = item.dataset.type;
    qs('#hotel-details').value = item.dataset.details;
    qs('#hotel-remarks').value = item.dataset.remarks;

    window.scrollTo({top: 0, behavior: 'smooth'});
    showToast('Edit mode: Update the form and save', 'info');
  });

  // Match Form
  const matchForm = qs('#match-form');
  const matchLog = qs('#match-log');
  const matchTemplate = qs('#tpl-match-item');
  let editingMatchItem = null;

  if (matchForm && matchLog && matchTemplate) {
    matchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const data = formToObject(matchForm);

      if (editingMatchItem) {
        // Update existing item
        editingMatchItem.dataset.pickup = data.pickup;
        editingMatchItem.dataset.dropoff = data.dropoff;
        editingMatchItem.dataset.type = data.type;
        editingMatchItem.dataset.details = data.details;
        editingMatchItem.dataset.remarks = data.remarks;

        const strong = qs('strong', editingMatchItem);
        strong.textContent = getTransportTitle(data.type) + ':';

        const details = qs('.details', editingMatchItem);
        details.textContent = data.details;

        const route = qs('.route', editingMatchItem);
        route.textContent = `${data.pickup} → ${data.dropoff}`;

        const datetime = qs('.datetime', editingMatchItem);
        const now = new Date();
        datetime.textContent = now.toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit', hour12: true}) + ', ' + now.toLocaleDateString('en-US', {day: 'numeric', month: 'short', year: 'numeric'});

        editingMatchItem = null;
        showToast('Match tracker details updated');
      } else {
        // Add new item
        const clone = matchTemplate.content.cloneNode(true);
        const item = qs('.item-entry', clone);

        item.dataset.pickup = data.pickup;
        item.dataset.dropoff = data.dropoff;
        item.dataset.type = data.type;
        item.dataset.details = data.details;
        item.dataset.remarks = data.remarks;
        item.dataset.status = 'Completed';

        const strong = qs('strong', item);
        strong.textContent = getTransportTitle(data.type) + ':';

        const details = qs('.details', item);
        details.textContent = data.details;

        const route = qs('.route', item);
        route.textContent = `${data.pickup} → ${data.dropoff}`;

        const datetime = qs('.datetime', item);
        const now = new Date();
        datetime.textContent = now.toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit', hour12: true}) + ', ' + now.toLocaleDateString('en-US', {day: 'numeric', month: 'short', year: 'numeric'});

        matchLog.insertBefore(item, matchLog.firstChild);
        showToast('Match tracker details added');
      }

      matchForm.reset();
    });
  }

  // Edit Match Item
  delegate(matchLog, 'click', '[data-action="edit-match"]', (e, btn) => {
    const item = btn.closest('.item-entry');
    editingMatchItem = item;

    qs('#match-pickup').value = item.dataset.pickup;
    qs('#match-dropoff').value = item.dataset.dropoff;
    qs('#match-type').value = item.dataset.type;
    qs('#match-details').value = item.dataset.details;
    qs('#match-remarks').value = item.dataset.remarks;

    window.scrollTo({top: 0, behavior: 'smooth'});
    showToast('Edit mode: Update the form and save', 'info');
  });
};

// ========== Complaints Page ==========
const initComplaintsPage = () => {
  const complaintsPage = qs('.complaints-list');
  if (!complaintsPage) return;

  const searchInput = qs('#complaint-search');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const term = e.target.value.toLowerCase();
      qsa('.complaint-card').forEach(card => {
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(term) ? '' : 'none';
      });
    });
  }

  // Send Remarks
  delegate(complaintsPage, 'click', '[data-action="send-remark"]', (e, btn) => {
    const id = btn.dataset.complaintId;
    const textarea = qs(`textarea[data-complaint-id="${id}"]`);
    const remarksList = qs(`.remarks-list[data-complaint-id="${id}"]`);
    
    if (textarea && textarea.value.trim() && remarksList) {
      const remarkDiv = document.createElement('div');
      remarkDiv.className = 'admin-reply';
      remarkDiv.innerHTML = `<strong>Admin Reply:</strong> ${textarea.value}`;
      remarksList.appendChild(remarkDiv);
      textarea.value = '';
      showToast('Remark sent successfully');
    }
  });

  // Save Complaint
  delegate(complaintsPage, 'click', '[data-action="save-complaint"]', (e, btn) => {
    const id = btn.dataset.complaintId;
    const select = qs(`.status-select[data-complaint-id="${id}"]`);
    
    if (select) {
      showToast('Complaint status updated');
    }
  });

  // Status Change
  delegate(complaintsPage, 'change', '.status-select', (e, select) => {
    const newStatus = select.value;
    showToast(`Status changed to ${newStatus}`, 'info');
  });
};

// ========== Announcements Page ==========
const initAnnouncementsPage = () => {
  const announcementsPage = qs('.announcements-list');
  if (!announcementsPage) return;

  const searchInput = qs('#announcement-search');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const term = e.target.value.toLowerCase();
      qsa('.announcement-card').forEach(card => {
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(term) ? '' : 'none';
      });
    });
  }

  // Create Announcement
  const createForm = qs('#create-announcement-form');
  const template = qs('#tpl-announcement');
  
  if (createForm && template) {
    createForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const data = formToObject(createForm);
      
      const clone = template.content.cloneNode(true);
      const h3 = qs('h3', clone);
      const date = qs('.announcement-date', clone);
      const body = qs('.announcement-body', clone);
      
      h3.textContent = data.title;
      date.textContent = new Date().toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      });
      body.textContent = data.details;
      
      announcementsPage.insertBefore(clone, announcementsPage.firstChild);
      
      modalManager.close('create-announcement-modal');
      showToast('Announcement created successfully');
    });
  }

  // Multi-select handling
  const audienceSelect = qs('#announcement-audience');
  if (audienceSelect) {
    audienceSelect.addEventListener('change', (e) => {
      const selected = Array.from(e.target.selectedOptions).map(opt => opt.value);
      console.log('Selected audience:', selected);
    });
  }
};

// ========== Users Page ==========
const initUsersPage = () => {
  const table = qs('#users-table');
  if (!table) return;

  const pagination = new Pagination('users-table', 10);
  
  const searchInput = qs('#user-search');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      pagination.filter(e.target.value);
    });
  }

  // Password Validation
  const validatePassword = (password) => {
    if (password.length < 8) return 'Password must be at least 8 characters';
    if (!/[A-Z]/.test(password)) return 'Password must contain at least one uppercase letter';
    if (!/[0-9]/.test(password)) return 'Password must contain at least one number';
    return null;
  };

  // Add User
  const addForm = qs('#add-user-form');
  if (addForm) {
    addForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const data = formToObject(addForm);
      
      // Validate password
      const passwordError = validatePassword(data.password);
      if (passwordError) {
        showToast(passwordError, 'error');
        return;
      }
      
      if (data.password !== data.confirmPassword) {
        showToast('Passwords do not match', 'error');
        return;
      }
      
      const id = Date.now();
      const template = qs('#tpl-user-row');
      const clone = template.content.cloneNode(true);
      const row = qs('tr', clone);
      
      row.dataset.id = id;
      row.dataset.name = data.name;
      row.dataset.email = data.email;
      row.dataset.phone = data.phone;
      row.dataset.department = data.department;
      row.dataset.role = data.role;
      
      qs('.name', row).textContent = data.name;
      qs('.email', row).textContent = data.email;
      qs('.phone', row).textContent = data.phone;
      qs('.department', row).textContent = data.department;
      
      const badge = qs('.badge', row);
      badge.textContent = data.role;
      badge.className = `badge badge--${data.role.toLowerCase()}`;
      
      qs('tbody', table).insertBefore(row, qs('tbody tr', table));
      
      pagination.rows = qsa('tr', qs('tbody', table));
      pagination.filteredRows = [...pagination.rows];
      pagination.render();
      
      modalManager.close('add-user-modal');
      showToast('User added successfully');
    });
  }

  // Edit/Delete Users
  delegate(table, 'click', '[data-action]', (e, btn) => {
    const action = btn.dataset.action;
    const row = btn.closest('tr');
    const id = row.dataset.id;

    if (action === 'edit') {
      showToast('Edit functionality would open a modal', 'info');
    } else if (action === 'delete') {
      if (confirm('Are you sure you want to delete this user?')) {
        pagination.deleteRow(id);
        showToast('User deleted successfully');
      }
    }
  });
};

// ========== Initialize Application ==========
const modalManager = new ModalManager();

document.addEventListener('DOMContentLoaded', () => {
  initLogin();
  initLogout();
  initPlayersPage();
  initProfilePage();
  initComplaintsPage();
  initAnnouncementsPage();
  initUsersPage();
});