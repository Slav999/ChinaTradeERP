<template>
  <div class="container mt-4">
    <!-- Заголовок + «Назад» -->
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h1>{{ isEdit ? 'Edit Order' : 'New Order' }}</h1>
      <div>
        <button
          class="btn btn-primary me-2"
          :disabled="isSending"
          @click="sendToCustomer"
        >
          {{ isSending ? 'Sending...' : 'Send to Customer' }}
        </button>
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
        >Order</button>
      </li>
      <li class="nav-item">
        <button
          class="nav-link"
          :class="{ active: activeTab==='positions' }"
          @click="activeTab = 'positions'"
        >Positions</button>
      </li>
      <li class="nav-item">
        <button
          class="nav-link"
          :class="{ active: activeTab==='files' }"
          @click="activeTab = 'files'"
        >Files</button>
      </li>
    </ul>

    <!-- Форма заказа -->
    <transition name="fade">
      <div v-if="activeTab==='order'">
        <!-- AUDIT-BLOCK -->
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

        <form @submit.prevent="saveOrder">
          <div class="row gx-2 gy-2">
            <div class="col-6 col-md-4">
              <label class="form-label small">Order Number</label>
              <input v-model="orderForm.order_number" class="form-control form-control-sm" required />
            </div>
            <div class="col-6 col-md-4">
              <label class="form-label small">Status</label>
              <select v-model="orderForm.status_id" class="form-select form-select-sm">
                <option disabled value="">Select status...</option>
                <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
            </div>
            <div class="col-6 col-md-4">
              <label class="form-label small">Customer</label>
              <select v-model="orderForm.customer_id" class="form-select form-select-sm">
                <option disabled value="">Select customer...</option>
                <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label small">Shipment</label>
              <input v-model="orderForm.shipment_date" type="date" class="form-control form-control-sm" />
            </div>
            <div class="col-12">
              <label class="form-label small">Shipping Address</label>
              <textarea v-model="orderForm.shipping_address" class="form-control form-control-sm" rows="2"></textarea>
            </div>
            <div class="col-6 col-md-4">
              <label class="form-label small">Shipping Code</label>
              <input v-model="orderForm.shipping_code" class="form-control form-control-sm" />
            </div>
          </div>
        </form>
      </div>
    </transition>

    <!-- Files Tab -->
    <transition name="fade">
      <div v-if="activeTab==='files'">
        <label class="form-label small">Attachments</label>
        <input
          type="file"
          multiple
          class="form-control form-control-sm mb-2"
          @change="e => attachments = Array.from(e.target.files)"
        />
        <ul class="attachment-list">
          <li v-for="att in existingAttachments" :key="att.id" class="d-flex align-items-center mb-1">
            <a :href="att.file" target="_blank" class="flex-grow-1 text-truncate">
              {{ att.file.split('/').pop() }}
            </a>
            <button
              class="btn btn-sm btn-outline-danger ms-2"
              @click="deleteAttachment(att.id)"
            >&times;</button>
          </li>
        </ul>
      </div>
    </transition>

    <!-- Positions Tab -->
    <transition name="fade">
      <div v-if="activeTab==='positions'">
        <div class="position-search position-relative mb-3">
          <input
            v-model="positionSearch"
            @input="fetchProductSuggestions"
            type="text"
            class="form-control form-control-sm"
            placeholder="Find product by name or SKU..."
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
              + Create new product: “{{ positionSearch }}”
            </li>
          </ul>
        </div>

        <table class="table table-sm">
          <thead>
            <tr>
              <th>Product</th>
              <th>Unit</th>
              <th>Qty</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in orderItems" :key="item.id">
              <td @click="openProductModalForEdit(item.product)" style="cursor:pointer; color:blue;">
                {{ item.product.name }}
              </td>
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
                <button class="btn btn-sm btn-outline-danger" @click="removeItem(item.id)">
                  ×
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

    <!-- HISTORY-MODAL -->
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
                    <td>{{ log.old_value || '—' }}</td>
                    <td>{{ log.new_value || '—' }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="text-center text-muted py-4">No changes found.</div>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" @click="closeHistory">Close</button>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <ProductAddEditModal
      :visible="showProductModal"
      :initial-product="editingProduct"
      :categories="categories"
      :units="units"
      :suppliers="suppliers"
      @saved="onProductSaved"
      @close="showProductModal = false"
    />
  </div>
</template>

<script>
import axios from '../axios';
import ProductAddEditModal from '../components/ProductAddEditModal.vue';

export default {
  name: 'CustomerOrderDetail',
  components: { ProductAddEditModal },
  data() {
    return {
      isSending: false,
      isSaving: false,
      activeTab: 'order',
      showHistoryModal: false,
      orderForm: {},
      defaultForm: {
        order_number: '',
        status_id: '',
        customer_id: '',
        planned_receipt_date: '',
        shipment_date: '',
        shipping_address: '',
        shipping_code: '',
      },
      existingAttachments: [],
      attachments: [],
      orderItems: [],
      positionSearch: '',
      productSuggestions: [],

      /* справочники */
      customers: [],
      suppliers: [],
      statuses: [],
      categories: [],
      units: [],

      /* history */
      historyLogs: [],

      /* product modal */
      showProductModal: false,
      editingProduct: null,

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
    this.fetchAux()
      .then(() => {
        if (this.isEdit) this.fetchOrder();
        this.fetchOrderItems();
      });
  },

  methods: {
    /* ——————— API ——————— */

    async fetchAux() {
      try {
        const [
          cpRes,
          stRes,
          catRes,
          unitRes
        ] = await Promise.all([
          axios.get('/api/counterparties/'),
          axios.get('/api/customer-order-statuses/'),
          axios.get('/api/product-category/'),
          axios.get('/api/units/'),
        ]);
        this.customers = cpRes.data;
        this.suppliers = cpRes.data;
        this.statuses = stRes.data;
        this.categories = catRes.data;
        this.units = unitRes.data;
      } catch (e) {
        console.error(e);
        alert('Ошибка при загрузке справочников');
      }
    },

    async fetchOrder() {
      try {
        const r = await axios.get(`/api/customer-order/${this.selectedId}/`);
        const o = r.data;
        this.orderForm = {
          ...this.defaultForm,
          ...o,
          status_id: o.status?.id,
          customer_id: o.customer?.id,
          shipping_address: o.shipping_address,
          shipping_code: o.shipping_code,
        };
        this.existingAttachments = o.attachments || [];
      } catch (e) {
        console.error(e);
        alert('Не удалось загрузить заказ');
      }
    },

    async fetchOrderItems() {
      if (!this.selectedId) return;
      const { data } = await axios.get('/api/customer-order-items/', {
        params: { order: this.selectedId }
      });
      this.orderItems = data;
    },

    async saveOrder() {
      this.isSaving = true;
      try {
        const fd = new FormData();
        const fields = [
          'order_number',
          'status_id',
          'customer_id',
          'planned_receipt_date',
          'shipment_date',
          'shipping_address',
          'shipping_code'
        ];
        fields.forEach(k => {
          const v = this.orderForm[k];
          if (v != null && v !== '') fd.append(k, v);
        });
        this.attachments.forEach(f => fd.append('attachments', f));
        const cfg = { headers: { 'Content-Type': 'multipart/form-data' } };
        let res;
        if (this.isEdit) {
          res = await axios.patch(`/api/customer-order/${this.selectedId}/`, fd, cfg);
          alert('Order updated');
          this.orderForm = { ...this.orderForm, ...res.data };
        } else {
          res = await axios.post('/api/customer-order/', fd, cfg);
          alert('Order created');
          this.$router.replace(`/customer-orders/${res.data.id}`);
          return;
        }
        this.attachments = [];
      } catch (e) {
        console.error(e.response?.data || e);
        alert('Ошибка при сохранении');
      } finally {
        this.isSaving = false;
      }
    },

    async sendToCustomer() {
      if (!confirm('Send order to customer?')) return;
      this.isSending = true;
      try {
        await axios.post(`/api/customer-order/${this.selectedId}/send/`);
        alert('Order sent');
      } catch (e) {
        console.error(e);
        alert('Не удалось отправить заказ');
      } finally {
        this.isSending = false;
      }
    },

    async deleteAttachment(id) {
      if (!confirm('Delete this file?')) return;
      try {
        await axios.delete(`/api/customer-order/${this.selectedId}/attachments/${id}/`);
        this.existingAttachments = this.existingAttachments.filter(a => a.id !== id);
      } catch (e) {
        console.error(e);
        alert('Не удалось удалить файл');
      }
    },

    async fetchProductSuggestions() {
      if (this.positionSearch.length < 2) {
        this.productSuggestions = [];
        return;
      }
      const { data } = await axios.get('/api/products/', {
        params: { search: this.positionSearch }
      });
      this.productSuggestions = data;
    },

    async addPosition(product) {
      await axios.post('/api/customer-order-items/', {
        order: this.selectedId,
        product_id: product.id,
        quantity: 1
      });
      this.positionSearch = '';
      this.productSuggestions = [];
      this.fetchOrderItems();
    },

    async removeItem(itemId) {
      await axios.delete(`/api/customer-order-items/${itemId}/`);
      this.fetchOrderItems();
    },

    async updatePosition(item) {
      await axios.patch(`/api/customer-order-items/${item.id}/`, {
        quantity: item.quantity
      });
      this.fetchOrderItems();
    },

    async onProductSaved(product) {
      this.showProductModal = false;
      await axios.post('/api/customer-order-items/', {
        order: this.selectedId,
        product_id: product.id,
        quantity: 1
      });
      this.fetchOrderItems();
    },

    /* ——————— Навигация и UI ——————— */

    goBack() {
      this.$router.push('/customer-orders');
    },

    resetForm() {
      this.orderForm = { ...this.defaultForm };
      this.existingAttachments = [];
      this.attachments = [];
      this.orderItems = [];
    },

    formatDate(v) {
      return v ? new Date(v).toLocaleString() : '—';
    },

    /* ——————— История изменений ——————— */

    async openHistory() {
      if (!this.isEdit) return;
      try {
        this.historyLogs = (await axios.get(`/api/customer-order/${this.selectedId}/history/`)).data;
        this.showHistoryModal = true;
      } catch {
        alert('Не удалось загрузить историю');
      }
    },
    closeHistory() {
      this.showHistoryModal = false;
    },

    /* ——————— Helpers ——————— */

    fieldLabel(k) {
      const m = {
        order_number: 'Order#',
        status_id: 'Status',
        customer_id: 'Customer',
        planned_receipt_date: 'Plan Receipt',
        shipment_date: 'Shipment',
        shipping_address: 'Address',
        shipping_code: 'Code',
      };
      return m[k] || k;
    },
  }
};
</script>

<style scoped>
.modal-backdrop { display: none; }
.modal-backdrop.show { display: block; }
.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity .3s, transform .3s;
}
.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0; transform: translateY(-10px);
}
.attachment-list { list-style: none; padding-left: 0; }
.attachment-list li { margin-bottom: .25rem; }
.attachment-list a {
  display: inline-block; max-width: 100%;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
</style>
