<template>
  <div class="container mt-4">
    <h1 class="mb-4">Products</h1>

    <!-- Search & Filters -->
    <div class="row mb-3 g-2">
      <div class="col-md-4">
        <input
            v-model.trim="searchQuery"
            @input="onSearchInput"
            type="text"
            class="form-control"
            placeholder="Search by name or SKU..."
        />
      </div>
      <div class="col-md-3">
        <select v-model="filters.category" class="form-select">
          <option disabled selected hidden value="">Select category...</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div class="col-md-3">
        <input
            v-model.trim="filters.supplierQuery"
            @input="onSearchInput"
            list="suppliersList"
            class="form-control"
            placeholder="Filter by supplier..."
        />
        <datalist id="suppliersList">
          <option v-for="s in suppliers" :key="s.id" :value="s.name"></option>
        </datalist>
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
          <th>Name</th>
          <th>SKU</th>
          <th class="d-none d-md-table-cell">Category</th>
          <th class="d-none d-md-table-cell">Unit</th>
          <th class="d-none d-md-table-cell">Supplier</th>
          <th>Quantity</th>
          <th>Purchase / Sale Price</th>
          <th>Actions</th>
        </tr>
        </thead>
        <tbody>
        <tr
            v-for="p in filteredProducts"
            :key="p.id"
            @click="editProduct(p)"
            style="cursor: pointer;"
        >
          <td>{{ p.name }}</td>
          <td>{{ p.sku }}</td>
          <td class="d-none d-md-table-cell">{{ p.category?.name || '—' }}</td>
          <td class="d-none d-md-table-cell">{{ p.unit?.name || '—' }}</td>
          <td class="d-none d-md-table-cell">{{ p.supplier?.name || '—' }}</td>
          <td>{{ p.quantity }}</td>
          <td>{{ p.purchase_price }} / {{ p.sale_price }}</td>
          <td @click.stop>
            <button
                v-if="p.image"
                class="btn btn-sm btn-secondary me-1"
                @click.stop="showImage(p.image)"
            >Фото
            </button>
            <button
                class="btn btn-sm btn-danger"
                @click.stop="deleteProduct(p.id)"
            >Delete
            </button>
          </td>
        </tr>
        <tr v-if="!filteredProducts.length">
          <td colspan="8" class="text-center text-muted">No products found.</td>
        </tr>
        </tbody>
      </table>
    </div>

    <!-- Add/Edit Modal -->
    <div
        class="modal fade edit-modal"
        :class="{ show: showModal }"
        :style="showModal ? 'display: block;' : ''"
        tabindex="-1"
    >
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <transition name="modal-fade">
          <div class="modal-content" v-if="showEditContent">
            <div class="modal-header">
              <h5 class="modal-title">{{ isEdit ? 'Edit' : 'Add' }} Product</h5>
              <button type="button" class="btn-close" @click="closeModal"></button>
            </div>
            <div class="modal-body">
              <!-- Audit Info -->
              <div
                  v-if="isEdit"
                  class="audit-info mb-3 p-3 bg-light rounded border"
                  @click="openHistory"
                  style="cursor: pointer;"
              >
                <div class="row">
                  <div class="col text-muted small">
                    <strong>Created At:</strong> {{ formatDate(productForm.created_at) }}
                  </div>
                  <div class="col text-muted small">
                    <strong>Updated At:</strong> {{ formatDate(productForm.updated_at) }}
                  </div>
                </div>
                <div class="row mt-2">
                  <div class="col text-muted small">
                    <strong>Created By:</strong> {{ productForm.created_by || '—' }}
                  </div>
                  <div class="col text-muted small">
                    <strong>Updated By:</strong> {{ productForm.updated_by || '—' }}
                  </div>
                </div>
              </div>

              <form @submit.prevent="saveProduct">
                <div class="row gy-3">
                  <div class="col-md-6">
                    <label class="form-label">Name</label>
                    <input
                        v-model="productForm.name"
                        type="text"
                        class="form-control"
                        required
                    />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">SKU</label>
                    <input
                        v-model="productForm.sku"
                        type="text"
                        class="form-control"
                        required
                    />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Category</label>
                    <select v-model="productForm.category_id" class="form-select">
                      <option disabled value="">Select category...</option>
                      <option
                          v-for="c in categories"
                          :key="c.id"
                          :value="c.id"
                      >{{ c.name }}
                      </option>
                    </select>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Unit</label>
                    <select v-model="productForm.unit_id" class="form-select">
                      <option disabled value="">Select unit...</option>
                      <option
                          v-for="u in units"
                          :key="u.id"
                          :value="u.id"
                      >{{ u.name }}
                      </option>
                    </select>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Supplier</label>
                    <select
                        v-model="productForm.supplier_id"
                        class="form-select"
                    >
                      <option disabled value="">Select supplier...</option>
                      <option
                          v-for="s in suppliers"
                          :key="s.id"
                          :value="s.id"
                      >{{ s.name }}
                      </option>
                    </select>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Quantity</label>
                    <input
                        type="number"
                        min="0"
                        v-model.number="productForm.quantity"
                        class="form-control"
                    />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Purchase Price</label>
                    <input
                        type="number"
                        step="0.01"
                        v-model.number="productForm.purchase_price"
                        class="form-control"
                    />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Sale Price</label>
                    <input
                        type="number"
                        step="0.01"
                        v-model.number="productForm.sale_price"
                        class="form-control"
                    />
                  </div>
                  <div class="col-12">
                    <label class="form-label">Image</label>
                    <input
                        type="file"
                        class="form-control"
                        @change="handleImageUpload"
                    />
                    <div v-if="imagePreview" class="mt-2 text-center">
                      <img
                          :src="imagePreview"
                          class="img-fluid"
                          style="max-height: 200px;"
                      />
                    </div>
                  </div>
                </div>
              </form>
            </div>
            <div class="modal-footer justify-content-end">
              <button class="btn btn-secondary" @click="closeModal">Cancel</button>
              <button
                  v-if="isEdit"
                  class="btn btn-warning me-auto"
                  @click="openCalcModal"
              >
                Calculate Price
              </button>
              <button class="btn btn-primary" @click="saveProduct">
                {{ isEdit ? 'Save' : 'Create' }}
              </button>
            </div>
          </div>
        </transition>
      </div>
    </div>
    <div
        class="modal-backdrop fade edit-backdrop"
        :class="{ show: showModal }"
    ></div>

    <!-- History Modal -->
    <div
        class="modal fade history-modal"
        :class="{ show: showHistoryModal }"
        :style="showHistoryModal ? 'display: block;' : ''"
        tabindex="-1"
    >
      <div class="modal-dialog modal-dialog-scrollable modal-lg">
        <transition name="modal-fade">
          <div class="modal-content" v-if="showHistoryContent">
            <div class="modal-header">
              <h5 class="modal-title">Change History</h5>
              <button type="button" class="btn-close" @click="closeHistory"></button>
            </div>
            <div class="modal-body">
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
                  <td>{{ fieldLabel(log.field_name) }}</td>
                  <td>{{ formatValue(log.field_name, log.old_value) }}</td>
                  <td>{{ formatValue(log.field_name, log.new_value) }}</td>
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

    <!-- Calculate Price Modal -->
    <div
        class="modal fade calc-modal"
        :class="{ show: showCalcModal }"
        :style="showCalcModal ? 'display: block;' : ''"
        tabindex="-1"
    >
      <div class="modal-dialog modal-dialog-centered">
        <transition name="modal-fade">
          <div class="modal-content" v-if="showCalcModal">
            <div class="modal-header">
              <h5 class="modal-title">Calculate Price</h5>
              <button type="button" class="btn-close" @click="closeCalcModal"></button>
            </div>
            <div class="modal-body">
              <!-- Поля для расчёта -->
              <div class="mb-3">
                <label>Price (CNY)</label>
                <input v-model.number="calcForm.price_yuan" type="number" step="0.01" class="form-control"/>
              </div>
              <div class="mb-3">
                <label>Units per Package</label>
                <input v-model.number="calcForm.units_per_package" type="number" min="1" class="form-control"/>
              </div>
              <div class="mb-3">
                <label>Weight (kg)</label>
                <input v-model.number="calcForm.weight_kg" type="number" step="0.001" class="form-control"/>
              </div>
              <div class="row">
                <div class="col-4 mb-3">
                  <label>Length (m)</label>
                  <input v-model.number="calcForm.length_m" type="number" step="0.001" class="form-control"/>
                </div>
                <div class="col-4 mb-3">
                  <label>Width (m)</label>
                  <input v-model.number="calcForm.width_m" type="number" step="0.001" class="form-control"/>
                </div>
                <div class="col-4 mb-3">
                  <label>Height (m)</label>
                  <input v-model.number="calcForm.height_m" type="number" step="0.001" class="form-control"/>
                </div>
              </div>

              <!-- Результат -->
              <div v-if="calcResult !== null" class="alert alert-info">
                Calculated Sale Price: {{ calcResult }}
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" @click="closeCalcModal">Back</button>
              <button class="btn btn-success" @click="doCalculate">Calculate</button>
            </div>
          </div>
        </transition>
      </div>
    </div>
    <div class="modal-backdrop fade" :class="{ show: showCalcModal }"></div>


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

export default {
  name: 'ProductView',
  data() {
    return {
      products: [],
      categories: [],
      units: [],
      suppliers: [],
      searchQuery: '',
      filters: {category: '', supplierQuery: ''},
      showModal: false,
      showEditContent: true,
      isEdit: false,
      showHistoryContent: true,
      showHistoryModal: false,
      historyLogs: [],
      imageModalUrl: null,
      imagePreview: null,
      defaultForm: {},
      productForm: {
        id: null,
        name: '',
        sku: '',
        category_id: null,
        unit_id: null,
        supplier_id: null,
        quantity: 0,
        purchase_price: 0,
        sale_price: 0,
        image: null,
        created_at: null,
        created_by: null,
        updated_at: null,
        updated_by: null,
      },
      systemSettings: null,
      showCalcModal: false,
      calcForm: {
        price_yuan: 0,
        units_per_package: 1,
        weight_kg: 0,
        length_m: 0,
        width_m: 0,
        height_m: 0,
      },
      calcResult: null,
    };
  },
  created() {
    this.defaultForm = {...this.productForm};
    this.fetchAll();
  },
  computed: {
    filteredProducts() {
      const q = this.searchQuery.trim().toLowerCase();
      return this.products.filter(p => {
        const text = `${p.name} ${p.sku}`.toLowerCase();
        const matchQuery = !q || text.includes(q);
        const matchCat = !this.filters.category || p.category?.id === +this.filters.category;
        const matchSup = !this.filters.supplierQuery || (p.supplier?.name || '').toLowerCase().includes(this.filters.supplierQuery.trim().toLowerCase());
        return matchQuery && matchCat && matchSup;
      });
    },
  },
  methods: {
    onSearchInput: debounce(function () {
    }, 300),
    async fetchAll() {
      await Promise.all([
        this.fetchProducts(),
        this.fetchCategories(),
        this.fetchUnits(),
        this.fetchSuppliers(),
        this.fetchSettings()
      ]);
    },
    async fetchSettings() {
      const res = await axios.get('/api/settings/');
      this.systemSettings = res.data[0] || null;
    },
    async fetchProducts() {
      const res = await axios.get('/api/products/');
      this.products = res.data;
    },
    async fetchCategories() {
      const res = await axios.get('/api/product-category/');
      this.categories = res.data;
    },
    async fetchUnits() {
      const res = await axios.get('/api/units/');
      this.units = res.data;
    },
    async fetchSuppliers() {
      const res = await axios.get('/api/counterparties/');
      this.suppliers = res.data;
    },
    resetFilters() {
      this.searchQuery = '';
      this.filters = {category: '', supplierQuery: ''};
    },
    openModal() {
      this.productForm = {...this.defaultForm};
      this.isEdit = false;
      this.showModal = true;
      this.imagePreview = null;
    },
    closeModal() {
      this.showModal = false;
    },
    editProduct(item) {
      this.productForm = {
        id: item.id,
        name: item.name,
        sku: item.sku,
        category_id: item.category?.id || null,
        unit_id: item.unit?.id || null,
        supplier_id: item.supplier?.id || null,
        quantity: item.quantity,
        purchase_price: item.purchase_price,
        sale_price: item.sale_price,
        image: null,
        created_at: item.created_at,
        created_by: item.created_by,
        updated_at: item.updated_at,
        updated_by: item.updated_by,
      };
      this.isEdit = true;
      this.showModal = true;
      this.imagePreview = item.image || null;
    },
    async saveProduct() {
      try {
        const formData = new FormData();
        Object.entries(this.productForm).forEach(([k, v]) => {
          if (v !== null && v !== undefined) formData.append(k, v);
        });
        const cfg = {headers: {'Content-Type': 'multipart/form-data'}};
        let res;
        if (this.isEdit && this.productForm.id) {
          res = await axios.put(`/api/products/${this.productForm.id}/`, formData, cfg);
          const idx = this.products.findIndex(x => x.id === this.productForm.id);
          if (idx !== -1) this.products.splice(idx, 1, res.data);
        } else {
          res = await axios.post('/api/products/', formData, cfg);
          this.products.unshift(res.data);
        }
        this.closeModal();
      } catch (err) {
        console.error('Save error:', err.response?.data || err);
      }
    },
    async deleteProduct(id) {
      if (confirm('Delete this product?')) {
        await axios.delete(`/api/products/${id}/`);
        this.products = this.products.filter(x => x.id !== id);
      }
    },
    handleImageUpload(ev) {
      const f = ev.target.files[0];
      if (f) {
        this.productForm.image = f;
        this.imagePreview = URL.createObjectURL(f);
      }
    },
    openHistory() {
      if (!this.isEdit) return;
      this.showEditContent = false;
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
      this.showEditContent = true;
    },
    fieldLabel(key) {
      const map = {
        name: 'Name',
        sku: 'SKU',
        description: 'Description',
        category_id: 'Category',
        unit_id: 'Unit',
        supplier_id: 'Supplier',
        quantity: 'Quantity',
        purchase_price: 'Purchase Price',
        sale_price: 'Sale Price',
        image: 'Image',
      };
      return map[key] || key;
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
    openCalcModal() {
      Object.assign(this.calcForm, {
        price_yuan: this.productForm.purchase_price ?? 0,
        units_per_package: this.productForm.units_per_package ?? 1,
        weight_kg: this.productForm.weight_kg ?? 0,
        length_m: this.productForm.length_m ?? 0,
        width_m: this.productForm.width_m ?? 0,
        height_m: this.productForm.height_m ?? 0,
      });
      this.calcResult = null;
      this.showEditContent = false;
      this.showCalcModal = true;
    },

    closeCalcModal() {
      this.showCalcModal = false;
      this.showEditContent = true;
    },
    toNum(x) {
      return parseFloat(String(x).replace(',', '.')) || 0;
    },

    async doCalculate() {
      const s = this.systemSettings;
      if (!s) return alert('Settings not loaded');

      // 1) Парсим все настройки
      const rateCNY = this.toNum(s.cny_to_local_rate);
      const rateUSD = this.toNum(s.usd_to_local_rate);
      const costPerKg = this.toNum(s.logistics_cost_per_kg_usd);

      const marginPct = this.toNum(s.margin_pct);
      const discountPct = this.toNum(s.discount_pct);
      const taxPct = this.toNum(s.retail_tax_pct);
      const acqPct = this.toNum(s.acquiring_pct);
      const packPct = this.toNum(s.packaging_pct);

      // 2) Входные поля
      const pp = Number(this.productForm.purchase_price);
      const up = Number(this.calcForm.units_per_package);
      const w = Number(this.calcForm.weight_kg);

      console.group('🔍 Price calc debug');
      console.log({
        pp, up, w, rateCNY, rateUSD, costPerKg,
        marginPct, discountPct, taxPct, acqPct, packPct
      });

      // 3) unit_cost_local
      const unit_cost_local = pp * rateCNY;
      console.log('1) unit_cost_local =', unit_cost_local);

      // 4) package_cost_local
      const package_cost_local = unit_cost_local * up;
      console.log('2) package_cost_local =', package_cost_local);

      // 5) box_weight
      const box_weight = w * up;
      console.log('3) box_weight =', box_weight);

      // 6) logistics
      const logistics_usd = box_weight * costPerKg;
      const logistics_local = logistics_usd * rateUSD;
      console.log('4) logistics_usd =', logistics_usd,
          '→ logistics_local =', logistics_local);

      // 7) total_package_cost
      const total_package_cost = package_cost_local + logistics_local;
      console.log('5) total_package_cost =', total_package_cost);

      // 8) cost_per_unit
      const cost_per_unit = total_package_cost / up;
      console.log('6) cost_per_unit =', cost_per_unit);

      // 9) margin & discount
      const with_margin = cost_per_unit * (1 + marginPct);
      const after_discount = with_margin * (1 - discountPct);
      console.log('7) with_margin =', with_margin,
          '→ after_discount =', after_discount);

      // 10) fees
      const tax_fee = after_discount * taxPct;
      const acq_fee = after_discount * acqPct;
      const pack_fee = after_discount * packPct;
      console.log('8) tax, acq, pack =', tax_fee, acq_fee, pack_fee);

      // 11) finalPrice
      const finalPrice = after_discount + tax_fee + acq_fee + pack_fee;
      console.log('9) finalPrice =', finalPrice);
      console.groupEnd();

      // выводим и сохраняем
      this.calcResult = parseFloat(finalPrice.toFixed(2));
      try {
        const {data} = await axios.patch(
            `/api/products/${this.productForm.id}/`,
            {sale_price: this.calcResult}
        );
        // обновляем локально
        const idx = this.products.findIndex(p => p.id === data.id);
        if (idx !== -1) this.products.splice(idx, 1, data);
        this.productForm.sale_price = data.sale_price;
      } catch (e) {
        console.error('Save error:', e.response?.data || e);
        alert(JSON.stringify(e.response?.data, null, 2));
      }
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

.table td, .table th {
  vertical-align: middle;
}
</style>
