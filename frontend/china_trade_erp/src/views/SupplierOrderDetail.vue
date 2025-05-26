<template>
  <div class="container mt-4">
    <!-- Заголовок + «Назад» -->
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h1>{{ isEdit ? 'Edit Order' : 'New Order' }}</h1>
      <div>
        <button type="button" class="btn btn-success me-2" :disabled="isSaving" @click="saveOrder">
          {{ isSaving ? 'Saving...' : (isEdit ? 'Update Order' : 'Create Order') }}
        </button>
        <button class="btn btn-secondary" @click="goBack">← Back to Orders</button>
      </div>
    </div>

    <!-- Табы -->
    <ul class="nav nav-tabs mb-3">
      <li class="nav-item">
        <button
            class="nav-link"
            :class="{ active: activeTab==='order' }"
            @click="activeTab = 'order'"
        >Order
        </button>
      </li>
      <li class="nav-item">
        <button
            class="nav-link"
            :class="{ active: activeTab==='positions' }"
            @click="activeTab = 'positions'"
        >Positions
        </button>
      </li>
      <li class="nav-item">
        <button
            class="nav-link"
            :class="{ active: activeTab==='docs' }"
            @click="activeTab = 'docs'"
        >Related documents
        </button>
      </li>
      <li class="nav-item">
        <button
            class="nav-link"
            :class="{ active: activeTab==='files' }"
            @click="activeTab = 'files'"
        >Files
        </button>
      </li>
    </ul>

    <!-- Форма (показывается, пока не открыта история) -->
    <transition name="fade">
      <div v-if="activeTab==='order'">
        <!-- ▼ AUDIT-BLOCK (клик — открываем историю) ▼ -->
        <div
            v-if="isEdit"
            class="audit-info mb-3 p-3 bg-light rounded border"
            @click="openHistory"
            style="cursor:pointer"
        >
          <div class="row">
            <div class="col text-muted small">
              <strong>Created At:</strong> {{ formatDate(orderForm.created_at) }}
            </div>
            <div class="col text-muted small">
              <strong>Updated At:</strong> {{ formatDate(orderForm.updated_at) }}
            </div>
          </div>
          <div class="row mt-2">
            <div class="col text-muted small">
              <strong>Created By:</strong> {{ orderForm.created_by || '—' }}
            </div>
            <div class="col text-muted small">
              <strong>Updated By:</strong> {{ orderForm.updated_by || '—' }}
            </div>
          </div>
        </div>
        <!-- ▲ AUDIT-BLOCK ▲ -->

        <!-- ▼ ФОРМА ЗАКАЗА (полностью из исходного файла) ▼ -->
        <form @submit.prevent="saveOrder">
          <div class="row gx-2 gy-2">
            <div class="row gx-2 gy-2">
              <div class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Order Number</label>
                <input v-model="orderForm.order_number" class="form-control form-control-sm" required/>
              </div>
              <div class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Status</label>
                <select v-model="orderForm.status_id" class="form-select form-select-sm">
                  <option disabled value="">Select status...</option>
                  <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.name }}</option>
                </select>
              </div>
              <div class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Supplier</label>
                <select v-model="orderForm.supplier_id" class="form-select form-select-sm">
                  <option disabled value="">Select supplier...</option>
                  <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
                </select>
              </div>
              <div class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Customer</label>
                <select v-model="orderForm.customer_id" class="form-select form-select-sm">
                  <option disabled value="">Select customer...</option>
                  <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label small">Plan Receipt</label>
                <input v-model="orderForm.planned_receipt_date" type="date" class="form-control form-control-sm"/>
              </div>
              <div class="col-md-4">
                <label class="form-label small">Shipment</label>
                <input v-model="orderForm.shipment_date" type="date" class="form-control form-control-sm"/>
              </div>
              <div class="col-md-4">
                <label class="form-label small">Delivery</label>
                <input v-model="orderForm.delivery_date" type="date" class="form-control form-control-sm"/>
              </div>
              <div class="col-12">
                <label class="form-label small">Shipping Address</label>
                <textarea v-model="orderForm.shipping_address" class="form-control form-control-sm" rows="2"></textarea>
              </div>
              <div class="col-12">
                <label class="form-label small">Supplier Comment</label>
                <textarea v-model="orderForm.supplier_comment" class="form-control form-control-sm" rows="2"></textarea>
              </div>
              <div class="col-md-4">
                <label class="form-label small">Amount CNY</label>
                <input v-model="orderForm.amount_cny" type="number" step="0.01" class="form-control form-control-sm"/>
              </div>
              <div class="col-md-4">
                <label class="form-label small">Track Number</label>
                <input v-model="orderForm.track_number" class="form-control form-control-sm"/>
              </div>
              <div class="col-md-4">
                <label class="form-label small">China Exit Date</label>
                <input v-model="orderForm.china_exit_date" type="date" class="form-control form-control-sm"/>
              </div>
              <div class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Logistic Invoice#</label>
                <input v-model="orderForm.logistic_invoice_no" class="form-control form-control-sm"/>
              </div>
              <div class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Production Due</label>
                <input v-model="orderForm.production_due_date" type="date" class="form-control form-control-sm"/>
              </div>
              <div class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Payment Date</label>
                <input v-model="orderForm.payment_date" type="date" class="form-control form-control-sm"/>
              </div>

              <div class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Shipping Code</label>
                <input v-model="orderForm.shipping_code" class="form-control form-control-sm"/>
              </div>

              <div class="col-6">
                <label class="form-label small">Payment QR</label>
                <div v-if="orderForm.payment_details_qr || qrPreview" class="mt-2 text-center">
                  <img
                      :src="qrPreview || orderForm.payment_details_qr"
                      class="img-fluid"
                      style="max-height:150px;"
                      alt="Payment QR"
                  />
                </div>
                <div v-else class="text-muted">—</div>
              </div>
            </div>
          </div>
        </form>
        <!-- ▲ ФОРМА ▲ -->
      </div>
    </transition>
    <transition>
      <div v-if="activeTab==='files'">
        <div class="col-12">
          <label class="form-label small">Attachments</label>
          <input
              type="file"
              multiple
              class="form-control form-control-sm"
              @change="e => attachments = Array.from(e.target.files)"
          />
          <ul class="mt-2 attachment-list">
            <li v-for="att in existingAttachments" :key="att.id" class="d-flex align-items-center">
              <a
                  :href="att.file"
                  target="_blank"
                  class="flex-grow-1 text-truncate"
              >
                {{ att.file.split('/').pop() }}
              </a>
              <button
                  class="btn btn-sm btn-outline-danger ms-2"
                  @click="deleteAttachment(att.id)"
                  title="Delete"
              >&times;
              </button>
            </li>
          </ul>
        </div>
      </div>
    </transition>
    <transition>
      <div v-if="activeTab==='positions'">
        <!-- 1) поиск -->
        <div class="position-search position-relative mb-3">
          <input
              v-model="positionSearch"
              @input="fetchProductSuggestions"
              type="text"
              class="form-control form-control-sm"
              placeholder="Найти товар по имени или SKU..."
          />
          <ul
              v-if="positionSearch.length >= 2"
              class="list-group position-absolute w-100"
              style="z-index:1000"
          >
            <li
                v-for="p in productSuggestions"
                :key="p.id"
                class="list-group-item list-group-item-action p-1"
                @click="addPosition(p)"
            >
              {{ p.name }} ({{ p.sku }}) — {{ p.unit?.name || '—' }}
            </li>
            <li
                v-if="!productSuggestions.length"
                class="list-group-item list-group-item-action text-primary p-1"
                @click="openProductModalWithName"
            >
              + Создать новый товар: «{{ positionSearch }}»
            </li>
          </ul>
        </div>

        <!-- 2) существующие позиции -->
        <table class="table table-sm mb-2">
          <thead>
          <tr>
            <th>Product</th>
            <th>Unit</th>
            <th>Qty</th>
            <th></th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="item in orderItems" :key="item.id" >
            <td @click="openProductModalForEdit(item.product)"
              style="cursor:pointer; color:blue;">{{ item.product.name }}</td>
            <td>{{ item.product.unit?.name || '—' }}</td>
            <td>
              <input
                  type="number"
                  step="0.01"
                  class="form-control form-control-sm"
                  v-model.number="item.quantity"
                  @change="updatePosition(item)"
              />
            </td>
            <td>
              <button class="btn btn-sm btn-outline-danger"
                      @click="removeItem(item.id)">×
              </button>
            </td>
          </tr>
          <tr v-if="!orderItems.length">
            <td colspan="4" class="text-center text-muted">No positions yet.</td>
          </tr>
          </tbody>
        </table>
      </div>
    </transition>

    <!-- ▼ HISTORY-MODAL (не тронут) ▼ -->
    <div
        class="modal fade"
        tabindex="-1"
        :class="{ show: showHistoryModal }"
        v-show="showHistoryModal"
        style="display: block;"
    >
      <div class="modal-dialog modal-dialog-scrollable modal-lg">
        <transition name="modal-fade">
          <div class="modal-content">
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
    <!-- ▲ HISTORY-MODAL ▲ -->

    <ProductAddEditModal
        :visible="showProductModal"
        :initial-product="editingProduct"
        :categories="categories"
        :units="units"
        :suppliers="suppliers"
        @saved="onProductSaved"
        @close="showProductModal = false"
    />

    <!-- ▼ QR-MODAL ▼ -->
    <div class="modal-dialog modal-dialog-centered modal-lg">
      <transition name="modal-fade">
        <div class="modal-content" v-if="showQrContent && qrModalUrl">
          <div class="modal-header">
            <h6 class="modal-title">QR Code</h6>
            <button type="button" class="btn-close" @click="qrModalUrl = null"></button>
          </div>
          <div class="modal-body text-center">
            <img :src="qrModalUrl" class="img-fluid" style="max-height: 80vh;" alt="QR code"/>
          </div>
        </div>
      </transition>
    </div>
  </div>
  <!-- ▲ QR-MODAL ▲ -->
</template>


<script>
import axios from '../axios';
import ProductAddEditModal from "../components/ProductAddEditModal.vue";

export default {
  name: 'SupplierOrderDetail',
  components: {ProductAddEditModal},
  data() {
    return {
      activeTab: 'order',
      showProductModal: false,
      editingProduct: null,
      orderItems: [],
      positionSearch: '',
      productSuggestions: [],
      /* вложения */
      attachments: [],
      existingAttachments: [],

      /* справочники */
      suppliers: [],
      categories: [],
      units: [],
      customers: [],
      statuses: [],

      /* форма */
      defaultForm: {
        order_number: '', status_id: '', supplier_id: '', customer_id: '',
        planned_receipt_date: '', shipment_date: '', delivery_date: '',
        china_exit_date: '', shipping_address: '', shipping_code: '',
        supplier_comment: '', amount_cny: '', track_number: '',
        logistic_invoice_no: '', production_due_date: '',
        payment_date: '', payment_details_qr: null
      },
      orderForm: {},

      /* UI-состояния */
      isSaving: false,
      qrPreview: null,           /* превью только что загруженного QR */
      qrModalUrl: null,
      showQrContent: true,
      historyLogs: [],
      showHistoryModal: false,
      showHistoryContent: false,
      showEditContent: true,

      /* текущее id */
      selectedId: null,
    };
  },

  computed: {
    isEdit() {
      return !!this.selectedId;
    }
  },

  created() {
    this.selectedId = this.$route.params.id ? +this.$route.params.id : null;
    this.resetForm();
    this.fetchAux().then(() => {
      if (this.isEdit) this.fetchOrder()
      this.fetchOrderItems();
    });
  },

  watch: {
    '$route.params.id'(val) {
      this.selectedId = val ? +val : null;
      this.resetForm();
      if (this.isEdit) this.fetchOrder();
    }
  },

  methods: {
    openProductModalForEdit(product) {
      this.editingProduct = product;
      this.showProductModal = true;
    },
    openProductModalWithName() {
      this.editingProduct = {name: this.positionSearch};
      this.showProductModal = true;
    },
    // 1) подсказки
    async fetchProductSuggestions() {
      if (this.positionSearch.length < 2) {
        this.productSuggestions = []
        return
      }
      const {data} = await axios.get('/api/products/', {
        params: {search: this.positionSearch}
      })
      this.productSuggestions = data
    },

    // 2) добавить позицию
    async addPosition(product) {
      await axios.post('/api/supplier-order-items/', {
        order: this.selectedId,
        product_id: product.id,
        quantity: 1
      })
      this.positionSearch = ''
      this.productSuggestions = []
      await this.fetchOrderItems()
    },

    // 3) удалить
    async removeItem(itemId) {
      await axios.delete(`/api/supplier-order-items/${itemId}/`)
      await this.fetchOrderItems()
    },

    // 4) загрузить список
    async fetchOrderItems() {
      if (!this.selectedId) return;
      const {data} = await axios.get('/api/supplier-order-items/', {
        params: {order: this.selectedId}
      })
      this.orderItems = data
    },

    // 5) менять количество «на лету»
    async updatePosition(item) {
      await axios.patch(`/api/supplier-order-items/${item.id}/`, {
        quantity: item.quantity
      })
      // либо перезагрузка:
      await this.fetchOrderItems()
    },
    async onProductSaved(product) {
      this.showProductModal = false;
      await axios.post('/api/supplier-order-items/', {
        order: this.selectedId,
        product_id: product.id,
        quantity: 1,                // можете читать из какого-то поля, если нужно
      });

      // и обновляем список позиций
      await this.fetchOrderItems();
    },
    /* --- навигация --- */
    goBack() {
      const query = this.selectedId ? {highlight: this.selectedId} : {};
      this.$router.push({path: '/supplier-orders', query});
    },

    /* --- util --- */
    resetForm() {
      this.orderForm = {...this.defaultForm};
    },
    formatDate(v) {
      return v ? new Date(v).toLocaleString() : '—';
    },

    /* --- справочники --- */
    async fetchAux() {
      try {
        const [
          cpRes,
          stRes,
          catRes,
          unitRes
        ] = await Promise.all([
          axios.get('/api/counterparties/'),
          axios.get('/api/supplier-order-statuses/'),
          axios.get('/api/product-category/'),
          axios.get('/api/units/'),
        ]);

        this.suppliers = cpRes.data;
        this.customers = cpRes.data;
        this.statuses = stRes.data;
        this.categories = catRes.data;
        this.units = unitRes.data;
      } catch (e) {
        console.error(e);
        alert('Ошибка при загрузке справочников');
      }
    },

    /* --- загрузка/сохранение заказа --- */
    async fetchOrder() {
      try {
        const r = await axios.get(`/api/supplier-order/${this.selectedId}/`);
        const o = r.data;
        this.orderForm = {
          ...this.defaultForm, ...o,
          status_id: o.status?.id, supplier_id: o.supplier?.id, customer_id: o.customer?.id
        };
        this.existingAttachments = o.attachments || [];
        this.qrPreview = o.payment_details_qr;
      } catch (e) {
        console.error(e);
        alert('Не удалось загрузить заказ');
      }
    },

    async saveOrder() {
      this.isSaving = true;
      try {
        /* 1. собираем form-data */
        const fd = new FormData();
        const allowed = [
          'status_id', 'supplier_id', 'customer_id',
          'planned_receipt_date', 'shipment_date', 'china_exit_date', 'delivery_date',
          'shipping_address', 'shipping_code', 'supplier_comment', 'amount_cny',
          'track_number', 'logistic_invoice_no', 'production_due_date', 'payment_date', 'order_number',
        ];
        allowed.forEach(k => {
          const v = this.orderForm[k];
          if (v != null && v !== '') fd.append(k, v);
        });

        /* QR */
        if (this.orderForm.payment_details_qr instanceof File)
          fd.append('payment_details_qr', this.orderForm.payment_details_qr);

        /* новые вложения */
        this.attachments.forEach(f => fd.append('attachments', f));

        const cfg = {headers: {'Content-Type': 'multipart/form-data'}};
        let res;

        if (this.isEdit) {
          /* PATCH */
          res = await axios.patch(`/api/supplier-order/${this.selectedId}/`, fd, cfg);
          this.orderForm = {...this.orderForm, ...res.data};
          alert('Заказ сохранён');
        } else {
          /* POST → переводим страницу в режим редактирования созданного заказа */
          res = await axios.post('/api/supplier-order/', fd, cfg);
          alert('Заказ создан');
          this.$router.replace(`/supplier-orders/${res.data.id}`);
          return;                /* компонент перезагрузится watcher-ом */
        }

        /* очищаем буферы */
        this.attachments = [];

      } catch (e) {
        console.error('Save error', e.response?.data || e);
        alert('Ошибка при сохранении. Проверьте поля.');
      } finally {
        this.isSaving = false;
      }
    },

    /* --- вложения --- */
    async deleteAttachment(id) {
      if (!confirm('Удалить этот файл?')) return;
      try {
        await axios.delete(`/api/supplier-order/${this.selectedId}/attachments/${id}/`);
        this.existingAttachments = this.existingAttachments.filter(a => a.id !== id);
      } catch (e) {
        console.error(e);
        alert('Не удалось удалить файл');
      }
    },

    /* --- история изменений --- */
    async openHistory() {
      if (!this.selectedId) return;
      this.showEditContent = false;
      this.showHistoryContent = false;
      try {
        this.historyLogs = (await axios.get(`/api/supplier-order/${this.selectedId}/history/`)).data;
      } finally {
        this.showHistoryContent = true;
        this.showHistoryModal = true;
      }
    },
    closeHistory() {
      this.showHistoryModal = false;
      this.showHistoryContent = false;
      this.showEditContent = true;
    },

    /* --- отображение полей в истории --- */
    fieldLabel(k) {
      const m = {
        order_number: 'Order#', supplier_id: 'Supplier', customer_id: 'Customer',
        planned_receipt_date: 'Plan Receipt', shipment_date: 'Shipment',
        delivery_date: 'Delivery', amount_cny: 'Amount CNY', track_number: 'Track#',
        logistic_invoice_no: 'Logistic Invoice#', china_exit_date: 'China Exit',
        production_due_date: 'Production Due', payment_date: 'Payment Date',
        payment_details_qr: 'Payment QR', shipping_address: 'Address',
        shipping_code: 'Code', supplier_comment: 'Comment', status_id: 'Status'
      };
      return m[k] || k;
    },
    formatValue(field, val) {
      if (field === 'status_id') {
        const s = this.statuses.find(x => String(x.id) === String(val));
        return s ? s.name : '—';
      }
      if (field === 'payment_details_qr')
        return val ? val.split('/').pop() : '—';
      return val || '—';
    },

    /* --- QR-код --- */
    showQr(url) {
      this.qrModalUrl = url;
      this.showQrContent = true;
    },
  }
};
</script>

<style scoped>
/* базовые эффекты модальных окон и списков вложений */
/* (скопированы из исходного файла без изменений) */
.modal-backdrop {
  display: none;
}

.modal-backdrop.show {
  display: block;
}

.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity .3s, transform .3s;
}

.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.attachment-list {
  list-style: none;
  padding-left: 0;
}

.attachment-list li {
  margin-bottom: .25rem;
}

.attachment-list a {
  display: inline-block;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

</style>
