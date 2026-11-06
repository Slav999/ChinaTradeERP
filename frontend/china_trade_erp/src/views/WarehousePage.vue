<template>
  <div class="container mt-4 warehouse-page">
    <h1 class="mb-4">{{ $t('Warehouse') }}</h1>

    <div class="row mb-2 g-2 warehouse-filters">
      <div class="col-md-2">
        <AutocompleteInput
            v-model.trim="searchQuery"
            @input="fetchProductSuggestions"
            @select="applyProductSearch"
            :options="productSuggestions"
            :placeholder="$t('Search warehouse items...')"
        />
      </div>
      <div class="col-md-2">
        <AutocompleteInput
            v-model.trim="filters.categoryQuery"
            @select="onFiltersChanged"
            :options="categories"
            translate-options
            :placeholder="$t('Category...')"
        />
      </div>
      <div class="col-md-2">
        <AutocompleteInput
            v-model.trim="filters.supplierQuery"
            @select="onFiltersChanged"
            :options="suppliers"
            :placeholder="$t('Supplier...')"
        />
      </div>
      <div class="col-md-2">
        <select v-model="filters.stockControl" class="form-select" @change="onFiltersChanged">
          <option value="">{{ $t('All stock statuses') }}</option>
          <option value="attention">{{ $t('Requires attention') }}</option>
          <option value="no_forecast">{{ $t('No forecast data') }}</option>
          <option value="normal">{{ $t('Normal') }}</option>
        </select>
      </div>
      <div class="col-md-auto d-flex align-items-center only-available-filter">
        <div class="form-check form-switch mb-0">
          <input
              id="only-available"
              v-model="filters.onlyAvailable"
              class="form-check-input"
              type="checkbox"
              @change="onFiltersChanged"
          />
          <label class="form-check-label" for="only-available">{{ $t('Only available') }}</label>
        </div>
      </div>
      <div class="col-md reset-filter">
        <button class="btn btn-secondary w-100" @click="resetFilters">{{ $t('Reset') }}</button>
      </div>
    </div>

    <div class="d-flex flex-wrap align-items-center gap-2 mb-3 warehouse-report-toolbar">
      <div class="input-group input-group-sm report-date-field">
        <span class="input-group-text">{{ $t('From') }}</span>
        <input v-model="reportFilters.dateFrom" type="date" class="form-control" :aria-label="$t('Supplier order date from')" @change="onReportFiltersChanged" />
      </div>
      <div class="input-group input-group-sm report-date-field">
        <span class="input-group-text">{{ $t('To') }}</span>
        <input v-model="reportFilters.dateTo" type="date" class="form-control" :aria-label="$t('Supplier order date to')" @change="onReportFiltersChanged" />
      </div>
      <div class="btn-group btn-group-sm" role="group" aria-label="Quick report periods">
        <button type="button" class="btn btn-outline-secondary" @click="setQuickPeriod(7)">{{ $t('7 days') }}</button>
        <button type="button" class="btn btn-outline-secondary" @click="setQuickPeriod(30)">{{ $t('30 days') }}</button>
        <button type="button" class="btn btn-outline-secondary" @click="setCurrentMonth">{{ $t('This month') }}</button>
      </div>
      <button
          type="button"
          class="btn btn-outline-secondary btn-sm d-inline-flex align-items-center"
          :disabled="isExporting"
          @click="downloadReport"
      >
        <i class="bi bi-download me-1"></i>
        {{ isExporting ? $t('Wait...') : $t('Export') }}
      </button>
      <button type="button" class="btn btn-outline-secondary btn-sm d-inline-flex align-items-center" @click="downloadWriteOffs">
        <i class="bi bi-download me-1" aria-hidden="true"></i>
        {{ $t('Write-off report') }}
      </button>
      <button
          type="button"
          class="btn btn-outline-primary btn-sm d-inline-flex align-items-center"
          :disabled="isStockControlLoading"
          @click="openStockControl"
      >
        <i class="bi bi-clipboard2-pulse me-1"></i>
        {{ $t('Stock control') }}
      </button>
      <div v-if="selectedProductIds.length || appliedProductIds.length" class="selected-products-note">
        {{ $t('Selected:') }} {{ selectedProductIds.length }}
        <span v-if="hasPendingSelection" class="selection-pending">{{ $t('Selection changed') }}</span>
        <button
            type="button"
            class="btn btn-primary btn-sm ms-1 selected-apply-btn"
            :disabled="!hasPendingSelection || isChartLoading"
            @click="applySelectedProducts"
        >
          {{ $t('Apply') }}
        </button>
        <button type="button" class="btn btn-outline-danger btn-sm selected-clear-btn" @click="clearSelectedProducts">{{ $t('Clear') }}</button>
      </div>
    </div>

    <div v-if="showMetricControls || selectionWarning" class="d-flex flex-wrap align-items-center gap-2 mb-3">
      <div v-if="showMetricControls" class="btn-group btn-group-sm" role="group" aria-label="Warehouse analytics metric">
        <button
            v-for="option in availableChartMetricOptions"
            :key="option.value"
            type="button"
            class="btn"
            :class="chartMetric === option.value ? 'btn-primary' : 'btn-outline-secondary'"
            @click="setChartMetric(option.value)"
        >
          {{ $t(option.label) }}
        </button>
      </div>
      <div v-if="selectionWarning" class="selection-warning">
        {{ $t(selectionWarning) }}
      </div>
    </div>

    <WarehouseAnalyticsChart
        :summary="chartSummary"
        :metric="chartMetric"
        :selected-unit="chartUnit"
        :selected-count="appliedProductIds.length"
        :limit="chartSelectionLimit"
        :is-loading="isChartLoading"
        @select-unit="setChartUnit"
    />

    <div class="table-responsive">
      <table class="table table-hover table-bordered align-middle warehouse-table">
        <thead class="table-light">
        <tr>
          <th class="select-col text-center">
            <input
                class="form-check-input"
                type="checkbox"
                :checked="allVisibleSelected"
                :disabled="!visibleProductIds.length"
                @change="toggleVisibleProducts"
            />
          </th>
          <th class="product-col">{{ $t('Product') }}</th>
          <th class="d-none d-md-table-cell">{{ $t('SKU') }}</th>
          <th class="d-none d-lg-table-cell">{{ $t('Supplier') }}</th>
          <th>{{ $t('Unit') }}</th>
          <th>{{ $t('Status') }}</th>
          <th class="text-end stock-metric-cell stock-metric-available">{{ $t('Available') }}</th>
          <th class="text-end">{{ $t('Defective') }}</th>
          <th class="text-end">{{ $t('Minimum') }}</th>
          <th class="text-end stock-metric-cell stock-metric-expected">{{ $t('Expected') }}</th>
          <th class="text-end">{{ $t('Recommended order') }}</th>
        </tr>
        </thead>
        <tbody>
        <tr
            v-for="stock in stocks"
            :key="stock.id"
            class="warehouse-product-row"
            role="button"
            tabindex="0"
            @click="openProductEditor(stock.product.id)"
            @keydown.enter.prevent="openProductEditor(stock.product.id)"
            @keydown.space.prevent="openProductEditor(stock.product.id)"
        >
          <td class="select-col text-center">
            <input
                class="form-check-input"
                type="checkbox"
                :checked="selectedProductIds.includes(stock.product.id)"
                @click.stop
                @change.stop="toggleProductSelection(stock.product.id, $event)"
            />
            <button
                v-if="canManageWarehouse"
                type="button"
                class="btn btn-sm btn-outline-secondary stock-operation-button"
                :title="$t('Operations')"
                :aria-label="`${$t('Operations')}: ${stock.product.sku || stock.product.name}`"
                @click.stop="openWarehouseOperation(stock)"
                @keydown.stop
            ><i class="bi bi-sliders" aria-hidden="true"></i></button>
          </td>
          <td class="product-col">{{ stock.product.name }}</td>
          <td class="d-none d-md-table-cell">{{ stock.product.sku }}</td>
          <td class="d-none d-lg-table-cell">{{ stock.product.supplier?.name || '—' }}</td>
          <td>{{ stock.product.unit?.name ? $t(stock.product.unit.name) : '—' }}</td>
          <td>
            <span v-if="stock.stock_control" class="badge" :class="stockStatusClass(stock.stock_control.status)">{{ $t(stock.stock_control.status_label) }}</span>
            <span v-else class="text-muted">—</span>
          </td>
          <td class="text-end stock-metric-cell stock-metric-available">{{ formatQty(stock.quantity_available) }}</td>
          <td class="text-end">{{ formatQty(stock.quantity_defective) }}</td>
          <td class="text-end">{{ stock.stock_control ? formatQty(stock.stock_control.minimum_stock_level) : '—' }}</td>
          <td class="text-end stock-metric-cell stock-metric-expected">{{ formatQty(stock.quantity_expected) }}</td>
          <td class="text-end">{{ stock.stock_control ? formatOptionalQty(stock.stock_control.recommended_order_quantity) : '—' }}</td>
        </tr>
        <tr v-if="isLoading">
          <td :colspan="warehouseTableColumnCount" class="text-center text-muted">{{ $t('Loading...') }}</td>
        </tr>
        <tr v-else-if="!stocks.length">
          <td :colspan="warehouseTableColumnCount" class="text-center text-muted">{{ $t('No warehouse items found.') }}</td>
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

    <div class="modal fade" :class="{ show: showWarehouseOperationModal }" :style="showWarehouseOperationModal ? 'display: block;' : ''" tabindex="-1">
      <div class="modal-dialog modal-dialog-centered">
        <div v-if="showWarehouseOperationModal" class="modal-content">
          <div class="modal-header">
            <div>
              <h5 class="modal-title">{{ $t('Warehouse operation') }}</h5>
              <div class="small text-muted">{{ operationStock?.product?.name }}</div>
            </div>
            <button type="button" class="btn-close" @click="closeWarehouseOperation"></button>
          </div>
          <div class="modal-body">
            <div class="row g-2 mb-3">
              <div class="col-4"><div class="border rounded p-2"><small class="text-muted d-block">{{ $t('Available') }}</small><strong>{{ formatQty(operationStock?.quantity_available) }}</strong></div></div>
              <div class="col-4"><div class="border rounded p-2"><small class="text-muted d-block">{{ $t('Defective') }}</small><strong>{{ formatQty(operationStock?.quantity_defective) }}</strong></div></div>
              <div class="col-4"><div class="border rounded p-2"><small class="text-muted d-block">{{ $t('Physical stock') }}</small><strong>{{ formatQty(operationStock?.quantity_physical) }}</strong></div></div>
            </div>
            <div class="mb-3">
              <label class="form-label">{{ $t('Operation') }}</label>
              <select v-model="warehouseOperation.action" class="form-select">
                <option value="release_defect">{{ $t('Return defect to available stock') }}</option>
                <option value="write_off_defect">{{ $t('Write off unusable defect') }}</option>
                <option value="write_off_stock">{{ $t('Write off available stock') }}</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">{{ $t('Quantity') }}</label>
              <div class="input-group">
                <input v-model="warehouseOperation.quantity" type="number" min="0.01" step="0.01" class="form-control" />
                <span class="input-group-text">{{ operationStock?.product?.unit?.name ? $t(operationStock.product.unit.name) : '' }}</span>
              </div>
            </div>
            <div v-if="warehouseOperation.action === 'write_off_stock'" class="mb-3">
              <label class="form-label">{{ $t('Reason') }}</label>
              <select v-model="warehouseOperation.reason" class="form-select">
                <option value="" disabled>{{ $t('Select...') }}</option>
                <option value="marketing">{{ $t('Marketing and internal use') }}</option>
                <option value="storage_damage">{{ $t('Damage during storage') }}</option>
                <option value="inventory_adjustment">{{ $t('Inventory adjustment') }}</option>
                <option value="other">{{ $t('Other') }}</option>
              </select>
            </div>
            <div>
              <label class="form-label">{{ $t('Comment') }}</label>
              <textarea v-model.trim="warehouseOperation.comment" class="form-control" rows="2"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-outline-secondary" @click="closeWarehouseOperation">{{ $t('Cancel') }}</button>
            <button type="button" class="btn btn-primary" :disabled="isWarehouseOperationSaving" @click="saveWarehouseOperation">{{ $t('Save') }}</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showWarehouseOperationModal" class="modal-backdrop fade show"></div>

    <div
        class="modal fade"
        :class="{ show: showStockControlModal }"
        :style="showStockControlModal ? 'display: block;' : ''"
        tabindex="-1"
    >
      <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
        <div v-if="showStockControlModal" class="modal-content">
          <div class="modal-header">
            <div>
              <h5 class="modal-title">{{ $t('Warehouse stock control') }}</h5>
              <div v-if="stockControlSnapshot" class="text-muted small">
                {{ $t('Updated') }} {{ formatDateTime(stockControlSnapshot.generated_at) }} · {{ $t('delivery lead') }} {{ stockControlSnapshot.delivery_lead_days }} {{ $t('calendar days') }}
              </div>
            </div>
            <button type="button" class="btn-close" @click="showStockControlModal = false"></button>
          </div>
          <div class="modal-body">
            <div v-if="isStockControlLoading" class="text-center text-muted py-5">{{ $t('Loading stock control...') }}</div>
            <template v-else-if="stockControlSnapshot">
              <div class="row g-2 mb-3 stock-control-summary">
                <div class="col-6 col-lg"><div class="summary-card summary-attention"><strong>{{ stockControlSnapshot.summary.attention_count }}</strong><span>{{ $t('Attention') }}</span></div></div>
                <div class="col-6 col-lg"><div class="summary-card summary-critical"><strong>{{ stockControlSnapshot.summary.out_of_stock_count || 0 }}</strong><span>{{ $t('Out of stock') }}</span></div></div>
                <div class="col-6 col-lg"><div class="summary-card summary-critical"><strong>{{ stockControlSnapshot.summary.below_minimum_count || 0 }}</strong><span>{{ $t('Below minimum') }}</span></div></div>
                <div class="col-6 col-lg"><div class="summary-card summary-order"><strong>{{ stockControlSnapshot.summary.requires_order_count }}</strong><span>{{ $t('Order required') }}</span></div></div>
                <div class="col-6 col-lg"><div class="summary-card summary-expected"><strong>{{ stockControlSnapshot.summary.supply_expected_count }}</strong><span>{{ $t('Incoming covers demand') }}</span></div></div>
                <div class="col-6 col-lg"><div class="summary-card summary-no-forecast"><strong>{{ stockControlSnapshot.summary.no_forecast_count || 0 }}</strong><span>{{ $t('No forecast') }}</span></div></div>
                <div class="col-6 col-lg"><div class="summary-card summary-normal"><strong>{{ stockControlSnapshot.summary.normal_count }}</strong><span>{{ $t('Normal') }}</span></div></div>
              </div>
              <div class="table-responsive stock-control-table-wrap">
                <table class="table table-sm table-hover align-middle mb-0">
                  <thead class="table-light">
                    <tr>
                      <th>{{ $t('Status') }}</th><th>{{ $t('Forecast') }}</th><th>{{ $t('SKU') }}</th><th>{{ $t('Product') }}</th><th>{{ $t('Supplier') }}</th><th>{{ $t('Available') }}</th><th>{{ $t('Defective') }}</th><th>{{ $t('Physical stock') }}</th>
                      <th>{{ $t('Minimum') }}</th><th>{{ $t('Expected') }}</th><th>{{ $t('Monthly use') }}</th><th>{{ $t('Purchase batch') }}</th>
                      <th>{{ $t('Projected') }}</th><th>{{ $t('Deficit at delivery') }}</th><th>{{ $t('Recommended order') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in stockControlSnapshot.items" :key="item.product_id">
                      <td><span class="badge" :class="stockStatusClass(item.status)">{{ $t(item.status_label) }}</span></td>
                      <td><span class="badge" :class="forecastQualityClass(item.forecast_quality)">{{ $t(item.forecast_quality_label) }}</span></td>
                      <td>{{ item.sku }}</td>
                      <td>{{ item.product_name }}</td>
                      <td>{{ item.supplier_name }}</td>
                      <td>{{ formatQty(item.quantity_available) }} {{ item.unit }}</td>
                      <td>{{ formatQty(item.quantity_defective) }} {{ item.unit }}</td>
                      <td>{{ formatQty(item.quantity_physical) }} {{ item.unit }}</td>
                      <td>{{ formatQty(item.minimum_stock_level) }} {{ item.unit }}</td>
                      <td>{{ formatQty(item.quantity_expected) }} {{ item.unit }}</td>
                      <td>
                        <div>{{ formatOptionalQtyWithUnit(item.average_monthly_consumption, item.unit) }}</div>
                        <small class="text-muted">{{ $t(consumptionDescription(item)) }}</small>
                      </td>
                      <td>{{ formatOptionalQtyWithUnit(item.purchase_batch_size, item.unit) }}</td>
                      <td>{{ formatOptionalQtyWithUnit(item.projected_stock, item.unit) }}</td>
                      <td>{{ formatOptionalQtyWithUnit(item.shortage_at_delivery, item.unit) }}</td>
                      <td>{{ formatOptionalQtyWithUnit(item.recommended_order_quantity, item.unit) }}</td>
                    </tr>
                    <tr v-if="!stockControlSnapshot.items.length"><td colspan="15" class="text-center text-muted py-4">{{ $t('No warehouse products have a minimum stock configured.') }}</td></tr>
                  </tbody>
                </table>
              </div>
            </template>
            <div v-else class="text-center text-muted py-5">{{ $t('No warehouse control data is available.') }}</div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-outline-secondary" @click="showStockControlModal = false">{{ $t('Close') }}</button>
            <button type="button" class="btn btn-primary" :disabled="!stockControlSnapshot || isStockControlExporting" @click="downloadStockControl">
              {{ isStockControlExporting ? 'Downloading...' : 'Download Excel' }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showStockControlModal" class="modal-backdrop fade show"></div>

    <ProductAddEditModal
        :visible="showProductModal"
        :initial-product="editingProduct"
        :categories="categories"
        :units="units"
        :suppliers="suppliers"
        purchase-currency-symbol="¥"
        :sale-currency-symbol="companyCurrencySymbol"
        :read-only="Boolean(editingProduct?.is_archived) || !canManageProducts"
        :can-view-purchase-price="canViewPurchasePrice"
        :can-edit-purchase-price="canEditPurchasePrice"
        :can-view-cost-price="canViewCostPrice"
        :can-view-cost-breakdown="canViewCostBreakdown"
        :can-view-sale-price="canViewSalePrice"
        :can-edit-sale-price="canEditCatalogSalePrice"
        @saved="onWarehouseProductSaved"
        @reference-created="onProductReferenceCreated"
        @open-history="showProductHistory = true"
        @close="closeProductEditor"
    />
    <ProductHistoryModal
        :visible="showProductHistory"
        :product-id="editingProduct?.id"
        :categories="categories"
        :units="units"
        :suppliers="suppliers"
        @close="showProductHistory = false"
    />
  </div>
</template>

<script>
import { defineAsyncComponent } from 'vue';
import axios from '../axios';
import AutocompleteInput from '../components/AutocompleteInput.vue';
import ProductAddEditModal from '../components/ProductAddEditModal.vue';
import ProductHistoryModal from '../components/ProductHistoryModal.vue';
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
import { clearCacheByPrefix, getCachedJson, setCachedJson } from '../utils/pageCache';

const TABLE_STATE_KEY = 'warehouse-table-state';
const CATEGORY_CACHE_KEY = 'product-categories';
const SUPPLIER_CACHE_KEY = 'counterparty-options:supplier';
const UNIT_CACHE_KEY = 'product-units';
const CHART_SELECTION_LIMIT = 20;

function debounce(fn, wait) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn.apply(this, args), wait);
  };
}

export default {
  name: 'WarehousePage',
  components: {
    AutocompleteInput,
    ProductAddEditModal,
    ProductHistoryModal,
    WarehouseAnalyticsChart: defineAsyncComponent(() => import('../components/WarehouseAnalyticsChart.vue')),
  },
  data() {
    return {
      stocks: [],
      productSuggestions: [],
      categories: [],
      suppliers: [],
      units: [],
      systemSettings: null,
      currentUser: null,
      searchQuery: '',
      appliedSearchQuery: '',
      filters: {
        categoryQuery: '',
        supplierQuery: '',
        onlyAvailable: false,
        stockControl: '',
      },
      appliedFilters: {
        categoryQuery: '',
        supplierQuery: '',
        onlyAvailable: false,
        stockControl: '',
      },
      page: 1,
      pageSize: DEFAULT_PAGE_SIZE,
      totalCount: 0,
      reportFilters: {
        dateFrom: '',
        dateTo: '',
      },
      selectedProductIds: [],
      appliedProductIds: [],
      chartMetric: 'quantity',
      chartUnit: '',
      chartSummary: { items: [], totals: {} },
      chartMetricOptions: [
        { value: 'quantity', label: 'Quantity' },
        { value: 'total_cny', label: 'CNY amount' },
        { value: 'total_local', label: 'Local amount' },
      ],
      chartSelectionLimit: CHART_SELECTION_LIMIT,
      selectionWarning: '',
      isLoading: false,
      isChartLoading: false,
      stocksRequestId: 0,
      chartRequestId: 0,
      isExporting: false,
      stockControlSnapshot: null,
      showStockControlModal: false,
      isStockControlLoading: false,
      isStockControlExporting: false,
      showProductModal: false,
      showProductHistory: false,
      editingProduct: null,
      isProductLoading: false,
      showWarehouseOperationModal: false,
      operationStock: null,
      warehouseOperation: { action: 'release_defect', quantity: '', reason: '', comment: '' },
      isWarehouseOperationSaving: false,
    };
  },
  computed: {
    canManageWarehouse() {
      return hasPermission(PERMISSIONS.WAREHOUSE_MANAGE, accessState.user);
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
    canViewFinancialReports() {
      return hasPermission(PERMISSIONS.FINANCIAL_REPORTS_VIEW, accessState.user);
    },
    availableChartMetricOptions() {
      return this.canViewFinancialReports
        ? this.chartMetricOptions
        : this.chartMetricOptions.filter(option => option.value === 'quantity');
    },
    warehouseTableColumnCount() {
      return 11;
    },
    showMetricControls() {
      return Number(this.chartSummary?.totals?.all_products_count || 0) > 1;
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
    visibleProductIds() {
      return this.stocks.map(stock => stock.product.id);
    },
    allVisibleSelected() {
      return Boolean(
        this.visibleProductIds.length &&
        this.visibleProductIds.every(id => this.selectedProductIds.includes(id))
      );
    },
    hasPendingSelection() {
      return this.selectionKey(this.selectedProductIds) !== this.selectionKey(this.appliedProductIds);
    },
    companyCurrencySymbol() {
      return this.systemSettings?.company_currency_symbol || this.systemSettings?.company_currency_code || '';
    },
    isCompanyAdmin() {
      return Boolean(this.currentUser?.is_company_admin);
    },
  },
  created() {
    this.restoreTableState();
    this.fetchCategories();
    this.fetchSuppliers();
    this.fetchUnits();
    this.fetchSystemSettings();
    this.fetchCurrentUser();
    this.fetchStocks({ useCache: true });
    this.fetchChartSummary();
    this.fetchStockControl(Boolean(this.$route.query.stockControl));
  },
  mounted() {
    window.addEventListener('open-stock-control', this.openStockControl);
  },
  beforeUnmount() {
    window.removeEventListener('open-stock-control', this.openStockControl);
    this.stocksRequestId += 1;
    this.chartRequestId += 1;
  },
  methods: {
    async downloadWriteOffs() {
      try {
        const { data } = await axios.get('/api/warehouse-write-offs/export/', {
          responseType: 'blob', params: {
            date_from: this.reportFilters.dateFrom || undefined,
            date_to: this.reportFilters.dateTo || undefined,
            product_ids: this.selectedProductIds.join(',') || undefined,
            search: this.appliedSearchQuery || undefined,
            supplier_query: this.appliedFilters.supplierQuery || undefined,
            category_query: this.appliedFilters.categoryQuery || undefined,
          },
        });
        const url = URL.createObjectURL(data);
        const link = document.createElement('a');
        link.href = url;
        link.download = this.currentUser?.company_language_code === 'en' ? 'Write-off report.xlsx' : 'Отчёт по списаниям.xlsx';
        link.click();
        URL.revokeObjectURL(url);
      } catch { alert(this.$t('Unable to download report. Please try again.')); }
    },
    onSearchInput: debounce(function () {
      this.page = 1;
      this.saveTableState();
      this.fetchStocks();
      this.fetchChartSummary();
    }, 300),
    fetchProductSuggestions: debounce(async function () {
      const query = this.searchQuery.trim();
      if (!query) {
        this.productSuggestions = [];
        return;
      }

      try {
        const { data } = await axios.get('/api/warehouse-stocks/', {
          params: {
            page: 1,
            page_size: 20,
            search: query,
            category_query: this.appliedFilters.categoryQuery || undefined,
            supplier_query: this.appliedFilters.supplierQuery || undefined,
            only_available: this.appliedFilters.onlyAvailable ? '1' : undefined,
          },
        });
        const rows = data.results || data;
        this.productSuggestions = rows.map(row => ({
          id: row.product.id,
          sku: row.product.sku,
          productName: row.product.name,
          name: row.product.sku
            ? `${row.product.sku} - ${row.product.name}`
            : row.product.name,
        }));
      } catch (error) {
        console.error(error);
        this.productSuggestions = [];
      }
    }, 250),
    onFiltersChanged() {
      this.page = 1;
      this.appliedFilters = { ...this.filters };
      this.saveTableState();
      this.fetchStocks();
      this.fetchChartSummary();
    },
    onReportFiltersChanged() {
      this.page = 1;
      this.saveTableState();
      this.fetchStocks();
      this.fetchChartSummary();
    },
    async fetchCategories() {
      const cached = getCachedJson(CATEGORY_CACHE_KEY);
      if (cached) {
        this.categories = cached;
        return;
      }

      const { data } = await axios.get('/api/product-category/');
      this.categories = data;
      setCachedJson(CATEGORY_CACHE_KEY, this.categories);
    },
    async fetchSuppliers() {
      const cached = getCachedJson(SUPPLIER_CACHE_KEY);
      if (cached) {
        this.suppliers = cached;
        return;
      }

      const { data } = await axios.get('/api/counterparties/options/', {
        params: { role: 'supplier' },
      });
      this.suppliers = data.results || data;
      setCachedJson(SUPPLIER_CACHE_KEY, this.suppliers);
    },
    async fetchUnits() {
      const cached = getCachedJson(UNIT_CACHE_KEY);
      if (cached) {
        this.units = cached;
        return;
      }
      try {
        const { data } = await axios.get('/api/units/');
        this.units = data.results || data;
        setCachedJson(UNIT_CACHE_KEY, this.units);
      } catch (error) {
        console.error(error);
      }
    },
    async fetchSystemSettings() {
      try {
        const { data } = await axios.get('/api/settings/');
        this.systemSettings = data[0] || null;
      } catch (error) {
        console.error(error);
      }
    },
    async fetchCurrentUser() {
      try {
        const { data } = await axios.get('/api/auth/me/');
        this.currentUser = data;
        setCurrentUser(data);
      } catch (error) {
        console.error(error);
      }
    },
    async fetchStocks({ useCache = false } = {}) {
      const requestId = ++this.stocksRequestId;
      const cacheKey = this.stocksCacheKey();
      const cached = getCachedTablePage(cacheKey, useCache);
      if (cached) {
        this.applyStocksResponse(cached);
      }

      this.isLoading = !cached;
      try {
        const { data } = await axios.get('/api/warehouse-stocks/', {
          params: this.stockQueryParams(),
        });
        if (requestId !== this.stocksRequestId) return;
        setCachedTablePage(cacheKey, data);
        this.applyStocksResponse(data);
      } catch (error) {
        if (requestId !== this.stocksRequestId) return;
        console.error(error);
        alert('Unable to load warehouse.');
      } finally {
        if (requestId === this.stocksRequestId) this.isLoading = false;
      }
    },
    resetFilters() {
      this.searchQuery = '';
      this.appliedSearchQuery = '';
      this.productSuggestions = [];
      this.filters = { categoryQuery: '', supplierQuery: '', onlyAvailable: false, stockControl: '' };
      this.appliedFilters = { categoryQuery: '', supplierQuery: '', onlyAvailable: false, stockControl: '' };
      this.reportFilters = { dateFrom: '', dateTo: '' };
      this.selectedProductIds = [];
      this.appliedProductIds = [];
      this.chartUnit = '';
      this.page = 1;
      this.saveTableState();
      this.fetchStocks();
      this.fetchChartSummary();
    },
    stockQueryParams() {
      return {
        page: this.page,
        page_size: this.pageSize,
        search: this.appliedSearchQuery || undefined,
        category_query: this.appliedFilters.categoryQuery || undefined,
        supplier_query: this.appliedFilters.supplierQuery || undefined,
        only_available: this.appliedFilters.onlyAvailable ? '1' : undefined,
        stock_control: this.appliedFilters.stockControl || undefined,
        date_from: this.reportFilters.dateFrom || undefined,
        date_to: this.reportFilters.dateTo || undefined,
      };
    },
    stocksCacheKey() {
      return makeTableCacheKey('warehouse-stocks', this.stockQueryParams());
    },
    applyStocksResponse(data) {
      applyPaginatedData(this, data, 'stocks');
    },
    async fetchChartSummary() {
      const requestId = ++this.chartRequestId;
      this.isChartLoading = true;
      try {
        const { data } = await axios.get('/api/warehouse-report/summary/', {
          params: this.chartQueryParams(),
        });
        if (requestId !== this.chartRequestId) return;
        this.chartSummary = data;
        if (this.chartMetric === 'quantity') {
          this.chartUnit = data.selected_unit || '';
        }
        this.selectionWarning = '';
      } catch (error) {
        if (requestId !== this.chartRequestId) return;
        console.error(error);
        this.chartSummary = { items: [], totals: {} };
        this.selectionWarning = error.response?.data?.detail || 'Unable to load warehouse analytics.';
      } finally {
        if (requestId === this.chartRequestId) this.isChartLoading = false;
      }
    },
    chartQueryParams() {
      return {
        date_from: this.reportFilters.dateFrom || undefined,
        date_to: this.reportFilters.dateTo || undefined,
        search: this.appliedSearchQuery || undefined,
        supplier_query: this.appliedFilters.supplierQuery || undefined,
        category_query: this.appliedFilters.categoryQuery || undefined,
        only_available: this.appliedFilters.onlyAvailable ? '1' : undefined,
        product_ids: this.appliedProductIds.length ? this.appliedProductIds.join(',') : undefined,
        metric: this.chartMetric,
        unit: this.chartMetric === 'quantity' && this.chartUnit ? this.chartUnit : undefined,
      };
    },
    saveTableState() {
      saveTableStateSnapshot(TABLE_STATE_KEY, this, ['appliedSearchQuery', 'appliedFilters', 'reportFilters', 'selectedProductIds', 'appliedProductIds', 'chartMetric', 'chartUnit']);
    },
    restoreTableState() {
      const state = restoreTableStateSnapshot(TABLE_STATE_KEY, {
        page: 1,
        searchQuery: '',
        appliedSearchQuery: '',
        filters: { categoryQuery: '', supplierQuery: '', onlyAvailable: false, stockControl: '' },
        appliedFilters: { categoryQuery: '', supplierQuery: '', onlyAvailable: false, stockControl: '' },
        reportFilters: { dateFrom: '', dateTo: '' },
        selectedProductIds: [],
        appliedProductIds: [],
        chartMetric: 'quantity',
        chartUnit: '',
      });
      this.page = state.page;
      this.searchQuery = state.searchQuery;
      this.appliedSearchQuery = state.appliedSearchQuery ?? state.searchQuery ?? '';
      this.filters = {
        categoryQuery: state.filters?.categoryQuery || '',
        supplierQuery: state.filters?.supplierQuery || '',
        onlyAvailable: Boolean(state.filters?.onlyAvailable),
        stockControl: state.filters?.stockControl || '',
      };
      this.appliedFilters = {
        categoryQuery: state.appliedFilters?.categoryQuery ?? this.filters.categoryQuery,
        supplierQuery: state.appliedFilters?.supplierQuery ?? this.filters.supplierQuery,
        onlyAvailable: state.appliedFilters?.onlyAvailable ?? this.filters.onlyAvailable,
        stockControl: state.appliedFilters?.stockControl ?? this.filters.stockControl,
      };
      this.reportFilters = {
        dateFrom: state.reportFilters?.dateFrom || '',
        dateTo: state.reportFilters?.dateTo || '',
      };
      this.selectedProductIds = Array.isArray(state.selectedProductIds)
        ? state.selectedProductIds.map(id => Number(id)).filter(Number.isFinite).slice(0, CHART_SELECTION_LIMIT)
        : [];
      this.appliedProductIds = Array.isArray(state.appliedProductIds)
        ? state.appliedProductIds.map(id => Number(id)).filter(Number.isFinite).slice(0, CHART_SELECTION_LIMIT)
        : [...this.selectedProductIds];
      const allowedMetrics = this.availableChartMetricOptions.map(option => option.value);
      this.chartMetric = allowedMetrics.includes(state.chartMetric) ? state.chartMetric : 'quantity';
      this.chartUnit = state.chartUnit || '';
    },
    changePage(page) {
      changeTablePage(this, page, 'fetchStocks');
    },
    applyProductSearch(option) {
      this.searchQuery = option?.name || this.searchQuery;
      this.appliedSearchQuery = option?.sku || option?.productName || this.searchQuery;
      this.productSuggestions = [];
      this.page = 1;
      this.saveTableState();
      this.fetchStocks();
      this.fetchChartSummary();
    },
    toggleVisibleProducts() {
      const selected = new Set(this.selectedProductIds);
      if (this.allVisibleSelected) {
        this.visibleProductIds.forEach(id => selected.delete(id));
      } else {
        for (const id of this.visibleProductIds) {
          if (selected.has(id)) continue;
          if (selected.size >= CHART_SELECTION_LIMIT) {
            this.selectionWarning = `You can select up to ${CHART_SELECTION_LIMIT} products for the chart.`;
            break;
          }
          selected.add(id);
        }
      }
      this.selectedProductIds = Array.from(selected);
      this.saveTableState();
    },
    toggleProductSelection(productId, event) {
      this.selectionWarning = '';
      if (event.target.checked) {
        if (
          !this.selectedProductIds.includes(productId) &&
          this.selectedProductIds.length >= CHART_SELECTION_LIMIT
        ) {
          event.target.checked = false;
          this.selectionWarning = `You can select up to ${CHART_SELECTION_LIMIT} products for the chart.`;
          return;
        }
        this.selectedProductIds = [...new Set([...this.selectedProductIds, productId])];
      } else {
        this.selectedProductIds = this.selectedProductIds.filter(id => id !== productId);
      }
      this.saveTableState();
    },
    applySelectedProducts() {
      this.appliedProductIds = [...this.selectedProductIds];
      this.selectionWarning = '';
      this.saveTableState();
      this.fetchChartSummary();
    },
    clearSelectedProducts() {
      this.selectedProductIds = [];
      this.appliedProductIds = [];
      this.selectionWarning = '';
      this.saveTableState();
      this.fetchChartSummary();
    },
    openWarehouseOperation(stock) {
      this.operationStock = stock;
      this.warehouseOperation = {
        action: Number(stock.quantity_defective) > 0 ? 'release_defect' : 'write_off_stock',
        quantity: '',
        reason: '',
        comment: '',
      };
      this.showWarehouseOperationModal = true;
    },
    closeWarehouseOperation() {
      if (this.isWarehouseOperationSaving) return;
      this.showWarehouseOperationModal = false;
      this.operationStock = null;
    },
    async saveWarehouseOperation() {
      const quantity = Number(this.warehouseOperation.quantity);
      if (!quantity || quantity <= 0) {
        alert(this.$t('Enter a positive quantity.'));
        return;
      }
      if (this.warehouseOperation.action === 'write_off_stock' && !this.warehouseOperation.reason) {
        alert(this.$t('Select a write-off reason.'));
        return;
      }
      this.isWarehouseOperationSaving = true;
      try {
        await axios.post(`/api/warehouse-stocks/${this.operationStock.id}/operation/`, this.warehouseOperation);
        clearCacheByPrefix('warehouse-stocks:');
        await Promise.all([this.fetchStocks(), this.fetchChartSummary(), this.fetchStockControl()]);
        this.showWarehouseOperationModal = false;
        this.operationStock = null;
      } catch (error) {
        console.error(error);
        alert(this.formatWarehouseOperationError(error));
      } finally {
        this.isWarehouseOperationSaving = false;
      }
    },
    formatWarehouseOperationError(error) {
      const data = error.response?.data;
      if (!data) return this.$t('Unable to save warehouse operation.');
      return Object.values(data).flat().join('\n');
    },
    setChartMetric(metric) {
      if (this.chartMetric === metric) return;
      this.chartMetric = metric;
      this.saveTableState();
      this.fetchChartSummary();
    },
    setChartUnit(unit) {
      if (this.chartMetric !== 'quantity' || this.chartUnit === unit) return;
      this.chartUnit = unit;
      this.saveTableState();
      this.fetchChartSummary();
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
      this.onReportFiltersChanged();
    },
    setCurrentMonth() {
      const today = new Date();
      const start = new Date(today.getFullYear(), today.getMonth(), 1);
      this.reportFilters.dateFrom = this.dateInputValue(start);
      this.reportFilters.dateTo = this.dateInputValue(today);
      this.onReportFiltersChanged();
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
            search: this.appliedSearchQuery || undefined,
            supplier_query: this.appliedFilters.supplierQuery || undefined,
            category_query: this.appliedFilters.categoryQuery || undefined,
            only_available: this.appliedFilters.onlyAvailable ? '1' : undefined,
            product_ids: this.selectedProductIds.length ? this.selectedProductIds.join(',') : undefined,
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
    async fetchStockControl(openModal = false) {
      this.isStockControlLoading = true;
      if (openModal) this.showStockControlModal = true;
      try {
        const { data } = await axios.get('/api/warehouse-stock-control/live/');
        this.stockControlSnapshot = data;
      } catch (error) {
        console.error(error);
        if (openModal) alert('Unable to load warehouse stock control.');
      } finally {
        this.isStockControlLoading = false;
      }
    },
    async openStockControl() {
      this.showStockControlModal = true;
      await this.fetchStockControl();
    },
    async downloadStockControl() {
      if (!this.stockControlSnapshot) return;
      this.isStockControlExporting = true;
      try {
        const response = await axios.get('/api/warehouse-stock-control/live/export/', { responseType: 'blob' });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.download = `stock_control_${this.stockControlSnapshot.schedule_date.replaceAll('-', '')}.xlsx`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      } catch (error) {
        console.error(error);
        alert('Unable to download warehouse stock control.');
      } finally {
        this.isStockControlExporting = false;
      }
    },
    async openProductEditor(productId) {
      if (this.isProductLoading) return;
      this.isProductLoading = true;
      try {
        const { data } = await axios.get(`/api/products/${productId}/`);
        this.editingProduct = data;
        this.showProductModal = true;
      } catch (error) {
        console.error(error);
        alert('Unable to load product.');
      } finally {
        this.isProductLoading = false;
      }
    },
    closeProductEditor() {
      this.showProductHistory = false;
      this.showProductModal = false;
      this.editingProduct = null;
    },
    async onWarehouseProductSaved(product) {
      this.editingProduct = product;
      clearCacheByPrefix('products:');
      clearCacheByPrefix('warehouse-stocks:');
      await Promise.all([
        this.fetchStocks(),
        this.fetchChartSummary(),
        this.fetchStockControl(),
      ]);
    },
    onProductReferenceCreated({ type, item }) {
      if (type === 'category') {
        this.categories.push(item);
        setCachedJson(CATEGORY_CACHE_KEY, this.categories);
      } else if (type === 'unit') {
        this.units.push(item);
        setCachedJson(UNIT_CACHE_KEY, this.units);
      } else if (type === 'supplier') {
        this.suppliers.push(item);
        setCachedJson(SUPPLIER_CACHE_KEY, this.suppliers);
      }
    },
    stockStatusClass(status) {
      return {
        out_of_stock: 'text-bg-danger',
        below_minimum: 'text-bg-danger',
        critical: 'text-bg-danger',
        requires_order: 'text-bg-warning',
        supply_expected: 'text-bg-info',
        no_forecast: 'text-bg-secondary',
        normal: 'text-bg-success',
      }[status] || 'text-bg-secondary';
    },
    forecastQualityClass(quality) {
      return {
        insufficient: 'text-bg-secondary',
        preliminary: 'text-bg-warning',
        sufficient: 'text-bg-success',
        manual: 'text-bg-primary',
      }[quality] || 'text-bg-secondary';
    },
    formatDateTime(value) {
      return value ? new Date(value).toLocaleString('ru-RU') : '—';
    },
    formatQty(value) {
      const numberValue = Number(String(value ?? 0).replace(',', '.'));
      return Number.isFinite(numberValue)
        ? numberValue.toLocaleString('ru-RU', { maximumFractionDigits: 2 })
        : '0';
    },
    formatOptionalQty(value) {
      return value === null || value === undefined || value === '' ? '—' : this.formatQty(value);
    },
    formatOptionalQtyWithUnit(value, unit) {
      const formatted = this.formatOptionalQty(value);
      return formatted === '—' ? formatted : `${formatted} ${unit || ''}`.trim();
    },
    consumptionDescription(item) {
      if (item.consumption_source === 'manual') return this.$t('Manual value');
      const labels = {
        insufficient: 'Insufficient history',
        preliminary: 'Preliminary automatic value',
        sufficient: 'Automatic value',
      };
      const days = item.consumption_observed_days
        ? ` · ${item.consumption_observed_days} ${this.$t('days')}`
        : '';
      return `${this.$t(labels[item.consumption_confidence] || 'Automatic')}${days}`;
    },
    selectionKey(ids) {
      return [...ids].map(id => Number(id)).filter(Number.isFinite).sort((a, b) => a - b).join(',');
    },
  },
};
</script>

<style scoped>
.warehouse-filters .btn {
  min-width: 72px;
}

.only-available-filter .form-check {
  align-items: center;
  display: flex;
  gap: 0.5rem;
  min-height: 38px;
  white-space: nowrap;
}

.reset-filter {
  min-width: 110px;
}

.only-available-filter .form-check-input {
  flex: 0 0 auto;
  margin: 0;
}

.report-date-field {
  width: 210px;
}

.selected-products-note {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
  color: #6c757d;
  font-size: 0.875rem;
}

.selected-clear-btn {
  line-height: 1.2;
}

.selection-warning {
  color: #842029;
  font-size: 0.875rem;
}

.warehouse-table .select-col {
  width: 44px;
}

.stock-operation-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  padding: 0;
  margin: 6px auto 0;
}

.warehouse-table .product-col {
  width: 34%;
}

.warehouse-product-row {
  cursor: pointer;
}

.warehouse-product-row:focus-visible {
  outline: 2px solid var(--bs-primary);
  outline-offset: -2px;
}

.warehouse-table .stock-metric-on-hand {
  background-color: #f1f3f5;
}

.warehouse-table .stock-metric-reserved {
  background-color: #fff3cd;
}

.warehouse-table .stock-metric-expected {
  background-color: #cff4fc;
}

.warehouse-table .stock-metric-available {
  background-color: #d1e7dd;
}

.stock-control-summary .summary-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #dee2e6;
  border-radius: 0.5rem;
  background: #f8f9fa;
}

.stock-control-summary .summary-card strong { font-size: 1.35rem; }
.stock-control-summary .summary-card span { color: #6c757d; font-size: 0.82rem; }
.stock-control-summary .summary-critical { border-color: #f1aeb5; background: #f8d7da; }
.stock-control-summary .summary-order { border-color: #ffe69c; background: #fff3cd; }
.stock-control-summary .summary-expected { border-color: #9eeaf9; background: #cff4fc; }
.stock-control-summary .summary-no-forecast { border-color: #c6c7c8; background: #e2e3e5; }
.stock-control-summary .summary-normal { border-color: #a3cfbb; background: #d1e7dd; }
.stock-control-table-wrap { max-height: 55vh; }
</style>
