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
        <AutocompleteInput
            v-model.trim="filters.categoryQuery"
            @input="onSearchInput"
            :options="categories"
            :placeholder="$t('Filter by category...')"
            translate-options
        />
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
    <button v-if="canManageProducts" class="btn btn-primary mb-3 d-block mx-auto" @click="openModal">
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
          <th v-if="canViewAnyProductPrice">{{ productPriceHeader }}</th>
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
                {{ $t('Archived') }} {{ formatDate(p.archived_at) }}<span v-if="p.archived_by"> {{ $t('by') }} {{ p.archived_by }}</span>
            </div>
          </td>
          <td>{{ p.sku }}</td>
          <td class="d-none d-md-table-cell">{{ p.category?.name ? $t(p.category.name) : '—' }}</td>
          <td class="d-none d-md-table-cell">{{ p.unit?.name ? $t(p.unit.name) : '—' }}</td>
          <td class="d-none d-md-table-cell">{{ p.supplier?.name || '—' }}</td>
          <td v-if="canViewAnyProductPrice">
            <span v-if="canViewPurchasePrice">{{ formatMoney(p.purchase_price, '¥') }}</span>
            <span v-if="canViewPurchasePrice && canViewSalePrice"> / </span>
            <span v-if="canViewSalePrice">{{ formatMoney(p.sale_price, companyCurrencySymbol) }}</span>
          </td>
          <td class="actions-cell" @click.stop>
            <div class="actions-group">
              <ChatShareButton type="product" :record-id="p.id" :title="p.name" compact />
              <button
                  v-if="p.image"
                  class="btn btn-sm btn-secondary"
                  @click.stop="showImage(p.image)"
              >Фото
              </button>
              <button
                  v-if="p.is_archived && canManageProducts"
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
                  v-if="!p.is_archived && canManageProducts"
                  class="btn btn-sm btn-outline-secondary"
                  @click.stop="archiveProduct(p.id)"
              >Archive
              </button>
              <button
                  v-if="!p.is_archived && !p.has_history && canManageProducts"
                  class="btn btn-sm btn-danger"
                  @click.stop="deleteProduct(p.id)"
              >Delete
              </button>
            </div>
          </td>
        </tr>
        <tr v-if="isLoading">
          <td :colspan="productTableColumnCount" class="text-center text-muted">Loading...</td>
        </tr>
        <tr v-else-if="!products.length">
          <td :colspan="productTableColumnCount" class="text-center text-muted">No products found.</td>
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

    <ProductAddEditModal
        :visible="showModal"
        :initial-product="isEdit ? productForm : null"
        :categories="categories"
        :units="units"
        :suppliers="suppliers"
        purchase-currency-symbol="¥"
        :sale-currency-symbol="companyCurrencySymbol"
        :read-only="productForm.is_archived || !canManageProducts"
        :can-view-purchase-price="canViewPurchasePrice"
        :can-edit-purchase-price="canEditPurchasePrice"
        :can-view-cost-price="canViewCostPrice"
        :can-view-cost-breakdown="canViewCostBreakdown"
        :can-view-sale-price="canViewSalePrice"
        :can-edit-sale-price="canEditCatalogSalePrice"
        @saved="onProductSaved"
        @reference-created="onReferenceCreated"
        @open-history="openHistory"
        @close="closeModal"
    />
    <ProductHistoryModal
        :visible="showHistoryModal"
        :product-id="productForm.id"
        :categories="categories"
        :units="units"
        :suppliers="suppliers"
        @close="closeHistory"
    />

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
import ChatShareButton from '../components/ChatShareButton.vue';
import debounce from 'lodash/debounce';
import AutocompleteInput from '../components/AutocompleteInput.vue';
import ProductAddEditModal from '../components/ProductAddEditModal.vue';
import ProductHistoryModal from '../components/ProductHistoryModal.vue';
import { clearCacheByPrefix, getCachedJson, setCachedJson } from '../utils/pageCache';
import { accessState, hasPermission, PERMISSIONS, setCurrentUser } from '../access';
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

const TABLE_STATE_KEY = 'products-table-state';

export default {
  name: 'ProductView',
  components: { ChatShareButton, AutocompleteInput, ProductAddEditModal, ProductHistoryModal },
  data() {
    return {
      products: [],
      currentUser: null,
      categories: [],
      units: [],
      suppliers: [],
      searchQuery: '',
      filters: {categoryQuery: '', supplierQuery: '', archiveStatus: 'active'},
      page: 1,
      pageSize: DEFAULT_PAGE_SIZE,
      totalCount: 0,
      isLoading: false,
      showModal: false,
      isEdit: false,
      showHistoryModal: false,
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
        cost_price: 0,
        automatic_sale_price: 0,
        sale_price_mode: 'automatic',
        applied_markup_pct: null,
        applied_markup_source: 'company',
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
        is_stock_item: false,
        minimum_stock_level: '',
        average_monthly_consumption: '',
        consumption_calculation_mode: 'automatic',
        purchase_batch_size: '',
      },
      systemSettings: null,
    };
  },
  created() {
    this.restoreTableState();
    this.fetchAll();
  },
  watch: {
    '$route.query.chatRecord': {
      immediate: true,
      async handler(value) {
        if (!value || !/^\d+$/.test(String(value))) return;
        try {
          const { data } = await axios.get(`/api/products/${value}/`);
          if (String(this.$route.query.chatRecord) === String(value)) this.editProduct(data);
        } catch { alert('Товар недоступен или у вас нет прав на просмотр.'); }
      },
    },
  },
  computed: {
    totalPages() {
      return pageMeta(this.page, this.totalCount, this.pageSize).totalPages;
    },
    pageStart() {
      return pageMeta(this.page, this.totalCount, this.pageSize).pageStart;
    },
    pageEnd() {
      return pageMeta(this.page, this.totalCount, this.pageSize).pageEnd;
    },
    companyCurrencySymbol() {
      return this.systemSettings?.company_currency_symbol || this.systemSettings?.company_currency_code || '';
    },
    isCompanyAdmin() {
      return Boolean(this.currentUser?.is_company_admin);
    },
    canManageProducts() {
      return hasPermission(PERMISSIONS.PRODUCTS_MANAGE, accessState.user);
    },
    canViewPurchasePrice() {
      return hasPermission(PERMISSIONS.PURCHASE_PRICE_VIEW, accessState.user);
    },
    canEditPurchasePrice() {
      return hasPermission(PERMISSIONS.PURCHASE_PRICE_MANAGE, accessState.user);
    },
    canViewCostPrice() {
      return hasPermission(PERMISSIONS.COST_PRICE_VIEW, accessState.user);
    },
    canViewCostBreakdown() {
      return hasPermission(PERMISSIONS.COMPANY_SETTINGS_MANAGE, accessState.user);
    },
    canViewSalePrice() {
      return hasPermission(PERMISSIONS.SALE_PRICE_VIEW, accessState.user);
    },
    canEditCatalogSalePrice() {
      return hasPermission(PERMISSIONS.CATALOG_SALE_PRICE_MANAGE, accessState.user);
    },
    canViewAnyProductPrice() {
      return this.canViewPurchasePrice || this.canViewSalePrice;
    },
    productPriceHeader() {
      if (this.canViewPurchasePrice && this.canViewSalePrice) return this.$t('Purchase / Sale Price');
      return this.canViewPurchasePrice ? this.$t('Purchase Price') : this.$t('Sale Price');
    },
    productTableColumnCount() {
      return this.canViewAnyProductPrice ? 7 : 6;
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
      const { data } = await axios.get('/api/auth/me/');
      this.currentUser = data;
      setCurrentUser(data);
    },
    async fetchSettings() {
      const res = await axios.get('/api/settings/');
      this.systemSettings = res.data[0] || null;
    },
    async fetchProducts({ useCache = false } = {}) {
      const cacheKey = this.productsCacheKey();
      const cached = getCachedTablePage(cacheKey, useCache);
      if (cached) {
        this.applyProductsResponse(cached);
      }

      this.isLoading = !cached;
      try {
        const res = await axios.get('/api/products/', {
          params: this.productQueryParams()
        });
        setCachedTablePage(cacheKey, res.data);
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
      this.filters = {categoryQuery: '', supplierQuery: '', archiveStatus: 'active'};
      this.page = 1;
      this.saveTableState();
      this.fetchProducts();
    },
    productQueryParams() {
      return {
        page: this.page,
        page_size: this.pageSize,
        search: this.searchQuery || undefined,
        category_query: this.filters.categoryQuery || undefined,
        supplier_query: this.filters.supplierQuery || undefined,
        archive_status: this.filters.archiveStatus || 'active',
      };
    },
    productsCacheKey() {
      return makeTableCacheKey('products', this.productQueryParams());
    },
    applyProductsResponse(data) {
      applyPaginatedData(this, data, 'products');
    },
    saveTableState() {
      saveTableStateSnapshot(TABLE_STATE_KEY, this);
    },
    restoreTableState() {
      const state = restoreTableStateSnapshot(TABLE_STATE_KEY, {
        page: 1,
        searchQuery: '',
        filters: {categoryQuery: '', supplierQuery: '', archiveStatus: 'active'},
      });
      this.page = state.page;
      this.searchQuery = state.searchQuery;
      this.filters = {
        categoryQuery: state.filters?.categoryQuery || '',
        supplierQuery: state.filters?.supplierQuery || '',
        archiveStatus: state.filters?.archiveStatus || 'active',
      };
    },
    changePage(page) {
      changeTablePage(this, page, 'fetchProducts');
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
        cost_price: 0,
        automatic_sale_price: 0,
        sale_price_mode: 'automatic',
        applied_markup_pct: null,
        applied_markup_source: 'company',
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
      if (this.$route.query.chatRecord) {
        const query = { ...this.$route.query };
        delete query.chatRecord;
        this.$router.replace({ path: this.$route.path, query });
      }
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
        cost_price: item.cost_price,
        automatic_sale_price: item.automatic_sale_price,
        sale_price_mode: item.sale_price_mode || 'automatic',
        applied_markup_pct: item.applied_markup_pct,
        applied_markup_source: item.applied_markup_source || 'company',
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
        is_stock_item: Boolean(item.is_stock_item),
        minimum_stock_level: item.minimum_stock_level ?? '',
        average_monthly_consumption: item.average_monthly_consumption ?? '',
        consumption_calculation_mode: item.consumption_calculation_mode || 'automatic',
        purchase_batch_size: item.purchase_batch_size ?? '',
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
      this.showHistoryModal = true;
    },
    closeHistory() {
      this.showHistoryModal = false;
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
  min-width: 170px;
}

.actions-col {
  min-width: 250px;
}

.actions-cell {
  min-width: 250px;
}

.actions-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
}

.actions-group .btn {
  white-space: nowrap;
}

.archived-product-row {
  color: #6c757d;
}

.table > tbody > tr.archived-product-row > * {
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
