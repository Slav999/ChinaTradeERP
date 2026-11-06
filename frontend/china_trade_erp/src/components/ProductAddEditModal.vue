<template>
  <!-- Add/Edit Product Modal -->
  <div
      class="modal fade edit-modal"
      :class="{ show: visible }"
      :style="visible ? 'display: block;' : ''"
      tabindex="-1"
  >
    <div class="modal-dialog modal-dialog-centered modal-lg">
      <transition name="modal-fade">
        <div class="modal-content" v-if="visible">
          <div class="modal-header">
            <h5 class="modal-title">{{ isEdit ? 'Edit Product' : 'Add Product' }}</h5>
            <button type="button" class="btn-close" @click="$emit('close')"></button>
          </div>
          <div class="modal-body">
            <div v-if="readOnly" class="alert alert-secondary py-2 mb-3">
              Archived product is read-only. Restore it before editing.
            </div>
            <div v-if="isEdit" class="audit-info mb-3 p-3 bg-light rounded border" style="cursor: pointer;"
                 @click="$emit('open-history')">
              <div class="row">
                <div class="col text-muted small">
                  <strong>Created At:</strong> {{ formatDate(form.created_at) }}
                </div>
                <div class="col text-muted small">
                  <strong>Updated At:</strong> {{ formatDate(form.updated_at) }}
                </div>
              </div>
              <div class="row mt-2">
                <div class="col text-muted small"><strong>Created By:</strong> {{ form.created_by || '—' }}</div>
                <div class="col text-muted small"><strong>Updated By:</strong> {{ form.updated_by || '—' }}</div>
              </div>
            </div>

            <form @submit.prevent="save">
              <div class="row gy-3">
                <div class="col-md-6">
                  <label class="form-label">Name</label>
                  <input v-model="form.name" type="text" class="form-control" :disabled="readOnly" required/>
                </div>
                <div class="col-md-6">
                  <label class="form-label">SKU</label>
                  <input v-model="form.sku" type="text" class="form-control" :disabled="readOnly" required/>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Category</label>
                  <div class="input-group">
                    <select v-model="form.category_id" class="form-select" :disabled="readOnly">
                      <option disabled value="">Select category...</option>
                      <option v-for="c in categories" :key="c.id" :value="c.id">{{ $t(c.name) }}</option>
                    </select>
                    <IconButton icon="plus-lg" variant="outline-primary" :title="$t('Create new item')" :disabled="readOnly" @click="toggleQuickAdd('category')" />
                  </div>
                  <div v-if="quickAdd.category" class="quick-add-row mt-2">
                    <input
                        v-model.trim="quickForms.category.name"
                        class="form-control form-control-sm"
                        placeholder="New category name"
                        @keydown.enter.prevent="createCategory"
                    />
                    <button type="button" class="btn btn-sm btn-primary" :disabled="isCreatingReference" @click="createCategory">
                      Add
                    </button>
                  </div>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Unit</label>
                  <div class="input-group">
                    <select v-model="form.unit_id" class="form-select" :disabled="readOnly">
                      <option disabled value="">Select unit...</option>
                      <option v-for="u in units" :key="u.id" :value="u.id">{{ $t(u.name) }}</option>
                    </select>
                    <IconButton icon="plus-lg" variant="outline-primary" :title="$t('Create new item')" :disabled="readOnly" @click="toggleQuickAdd('unit')" />
                  </div>
                  <div v-if="quickAdd.unit" class="quick-add-row mt-2">
                    <input
                        v-model.trim="quickForms.unit.name"
                        class="form-control form-control-sm"
                        placeholder="New unit name"
                        @keydown.enter.prevent="createUnit"
                    />
                    <button type="button" class="btn btn-sm btn-primary" :disabled="isCreatingReference" @click="createUnit">
                      Add
                    </button>
                  </div>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Supplier</label>
                  <div class="input-group">
                    <select v-model="form.supplier_id" class="form-select" :disabled="readOnly" required>
                      <option disabled value="">Select supplier...</option>
                      <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
                    </select>
                    <IconButton icon="plus-lg" variant="outline-primary" :title="$t('Create supplier')" :disabled="readOnly" @click="openSupplierModal" />
                  </div>
                </div>
                <div v-if="canViewPurchasePrice" class="col-md-6">
                  <label class="form-label">Purchase Price</label>
                  <div class="input-group">
                    <span class="input-group-text">{{ purchaseCurrencySymbol }}</span>
                    <input v-model.number="form.purchase_price" type="number" step="0.01" class="form-control" :disabled="readOnly || !canEditPurchasePrice"/>
                  </div>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Weight per unit, kg</label>
                  <input
                      v-model.number="form.weight_kg"
                      type="number"
                      step="0.001"
                      min="0"
                      class="form-control"
                      :disabled="readOnly"
                  />
                </div>
                <div class="col-md-6">
                  <label class="form-label d-block">Warehouse</label>
                  <div class="form-check form-switch product-switch">
                    <input
                        id="product-is-stock-item"
                        v-model="form.is_stock_item"
                        class="form-check-input"
                        type="checkbox"
                        :disabled="readOnly"
                    />
                    <label class="form-check-label" for="product-is-stock-item">
                      Warehouse item
                    </label>
                  </div>
                </div>
                <template v-if="form.is_stock_item">
                  <div class="col-md-4">
                    <label class="form-label">Minimum stock</label>
                    <div class="input-group">
                      <input
                          v-model="form.minimum_stock_level"
                          type="number"
                          step="0.01"
                          min="0"
                          class="form-control"
                          :disabled="readOnly"
                          placeholder="Not configured"
                      />
                      <span class="input-group-text">{{ selectedUnitName }}</span>
                    </div>
                    <div class="form-text">The quantity that should remain available in the warehouse.</div>
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Consumption calculation</label>
                    <select
                        v-model="form.consumption_calculation_mode"
                        class="form-select"
                        :disabled="readOnly"
                    >
                      <option value="automatic">Automatic from shipments</option>
                      <option value="manual">Manual</option>
                    </select>
                    <div class="form-text">Automatic mode uses the history period configured for the company.</div>
                  </div>
                  <div v-if="form.consumption_calculation_mode === 'manual'" class="col-md-4">
                    <label class="form-label">Average consumption per month</label>
                    <div class="input-group">
                      <input
                          v-model="form.average_monthly_consumption"
                          type="number"
                          step="0.01"
                          min="0"
                          class="form-control"
                          :disabled="readOnly"
                          placeholder="0"
                      />
                      <span class="input-group-text">{{ selectedUnitName }}</span>
                    </div>
                    <div class="form-text">Used to forecast the balance by the next delivery.</div>
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Purchase batch</label>
                    <div class="input-group">
                      <input
                          v-model="form.purchase_batch_size"
                          type="number"
                          step="0.01"
                          min="0.01"
                          class="form-control"
                          :disabled="readOnly"
                          placeholder="Not configured"
                      />
                      <span class="input-group-text">{{ selectedUnitName }}</span>
                    </div>
                    <div class="form-text">Roll, box, or supplier lot used to round the suggested order.</div>
                  </div>
                </template>
                <div v-if="canViewCostPrice" class="col-md-6">
                  <label class="form-label">{{ $t('Cost price') }}</label>
                  <div class="form-control-plaintext fw-semibold">
                    {{ saleCurrencySymbol || '' }} {{ form.cost_price || 0 }}
                  </div>
                  <div v-if="canViewCostBreakdown" class="form-text">{{ $t('Calculated from purchase price, exchange rates, logistics, internal costs and packaging.') }}</div>
                  <div v-if="canViewCostBreakdown && form.applied_markup_pct !== null && form.applied_markup_pct !== undefined" class="form-text">
                    {{ $t('Applied markup') }}: {{ formatPercent(form.applied_markup_pct) }}
                    ({{ form.applied_markup_source === 'category' ? $t('product category') : $t('company settings') }})
                  </div>
                </div>
                <div v-if="canViewSalePrice" class="col-md-6">
                  <label class="form-label">{{ $t('Sale Price') }}</label>
                  <div class="input-group sale-price-group">
                    <span class="input-group-text">{{ saleCurrencySymbol || '-' }}</span>
                    <input
                        v-model.number="form.sale_price"
                        type="number"
                        step="0.01"
                        min="0"
                        class="form-control sale-price-input"
                        :readonly="readOnly || !canEditSalePrice"
                    />
                  </div>
                  <div v-if="canEditSalePrice" class="form-text">{{ $t('Clear the price to calculate it automatically.') }}</div>
                  <div v-else class="form-text">{{ $t('Only a company administrator can change the sale price.') }}</div>
                </div>
                <div class="col-12">
                  <label class="form-label">Image</label>
                  <input type="file" class="form-control" :disabled="readOnly" @change="handleImageUpload"/>
                  <div v-if="imagePreview" class="mt-2 text-center">
                    <img :src="imagePreview" class="img-fluid" style="max-height: 200px;"/>
                  </div>
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer justify-content-end">
            <div v-if="initialProduct?.id" class="me-auto d-flex flex-wrap gap-2">
              <ChatShareButton type="product" :record-id="Number(initialProduct.id)" :title="initialProduct.name" @shared="$emit('close')" />
              <RelatedChatsButton type="product" :record-id="Number(initialProduct.id)" :title="initialProduct.name" @opened="$emit('close')" />
            </div>
            <button class="btn btn-secondary" @click="$emit('close')">Cancel</button>
            <button v-if="!readOnly" class="btn btn-primary" @click="save">{{ isEdit ? 'Save' : 'Create' }}</button>
          </div>
        </div>
      </transition>
    </div>
  </div>
  <div v-if="visible" class="modal-backdrop product-modal-backdrop"></div>

  <div
      class="modal fade supplier-modal"
      :class="{ show: supplierModalVisible }"
      :style="supplierModalVisible ? 'display: block;' : ''"
      tabindex="-1"
  >
    <div class="modal-dialog modal-dialog-centered modal-lg">
      <transition name="modal-fade">
        <div class="modal-content" v-if="supplierModalVisible">
          <div class="modal-header">
            <h5 class="modal-title">Add Counterparty</h5>
            <button type="button" class="btn-close" @click="closeSupplierModal"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="createSupplier">
              <div class="row gy-3">
                <div class="col-md-6">
                  <label class="form-label">Name</label>
                  <input v-model.trim="supplierForm.name" type="text" class="form-control" required/>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Region</label>
                  <select v-model="supplierForm.type" class="form-select">
                    <option value="china">Chinese</option>
                    <option value="local">Local</option>
                  </select>
                </div>
                <div class="col-12">
                  <label class="form-label">Roles</label>
                  <div class="d-flex flex-wrap gap-3">
                    <div class="form-check">
                      <input id="quickSupplierIsSupplier" v-model="supplierForm.is_supplier" class="form-check-input" type="checkbox"/>
                      <label class="form-check-label" for="quickSupplierIsSupplier">Supplier</label>
                    </div>
                    <div class="form-check">
                      <input id="quickSupplierIsCustomer" v-model="supplierForm.is_customer" class="form-check-input" type="checkbox"/>
                      <label class="form-check-label" for="quickSupplierIsCustomer">Customer</label>
                    </div>
                  </div>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Unique Code</label>
                  <input v-model.trim="supplierForm.unique_code" class="form-control"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Status</label>
                  <select v-model="supplierForm.status_id" class="form-select">
                    <option value="">No status</option>
                    <option v-for="status in counterpartyStatuses" :key="status.id" :value="status.id">
                      {{ status.display_name || status.name }}
                    </option>
                  </select>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Phone</label>
                  <input v-model.trim="supplierForm.phone" class="form-control"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Email</label>
                  <input v-model.trim="supplierForm.email" type="email" class="form-control"/>
                </div>
                <div class="col-12">
                  <label class="form-label">Address</label>
                  <input v-model.trim="supplierForm.address" class="form-control"/>
                </div>
                <div class="col-12">
                  <label class="form-label">Source</label>
                  <input v-model.trim="supplierForm.source" class="form-control"/>
                </div>
                <div class="col-12">
                  <label class="form-label">QR Code Image</label>
                  <input type="file" class="form-control" accept="image/*" @change="handleSupplierQrUpload"/>
                  <div v-if="supplierQrPreview" class="supplier-qr-preview-box mt-2">
                    <img :src="supplierQrPreview" class="supplier-qr-preview" alt="QR preview"/>
                  </div>
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="closeSupplierModal">Cancel</button>
            <button class="btn btn-primary" :disabled="isCreatingReference" @click="createSupplier">
              {{ isCreatingReference ? 'Creating...' : 'Create' }}
            </button>
          </div>
        </div>
      </transition>
    </div>
  </div>
  <div v-if="supplierModalVisible" class="modal-backdrop supplier-modal-backdrop"></div>
</template>

<script>
import axios from '../axios';
import IconButton from './IconButton.vue';
import ChatShareButton from './ChatShareButton.vue';
import RelatedChatsButton from './RelatedChatsButton.vue';

const emptySupplierForm = () => ({
  name: '',
  type: 'china',
  is_supplier: true,
  is_customer: false,
  unique_code: '',
  status_id: '',
  phone: '',
  email: '',
  address: '',
  source: '',
  qr_code_image: null,
});

export default {
  name: 'ProductAddEditModal',
  components: { IconButton, ChatShareButton, RelatedChatsButton },
  props: {
    visible: {type: Boolean, default: false},
    initialProduct: {type: Object, default: null},
    categories: Array,
    units: Array,
    suppliers: Array,
    purchaseCurrencySymbol: {type: String, default: '¥'},
    saleCurrencySymbol: {type: String, default: ''},
    readOnly: {type: Boolean, default: false},
    canViewPurchasePrice: {type: Boolean, default: false},
    canEditPurchasePrice: {type: Boolean, default: false},
    canViewCostPrice: {type: Boolean, default: false},
    canViewCostBreakdown: {type: Boolean, default: false},
    canViewSalePrice: {type: Boolean, default: false},
    canEditSalePrice: {type: Boolean, default: false},
  },
  data() {
    return {
      form: this.initialProduct ? this.normalizeProduct(this.initialProduct) : this.emptyForm(),
      imagePreview: this.initialProduct?.image || null,
      isCreatingReference: false,
      quickAdd: {
        category: false,
        unit: false,
      },
      quickForms: {
        category: { name: '' },
        unit: { name: '' },
      },
      supplierModalVisible: false,
      supplierForm: emptySupplierForm(),
      supplierQrPreview: null,
      counterpartyStatuses: [],
    };
  },
  methods: {
    toggleQuickAdd(type) {
      this.quickAdd[type] = !this.quickAdd[type];
    },
    async createCategory() {
      const name = this.quickForms.category.name.trim();
      if (!name) return;
      const item = await this.createReference('/api/product-category/', {name}, 'category');
      if (item) {
        this.form.category_id = item.id;
        this.quickForms.category.name = '';
        this.quickAdd.category = false;
      }
    },
    async createUnit() {
      const name = this.quickForms.unit.name.trim();
      if (!name) return;
      const item = await this.createReference('/api/units/', {name}, 'unit');
      if (item) {
        this.form.unit_id = item.id;
        this.quickForms.unit.name = '';
        this.quickAdd.unit = false;
      }
    },
    emptySupplierForm() {
      return emptySupplierForm();
    },
    async openSupplierModal() {
      this.supplierForm = this.emptySupplierForm();
      this.supplierQrPreview = null;
      this.supplierModalVisible = true;
      if (!this.counterpartyStatuses.length) {
        try {
          const {data} = await axios.get('/api/counterparty-statuses/');
          this.counterpartyStatuses = Array.isArray(data) ? data : data.results || [];
        } catch (error) {
          console.error(error);
        }
      }
    },
    closeSupplierModal() {
      this.supplierModalVisible = false;
    },
    handleSupplierQrUpload(e) {
      const file = e.target.files[0];
      if (!file) return;
      this.supplierForm.qr_code_image = file;
      this.supplierQrPreview = URL.createObjectURL(file);
    },
    async createSupplier() {
      const name = this.supplierForm.name.trim();
      if (!name) {
        alert('Please enter counterparty name');
        return;
      }
      if (!this.supplierForm.is_supplier && !this.supplierForm.is_customer) {
        alert('Select at least one role: supplier or customer.');
        return;
      }
      const payload = new FormData();
      Object.entries(this.supplierForm).forEach(([key, value]) => {
        if (value === null || value === undefined || value === '') return;
        payload.append(key, value);
      });
      const item = await this.createReference('/api/counterparties/', payload, 'supplier', {
        headers: {'Content-Type': 'multipart/form-data'},
      });
      if (item) {
        this.form.supplier_id = item.id;
        this.closeSupplierModal();
      }
    },
    async createReference(url, payload, type, config = undefined) {
      this.isCreatingReference = true;
      try {
        const {data} = await axios.post(url, payload, config);
        this.$emit('reference-created', {type, item: data});
        return data;
      } catch (error) {
        alert(this.formatApiError(error));
        return null;
      } finally {
        this.isCreatingReference = false;
      }
    },
    emptyForm() {
      return {
        name: '', sku: '', category_id: null, unit_id: null,
        supplier_id: null,
        purchase_price: 0, cost_price: 0, sale_price: 0,
        automatic_sale_price: 0, sale_price_mode: 'automatic',
        applied_markup_pct: null, applied_markup_source: 'company',
        is_stock_item: false,
        minimum_stock_level: '', average_monthly_consumption: '',
        consumption_calculation_mode: 'automatic', purchase_batch_size: '',
        units_per_package: 1, weight_kg: 0,
        length_m: 0, width_m: 0, height_m: 0,
        image: null,
        created_at: null, created_by: null,
        updated_at: null, updated_by: null,
      };
    },
    normalizeProduct(product) {
      return {
        ...this.emptyForm(),
        ...product,
        category_id: product.category_id || product.category?.id || null,
        unit_id: product.unit_id || product.unit?.id || null,
        supplier_id: product.supplier_id || product.supplier?.id || null,
        image: null,
      };
    },
    validateForm() {
      if (!this.form.name?.trim()) {
        alert('Please enter a product name');
        return false;
      }
      if (!this.form.sku?.trim()) {
        alert('Please enter SKU');
        return false;
      }
      if (!this.form.supplier_id) {
        alert('Please select a supplier');
        return false;
      }
      for (const field of ['minimum_stock_level', 'average_monthly_consumption', 'purchase_batch_size']) {
        const value = this.form[field];
        const minimum = field === 'purchase_batch_size' ? 0.01 : 0;
        if (value !== '' && value !== null && Number(value) < minimum) {
          alert('Warehouse control quantities must be valid positive values.');
          return false;
        }
      }
      const salePriceEmpty = this.form.sale_price === '' || this.form.sale_price === null;
      if (!salePriceEmpty && Number(this.form.sale_price) < 0) {
        alert(this.$t('Sale price cannot be negative.'));
        return false;
      }
      if (
        salePriceEmpty
        && (!this.form.weight_kg || Number(this.form.weight_kg) <= 0)
      ) {
        return confirm(this.$t('Weight per unit is empty. Cost and automatic sale price will remain zero. Continue?'));
      }
      return true;
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
    async save() {
      if (!this.validateForm()) return;
      const fd = new FormData();
      const salePriceEmpty = this.form.sale_price === '' || this.form.sale_price === null;
      const automaticPrice = Number(this.form.automatic_sale_price || 0);
      const enteredPrice = Number(this.form.sale_price || 0);
      const useAutomaticPrice = salePriceEmpty || (
        this.form.sale_price_mode === 'automatic' && enteredPrice === automaticPrice
      );
      Object.entries(this.form).forEach(([k, v]) => {
        if ([
          'id', 'category', 'unit', 'supplier',
          'is_archived', 'archived_at', 'archived_by',
          'created_at', 'created_by', 'updated_at', 'updated_by',
          'cost_price', 'automatic_sale_price',
          'applied_markup_pct', 'applied_markup_source',
        ].includes(k)) return;
        if (k === 'sale_price' || k === 'sale_price_mode') return;
        if (k === 'purchase_price' && !this.canEditPurchasePrice) return;
        if (v !== null && v !== undefined) fd.append(k, v);
      });
      if (this.canEditSalePrice) {
        fd.append('sale_price_mode', useAutomaticPrice ? 'automatic' : 'manual');
        if (!useAutomaticPrice) fd.append('sale_price', this.form.sale_price);
      }
      try {
        let res;
        const cfg = {headers: {'Content-Type': 'multipart/form-data'}};
        if (this.isEdit && this.form.id) {
          res = await axios.put(`/api/products/${this.form.id}/`, fd, cfg);
        } else {
          res = await axios.post('/api/products/', fd, cfg);
        }
        this.form = this.normalizeProduct(res.data);
        this.imagePreview = res.data.image || this.imagePreview;
        this.$emit('saved', res.data);
      } catch (e) {
        console.error(e);
        alert(this.formatApiError(e));
      }
    },
    handleImageUpload(e) {
      const file = e.target.files[0];
      if (file) {
        this.form.image = file;
        this.imagePreview = URL.createObjectURL(file);
      }
    },
    formatDate(val) {
      return val ? new Date(val).toLocaleString() : '—';
    },
    formatPercent(value) {
      const percent = Number(value) * 100;
      return Number.isFinite(percent) ? `${percent.toLocaleString(undefined, { maximumFractionDigits: 2 })}%` : '—';
    },
  },
  computed: {
    isEdit() {
      return Boolean(this.initialProduct && this.initialProduct.id);
    },
    selectedUnitName() {
      return this.units.find(unit => Number(unit.id) === Number(this.form.unit_id))?.name || 'unit';
    }
  },
  watch: {
    visible(value) {
      if (!value) return;
      this.form = this.initialProduct ? this.normalizeProduct(this.initialProduct) : this.emptyForm();
      this.imagePreview = this.initialProduct?.image || null;
      this.supplierModalVisible = false;
    },
    initialProduct(prod) {
      this.form = prod ? this.normalizeProduct(prod) : this.emptyForm();
      this.imagePreview = prod?.image || null;
    }
  }
};
</script>

<style scoped>
.product-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1050;
  background-color: #000;
  opacity: 0.5;
}
.supplier-modal {
  z-index: 1070;
}
.supplier-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1065;
  background-color: #000;
  opacity: 0.35;
}
.supplier-qr-preview-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 180px;
  height: 180px;
  margin-left: auto;
  margin-right: auto;
  padding: 10px;
  border: 1px solid #d8e0e7;
  border-radius: 8px;
  background: #fff;
}
.supplier-qr-preview {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.quick-add-row {
  display: flex;
  gap: 0.5rem;
}
.quick-add-row .form-control,
.quick-add-row .form-select {
  min-width: 0;
}
.quick-add-type {
  max-width: 110px;
}
.quick-add-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  padding-left: 0;
  padding-right: 0;
  font-size: 1.1rem;
  line-height: 1;
}
.sale-price-group .input-group-text,
.sale-price-input {
  background-color: #fff8e1;
  border-color: #f1d48a;
  color: #2f3f50;
  cursor: default;
}
.sale-price-input:not([readonly]) {
  cursor: text;
}
.sale-price-input:focus {
  background-color: #fff8e1;
  border-color: #f1d48a;
  box-shadow: 0 0 0 0.2rem rgba(241, 196, 93, 0.18);
}
.product-switch {
  min-height: 38px;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding-left: 2.5rem;
}
</style>
