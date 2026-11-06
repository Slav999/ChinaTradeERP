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
    <div class="d-flex flex-wrap justify-content-center gap-2 mb-3">
      <button v-if="canManageOrders" class="btn btn-primary mb-3" @click="openModal">
        + Add Order
      </button>
      <button
          class="btn btn-outline-secondary mb-3 d-inline-flex align-items-center"
          @click="exportOrders"
      >
        <i class="bi bi-download me-1"></i>
        Export orders
      </button>
      <button v-if="canViewFinancialReports" class="btn btn-outline-primary mb-3" :disabled="isLoading" @click="showAnalytics = true">Customer analytics</button>
    </div>
    <OrderAnalyticsModal v-if="showAnalytics" kind="customer" :options="customers" :initial-query="filters.customerQuery" @close="showAnalytics = false" />

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
          <td>
            <div class="d-flex align-items-center gap-2">
              <span>{{ item.order_number }}</span>
              <span
                  v-if="item.sent_at"
                  class="sent-badge"
                  :title="`Sent ${formatDateTime(item.sent_at)}`"
              >Sent</span>
            </div>
            <small
                v-if="item.created_at"
                class="order-created-date"
                :class="{ 'previous-year-date': item.is_previous_year }"
            >{{ formatDate(item.created_at) }}</small>
          </td>
          <td>{{ item.customer?.name || '—' }}</td>
          <td>{{ formatDate(item.shipment_date) }}</td>
          <td>
              <span
                  v-if="item.status"
                  class="badge rounded-pill"
                  :style="{ backgroundColor: item.status.color, color: '#fff' }"
              >{{ item.status.display_name || item.status.name }}</span>
            <span v-else class="text-muted">—</span>
          </td>
          <td @click.stop>
            <ChatShareButton type="customer_order" :record-id="item.id" :title="`Заказ покупателя №${item.order_number}`" class="me-1" compact />
            <button v-if="canManageOrders" class="btn btn-sm btn-danger" @click="deleteOrder(item.id)">
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

    <div class="d-flex justify-content-between align-items-center mt-3 mb-4" v-if="totalCount">
      <div class="text-muted small">
        {{ $t(`Showing ${pageStart}-${pageEnd} of ${totalCount}`) }}
      </div>
      <div class="btn-group">
        <button class="btn btn-outline-secondary btn-sm" :disabled="page <= 1 || isLoading" @click="changePage(page - 1)">
          {{ $t('Previous') }}
        </button>
        <button class="btn btn-outline-secondary btn-sm disabled">
          {{ $t(`Page ${page} / ${totalPages}`) }}
        </button>
        <button class="btn btn-outline-secondary btn-sm" :disabled="page >= totalPages || isLoading" @click="changePage(page + 1)">
          {{ $t('Next') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import OrderAnalyticsModal from '../components/OrderAnalyticsModal.vue';
import axios from '../axios';
import ChatShareButton from '../components/ChatShareButton.vue';
import AutocompleteInput from '../components/AutocompleteInput.vue';
import { clearCacheByPrefix, getCachedJson, setCachedJson } from '../utils/pageCache';
import { accessState, hasPermission, PERMISSIONS } from '../access';
import {
  applyPaginatedData,
  changeTablePage,
  DEFAULT_PAGE_SIZE,
  getCachedTablePage,
  makeTableCacheKey,
  pageMeta,
  restoreTableStateSnapshot,
  saveTableStateSnapshot,
  setCachedTablePage,
} from '../utils/tablePage';

const TABLE_STATE_KEY = 'customer-orders-table-state';
const STATUS_CACHE_KEY = 'customer-order-statuses:v2';

export default {
  name: 'CustomerOrdersPage',
  components: { ChatShareButton, AutocompleteInput, OrderAnalyticsModal },
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
      pageSize: DEFAULT_PAGE_SIZE,
      totalCount: 0,
      isLoading: false,
      searchTimer: null,
      showAnalytics: false,
    };
  },

  computed: {
    canManageOrders() {
      return hasPermission(PERMISSIONS.CUSTOMER_ORDERS_MANAGE, accessState.user);
    },
    canViewFinancialReports() {
      return hasPermission(PERMISSIONS.FINANCIAL_REPORTS_VIEW, accessState.user);
    },
    totalPages() {
      return pageMeta(this.page, this.totalCount, this.pageSize).totalPages;
    },
    pageStart() {
      return pageMeta(this.page, this.totalCount, this.pageSize).pageStart;
    },
    pageEnd() {
      return pageMeta(this.page, this.totalCount, this.pageSize).pageEnd;
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
          params: { ...this.orderQueryParams(), page: undefined, page_size: undefined },
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
        alert('Unable to export orders.');
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
        alert('Unable to load reference data.');
      }
    },
    async fetchOrders({ useCache = false } = {}) {
      const cacheKey = this.ordersCacheKey();
      const cached = getCachedTablePage(cacheKey, useCache);
      if (cached) {
        this.applyOrdersResponse(cached);
      }

      this.isLoading = !cached;
      try {
        const res = await axios.get('/api/customer-order/', {
          params: this.orderQueryParams()
        });
        setCachedTablePage(cacheKey, res.data);
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
    formatDateTime(v) {
      return v ? new Date(v).toLocaleString() : '—';
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
      return makeTableCacheKey('customer-orders:v2', this.orderQueryParams());
    },
    applyOrdersResponse(data) {
      applyPaginatedData(this, data, 'orders');
    },
    saveTableState() {
      saveTableStateSnapshot(TABLE_STATE_KEY, this);
    },
    restoreTableState() {
      const state = restoreTableStateSnapshot(TABLE_STATE_KEY, {
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
      changeTablePage(this, page, 'fetchOrders');
    },

    openModal() {
      this.$router.push('/customer-orders/new');
    },
    editOrder(order) {
      this.$router.push(`/customer-orders/${order.id}`);
    },

    /* --- действия --- */
    async deleteOrder(id) {
      if (!confirm('Delete this order?')) return;
      try {
        await axios.delete(`/api/customer-order/${id}/`);
        clearCacheByPrefix('customer-orders:');
        this.orders = this.orders.filter(o => o.id !== id);
        this.totalCount = Math.max(0, this.totalCount - 1);
      } catch (e) {
        console.error(e);
        alert('Unable to delete order.');
      }
    }
  }
};
</script>

<style scoped>
.sent-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.18rem 0.52rem;
  border: 1px solid #badbcc;
  border-radius: 999px;
  background: #d1e7dd;
  color: #0f5132;
  font-size: 0.78rem;
  font-weight: 700;
  line-height: 1.1;
  vertical-align: middle;
}
</style>

<style scoped>
.order-created-date {
  display: inline-block;
  margin-top: 2px;
  color: #6c757d;
}
.previous-year-date {
  padding: 1px 4px;
  border-radius: 3px;
  background-color: #eceff1;
}
</style>
