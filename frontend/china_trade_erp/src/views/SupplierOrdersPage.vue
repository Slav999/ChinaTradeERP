<template>
  <div class="container mt-4">
    <h1 class="mb-4">Supplier Orders</h1>

    <!-- Search & Filters -->
    <div class="row mb-3 g-2">
      <div class="col-md-4">
        <input
            v-model.trim="searchQuery"
            type="text"
            class="form-control"
            placeholder="Search by order#, supplier, track..."
        />
      </div>
      <div class="col-md-3">
        <select v-model="filters.supplier" class="form-select">
          <option disabled value="">Select supplier...</option>
          <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>
      <div class="col-md-3">
        <select v-model="filters.status" class="form-select">
          <option disabled value="">Select status...</option>
          <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>
      <div class="col-md-2 d-flex align-items-end">
        <button class="btn btn-secondary w-100" @click="resetFilters">Reset</button>
      </div>
    </div>

    <!-- Add Button -->
    <button class="btn btn-primary mb-3 d-block mx-auto" @click="openModal">
      + Add Order
    </button>

    <!-- Table -->
    <div class="table-responsive">
      <table class="table table-hover table-bordered align-middle">
        <thead class="table-light">
        <tr>
          <th>Order#</th>
          <th>Supplier</th>
          <th>Customer</th>
          <th>Plan Receipt</th>
          <th>Shipment</th>
          <th>Delivery</th>
          <th>Amount CNY</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
        </thead>
        <tbody>
        <tr
            v-for="item in filteredOrders"
            :key="item.id"
            @click="editOrder(item)"
            style="cursor: pointer;"
        >
          <td>{{ item.order_number }}</td>
          <td>{{ item.supplier?.name || '—' }}</td>
          <td>{{ item.customer?.name || '—' }}</td>
          <td>{{ formatDate(item.planned_receipt_date) }}</td>
          <td>{{ formatDate(item.shipment_date) }}</td>
          <td>{{ formatDate(item.delivery_date) }}</td>
          <td>{{ item.amount_cny || '—' }}</td>
          <td>
              <span
                  v-if="item.status"
                  class="badge rounded-pill"
                  :style="{ backgroundColor: item.status.color, color: '#fff' }"
              >{{ item.status.name }}</span>
            <span v-else class="text-muted">—</span>
          </td>
          <td @click.stop>
            <button
                v-if="item.payment_details_qr"
                class="btn btn-sm btn-secondary me-1"
                @click="showQr(item.payment_details_qr)"
            >QR
            </button>
            <button class="btn btn-sm btn-danger" @click="deleteOrder(item.id)">
              Delete
            </button>
          </td>
        </tr>
        <tr v-if="!filteredOrders.length">
          <td colspan="9" class="text-center text-muted">No orders yet.</td>
        </tr>
        </tbody>
      </table>
    </div>
    </div>
</template>

<script>
import axios from '../axios';

export default {
  name: 'SupplierOrdersPage',
  data() {
    return {
      /* справочники */
      suppliers: [],
      statuses: [],

      /* список заказов */
      orders: [],

      /* фильтрация */
      searchQuery: '',
      filters: { supplier: '', status: '' },
    };
  },

  computed: {
    highlightId() {
      return this.$route.query.highlight ? +this.$route.query.highlight : null;
    },
    filteredOrders() {
      const q = this.searchQuery.toLowerCase().trim();
      return this.orders.filter(o => {
        const text = `${o.order_number} ${o.supplier?.name || ''} ${o.track_number || ''}`.toLowerCase();
        return (!q || text.includes(q))
          && (!this.filters.supplier || o.supplier?.id === +this.filters.supplier)
          && (!this.filters.status   || o.status?.id   === +this.filters.status);
      });
    },
  },

  created() {
    this.fetchAux();
    this.fetchOrders();
  },

  methods: {
    /* --- API --- */
    async fetchAux() {
      try {
        const [cpRes, stRes] = await Promise.all([
          axios.get('/api/counterparties/'),
          axios.get('/api/supplier-order-statuses/')
        ]);
        this.suppliers = cpRes.data;
        this.statuses  = stRes.data;
      } catch (e) {
        console.error(e); alert('Ошибка при загрузке справочников');
      }
    },
    async fetchOrders() {
      try { this.orders = (await axios.get('/api/supplier-order/')).data; }
      catch (e) { console.error(e); alert('Не удалось загрузить заказы'); }
    },

    /* --- утилиты --- */
    formatDate(v) { return v ? new Date(v).toLocaleDateString() : '—'; },
    resetFilters() { this.searchQuery=''; this.filters={ supplier:'', status:'' }; },

    /* --- переходы --- */
    openModal()          { this.$router.push('/supplier-orders/new'); },
    editOrder(order)     { this.$router.push(`/supplier-orders/${order.id}`); },

    /* --- действия --- */
    async deleteOrder(id) {
      if (!confirm('Удалить заказ?')) return;
      try {
        await axios.delete(`/api/supplier-order/${id}/`);
        this.orders = this.orders.filter(o => o.id !== id);
      } catch (e) { console.error(e); alert('Ошибка при удалении'); }
    },
    showQr(url) { window.open(url, '_blank'); }   // простейший предпросмотр
  }
};
</script>
