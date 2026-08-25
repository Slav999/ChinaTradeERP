<template>
  <div class="container mt-4">
    <transition name="save-toast">
      <div v-if="toastMessage" class="save-toast">
        {{ toastMessage }}
      </div>
    </transition>

    <h1 class="mb-4">Products</h1>

    <!-- Search & Filters -->
    <div class="row mb-3 g-2">
      <div class="col-md-3">
        <input
            v-model.trim="searchQuery"
            @input="onSearchInput"
            type="text"
            class="form-control"
            placeholder="Search by name or SKU..."
        />
      </div>
      <div class="col-md-2">
        <select v-model="filters.category" class="form-select" @change="onSearchInput">
          <option disabled selected hidden value="">Select category...</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div class="col-md-3">
        <AutocompleteInput
            v-model.trim="filters.supplierQuery"
            @input="onSearchInput"
            :options="suppliers"
            placeholder="Filter by supplier..."
        />
      </div>
      <div class="col-md-2">
        <select v-model="filters.archiveStatus" class="form-select" @change="onFiltersChanged">
          <option value="active">Active</option>
          <option value="archived">Archived</option>
          <option value="all">All</option>
        </select>
      </div>
      <div class="col-md-2 d-flex align-items-end">
        <button class="btn btn-secondary w-100" @click="resetFilters">Reset</button>
      </div>
    </div>

    <!-- Add Button -->
    <button class="btn btn-primary mb-3 d-block mx-auto" @click="openModal">
      + Add Product
    </button>

    <!-- Table -->
    <div class="table-responsive">
      <table class="table table-hover table-bordered align-middle">
        <thead class="table-light">
        <tr>
          <th class="product-name-col">Name</th>
          <th>SKU</th>
          <th class="d-none d-md-table-cell">Category</th>
          <th class="d-none d-md-table-cell">Unit</th>
          <th class="d-none d-md-table-cell">Supplier</th>
          <th>Purchase / Sale Price</th>
          <th class="actions-col">Actions</th>
        </tr>
        </thead>
        <tbody>
        <tr
            v-for="p in products"
            :key="p.id"
            @click="editProduct(p)"
            :class="{ 'archived-product-row': p.is_archived }"
            style="cursor: pointer;"
        >
          <td>
            <div class="d-flex align-items-center gap-2">
              <span>{{ p.name }}</span>
              <span v-if="p.is_archived" class="badge rounded-pill text-bg-secondary">Archived</span>
            </div>
            <div v-if="p.is_archived" class="small text-muted mt-1">
              Archived {{ formatDate(p.archived_at) }}<span v-if="p.archived_by"> by {{ p.archived_by }}</span>
            </div>
          </td>
          <td>{{ p.sku }}</td>
          <td class="d-none d-md-table-cell">{{ p.category?.name || '—' }}</td>
          <td class="d-none d-md-table-cell">{{ p.unit?.name || '—' }}</td>
          <td class="d-none d-md-table-cell">{{ p.supplier?.name || '—' }}</td>
          <td>{{ formatMoney(p.purchase_price, '¥') }} / {{ formatMoney(p.sale_price, companyCurrencySymbol) }}</td>
          <td class="actions-cell" @click.stop>
            <button
                v-if="p.image"
                class="btn btn-sm btn-secondary"
                @click.stop="showImage(p.image)"
            >Фото
            </button>
            <button
                v-if="p.is_archived"
                class="btn btn-sm btn-outline-primary"
                @click.stop="restoreProduct(p.id)"
            >Restore
            </button>
            <button
                v-if="p.is_archived && isCompanyAdmin"
                class="btn btn-sm btn-outline-danger"
                @click.stop="permanentlyDeleteProduct(p.id)"
            >Delete permanently
            </button>
            <button
                v-if="!p.is_archived"
                class="btn btn-sm btn-outline-secondary"
                @click.stop="archiveProduct(p.id)"
            >Archive
            </button>
            <button
                v-if="!p.is_archived && !p.has_history"
                class="btn btn-sm btn-danger"
                @click.stop="deleteProduct(p.id)"
            >Delete
            </button>
          </td>
        </tr>
        <tr v-if="isLoading">
          <td colspan="7" class="text-center text-muted">Loading...</td>
        </tr>
        <tr v-else-if="!products.length">
          <td colspan="7" class="text-center text-muted">No products found.</td>
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

    <ProductAddEditModal
        :visible="showModal"
        :initial-product="isEdit ? productForm : null"
        :categories="categories"
        :units="units"
        :suppliers="suppliers"
        purchase-currency-symbol="¥"
        :sale-currency-symbol="companyCurrencySymbol"
        :read-only="productForm.is_archived"
        @saved="onProductSaved"
        @reference-created="onReferenceCreated"
        @open-history="openHistory"
        @close="closeModal"
    />
    <!-- History Modal -->
    <div
        class="modal fade history-modal"
        :class="{ show: showHistoryModal }"
        :style="showHistoryModal ? 'display: block;' : ''"
        tabindex="-1"
    >
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <transition name="modal-fade">
          <div class="modal-content" v-if="showHistoryContent">
            <div class="modal-header">
              <h5 class="modal-title">Change History</h5>
              <button type="button" class="btn-close" @click="closeHistory"></button>
            </div>
            <div class="modal-body history-modal-body">
              <table v-if="historyLogs.length" class="table table-striped">
                <thead>
                <tr>
                  <th>Date</th>
                  <th>User</th>
                  <th>Field</th>
                  <th>From</th>
                  <th>To</th>
                </tr>
                </thead>
                <tbody>
                <tr v-for="(log, idx) in historyLogs" :key="idx">
                  <td>{{ log.changed_at }}</td>
                  <td>{{ log.changed_by }}</td>
                  <td>{{ historyFieldLabel(log) }}</td>
                  <td>{{ historyOldValue(log) }}</td>
                  <td>{{ historyNewValue(log) }}</td>
                </tr>
                </tbody>
              </table>
              <div v-else class="text-center text-muted py-4">
                No changes found.
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" @click="closeHistory">Close</button>
            </div>
          </div>
        </transition>
      </div>
    </div>
    <div class="modal-backdrop fade history-backdrop" :class="{ show: showHistoryModal }"></div>

    <!-- Image Preview Modal -->
    <div
        class="modal fade"
        :class="{ show: imageModalUrl }"
        :style="imageModalUrl ? 'display: block;' : ''"
        tabindex="-1"
    >
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <transition name="modal-fade">
          <div class="modal-content" v-if="imageModalUrl">
            <div class="modal-header">
              <h6 class="modal-title">Image Preview</h6>
              <button
                  type="button"
                  class="btn-close"
                  @click="closeImage"
              ></button>
            </div>
            <div class="modal-body text-center">
              <img
                  :src="imageModalUrl"
                  class="img-fluid"
                  alt="Product Image"
              />
            </div>
          </div>
        </transition>
      </div>
    </div>
    <div
        class="modal-backdrop fade"
        :class="{ show: imageModalUrl }"
    ></div>
  </div>
</template>

<script>
import axios from '../axios';
import debounce from 'lodash/debounce';
import AutocompleteInput from '../components/AutocompleteInput.vue';
import ProductAddEditModal from '../components/ProductAddEditModal.vue';
import { clearCacheByPrefix, getCachedJson, getSavedState, paginatedResults, setCachedJson, setSavedState } from '../utils/pageCache';

const TABLE_STATE_KEY = 'products-table-state';
const PAGE_SIZE = 50;

export default {
  name: 'ProductView',
  components: { AutocompleteInput, ProductAddEditModal },
  data() {
    return {
      products: [],
      currentUser: null,
      categories: [],
      units: [],
      suppliers: [],
      searchQuery: '',
      filters: {category: '', supplierQuery: '', archiveStatus: 'active'},
      page: 1,
      pageSize: PAGE_SIZE,
      totalCount: 0,
      isLoading: false,
      showModal: false,
      isEdit: false,
      showHistoryContent: true,
      showHistoryModal: false,
      historyLogs: [],
      imageModalUrl: null,
      toastMessage: '',
      toastTimer: null,
      productForm: {
        id: null,
        name: '',
        sku: '',
        category_id: null,
        unit_id: null,
        supplier_id: null,
        purchase_price: 0,
        sale_price: 0,
        units_per_package: 1,
        weight_kg: 0,
        length_m: 0,
        width_m: 0,
        height_m: 0,
        image: null,
        created_at: null,
        created_by: null,
        updated_at: null,
        updated_by: null,
        is_archived: false,
        archived_at: null,
        archived_by: null,
        has_history: false,
      },
      systemSettings: null,
    };
  },
  created() {
    this.restoreTableState();
    this.fetchAll();
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
    companyCurrencySymbol() {
      return this.systemSettings?.company_currency_symbol || this.systemSettings?.company_currency_code || '';
    },
    isCompanyAdmin() {
      return Boolean(this.currentUser?.is_company_admin);
    },
  },
  methods: {
    onSearchInput: debounce(function () {
      this.page = 1;
      this.saveTableState();
      this.fetchProducts();
    }, 300),
    onFiltersChanged() {
      this.page = 1;
      this.saveTableState();
      this.fetchProducts();
    },
    async fetchAll() {
      await Promise.all([
        this.fetchProducts({ useCache: true }),
        this.fetchCategories(),
        this.fetchUnits(),
        this.fetchSuppliers(),
        this.fetchSettings(),
        this.fetchCurrentUser(),
      ]);
    },
    async fetchCurrentUser() {
      const { data } = await axios.get('/api/me/');
      this.currentUser = data;
    },
    async fetchSettings() {
      const res = await axios.get('/api/settings/');
      this.systemSettings = res.data[0] || null;
    },
    async fetchProducts({ useCache = false } = {}) {
      const cacheKey = this.productsCacheKey();
      const cached = useCache ? getCachedJson(cacheKey) : null;
      if (cached) {
        this.applyProductsResponse(cached);
      }

      this.isLoading = !cached;
      try {
        const res = await axios.get('/api/products/', {
          params: this.productQueryParams()
        });
        setCachedJson(cacheKey, res.data);
        this.applyProductsResponse(res.data);
      } catch (e) {
        console.error(e);
        alert('Unable to load products');
      } finally {
        this.isLoading = false;
      }
    },
    async fetchCategories() {
      const cached = getCachedJson('product-categories');
      if (cached) {
        this.categories = cached;
        return;
      }

      const res = await axios.get('/api/product-category/');
      this.categories = res.data;
      setCachedJson('product-categories', this.categories);
    },
    async fetchUnits() {
      const cached = getCachedJson('product-units');
      if (cached) {
        this.units = cached;
        return;
      }

      const res = await axios.get('/api/units/');
      this.units = res.data;
      setCachedJson('product-units', this.units);
    },
    async fetchSuppliers() {
      const cached = getCachedJson('counterparty-options:supplier');
      if (cached) {
        this.suppliers = cached;
        return;
      }

      const res = await axios.get('/api/counterparties/options/', { params: { role: 'supplier' } });
      this.suppliers = res.data;
      setCachedJson('counterparty-options:supplier', this.suppliers);
    },
    resetFilters() {
      this.searchQuery = '';
      this.filters = {category: '', supplierQuery: '', archiveStatus: 'active'};
      this.page = 1;
      this.saveTableState();
      this.fetchProducts();
    },
    productQueryParams() {
      return {
        page: this.page,
        page_size: this.pageSize,
        search: this.searchQuery || undefined,
        category: this.filters.category || undefined,
        supplier_query: this.filters.supplierQuery || undefined,
        archive_status: this.filters.archiveStatus || 'active',
      };
    },
    productsCacheKey() {
      return `products:${JSON.stringify(this.productQueryParams())}`;
    },
    applyProductsResponse(data) {
      const page = paginatedResults(data);
      this.products = page.results;
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
        filters: {category: '', supplierQuery: '', archiveStatus: 'active'},
      });
      this.page = state.page;
      this.searchQuery = state.searchQuery;
      this.filters = {
        category: state.filters?.category || '',
        supplierQuery: state.filters?.supplierQuery || '',
        archiveStatus: state.filters?.archiveStatus || 'active',
      };
    },
    changePage(page) {
      if (page < 1 || page > this.totalPages || page === this.page) return;
      this.page = page;
      this.saveTableState();
      this.fetchProducts({ useCache: true });
    },
    openModal() {
      this.productForm = {
        id: null,
        name: '',
        sku: '',
        category_id: null,
        unit_id: null,
        supplier_id: null,
        purchase_price: 0,
        sale_price: 0,
        units_per_package: 1,
        weight_kg: 0,
        length_m: 0,
        width_m: 0,
        height_m: 0,
        image: null,
        created_at: null,
        created_by: null,
        updated_at: null,
        updated_by: null,
        is_archived: false,
        archived_at: null,
        archived_by: null,
        has_history: false,
      };
      this.isEdit = false;
      this.showModal = true;
    },
    closeModal() {
      this.showModal = false;
    },
    onProductSaved(product) {
      const idx = this.products.findIndex(x => x.id === product.id);
      if (idx !== -1) {
        this.products.splice(idx, 1, product);
      } else {
        this.products.unshift(product);
        this.totalCount += 1;
      }
      this.productForm = this.productToForm(product);
      this.isEdit = true;
      clearCacheByPrefix('products:');
      this.fetchProducts();
    },
    onReferenceCreated({type, item}) {
      if (type === 'category') {
        this.categories.push(item);
        setCachedJson('product-categories', this.categories);
      } else if (type === 'unit') {
        this.units.push(item);
        setCachedJson('product-units', this.units);
      } else if (type === 'supplier') {
        this.suppliers.push(item);
        setCachedJson('counterparty-options:supplier', this.suppliers);
      }
    },
    editProduct(item) {
      this.productForm = this.productToForm(item);
      this.isEdit = true;
      this.showModal = true;
    },
    productToForm(item) {
      return {
        id: item.id,
        name: item.name,
        sku: item.sku,
        category_id: item.category?.id || null,
        unit_id: item.unit?.id || null,
        supplier_id: item.supplier?.id || null,
        purchase_price: item.purchase_price,
        sale_price: item.sale_price,
        units_per_package: item.units_per_package ?? 1,
        weight_kg: item.weight_kg ?? 0,
        length_m: item.length_m ?? 0,
        width_m: item.width_m ?? 0,
        height_m: item.height_m ?? 0,
        image: null,
        created_at: item.created_at,
        created_by: item.created_by,
        updated_at: item.updated_at,
        updated_by: item.updated_by,
        is_archived: item.is_archived || false,
        archived_at: item.archived_at || null,
        archived_by: item.archived_by || null,
        has_history: item.has_history || false,
      };
    },
    showToast(message) {
      this.toastMessage = message;
      clearTimeout(this.toastTimer);
      this.toastTimer = setTimeout(() => {
        this.toastMessage = '';
      }, 1800);
    },
    formatMoney(value, symbol = '') {
      const numberValue = Number(String(value ?? 0).replace(',', '.'));
      const amount = Number.isFinite(numberValue) ? numberValue.toFixed(2) : value;
      return symbol ? `${symbol} ${amount}` : amount;
    },
    formatApiError(error) {
      const data = error.response?.data;
      if (!data) return 'Unable to save product';
      if (typeof data === 'string') return data;

      const labels = {
        name: 'Name',
        sku: 'SKU',
        supplier_id: 'Supplier',
        category_id: 'Category',
        unit_id: 'Unit',
      };

      return Object.entries(data)
          .map(([field, messages]) => {
            const label = labels[field] || field;
            const text = Array.isArray(messages) ? messages.join(' ') : messages;
            return `${label}: ${text}`;
          })
          .join('\n');
    },
    async deleteProduct(id) {
      if (confirm('Delete this product permanently?')) {
        try {
          await axios.delete(`/api/products/${id}/`);
          clearCacheByPrefix('products:');
          this.products = this.products.filter(x => x.id !== id);
          this.totalCount = Math.max(0, this.totalCount - 1);
          this.showToast('Product deleted');
        } catch (error) {
          alert(this.formatApiError(error));
        }
      }
    },
    async archiveProduct(id) {
      if (confirm('Move this product to archive?')) {
        try {
          const { data } = await axios.post(`/api/products/${id}/archive/`);
          clearCacheByPrefix('products:');
          if (this.filters.archiveStatus === 'active') {
            this.products = this.products.filter(x => x.id !== id);
            this.totalCount = Math.max(0, this.totalCount - 1);
          } else {
            const idx = this.products.findIndex(x => x.id === id);
            if (idx !== -1) this.products.splice(idx, 1, data);
          }
          this.showToast('Product archived');
        } catch (error) {
          alert(this.formatApiError(error));
        }
      }
    },
    async restoreProduct(id) {
      try {
        const { data } = await axios.post(`/api/products/${id}/restore/`);
        clearCacheByPrefix('products:');
        if (this.filters.archiveStatus === 'archived') {
          this.products = this.products.filter(x => x.id !== id);
          this.totalCount = Math.max(0, this.totalCount - 1);
        } else {
          const idx = this.products.findIndex(x => x.id === id);
          if (idx !== -1) this.products.splice(idx, 1, data);
        }
        this.showToast('Product restored');
      } catch (error) {
        alert(this.formatApiError(error));
      }
    },
    async permanentlyDeleteProduct(id) {
      if (confirm('Permanently delete this product? This action cannot be undone.')) {
        try {
          await axios.delete(`/api/products/${id}/permanent-delete/`);
          clearCacheByPrefix('products:');
          this.products = this.products.filter(x => x.id !== id);
          this.totalCount = Math.max(0, this.totalCount - 1);
          this.showToast('Product deleted');
        } catch (error) {
          alert(this.formatApiError(error));
        }
      }
    },
    openHistory() {
      if (!this.isEdit) return;
      axios.get(`/api/products/${this.productForm.id}/history/`)
          .then(res => {
            this.historyLogs = res.data;
            this.showHistoryContent = true;
            this.showHistoryModal = true;
          });
    },
    closeHistory() {
      this.showHistoryModal = false;
      this.showHistoryContent = false;
    },
    fieldLabel(key) {
      const map = {
        name: 'Name',
        sku: 'SKU',
        description: 'Description',
        category_id: 'Category',
        unit_id: 'Unit',
        supplier_id: 'Supplier',
        purchase_price: 'Purchase Price',
        sale_price: 'Sale Price',
        image: 'Image',
      };
      return map[key] || key;
    },
    isArchiveLog(log) {
      return log.field_name === 'is_archived';
    },
    historyFieldLabel(log) {
      if (!this.isArchiveLog(log)) return this.fieldLabel(log.field_name);
      return log.new_value === 'True' ? 'Archived' : 'Restored';
    },
    historyOldValue(log) {
      return this.isArchiveLog(log) ? '—' : this.formatValue(log.field_name, log.old_value);
    },
    historyNewValue(log) {
      return this.isArchiveLog(log) ? '—' : this.formatValue(log.field_name, log.new_value);
    },

    formatValue(field, val) {
      if (field === 'category_id') {
        const c = this.categories.find(x => String(x.id) === String(val));
        return c ? c.name : '—';
      }
      if (field === 'unit_id') {
        const u = this.units.find(x => String(x.id) === String(val));
        return u ? u.name : '—';
      }
      if (field === 'supplier_id') {
        const s = this.suppliers.find(x => String(x.id) === String(val));
        return s ? s.name : '—';
      }
      if (field === 'image') {
        // покажем только имя файла
        return val ? val.split('/').pop() : '—';
      }
      // для чисел и остальных строк
      return val != null && val !== '' ? val : '—';
    },
    showImage(url) {
      this.imageModalUrl = url;
    },
    closeImage() {
      this.imageModalUrl = null;
    },
    formatDate(val) {
      return val ? new Date(val).toLocaleString() : '—';
    },
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

.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.modal-fade-enter-to, .modal-fade-leave-from {
  opacity: 1;
  transform: translateY(0);
}

.history-modal-body {
  max-height: calc(100vh - 220px);
  overflow-y: auto;
}

.table td, .table th {
  vertical-align: middle;
}

.product-name-col {
  min-width: 240px;
}

.actions-col {
  min-width: 250px;
}

.actions-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  min-width: 250px;
}

.actions-cell .btn {
  white-space: nowrap;
}

.archived-product-row {
  color: #6c757d;
  background-color: #f8f9fa;
}

.save-toast {
  position: fixed;
  top: 82px;
  left: 50%;
  z-index: 1080;
  min-width: 180px;
  padding: 0.65rem 0.9rem;
  border: 1px solid #badbcc;
  border-radius: 0.375rem;
  background: #d1e7dd;
  color: #0f5132;
  box-shadow: 0 8px 22px rgba(15, 81, 50, 0.16);
  font-weight: 600;
  text-align: center;
  transform: translateX(-50%);
}

.save-toast-enter-active,
.save-toast-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.save-toast-enter-from,
.save-toast-leave-to {
  opacity: 0;
  transform: translate(-50%, -8px);
}
</style>
