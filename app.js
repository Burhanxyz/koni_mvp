// Kopi Koni — Main Application
(function() {
  'use strict';

  // ── State ──
  const state = {
    currentPage: 'home',
    activeCategory: 'Kopi',
    cart: [],
    selectedItem: null,
    customization: { suhu: 'dingin', manis: 'normal' },
    voucherCode: '',
    discount: 0,
    deliveryOption: 'delivery',
    selectedFloor: 'Lantai 6',
    roomNumber: '',
    customerName: '',
    customerWA: '',
    activeOrder: null,
    orderItemsOpen: false,
  };

  let MENU_DATA = {};
  let STORE_OPEN = true;

  // ── Router ──
  function navigate(page) {
    state.currentPage = page;
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const el = document.getElementById('page-' + page);
    if (el) el.classList.add('active');
    updateNav();
    updateFab();
    if (page === 'home') renderMenu();
    if (page === 'cart') renderCart();
    if (page === 'payment') renderPayment();
    if (page === 'tracking') renderTracking();
    window.scrollTo(0, 0);
  }

  function updateNav() {
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.page === state.currentPage);
    });
  }

  function updateFab() {
    const fab = document.getElementById('fab-cart');
    const count = state.cart.reduce((sum, c) => sum + c.qty, 0);
    if (count > 0 && state.currentPage === 'home') {
      fab.classList.remove('hidden');
      fab.querySelector('.badge').textContent = count;
    } else {
      fab.classList.add('hidden');
    }
  }

  // ── Menu Rendering ──
  function renderMenu() {
    const tabs = document.getElementById('category-tabs');
    const list = document.getElementById('menu-list');
    tabs.innerHTML = '';
    list.innerHTML = '';
    
    if (!STORE_OPEN) {
      document.querySelector('.status-banner .status-dot').style.backgroundColor = 'var(--error)';
      document.querySelector('.status-banner .status-text').textContent = 'Store Closed';
      document.querySelector('.status-banner .text-caption').textContent = 'Pemesanan ditutup sementara';
      list.innerHTML = '<p class="text-body text-muted" style="text-align:center;padding:40px;">Maaf, Kopi Koni sedang tutup saat ini.</p>';
      return;
    } else {
      document.querySelector('.status-banner .status-dot').style.backgroundColor = 'var(--primary)';
      document.querySelector('.status-banner .status-text').textContent = 'Open Order';
      document.querySelector('.status-banner .text-caption').textContent = 'Closes at 23:00';
    }

    Object.keys(MENU_DATA).forEach(cat => {
      const btn = document.createElement('button');
      btn.className = 'cat-tab' + (cat === state.activeCategory ? ' active' : '');
      btn.textContent = cat;
      btn.onclick = () => { state.activeCategory = cat; renderMenu(); };
      tabs.appendChild(btn);
    });

    const items = MENU_DATA[state.activeCategory] || [];
    items.forEach(item => {
      const card = document.createElement('article');
      card.className = 'menu-card' + (!item.available ? ' sold-out' : '');
      if (item.available) {
        card.innerHTML = `
          <div class="menu-card-info">
            <h3 class="text-headline-md">${item.name}</h3>
            <p class="text-body">${item.desc}</p>
          </div>
          <div class="menu-card-action">
            <span class="price text-label">${formatRupiah(item.price)}</span>
            <button class="btn-add" aria-label="Add ${item.name}">
              <span class="material-symbols-outlined">add</span>
            </button>
          </div>`;
        card.querySelector('.btn-add').onclick = (e) => { e.stopPropagation(); openCustomization(item); };
        card.onclick = () => openCustomization(item);
      } else {
        card.innerHTML = `
          <div class="menu-card-info">
            <h3 class="text-headline-md">${item.name}</h3>
            <p class="text-body">${item.desc}</p>
          </div>
          <div class="menu-card-action">
            <span class="sold-label">Habis</span>
          </div>`;
      }
      list.appendChild(card);
    });
  }

  // ── Customization Modal ──
  function openCustomization(item) {
    state.selectedItem = item;
    state.customization = { suhu: 'dingin', manis: 'normal' };
    renderCustomizationModal();
    document.getElementById('modal-customization').classList.add('active');
  }

  function closeCustomization() {
    document.getElementById('modal-customization').classList.remove('active');
    state.selectedItem = null;
  }

  function renderCustomizationModal() {
    const item = state.selectedItem;
    if (!item) return;
    document.getElementById('custom-item-name').textContent = item.name;
    document.getElementById('custom-item-price').textContent = formatRupiah(item.price);
    document.getElementById('custom-cta-price').textContent = formatRupiah(item.price);

    ['suhu', 'manis'].forEach(group => {
      const container = document.getElementById('options-' + group);
      container.innerHTML = '';
      CUSTOMIZATION[group].forEach(opt => {
        const label = document.createElement('label');
        const isSelected = state.customization[group] === opt.value;
        label.className = 'option-item' + (isSelected ? ' selected' : '');
        label.innerHTML = `
          <span class="text-body">${opt.label}</span>
          <input class="custom-radio" type="radio" name="${group}" value="${opt.value}" ${isSelected ? 'checked' : ''}>`;
        label.querySelector('input').onchange = () => {
          state.customization[group] = opt.value;
          renderCustomizationModal();
        };
        container.appendChild(label);
      });
    });
  }

  function addToCart() {
    const item = state.selectedItem;
    if (!item) return;
    const existing = state.cart.find(c =>
      c.item.id === item.id &&
      c.suhu === state.customization.suhu &&
      c.manis === state.customization.manis
    );
    if (existing) {
      existing.qty++;
    } else {
      state.cart.push({
        item: item,
        qty: 1,
        suhu: state.customization.suhu,
        manis: state.customization.manis
      });
    }
    closeCustomization();
    updateFab();
  }

  // ── Cart Rendering ──
  function renderCart() {
    const list = document.getElementById('cart-list');
    const emptyMsg = document.getElementById('cart-empty');
    const cartContent = document.getElementById('cart-content');

    if (state.cart.length === 0) {
      emptyMsg.classList.remove('hidden');
      cartContent.classList.add('hidden');
      return;
    }
    emptyMsg.classList.add('hidden');
    cartContent.classList.remove('hidden');

    list.innerHTML = '';
    state.cart.forEach((entry, idx) => {
      const suhuLabel = CUSTOMIZATION.suhu.find(o => o.value === entry.suhu)?.label || '';
      const manisLabel = CUSTOMIZATION.manis.find(o => o.value === entry.manis)?.label || '';
      const div = document.createElement('div');
      div.className = 'cart-item';
      div.innerHTML = `
        <div class="cart-item-info">
          <h4>${entry.item.name}</h4>
          <div class="item-options text-caption">${suhuLabel}, ${manisLabel}</div>
          <div class="item-price">${formatRupiah(entry.item.price)}</div>
        </div>
        <div class="qty-control">
          <button class="qty-btn" data-action="dec" data-idx="${idx}">−</button>
          <span class="qty-value">${entry.qty}</span>
          <button class="qty-btn" data-action="inc" data-idx="${idx}">+</button>
        </div>`;
      div.querySelectorAll('.qty-btn').forEach(btn => {
        btn.onclick = () => {
          const i = parseInt(btn.dataset.idx);
          if (btn.dataset.action === 'inc') state.cart[i].qty++;
          else {
            state.cart[i].qty--;
            if (state.cart[i].qty <= 0) state.cart.splice(i, 1);
          }
          renderCart();
          updateFab();
        };
      });
      list.appendChild(div);
    });

    // Delivery option
    document.querySelectorAll('.delivery-card').forEach(card => {
      card.classList.toggle('selected', card.dataset.option === state.deliveryOption);
      card.onclick = () => { state.deliveryOption = card.dataset.option; renderCart(); };
    });

    // Floor select
    const floorSel = document.getElementById('floor-select');
    if (floorSel && !floorSel.children.length) {
      FLOOR_OPTIONS.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f; opt.textContent = f;
        if (f === state.selectedFloor) opt.selected = true;
        floorSel.appendChild(opt);
      });
      floorSel.onchange = (e) => { 
          state.selectedFloor = e.target.value; 
          renderDeliveryFields();
      };
    }
    renderDeliveryFields();

    // Summary
    const subtotal = state.cart.reduce((sum, c) => sum + c.item.price * c.qty, 0);
    const total = subtotal - state.discount;
    document.getElementById('summary-subtotal').textContent = formatRupiah(subtotal);
    document.getElementById('summary-discount').textContent = '- ' + formatRupiah(state.discount);
    document.getElementById('summary-total').textContent = formatRupiah(total);
    document.getElementById('btn-pay').textContent = 'Bayar Sekarang (' + formatRupiah(total) + ')';
  }

  async function applyVoucher() {
    const code = document.getElementById('voucher-input').value.trim().toUpperCase();
    if (!code) return;
    const subtotal = state.cart.reduce((sum, c) => sum + c.item.price * c.qty, 0);
    
    try {
        const response = await fetch('/api/vouchers/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code, subtotal: subtotal })
        });
        const data = await response.json();
        if (response.ok) {
            state.voucherCode = data.code;
            state.discount = data.discount;
            showToast(`Voucher berhasil! Diskon ${formatRupiah(data.discount)}`);
        } else {
            state.discount = 0;
            state.voucherCode = '';
            showToast(data.error || 'Voucher tidak valid');
        }
    } catch(e) {
        state.discount = 0;
        showToast('Gagal memvalidasi voucher');
    }
    renderCart();
  }

  function renderDeliveryFields() {
    const container = document.getElementById('dynamic-delivery-fields');
    if (!container) return;
    
    const floor = state.selectedFloor;
    const prevFloor = container.dataset.renderedFloor;
    
    // Only clear input if the floor ACTUALLY changed
    if (prevFloor && prevFloor !== floor) {
        state.roomNumber = '';
    }
    container.dataset.renderedFloor = floor;
    
    let html = '';
    if (floor === 'Lantai 1' || floor === 'Lantai 2') {
        html = `<input id="room-input" class="room-input" type="text" placeholder="Dikirim ke mana? (contoh: Lobi)" value="${state.roomNumber}">`;
    } else if (floor === 'Lantai 7' || floor === 'Lantai 8') {
        const roomVal = state.roomNumber.split(' (')[0];
        const hasCowo = state.roomNumber.includes('Cowo');
        html = `
            <input id="room-input" class="room-input" type="text" placeholder="Nomor Kamar (contoh: 7.02)" value="${roomVal}">
            <select id="lift-select" class="floor-select" style="margin-top:8px">
                <option value="Lift Cewe" ${!hasCowo ? 'selected' : ''}>Lewat Lift Cewe</option>
                <option value="Lift Cowo" ${hasCowo ? 'selected' : ''}>Lewat Lift Cowo</option>
            </select>
        `;
    } else if (floor === 'Lantai 6') {
        html = `
            <input id="room-input" class="room-input" type="text" placeholder="Nomor Kamar (1-16)" value="${state.roomNumber}">
            <p class="text-caption text-muted" style="margin-top:4px;font-size:11px">Catatan: Kamar 1-8 via Lift Cewe.</p>
        `;
    } else {
        html = `<input id="room-input" class="room-input" type="text" placeholder="Nomor Kamar (1-16)" value="${state.roomNumber}">`;
    }
    
    container.innerHTML = html;
    
    const updateRoom = () => {
        const roomInput = document.getElementById('room-input');
        const liftSelect = document.getElementById('lift-select');
        let details = roomInput ? roomInput.value : '';
        if (liftSelect) details += ` (${liftSelect.value})`;
        state.roomNumber = details;
    };
    
    const roomInput = document.getElementById('room-input');
    if (roomInput) roomInput.oninput = updateRoom;
    const liftSelect = document.getElementById('lift-select');
    if (liftSelect) {
        liftSelect.onchange = updateRoom;
        if (!state.roomNumber.includes('Lift')) updateRoom(); // Init default lift choice
    }
  }

  // ── Payment ──
  function renderPayment() {
    if (!state.activeOrder) return;
    const total = state.activeOrder.total;
    document.getElementById('payment-total').textContent = formatRupiah(total);
    document.getElementById('payment-order-id').textContent = state.activeOrder.id;
    document.getElementById('qris-image').src = `/api/qris/${state.activeOrder.id}`;
    startPaymentTimer();
  }

  let timerInterval = null;
  function startPaymentTimer() {
    if (timerInterval) clearInterval(timerInterval);
    let seconds = 300; // 5 min
    const timerEl = document.getElementById('payment-timer');
    function tick() {
      const m = Math.floor(seconds / 60);
      const s = seconds % 60;
      timerEl.textContent = String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
      if (seconds <= 0) { clearInterval(timerInterval); timerEl.textContent = 'Expired'; }
      seconds--;
    }
    tick();
    timerInterval = setInterval(tick, 1000);
  }

  function confirmPayment() {
    navigate('tracking');
  }

  // Removed getCurrentTime, handled by backend

  // ── Tracking ──
  async function renderTracking() {
    const orderRef = state.activeOrder;
    const searchSection = document.getElementById('tracking-search');
    const activeSection = document.getElementById('tracking-active');

    if (!orderRef) {
      searchSection.classList.remove('hidden');
      activeSection.classList.add('hidden');
      return;
    }

    searchSection.classList.add('hidden');
    activeSection.classList.remove('hidden');

    try {
        const response = await fetch('/api/orders/' + orderRef.id);
        if (!response.ok) throw new Error('Order not found');
        const data = await response.json();
        
        const order = data.order;
        const items = data.items;

        document.getElementById('track-order-id').textContent = order.id;
        document.getElementById('track-order-total').textContent = formatRupiah(order.total_price);

    const timeline = document.getElementById('timeline');
    timeline.innerHTML = '';
    ORDER_TIMELINE_STEPS.forEach((step, idx) => {
      let statusClass = 'pending';
      if (idx < order.status) statusClass = 'completed';
      else if (idx === order.status) statusClass = 'active';

      const div = document.createElement('div');
      div.className = 'timeline-step ' + statusClass;

      let dotContent = '';
      if (statusClass === 'completed') dotContent = '<span class="material-symbols-outlined" style="font-variation-settings:\'FILL\' 1">check</span>';
      else if (statusClass === 'active') dotContent = '<span class="material-symbols-outlined" style="font-variation-settings:\'FILL\' 1">pending</span>';

      let timeStr = order.times[idx] ? `<div class="step-time">${order.times[idx]} PM</div>` : '';
      let descStr = statusClass === 'active' ? `<div class="step-desc">${step.desc}</div>` : '';

      div.innerHTML = `
        <div class="step-dot">${dotContent}</div>
        <div class="step-content">
          <div class="step-label">${step.label}</div>
          ${timeStr}${descStr}
        </div>`;
      timeline.appendChild(div);
    });

    // Order items toggle
    renderOrderItems(items);
    } catch(e) {
        showToast('Pesanan tidak ditemukan atau terjadi kesalahan jaringan.');
        state.activeOrder = null;
        searchSection.classList.remove('hidden');
        activeSection.classList.add('hidden');
    }
  }

  function renderOrderItems(items) {
    const listEl = document.getElementById('order-items-list');
    listEl.innerHTML = '';
    items.forEach(entry => {
      const suhuLabel = CUSTOMIZATION.suhu.find(o => o.value === entry.temperature)?.label || '';
      const manisLabel = CUSTOMIZATION.manis.find(o => o.value === entry.sweetness)?.label || '';
      const div = document.createElement('div');
      div.className = 'order-item-row';
      div.innerHTML = `<span>${entry.qty}x ${entry.menu_name} (${suhuLabel}, ${manisLabel})</span><span>${formatRupiah(entry.subtotal)}</span>`;
      listEl.appendChild(div);
    });
  }

  function toggleOrderItems() {
    state.orderItemsOpen = !state.orderItemsOpen;
    const list = document.getElementById('order-items-list');
    const toggle = document.getElementById('order-items-toggle');
    list.classList.toggle('open', state.orderItemsOpen);
    const icon = toggle.querySelector('.material-symbols-outlined');
    if (icon) icon.textContent = state.orderItemsOpen ? 'expand_less' : 'expand_more';
  }

  // ── Toast ──
  function showToast(msg) {
    let toast = document.getElementById('toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'toast';
      toast.style.cssText = 'position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:var(--surface-container-highest);color:var(--on-surface);padding:12px 24px;border-radius:var(--radius-full);font-size:14px;font-weight:600;z-index:100;opacity:0;transition:opacity 0.3s;pointer-events:none;white-space:nowrap;';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.opacity = '1';
    setTimeout(() => { toast.style.opacity = '0'; }, 2500);
  }

  // ── Init ──
  function init() {
    // Nav
    document.querySelectorAll('.nav-item').forEach(item => {
      item.onclick = () => navigate(item.dataset.page);
    });

    // FAB
    document.getElementById('fab-cart').onclick = () => navigate('cart');

    // Modal close
    document.getElementById('btn-close-modal').onclick = closeCustomization;
    document.getElementById('modal-customization').onclick = (e) => {
      if (e.target === e.currentTarget) closeCustomization();
    };

    // Add to cart
    document.getElementById('btn-add-to-cart').onclick = addToCart;

    // Cart back
    document.getElementById('cart-back').onclick = () => navigate('home');
    document.getElementById('btn-add-more').onclick = () => navigate('home');

    // Voucher
    document.getElementById('btn-apply-voucher').onclick = applyVoucher;

    // Pay
    document.getElementById('btn-pay').onclick = async () => {
      if (state.cart.length === 0) return;
      
      const btnPay = document.getElementById('btn-pay');
      const origText = btnPay.textContent;
      btnPay.textContent = 'Memproses...';
      btnPay.disabled = true;

      try {
          const payload = {
              customerName: state.customerName,
              customerWA: state.customerWA,
              deliveryOption: state.deliveryOption,
              selectedFloor: state.selectedFloor,
              roomNumber: state.roomNumber,
              discount: state.discount,
              items: state.cart.map(c => ({
                  name: c.item.name,
                  qty: c.qty,
                  temperature: c.suhu,
                  sweetness: c.manis,
                  price: c.item.price
              }))
          };

          const response = await fetch('/api/orders', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
          });

          if (!response.ok) throw new Error('Failed to create order');
          const data = await response.json();
          
          state.activeOrder = {
              id: data.id,
              total: state.cart.reduce((sum, c) => sum + c.item.price * c.qty, 0) - state.discount
          };
          
          state.cart = [];
          state.discount = 0;
          state.voucherCode = '';
          
          navigate('payment');
      } catch (e) {
          showToast('Terjadi kesalahan saat memproses pesanan.');
      } finally {
          btnPay.textContent = origText;
          btnPay.disabled = false;
      }
    };

    // Payment confirm
    document.getElementById('btn-confirm-payment').onclick = confirmPayment;
    document.getElementById('payment-back').onclick = () => navigate('cart');

    // Copy Order ID & Download QRIS
    document.getElementById('btn-copy-id').onclick = () => {
      const id = document.getElementById('payment-order-id').textContent;
      navigator.clipboard.writeText(id).then(() => showToast('Kode disalin!'));
    };
    document.getElementById('btn-download-qris').onclick = () => {
        const id = document.getElementById('payment-order-id').textContent;
        const a = document.createElement('a');
        a.href = `/api/qris/${id}`;
        a.download = `QRIS-${id}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        showToast('Mengunduh QRIS...');
    };

    // Tracking
    document.getElementById('btn-search-order').onclick = () => {
      const input = document.getElementById('search-order-input').value.trim();
      if (!input) return;
      state.activeOrder = { id: input };
      renderTracking();
    };
    document.getElementById('order-items-toggle').onclick = toggleOrderItems;
    document.getElementById('btn-contact-admin').onclick = () => showToast('Hubungi admin via WhatsApp/Telegram');
    document.getElementById('btn-return-home').onclick = () => {
      state.activeOrder = null;
      navigate('home');
    };
    document.getElementById('tracking-back').onclick = () => navigate('home');

    // Customer Data Inputs
    const nameInput = document.getElementById('customer-name');
    if (nameInput) nameInput.oninput = (e) => { state.customerName = e.target.value; };
    const waInput = document.getElementById('customer-wa');
    if (waInput) waInput.oninput = (e) => { state.customerWA = e.target.value; };

    // Removed static room input binding, it is now dynamic in renderDeliveryFields

    // Initial render
    navigate('home');
  }

  async function loadInitialData() {
      try {
          const [storeRes, menuRes] = await Promise.all([
              fetch('/api/store_status'),
              fetch('/api/menu')
          ]);
          if (storeRes.ok) {
              const storeData = await storeRes.json();
              STORE_OPEN = storeData.is_open;
          }
          if (menuRes.ok) {
              MENU_DATA = await menuRes.json();
              // Auto select first category
              const cats = Object.keys(MENU_DATA);
              if (cats.length > 0 && !MENU_DATA[state.activeCategory]) {
                  state.activeCategory = cats[0];
              }
          }
      } catch (e) {
          console.error("Gagal memuat data dari server:", e);
      }
      init();
  }

  document.addEventListener('DOMContentLoaded', loadInitialData);
})();
