<template>
  <div class="container mt-4">
    <h1 class="mb-4">Customer Orders</h1>

    <!-- Search & Filters -->
    <div class="row mb-3 g-2">
      <div class="col-md-4">
        <input
            v-model.trim="searchQuery"
            @input="onFiltersChanged"
            type="text"
            class="form-control"
            placeholder="Search by order#, customer, track..."
        />
      </div>
      <div class="col-md-3">
        <AutocompleteInput
            v-model.trim="filters.customerQuery"
            @input="onFiltersChanged"
            :options="customers"
            placeholder="Customer..."
        />
      </div>
      <div class="col-md-3">
        <select v-model="filters.status" class="form-select" @change="onFiltersChanged">
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
            v-for="item in orders"
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
            <button class="btn btn-sm btn-danger" @click="deleteOrder(item.id)">
              Delete
            </button>
          </td>
        </tr>
        <tr v-if="isLoading">
          <td colspan="5" class="text-center text-muted">Loading...</td>
        </tr>
        <tr v-else-if="!orders.length">
          <td colspan="5" class="text-center text-muted">No orders yet.</td>
        </tr>
        </tbody>
      </table>
    </div>

    <div class="d-flex justify-content-between align-items-center mt-3" v-if="totalCount">
      <div class="text-muted small">
        Showing {{ pageStart }}-{{ pageEnd }} of {{ totalCount }}
      </div>
      <div class="btn-group">
        <button class="btn btn-outline-secondary btn-sm" :disabled="page <= 1 || isLoading" @click="changePage(page - 1)">
          Previous
        </button>
        <button class="btn btn-outline-secondary btn-sm disabled">
          Page {{ page }} / {{ totalPages }}
        </button>
        <button class="btn btn-outline-secondary btn-sm" :disabled="page >= totalPages || isLoading" @click="changePage(page + 1)">
          Next
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from '../axios';
import AutocompleteInput from '../components/AutocompleteInput.vue';
import { clearCacheByPrefix, getCachedJson, getSavedState, paginatedResults, setCachedJson, setSavedState } from '../utils/pageCache';

const TABLE_STATE_KEY = 'customer-orders-table-state';
const STATUS_CACHE_KEY = 'customer-order-statuses:v2';
const PAGE_SIZE = 50;

export default {
  name: 'CustomerOrdersPage',
  components: { AutocompleteInput },
  data() {
    return {
      /* справочники */
      customers: [],
      statuses: [],

      /* список заказов */
      orders: [],

      /* фильтрация */
      searchQuery: '',
      filters: {customerQuery: '', status: ''},
      page: 1,
      pageSize: PAGE_SIZE,
      totalCount: 0,
      isLoading: false,
      searchTimer: null,
    };
  },

  computed: {
    totalPages() {
      return Math.max(1, Math.ceil(this.totalCount / this.pageSize));
    },
    pageStart() {
      return this.totalCount ? ((this.page - 1) * this.pageSize) + 1 : 0;
    },
    pageEnd() {
      return Math.min(this.page * this.pageSize, this.totalCount);
    },
  },

  created() {
    this.restoreTableState();
    this.fetchAux();
    this.fetchOrders({ useCache: true });
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
        const cachedCustomers = getCachedJson('counterparty-options:customer');
        const cachedStatuses = getCachedJson(STATUS_CACHE_KEY);

        if (cachedCustomers) this.customers = cachedCustomers;
        if (cachedStatuses) this.statuses = cachedStatuses;

        const requests = [];
        if (!cachedCustomers) requests.push(axios.get('/api/counterparties/options/', { params: { role: 'customer' } }));
        if (!cachedStatuses) requests.push(axios.get('/api/customer-order-statuses/'));

        const responses = await Promise.all(requests);
        let idx = 0;
        if (!cachedCustomers) {
          this.customers = responses[idx].data;
          setCachedJson('counterparty-options:customer', this.customers);
          idx += 1;
        }
        if (!cachedStatuses) {
          this.statuses = responses[idx].data;
          setCachedJson(STATUS_CACHE_KEY, this.statuses);
        }
      } catch (e) {
        console.error(e);
        alert('Ошибка при загрузке справочников');
      }
    },
    async fetchOrders({ useCache = false } = {}) {
      const cacheKey = this.ordersCacheKey();
      const cached = useCache ? getCachedJson(cacheKey) : null;
      if (cached) {
        this.applyOrdersResponse(cached);
      }

      this.isLoading = !cached;
      try {
        const res = await axios.get('/api/customer-order/', {
          params: this.orderQueryParams()
        });
        setCachedJson(cacheKey, res.data);
        this.applyOrdersResponse(res.data);
      } catch (e) {
        console.error(e);
        alert('Unable to load orders');
      } finally {
        this.isLoading = false;
      }
    },

    /* --- утилиты --- */
    formatDate(v) {
      return v ? new Date(v).toLocaleDateString() : '—';
    },
    resetFilters() {
      this.searchQuery = '';
      this.filters = {customerQuery: '', status: ''};
      this.page = 1;
      this.saveTableState();
      this.fetchOrders();
    },

    /* --- переходы --- */
    orderQueryParams() {
      return {
        page: this.page,
        page_size: this.pageSize,
        search: this.searchQuery || undefined,
        customer_query: this.filters.customerQuery || undefined,
        status: this.filters.status || undefined,
      };
    },
    ordersCacheKey() {
      return `customer-orders:${JSON.stringify(this.orderQueryParams())}`;
    },
    applyOrdersResponse(data) {
      const page = paginatedResults(data);
      this.orders = page.results;
      this.totalCount = page.count;
    },
    saveTableState() {
      setSavedState(TABLE_STATE_KEY, {
        page: this.page,
        searchQuery: this.searchQuery,
        filters: this.filters,
      });
    },
    restoreTableState() {
      const state = getSavedState(TABLE_STATE_KEY, {
        page: 1,
        searchQuery: '',
        filters: {customerQuery: '', status: ''},
      });
      this.page = state.page;
      this.searchQuery = state.searchQuery;
      this.filters = {
        customerQuery: state.filters?.customerQuery || '',
        status: state.filters?.status || '',
      };
    },
    onFiltersChanged() {
      window.clearTimeout(this.searchTimer);
      this.searchTimer = window.setTimeout(() => {
        this.page = 1;
        this.saveTableState();
        this.fetchOrders();
      }, 300);
    },
    changePage(page) {
      if (page < 1 || page > this.totalPages || page === this.page) return;
      this.page = page;
      this.saveTableState();
      this.fetchOrders({ useCache: true });
    },

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
        clearCacheByPrefix('customer-orders:');
        this.orders = this.orders.filter(o => o.id !== id);
        this.totalCount = Math.max(0, this.totalCount - 1);
      } catch (e) {
        console.error(e);
        alert('Ошибка при удалении');
      }
    }
  }
};
</script>
