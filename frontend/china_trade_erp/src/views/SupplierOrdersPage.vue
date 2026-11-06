<template>
  <div class="container mt-4">
    <h1 class="mb-4">{{ $t(isSamples ? 'Samples and trips' : 'Supplier Orders') }}</h1>

    <!-- Search & Filters -->
    <div class="row mb-3 g-2">
      <div :class="isSamples ? 'col-md-6' : 'col-md-4'">
        <input
            v-model.trim="searchQuery"
            @input="onFiltersChanged"
            type="text"
            class="form-control"
            :placeholder="$t(isSamples ? 'Search by SKU, order#, supplier, trip...' : 'Search by SKU, order#, supplier, track...')"
        />
      </div>
      <div class="col-md-2">
        <AutocompleteInput
            v-model.trim="filters.supplierQuery"
            @input="onFiltersChanged"
            :options="suppliers"
            placeholder="Supplier..."
        />
      </div>
      <div v-if="!isSamples" class="col-md-2">
        <AutocompleteInput
            v-model.trim="filters.customerQuery"
            @input="onFiltersChanged"
            :options="customers"
            placeholder="Customer..."
        />
      </div>
      <div class="col-md-2">
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
      <button v-if="!isSamples"
          class="btn btn-outline-secondary mb-3 d-inline-flex align-items-center"
          @click="exportOrders"
      >
        <i class="bi bi-download me-1"></i>
        Export orders
      </button>
      <button v-if="canViewFinancialReports && !isSamples" class="btn btn-outline-primary mb-3" :disabled="isLoading" @click="showAnalytics = true">Supplier analytics</button>
    </div>

    <OrderAnalyticsModal v-if="showAnalytics" kind="supplier" :options="suppliers" :initial-query="filters.supplierQuery" @close="showAnalytics = false" />

    <!-- Table -->
    <div class="table-responsive">
      <table class="table table-hover table-bordered align-middle">
        <thead class="table-light">
        <tr>
          <th>Order#</th>
          <th>Supplier</th>
          <th v-if="isSamples">{{ $t('Trip / exhibition / meeting') }}</th>
          <th v-else>Customer</th>
          <th v-if="!isSamples">Plan Receipt</th>
          <th v-if="!isSamples">Shipment</th>
          <th>Delivery</th>
          <th v-if="canViewPurchasePrice">Amount CNY</th>
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
          <td>{{ item.supplier?.name || '—' }}</td>
          <td v-if="isSamples">{{ item.trip_name || '—' }}</td>
          <td v-else>{{ item.customer?.name || '—' }}</td>
          <td v-if="!isSamples">{{ formatDate(item.planned_receipt_date) }}</td>
          <td v-if="!isSamples">{{ formatDate(item.shipment_date) }}</td>
          <td>{{ formatDate(item.delivery_date) }}</td>
          <td v-if="canViewPurchasePrice">{{ item.amount_cny || '—' }}</td>
          <td>
              <span
                  v-if="item.status"
                  class="badge rounded-pill"
                  :style="{ backgroundColor: item.status.color, color: '#fff' }"
              >{{ item.status.display_name || item.status.name }}</span>
            <span v-else class="text-muted">—</span>
          </td>
          <td @click.stop>
            <ChatShareButton type="supplier_order" :record-id="item.id" :title="`${isSamples ? 'Командировка / образцы' : 'Заказ поставщику'} №${item.order_number}`" class="me-1" compact />
            <button
                v-if="item.payment_details_qr"
                class="btn btn-sm btn-secondary me-1"
                @click="showQr(item.payment_details_qr)"
            >QR
            </button>
            <button v-if="canManageOrders" class="btn btn-sm btn-danger" @click="deleteOrder(item.id)">
              Delete
            </button>
          </td>
        </tr>
        <tr v-if="isLoading">
          <td :colspan="orderTableColumnCount" class="text-center text-muted">Loading...</td>
        </tr>
        <tr v-else-if="!orders.length">
          <td :colspan="orderTableColumnCount" class="text-center text-muted">No orders yet.</td>
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

    <!-- QR Preview Modal -->
    <div
        class="modal fade qr-modal"
        :class="{ show: !!qrModalUrl }"
        :style="qrModalUrl ? 'display: block;' : ''"
        tabindex="-1"
    >
      <div class="modal-dialog modal-dialog-centered qr-dialog">
        <transition name="modal-fade">
          <div class="modal-content" v-if="showQrContent && qrModalUrl">
            <div class="modal-header">
              <h6 class="modal-title">QR Code</h6>
              <button type="button" class="btn-close" @click="closeQr"></button>
            </div>
            <div class="modal-body text-center">
              <div class="qr-modal-frame">
                <img :src="qrModalUrl" class="qr-modal-image" alt="QR code"/>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>
    <div class="modal-backdrop fade qr-backdrop" :class="{ show: !!qrModalUrl }"></div>
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

const TABLE_STATE_KEY = 'supplier-orders-table-state';

export default {
  name: 'SupplierOrdersPage',
  components: { ChatShareButton, AutocompleteInput, OrderAnalyticsModal },
  data() {
    return {
      /* справочники */
      suppliers: [],
      customers: [],
      statuses: [],

      /* список заказов */
      orders: [],

      /* фильтрация */
      searchQuery: '',
      filters: { supplierQuery: '', customerQuery: '', status: '' },
      page: 1,
      pageSize: DEFAULT_PAGE_SIZE,
      totalCount: 0,
      isLoading: false,
      searchTimer: null,
      showAnalytics: false,
      showQrContent: true,
      qrModalUrl: null,
    };
  },

  computed: {
    isSamples() { return !!this.$route.meta.samples; },
    sectionPath() { return this.isSamples ? '/samples-trips' : '/supplier-orders'; },
    tableStateKey() { return this.isSamples ? 'samples-trips-table-state' : TABLE_STATE_KEY; },
    canManageOrders() {
      return hasPermission(PERMISSIONS.SUPPLIER_ORDERS_MANAGE, accessState.user);
    },
    canViewPurchasePrice() {
      return hasPermission(PERMISSIONS.PURCHASE_PRICE_VIEW, accessState.user);
    },
    canViewFinancialReports() {
      return hasPermission(PERMISSIONS.FINANCIAL_REPORTS_VIEW, accessState.user);
    },
    orderTableColumnCount() {
      return (this.canViewPurchasePrice ? 9 : 8) - (this.isSamples ? 2 : 0);
    },
    highlightId() {
      return this.$route.query.highlight ? +this.$route.query.highlight : null;
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
        const res = await axios.get('/api/supplier-order/export/', {
          params: { ...this.orderQueryParams(), page: undefined, page_size: undefined },
          responseType: 'blob'
        });
        // создаём ссылку и кликаем для скачивания
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const a = document.createElement('a');
        a.href = url;
        a.download = 'supplier_orders.xlsx';
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
        const cachedSuppliers = getCachedJson('counterparty-options:supplier');
        const cachedCustomers = getCachedJson('counterparty-options:customer');
        const cachedStatuses = getCachedJson('supplier-order-statuses');

        if (cachedSuppliers) this.suppliers = cachedSuppliers;
        if (cachedCustomers) this.customers = cachedCustomers;
        if (cachedStatuses) this.statuses = cachedStatuses;

        const requests = [];
        if (!cachedSuppliers) requests.push(axios.get('/api/counterparties/options/', { params: { role: 'supplier' } }));
        if (!cachedCustomers) requests.push(axios.get('/api/counterparties/options/', { params: { role: 'customer' } }));
        if (!cachedStatuses) requests.push(axios.get('/api/supplier-order-statuses/'));

        const responses = await Promise.all(requests);
        let idx = 0;
        if (!cachedSuppliers) {
          this.suppliers = responses[idx].data;
          setCachedJson('counterparty-options:supplier', this.suppliers);
          idx += 1;
        }
        if (!cachedCustomers) {
          this.customers = responses[idx].data;
          setCachedJson('counterparty-options:customer', this.customers);
          idx += 1;
        }
        if (!cachedStatuses) {
          this.statuses = responses[idx].data;
          setCachedJson('supplier-order-statuses', this.statuses);
        }
      } catch (e) {
        console.error(e); alert('Unable to load reference data.');
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
        const res = await axios.get('/api/supplier-order/', {
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
    formatDate(v) { return v ? new Date(v).toLocaleDateString() : '—'; },
    formatDateTime(v) { return v ? new Date(v).toLocaleString() : '—'; },
    resetFilters() {
      this.searchQuery='';
      this.filters={ supplierQuery:'', customerQuery:'', status:'' };
      this.page = 1;
      this.saveTableState();
      this.fetchOrders();
    },

    /* --- переходы --- */
    orderQueryParams() {
      return {
        is_sample: this.isSamples,
        page: this.page,
        page_size: this.pageSize,
        search: this.searchQuery || undefined,
        supplier_query: this.filters.supplierQuery || undefined,
        customer_query: this.filters.customerQuery || undefined,
        status: this.filters.status || undefined,
      };
    },
    ordersCacheKey() {
      return makeTableCacheKey('supplier-orders:v3', this.orderQueryParams());
    },
    applyOrdersResponse(data) {
      applyPaginatedData(this, data, 'orders');
    },
    saveTableState() {
      saveTableStateSnapshot(this.tableStateKey, this);
    },
    restoreTableState() {
      const state = restoreTableStateSnapshot(this.tableStateKey, {
        page: 1,
        searchQuery: '',
        filters: { supplierQuery: '', customerQuery: '', status: '' },
      });
      this.page = state.page;
      this.searchQuery = state.searchQuery;
      this.filters = {
        supplierQuery: state.filters?.supplierQuery || '',
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

    openModal()          { this.$router.push(`${this.sectionPath}/new`); },
    editOrder(order)     { this.$router.push(`${this.sectionPath}/${order.id}`); },

    /* --- действия --- */
    async deleteOrder(id) {
      if (!confirm('Delete this order?')) return;
      try {
        await axios.delete(`/api/supplier-order/${id}/`);
        clearCacheByPrefix('supplier-orders:');
        this.orders = this.orders.filter(o => o.id !== id);
        this.totalCount = Math.max(0, this.totalCount - 1);
      } catch (e) { console.error(e); alert('Unable to delete order.'); }
    },
    showQr(url) {
      this.showQrContent = true;
      this.qrModalUrl = url;
    },
    closeQr() {
      this.showQrContent = false;
      this.qrModalUrl = null;
    }
  }
};
</script>

<style scoped>
.modal-backdrop {
  display: none;
}

.modal-backdrop.show {
  display: block;
}

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

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.modal-fade-enter-to,
.modal-fade-leave-from {
  opacity: 1;
  transform: translateY(0);
}

.qr-modal {
  z-index: 1090;
}

.qr-backdrop {
  z-index: 1085;
}

.qr-dialog {
  width: min(440px, calc(100vw - 1rem));
  max-width: min(440px, calc(100vw - 1rem));
  margin-left: auto;
  margin-right: auto;
}

.qr-dialog .modal-body {
  padding: 1rem;
}

.qr-modal-frame {
  display: flex;
  align-items: center;
  justify-content: center;
  width: min(360px, calc(100vw - 4rem));
  height: min(360px, calc(100vw - 4rem));
  margin: 0 auto;
  padding: 14px;
  border: 1px solid #d8e0e7;
  border-radius: 8px;
  background: #fff;
}

.qr-modal-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
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
