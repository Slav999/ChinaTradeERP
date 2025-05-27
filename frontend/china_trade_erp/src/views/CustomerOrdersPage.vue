<template>
  <div class="container mt-4">
    <h1 class="mb-4">Customer Orders</h1>

    <!-- Search & Filters -->
    <div class="row mb-3 g-2">
      <div class="col-md-4">
        <input
            v-model.trim="searchQuery"
            type="text"
            class="form-control"
            placeholder="Search by order#, customer, track..."
        />
      </div>
      <div class="col-md-3">
        <select v-model="filters.customer" class="form-select">
          <option disabled value="">Select customer...</option>
          <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option>
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
    <div class="d-flex justify-content-center gap-2 mb-3">
      <button class="btn btn-primary mb-3" @click="openModal">
        + Add Order
      </button>
      <button
          class="btn btn-outline-secondary mb-3 d-inline-flex align-items-center"
          @click="exportOrders"
      >
        <i class="bi bi-download me-1"></i>
        Export
      </button>
    </div>
    <!-- Table -->
    <div class="table-responsive">
      <table class="table table-hover table-bordered align-middle">
        <thead class="table-light">
        <tr>
          <th>Order#</th>
          <th>Customer</th>
          <th>Shipment</th>
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
          <td>{{ item.customer?.name || '—' }}</td>
          <td>{{ formatDate(item.shipment_date) }}</td>
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
          <td colspan="8" class="text-center text-muted">No orders yet.</td>
        </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import axios from '../axios';

export default {
  name: 'CustomerOrdersPage',
  data() {
    return {
      /* справочники */
      customers: [],
      statuses: [],

      /* список заказов */
      orders: [],

      /* фильтрация */
      searchQuery: '',
      filters: {customer: '', status: ''},
    };
  },

  computed: {
    filteredOrders() {
      const q = this.searchQuery.toLowerCase().trim();
      return this.orders.filter(o => {
        const text = `${o.order_number} ${o.customer?.name || ''} ${o.track_number || ''}`.toLowerCase();
        return (!q || text.includes(q))
            && (!this.filters.customer || o.customer?.id === +this.filters.customer)
            && (!this.filters.status || o.status?.id === +this.filters.status);
      });
    },
  },

  created() {
    this.fetchAux();
    this.fetchOrders();
  },

  methods: {
    async exportOrders() {
      try {
        const res = await axios.get('/api/customer-order/export/', {
          responseType: 'blob'
        });
        // создаём ссылку и кликаем для скачивания
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const a = document.createElement('a');
        a.href = url;
        a.download = 'customer_orders.xlsx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } catch (e) {
        console.error(e);
        alert('Не удалось экспортировать заказы');
      }
    },
    /* --- API --- */
    async fetchAux() {
      try {
        const [custRes, stRes] = await Promise.all([
          axios.get('/api/counterparties/'),
          axios.get('/api/customer-order-statuses/')
        ]);
        this.customers = custRes.data;
        this.statuses = stRes.data;
      } catch (e) {
        console.error(e);
        alert('Ошибка при загрузке справочников');
      }
    },
    async fetchOrders() {
      try {
        this.orders = (await axios.get('/api/customer-order/')).data;
      } catch (e) {
        console.error(e);
        alert('Не удалось загрузить заказы');
      }
    },

    /* --- утилиты --- */
    formatDate(v) {
      return v ? new Date(v).toLocaleDateString() : '—';
    },
    resetFilters() {
      this.searchQuery = '';
      this.filters = {customer: '', status: ''};
    },

    /* --- переходы --- */
    openModal() {
      this.$router.push('/customer-orders/new');
    },
    editOrder(order) {
      this.$router.push(`/customer-orders/${order.id}`);
    },

    /* --- действия --- */
    async deleteOrder(id) {
      if (!confirm('Удалить заказ?')) return;
      try {
        await axios.delete(`/api/customer-order/${id}/`);
        this.orders = this.orders.filter(o => o.id !== id);
      } catch (e) {
        console.error(e);
        alert('Ошибка при удалении');
      }
    },
    showQr(url) {
      window.open(url, '_blank');
    }
  }
};
</script>
