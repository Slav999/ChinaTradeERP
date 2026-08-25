<template>
  <div class="container mt-4 warehouse-page">
    <h1 class="mb-4">Warehouse</h1>

    <div class="row mb-2 g-2 warehouse-filters">
      <div class="col-md-3">
        <input
            v-model.trim="searchQuery"
            @input="onSearchInput"
            type="text"
            class="form-control"
            placeholder="Search warehouse items..."
        />
      </div>
      <div class="col-md-2">
        <select v-model="filters.category" class="form-select" @change="fetchStocks">
          <option value="">All categories</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div class="col-md-3">
        <select v-model="filters.supplier" class="form-select" @change="fetchStocks">
          <option value="">All suppliers</option>
          <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>
      <div class="col-md-2 d-flex align-items-center">
        <div class="form-check form-switch mb-0">
          <input
              id="only-available"
              v-model="filters.onlyAvailable"
              class="form-check-input"
              type="checkbox"
              @change="fetchStocks"
          />
          <label class="form-check-label" for="only-available">Only in stock</label>
        </div>
      </div>
      <div class="col-md-2">
        <button class="btn btn-secondary w-100" @click="resetFilters">Reset</button>
      </div>
    </div>

    <div class="d-flex flex-wrap align-items-center gap-2 mb-3 warehouse-report-toolbar">
      <div class="input-group input-group-sm report-date-field">
        <span class="input-group-text">From</span>
        <input v-model="reportFilters.dateFrom" type="date" class="form-control" aria-label="Order date from" />
      </div>
      <div class="input-group input-group-sm report-date-field">
        <span class="input-group-text">To</span>
        <input v-model="reportFilters.dateTo" type="date" class="form-control" aria-label="Order date to" />
      </div>
      <div class="btn-group btn-group-sm" role="group" aria-label="Quick report periods">
        <button type="button" class="btn btn-outline-secondary" @click="setQuickPeriod(7)">7 days</button>
        <button type="button" class="btn btn-outline-secondary" @click="setQuickPeriod(30)">30 days</button>
        <button type="button" class="btn btn-outline-secondary" @click="setCurrentMonth">This month</button>
      </div>
      <button
          type="button"
          class="btn btn-outline-secondary btn-sm d-inline-flex align-items-center"
          :disabled="isExporting"
          @click="downloadReport"
      >
        <i class="bi bi-download me-1"></i>
        {{ isExporting ? 'Wait...' : 'Export' }}
      </button>
    </div>

    <div class="table-responsive">
      <table class="table table-hover table-bordered align-middle warehouse-table">
        <thead class="table-light">
        <tr>
          <th>Product</th>
          <th class="d-none d-md-table-cell">SKU</th>
          <th class="d-none d-lg-table-cell">Category</th>
          <th class="d-none d-lg-table-cell">Supplier</th>
          <th>Unit</th>
          <th class="text-end">On hand</th>
          <th class="text-end">Reserved</th>
          <th class="text-end">Expected</th>
          <th class="text-end">Available</th>
        </tr>
        </thead>
        <tbody>
        <tr v-for="stock in stocks" :key="stock.id">
          <td>{{ stock.product.name }}</td>
          <td class="d-none d-md-table-cell">{{ stock.product.sku }}</td>
          <td class="d-none d-lg-table-cell">{{ stock.product.category?.name || '—' }}</td>
          <td class="d-none d-lg-table-cell">{{ stock.product.supplier?.name || '—' }}</td>
          <td>{{ stock.product.unit?.name || '—' }}</td>
          <td class="text-end">{{ formatQty(stock.quantity_on_hand) }}</td>
          <td class="text-end">{{ formatQty(stock.quantity_reserved) }}</td>
          <td class="text-end">{{ formatQty(stock.quantity_expected) }}</td>
          <td class="text-end fw-semibold">{{ formatQty(stock.quantity_available) }}</td>
        </tr>
        <tr v-if="isLoading">
          <td colspan="9" class="text-center text-muted">Loading...</td>
        </tr>
        <tr v-else-if="!stocks.length">
          <td colspan="9" class="text-center text-muted">No warehouse items found.</td>
        </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import axios from '../axios';

function debounce(fn, wait) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn.apply(this, args), wait);
  };
}

export default {
  name: 'WarehousePage',
  data() {
    return {
      stocks: [],
      categories: [],
      suppliers: [],
      searchQuery: '',
      filters: {
        category: '',
        supplier: '',
        onlyAvailable: false,
      },
      reportFilters: {
        dateFrom: '',
        dateTo: '',
      },
      isLoading: false,
      isExporting: false,
    };
  },
  created() {
    this.fetchCategories();
    this.fetchSuppliers();
    this.fetchStocks();
  },
  methods: {
    onSearchInput: debounce(function () {
      this.fetchStocks();
    }, 300),
    async fetchCategories() {
      const { data } = await axios.get('/api/product-category/');
      this.categories = data;
    },
    async fetchSuppliers() {
      const { data } = await axios.get('/api/counterparties/options/', {
        params: { role: 'supplier' },
      });
      this.suppliers = data.results || data;
    },
    async fetchStocks() {
      this.isLoading = true;
      try {
        const { data } = await axios.get('/api/warehouse-stocks/', {
          params: {
            search: this.searchQuery || undefined,
            category: this.filters.category || undefined,
            supplier: this.filters.supplier || undefined,
            only_available: this.filters.onlyAvailable ? '1' : undefined,
          },
        });
        this.stocks = data.results || data;
      } catch (error) {
        console.error(error);
        alert('Unable to load warehouse.');
      } finally {
        this.isLoading = false;
      }
    },
    resetFilters() {
      this.searchQuery = '';
      this.filters = { category: '', supplier: '', onlyAvailable: false };
      this.reportFilters = { dateFrom: '', dateTo: '' };
      this.fetchStocks();
    },
    dateInputValue(date) {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    },
    setQuickPeriod(days) {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - days + 1);
      this.reportFilters.dateFrom = this.dateInputValue(start);
      this.reportFilters.dateTo = this.dateInputValue(end);
    },
    setCurrentMonth() {
      const today = new Date();
      const start = new Date(today.getFullYear(), today.getMonth(), 1);
      this.reportFilters.dateFrom = this.dateInputValue(start);
      this.reportFilters.dateTo = this.dateInputValue(today);
    },
    async downloadReport() {
      if (
        this.reportFilters.dateFrom &&
        this.reportFilters.dateTo &&
        this.reportFilters.dateFrom > this.reportFilters.dateTo
      ) {
        alert('The end date must be on or after the start date.');
        return;
      }

      this.isExporting = true;
      try {
        const response = await axios.get('/api/warehouse-report/export/', {
          params: {
            date_from: this.reportFilters.dateFrom || undefined,
            date_to: this.reportFilters.dateTo || undefined,
            search: this.searchQuery || undefined,
            supplier: this.filters.supplier || undefined,
            category: this.filters.category || undefined,
          },
          responseType: 'blob',
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.download = `warehouse_report_${this.dateInputValue(new Date()).replaceAll('-', '')}.xlsx`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      } catch (error) {
        console.error(error);
        alert('Unable to export the warehouse report.');
      } finally {
        this.isExporting = false;
      }
    },
    formatQty(value) {
      const numberValue = Number(String(value ?? 0).replace(',', '.'));
      return Number.isFinite(numberValue)
        ? numberValue.toLocaleString('ru-RU', { maximumFractionDigits: 2 })
        : '0';
    },
  },
};
</script>

<style scoped>
.warehouse-filters .btn {
  min-width: 72px;
}

.report-date-field {
  width: 210px;
}
</style>
