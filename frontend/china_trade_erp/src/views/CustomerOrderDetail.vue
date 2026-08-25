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
        <button
          v-if="isEdit"
          class="btn btn-outline-primary me-2"
          :disabled="isCreatingSupplierOrders"
          @click="createSupplierOrders"
        >
          {{ supplierOrdersActionLabel }}
        </button>
        <button type="button" class="btn btn-success me-2" :disabled="isSaving" @click="saveOrder">
          {{ isSaving ? 'Saving...' : (isEdit ? 'Update Order' : 'Create Order') }}
        </button>
        <button class="btn btn-secondary" @click="goBack">← Back to Orders</button>
      </div>
    </div>
    <transition name="save-toast">
      <div v-if="saveToast" class="save-toast">
        {{ saveToast }}
      </div>
    </transition>


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
        >Positions <span class="badge bg-secondary ms-1">{{ orderItems.length }}</span></button>
      </li>
      <li class="nav-item">
        <button
          class="nav-link"
          :class="{ active: activeTab==='docs' }"
          @click="activeTab = 'docs'"
        >Related documents <span class="badge bg-secondary ms-1">{{ relatedDocs.length }}</span></button>
      </li>
      <li class="nav-item">
        <button
          class="nav-link"
          :class="{ active: activeTab==='files' }"
          @click="activeTab = 'files'"
        >Files <span class="badge bg-secondary ms-1">{{ filesCount }}</span></button>
      </li>
    </ul>

    <!-- Форма заказа -->
    <transition name="fade">
      <div v-if="activeTab==='order'">
        <!-- AUDIT-BLOCK -->
        <div
            v-if="isEdit"
            class="audit-info mt-3 mb-3 p-3 bg-light rounded border"
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
          <div class="row gx-2 gy-2 order-form-grid">
            <div class="col-6 col-md-4">
              <label class="form-label small">Order Number</label>
              <input v-model="orderForm.order_number" class="form-control form-control-sm" required />
            </div>
            <div class="col-6 col-md-4">
              <label class="form-label small">Status</label>
              <StatusSelect v-model="orderForm.status_id" :statuses="statuses" size="sm" />
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
            <div class="col-12 compact-text-field">
              <label class="form-label small">Shipping Address</label>
              <textarea v-model="orderForm.shipping_address" class="form-control form-control-sm" rows="2"></textarea>
            </div>
            <div class="col-12 compact-text-field">
              <label class="form-label small">Customer Comment</label>
              <textarea v-model="orderForm.customer_comment" class="form-control form-control-sm" rows="3"></textarea>
            </div>
            <div class="col-12 compact-text-field">
              <label class="form-label small">Internal Comment</label>
              <textarea v-model="orderForm.internal_comment" class="form-control form-control-sm" rows="3"></textarea>
            </div>
          </div>
        </form>
      </div>
    </transition>

    <!-- Related Documents Tab -->
    <transition name="fade">
      <div v-if="activeTab==='docs'">
        <RelatedDocumentsTree
          :root="relatedRoot"
          :children="relatedDocs"
          empty-text="No supplier orders linked yet."
        />
      </div>
    </transition>

    <!-- Files Tab -->
    <transition name="fade">
      <div v-if="activeTab==='files'">
        <div class="compact-files-block">
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
                {{ attachmentName(att) }}
              </a>
              <button
                class="btn btn-sm btn-outline-danger ms-2"
                @click="deleteAttachment(att.id)"
              >&times;</button>
            </li>
          </ul>
        </div>
      </div>
    </transition>

    <!-- Positions Tab -->
    <transition name="fade">
      <div v-if="activeTab==='positions'">
        <div class="position-search position-relative compact-position-search mb-3">
          <input
            v-model="positionSearch"
            @input="fetchProductSuggestions"
            type="text"
            class="form-control form-control-sm"
            placeholder="Find product by name or SKU..."
          />
          <ul
            v-if="positionSearch.length >= 1"
            class="list-group position-absolute w-100 product-suggestions-list"
          >
            <li
              v-for="p in productSuggestions"
              :key="p.id"
              class="list-group-item list-group-item-action product-suggestion p-1"
              @click="addPosition(p)"
            >
              {{ p.name }} ({{ p.sku }}) — {{ p.unit?.name || '—' }}
            </li>
            <li
              v-if="!productSuggestions.length"
              class="list-group-item list-group-item-action product-suggestion text-primary p-1"
              @click="openProductModalWithName"
            >
              + Create new product: “{{ positionSearch }}”
            </li>
          </ul>
        </div>
        <div v-if="hasOrderDiscount" class="alert alert-light border small py-2 mb-2 compact-position-notice">
          Remove the order discount before setting discounts on product lines.
        </div>

        <div class="positions-layout">
          <div class="positions-table-wrap">
            <table class="table table-sm align-middle positions-table">
              <thead>
                <tr>
                  <th class="product-col">Product</th>
                  <th class="qty-col">Qty</th>
                  <th class="unit-col">Unit</th>
                  <th class="money-col text-end">Sale price</th>
                  <th class="discount-col">Discount, %</th>
                  <th class="money-col text-end">Total</th>
                  <th class="action-col"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in orderItems" :key="item.id">
                  <td class="product-col product-link" @click="openProductModalForEdit(item.product)">
                    {{ item.product.name }}
                  </td>
                  <td class="qty-col">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      class="form-control form-control-sm qty-input"
                      v-model.number="item.quantity"
                      @change="updatePosition(item)"
                    />
                  </td>
                  <td class="unit-col">{{ item.product.unit?.name || '—' }}</td>
                  <td class="money-col text-end">{{ formatMoney(itemUnitSalePrice(item)) }}</td>
                  <td class="discount-col">
                    <input
                      type="text"
                      inputmode="numeric"
                      :disabled="hasOrderDiscount"
                      class="form-control form-control-sm discount-input"
                      v-model="item.discount_percent"
                      @change="updatePosition(item)"
                    />
                  </td>
                  <td class="money-col text-end fw-semibold">{{ formatMoney(itemTotalAfterDiscount(item)) }}</td>
                  <td class="action-col">
                    <button class="btn btn-sm btn-outline-danger position-remove-btn" @click="removeItem(item.id)">
                      &times;
                    </button>
                  </td>
                </tr>
                <tr v-if="!orderItems.length">
                  <td colspan="7" class="text-center text-muted">No positions yet.</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="orderItems.length" class="order-totals">
            <div class="d-flex justify-content-between align-items-center gap-3 mb-2">
              <span class="text-muted">Subtotal</span>
              <strong>{{ formatMoney(positionsSubtotal) }}</strong>
            </div>
            <div class="d-flex justify-content-between align-items-center gap-3 mb-2">
              <label class="form-label small text-muted mb-0" for="order-discount">Order discount, %</label>
              <input
                id="order-discount"
                v-model="orderForm.discount_pct"
                type="text"
                inputmode="numeric"
                :disabled="hasLineDiscounts"
                class="form-control form-control-sm discount-input"
              />
            </div>
            <div v-if="hasLineDiscounts" class="small text-muted mb-2">
              Remove discounts from product lines before setting an order discount.
            </div>
            <div class="d-flex justify-content-between align-items-center gap-3 mb-2">
              <span class="text-muted">Discount amount</span>
              <span>{{ formatMoney(orderDiscountAmount) }}</span>
            </div>
            <div class="d-flex justify-content-between align-items-center gap-3 total-row">
              <span>Total</span>
              <strong>{{ formatMoney(orderTotalAfterDiscount) }}</strong>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- HISTORY-MODAL -->
    <div
      class="modal fade"
      tabindex="-1"
      :class="{ show: showHistoryModal }"
      :style="showHistoryModal ? 'display: block;' : ''"
    >
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <transition name="modal-fade">
          <div class="modal-content" v-if="showHistoryModal">
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
    <div class="modal-backdrop fade history-backdrop" :class="{ show: showHistoryModal }"></div>

    <ProductAddEditModal
      :visible="showProductModal"
      :initial-product="editingProduct"
      :categories="categories"
      :units="units"
      :suppliers="suppliers"
      @saved="onProductSaved"
      @reference-created="onReferenceCreated"
      @open-history="openProductHistory"
      @close="showProductModal = false"
    />

    <!-- PRODUCT HISTORY-MODAL -->
    <div
      class="modal fade"
      tabindex="-1"
      :class="{ show: showProductHistoryModal }"
      :style="showProductHistoryModal ? 'display: block;' : ''"
    >
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <transition name="modal-fade">
          <div class="modal-content" v-if="showProductHistoryModal">
            <div class="modal-header">
              <h5 class="modal-title">Product Change History</h5>
              <button type="button" class="btn-close" @click="closeProductHistory"></button>
            </div>
            <div class="modal-body history-modal-body">
              <table v-if="productHistoryLogs.length" class="table table-striped">
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
                  <tr v-for="(log, idx) in productHistoryLogs" :key="idx">
                    <td>{{ log.changed_at }}</td>
                    <td>{{ log.changed_by }}</td>
                    <td>{{ productFieldLabel(log.field_name) }}</td>
                    <td>{{ formatProductHistoryValue(log.field_name, log.old_value) }}</td>
                    <td>{{ formatProductHistoryValue(log.field_name, log.new_value) }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="text-center text-muted py-4">No changes found.</div>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" @click="closeProductHistory">Close</button>
            </div>
          </div>
        </transition>
      </div>
    </div>
    <div class="modal-backdrop fade history-backdrop" :class="{ show: showProductHistoryModal }"></div>
  </div>
</template>

<script>
import axios from '../axios';
import ProductAddEditModal from '../components/ProductAddEditModal.vue';
import RelatedDocumentsTree from '../components/RelatedDocumentsTree.vue';
import StatusSelect from '../components/StatusSelect.vue';

export default {
  name: 'CustomerOrderDetail',
  components: { ProductAddEditModal, RelatedDocumentsTree, StatusSelect },
  data() {
    return {
      isSending: false,
      isSaving: false,
      saveToast: '',
      saveToastTimer: null,
      isCreatingSupplierOrders: false,
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
        customer_comment: '',
        internal_comment: '',
        discount_pct: 0,
      },
      existingAttachments: [],
      attachments: [],
      orderItems: [],
      positionSearch: '',
      productSuggestions: [],
      relatedRoot: null,
      relatedDocs: [],

      /* справочники */
      customers: [],
      suppliers: [],
      statuses: [],
      categories: [],
      units: [],

      /* history */
      historyLogs: [],
      productHistoryLogs: [],
      showProductHistoryModal: false,

      /* product modal */
      showProductModal: false,
      editingProduct: null,
      addProductToOrderAfterSave: false,

      selectedId: null,
      savedSnapshot: '',
      savedItemIds: [],
    };
  },

  computed: {
    isEdit() {
      return !!this.selectedId;
    },
    filesCount() {
      return this.existingAttachments.length + this.attachments.length;
    },
    hasSupplierOrders() {
      return this.relatedDocs.length > 0;
    },
    supplierOrdersActionLabel() {
      if (this.isCreatingSupplierOrders) {
        return this.hasSupplierOrders ? 'Updating...' : 'Creating...';
      }
      return this.hasSupplierOrders ? 'Update supplier orders' : 'Create supplier orders';
    },
    hasLineDiscounts() {
      return this.orderItems.some(item => this.numberOrZero(item.discount_percent) > 0);
    },
    positionsSubtotal() {
      return this.orderItems.reduce((sum, item) => sum + this.itemTotalAfterDiscount(item), 0);
    },
    orderDiscountAmount() {
      return this.positionsSubtotal * (this.numberOrZero(this.orderForm.discount_pct) / 100);
    },
    orderTotalAfterDiscount() {
      return this.positionsSubtotal - this.orderDiscountAmount;
    },
    hasOrderDiscount() {
      return this.numberOrZero(this.orderForm.discount_pct) > 0;
    },
    hasUnsavedChanges() {
      return this.savedSnapshot !== this.currentSnapshot();
    }
  },

  created() {
    this.selectedId = this.$route.params.id ? +this.$route.params.id : null;
    this.resetForm();
    this.fetchAux()
      .then(async () => {
        if (this.isEdit) {
          await Promise.all([
            this.fetchOrder(),
            this.fetchOrderItems(),
            this.fetchRelatedDocuments(),
          ]);
          this.normalizeDiscountState();
          this.updateSavedSnapshot();
        } else {
          this.updateSavedSnapshot();
        }
      });
  },

  watch: {
    '$route.params.id'(val) {
      this.selectedId = val ? +val : null;
      this.resetForm();
      if (this.isEdit) {
        Promise.all([
          this.fetchOrder(),
          this.fetchOrderItems(),
          this.fetchRelatedDocuments(),
        ]).then(() => {
          this.normalizeDiscountState();
          this.updateSavedSnapshot();
        });
      } else {
        this.updateSavedSnapshot();
      }
    }
  },

  methods: {
    /* ——————— API ——————— */

    async fetchAux() {
      try {
        const [
          customerRes,
          supplierRes,
          stRes,
          catRes,
          unitRes
        ] = await Promise.all([
          axios.get('/api/counterparties/options/', { params: { role: 'customer' } }),
          axios.get('/api/counterparties/options/', { params: { role: 'supplier' } }),
          axios.get('/api/customer-order-statuses/'),
          axios.get('/api/product-category/'),
          axios.get('/api/units/'),
        ]);
        this.customers = customerRes.data;
        this.suppliers = supplierRes.data;
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
          discount_pct: this.rateToPercent(o.discount_pct),
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
      this.orderItems = data.map(this.normalizeOrderItem);
    },

    async fetchRelatedDocuments() {
      if (!this.selectedId) return;
      const { data } = await axios.get(`/api/customer-order/${this.selectedId}/related-documents/`);
      this.relatedRoot = data.root;
      this.relatedDocs = data.children || [];
    },

    async saveOrder(options = {}) {
      const silent = options?.silent === true;
      if (!this.orderForm.customer_id) {
        if (!silent) {
          alert('Select a customer before saving the order.');
        }
        return null;
      }
      if (this.isEdit && !this.hasUnsavedChanges) {
        if (!silent) this.showSaveToast('No changes to save');
        return this.orderForm;
      }
      this.isSaving = true;
      try {
        const pendingItems = this.selectedId ? [] : [...this.orderItems];
        const fd = new FormData();
        const fields = [
          'order_number',
          'status_id',
          'customer_id',
          'planned_receipt_date',
          'shipment_date',
          'shipping_address',
          'customer_comment',
          'internal_comment'
        ];
        fields.forEach(k => {
          const v = this.orderForm[k];
          if (v != null && (v !== '' || ['customer_comment', 'internal_comment'].includes(k))) fd.append(k, v);
        });
        fd.append('discount_pct', this.hasLineDiscounts ? '0.0000' : this.percentToRate(this.orderForm.discount_pct));
        this.attachments.forEach(f => fd.append('attachments', f));
        const cfg = { headers: { 'Content-Type': 'multipart/form-data' } };
        let res;
        if (this.isEdit) {
          const wantsOrderDiscount = !this.hasLineDiscounts && this.numberOrZero(this.orderForm.discount_pct) > 0;
          const needsOrderDiscountReset = wantsOrderDiscount && this.savedSnapshotHasLineDiscounts();
          if (needsOrderDiscountReset) {
            const clearOrderDiscountFd = new FormData();
            fields.forEach(k => {
              const v = this.orderForm[k];
              if (v != null && (v !== '' || ['customer_comment', 'internal_comment'].includes(k))) clearOrderDiscountFd.append(k, v);
            });
            clearOrderDiscountFd.append('discount_pct', '0.0000');
            await axios.patch(`/api/customer-order/${this.selectedId}/`, clearOrderDiscountFd, cfg);
          }
          if (!needsOrderDiscountReset) {
            res = await axios.patch(`/api/customer-order/${this.selectedId}/`, fd, cfg);
          }
          this.orderForm = {
            ...this.orderForm,
            ...(res?.data || {}),
            discount_pct: res?.data ? this.rateToPercent(res.data.discount_pct) : this.orderForm.discount_pct,
          };
          const currentExistingIds = this.orderItems
            .filter(item => !String(item.id).startsWith('tmp-'))
            .map(item => item.id);
          const removedIds = this.savedItemIds.filter(id => !currentExistingIds.includes(id));
          for (const itemId of removedIds) {
            await axios.delete(`/api/customer-order-items/${itemId}/`);
          }
          for (const item of this.orderItems) {
            if (String(item.id).startsWith('tmp-')) {
              await axios.post('/api/customer-order-items/', {
                order: this.selectedId,
                product_id: item.product.id,
                quantity: item.quantity,
                discount_pct: this.percentToRate(item.discount_percent),
                comment: item.comment || '',
              });
            } else {
              await axios.patch(`/api/customer-order-items/${item.id}/`, {
                quantity: item.quantity,
                discount_pct: this.percentToRate(item.discount_percent),
                comment: item.comment || '',
              });
            }
          }
          await this.fetchOrderItems();
          if (needsOrderDiscountReset) {
            res = await axios.patch(`/api/customer-order/${this.selectedId}/`, fd, cfg);
            this.orderForm = {
              ...this.orderForm,
              ...res.data,
              discount_pct: this.rateToPercent(res.data.discount_pct),
            };
          }
          if (!silent) this.showSaveToast('Order saved');
        } else {
          res = await axios.post('/api/customer-order/', fd, cfg);
          const newOrderId = res.data.id;
          for (const item of pendingItems) {
            await axios.post('/api/customer-order-items/', {
              order: newOrderId,
              product_id: item.product.id,
              quantity: item.quantity,
              discount_pct: this.percentToRate(item.discount_percent),
              comment: item.comment || '',
            });
          }
          this.selectedId = newOrderId;
          this.orderForm = {
            ...this.defaultForm,
            ...res.data,
            status_id: res.data.status?.id,
            customer_id: res.data.customer?.id,
            discount_pct: this.rateToPercent(res.data.discount_pct),
          };
          if (!silent) this.showSaveToast('Order created');
          await this.$router.replace(`/customer-orders/${newOrderId}`);
          await this.fetchOrderItems();
        }
        this.attachments = [];
        this.updateSavedSnapshot();
        return res.data;
      } catch (e) {
        console.error(e.response?.data || e);
        const message = this.formatError(e.response?.data) || 'Unable to save order.';
        alert(message);
        if (silent) return null;
        return null;
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
        this.showSaveToast('Order sent');
      } catch (e) {
        console.error(e);
        alert('Не удалось отправить заказ');
      } finally {
        this.isSending = false;
      }
    },

    async createSupplierOrders() {
      if (!this.selectedId) return;
      this.isCreatingSupplierOrders = true;
      try {
        await axios.post(`/api/customer-order/${this.selectedId}/create-supplier-orders/`);
        await this.fetchRelatedDocuments();
        this.activeTab = 'docs';
      } catch (e) {
        console.error(e.response?.data || e);
        alert(e.response?.data?.detail || 'Unable to create supplier orders');
      } finally {
        this.isCreatingSupplierOrders = false;
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
      if (this.positionSearch.length < 1) {
        this.productSuggestions = [];
        return;
      }
      const { data } = await axios.get('/api/products/', {
        params: { search: this.positionSearch }
      });
      this.productSuggestions = Array.isArray(data) ? data : (data.results || []);
    },

    async addPosition(product) {
      this.orderItems.push({
        id: `tmp-${Date.now()}-${product.id}`,
        product,
        quantity: 1,
        discount_percent: 0,
        comment: '',
      });
      this.positionSearch = '';
      this.productSuggestions = [];
    },

    openProductModalForEdit(product) {
      this.editingProduct = product;
      this.addProductToOrderAfterSave = false;
      this.showProductModal = true;
    },

    openProductModalWithName() {
      this.editingProduct = { name: this.positionSearch };
      this.addProductToOrderAfterSave = true;
      this.showProductModal = true;
    },

    async removeItem(itemId) {
      this.orderItems = this.orderItems.filter(item => item.id !== itemId);
    },

    async updatePosition(item) {
      item.quantity = this.formatQuantityInput(item.quantity);
      if (this.hasOrderDiscount && this.numberOrZero(item.discount_percent) > 0) {
        item.discount_percent = 0;
        alert('Remove the order discount before setting a product discount.');
      }
    },

    async onProductSaved(product) {
      this.showProductModal = false;
      this.positionSearch = '';
      this.productSuggestions = [];
      if (!this.addProductToOrderAfterSave) {
        this.orderItems = this.orderItems.map(item =>
          item.product?.id === product.id ? { ...item, product } : item
        );
        this.addProductToOrderAfterSave = false;
        return;
      }
      this.addProductToOrderAfterSave = false;
      if (!this.selectedId) {
        this.orderItems.push({
          id: `tmp-${Date.now()}-${product.id}`,
          product,
          quantity: 1,
          discount_percent: 0,
          comment: '',
        });
        return;
      }
      this.orderItems.push({
        id: `tmp-${Date.now()}-${product.id}`,
        product,
        quantity: 1,
        discount_percent: 0,
        comment: '',
      });
    },

    onReferenceCreated({ type, item }) {
      const lists = {
        category: this.categories,
        unit: this.units,
        supplier: this.suppliers,
      };
      const list = lists[type];
      if (list && !list.some(existing => existing.id === item.id)) {
        list.push(item);
      }
    },

    /* ——————— Навигация и UI ——————— */

    goBack() {
      this.leaveToOrders();
    },
    async leaveToOrders() {
      const canLeave = await this.confirmUnsavedChanges();
      if (canLeave) this.$router.push('/customer-orders');
    },
    async confirmUnsavedChanges() {
      if (!this.hasUnsavedChanges) return true;
      if (confirm('Save changes before leaving?')) {
        const saved = await this.saveOrder({ silent: true });
        return !!saved;
      }
      return confirm('Leave without saving changes?');
    },
    showSaveToast(message) {
      this.saveToast = message;
      if (this.saveToastTimer) clearTimeout(this.saveToastTimer);
      this.saveToastTimer = setTimeout(() => {
        this.saveToast = '';
        this.saveToastTimer = null;
      }, 1800);
    },

    resetForm() {
      this.orderForm = { ...this.defaultForm };
      this.existingAttachments = [];
      this.attachments = [];
      this.orderItems = [];
      this.relatedRoot = null;
      this.relatedDocs = [];
    },
    normalizeDiscountState() {
      if (this.hasLineDiscounts) {
        this.orderForm.discount_pct = 0;
      }
    },
    currentSnapshot() {
      return JSON.stringify({
        order: {
          status_id: this.orderForm.status_id || '',
          customer_id: this.orderForm.customer_id || '',
          planned_receipt_date: this.orderForm.planned_receipt_date || '',
          shipment_date: this.orderForm.shipment_date || '',
          shipping_address: this.orderForm.shipping_address || '',
          customer_comment: this.orderForm.customer_comment || '',
          internal_comment: this.orderForm.internal_comment || '',
          discount_pct: this.hasLineDiscounts ? 0 : this.numberOrZero(this.orderForm.discount_pct),
        },
        items: this.orderItems.map(item => ({
          id: item.id,
          product_id: item.product?.id,
          quantity: this.numberOrZero(item.quantity),
          discount_percent: this.numberOrZero(item.discount_percent),
          comment: item.comment || '',
        })),
        attachments: this.attachments.map(file => file.name),
      });
    },
    savedSnapshotHasLineDiscounts() {
      try {
        const snapshot = JSON.parse(this.savedSnapshot || '{}');
        return (snapshot.items || []).some(item => this.numberOrZero(item.discount_percent) > 0);
      } catch {
        return false;
      }
    },
    updateSavedSnapshot() {
      this.savedSnapshot = this.currentSnapshot();
      this.savedItemIds = this.orderItems
        .filter(item => !String(item.id).startsWith('tmp-'))
        .map(item => item.id);
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

    async openProductHistory() {
      const productId = this.editingProduct?.id;
      if (!productId) return;
      try {
        this.productHistoryLogs = (await axios.get(`/api/products/${productId}/history/`)).data;
        this.showProductHistoryModal = true;
      } catch (e) {
        console.error(e);
        alert('Unable to load product history.');
      }
    },
    closeProductHistory() {
      this.showProductHistoryModal = false;
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
        customer_comment: 'Customer Comment',
        internal_comment: 'Internal Comment',
      };
      return m[k] || k;
    },
    productFieldLabel(key) {
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
    formatProductHistoryValue(field, val) {
      if (field === 'category_id') {
        const category = this.categories.find(x => String(x.id) === String(val));
        return category ? category.name : '—';
      }
      if (field === 'unit_id') {
        const unit = this.units.find(x => String(x.id) === String(val));
        return unit ? unit.name : '—';
      }
      if (field === 'supplier_id') {
        const supplier = this.suppliers.find(x => String(x.id) === String(val));
        return supplier ? supplier.name : '—';
      }
      if (field === 'image') {
        return val ? val.split('/').pop() : '—';
      }
      return val != null && val !== '' ? val : '—';
    },
    normalizeOrderItem(item) {
      return {
        ...item,
        quantity: this.formatQuantityInput(item.quantity),
        discount_percent: this.rateToPercent(item.discount_pct),
      };
    },
    itemUnitSalePrice(item) {
      return Number(item.unit_sale_price ?? item.product?.sale_price ?? 0);
    },
    itemTotalAfterDiscount(item) {
      const price = this.itemUnitSalePrice(item);
      const quantity = this.numberOrZero(item.quantity);
      const discount = this.numberOrZero(item.discount_percent) / 100;
      return price * quantity * (1 - discount);
    },
    numberOrZero(value) {
      const numberValue = Number(String(value ?? 0).replace(',', '.'));
      return Number.isFinite(numberValue) ? numberValue : 0;
    },
    percentToRate(value) {
      return (this.numberOrZero(value) / 100).toFixed(4);
    },
    rateToPercent(value) {
      return Number((this.numberOrZero(value) * 100).toFixed(2));
    },
    formatQuantityInput(value) {
      return this.numberOrZero(value);
    },
    formatMoney(value) {
      return this.numberOrZero(value).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    },
    attachmentName(att) {
      if (att.file_name) return att.file_name;
      const rawName = att.file ? att.file.split('/').pop() : '';
      try {
        return decodeURIComponent(rawName);
      } catch {
        return rawName;
      }
    },
    formatError(data) {
      if (!data) return '';
      if (typeof data === 'string') return data;
      if (data.detail || data.error) return data.detail || data.error;
      return Object.values(data).flat().join(' ');
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
.history-modal-body {
  max-height: calc(100vh - 220px);
  overflow-y: auto;
}
.attachment-list { list-style: none; padding-left: 0; }
.attachment-list li { margin-bottom: .25rem; }
.attachment-list a {
  display: inline-block; max-width: 100%;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.product-suggestion {
  cursor: pointer;
  white-space: normal;
  overflow-wrap: anywhere;
  line-height: 1.35;
}
.product-suggestion:hover {
  background-color: #eef5ff;
}
.product-suggestions-list {
  z-index: 1000;
  max-width: 100%;
  max-height: 260px;
  overflow-y: auto;
  overflow-x: hidden;
}
.compact-position-search {
  max-width: 520px;
}
.compact-text-field {
  max-width: 760px;
}
.compact-files-block,
.compact-position-notice {
  max-width: 520px;
}
.order-form-grid > [class*="col-"]:not(.col-12) {
  flex: 0 0 auto;
  width: min(100%, 260px);
}
.order-form-grid > .col-12 textarea {
  width: 100%;
}
.product-link {
  color: #0d6efd;
  cursor: pointer;
}
.product-link:hover {
  color: #0a58ca;
  text-decoration: underline;
}
.positions-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 1rem;
  align-items: start;
}
.positions-table-wrap {
  min-width: 0;
  overflow-x: auto;
}
.positions-table {
  table-layout: fixed;
  min-width: 760px;
}
.positions-table th,
.positions-table td {
  white-space: nowrap;
}
.positions-table th.product-col,
.positions-table td.product-col {
  width: auto;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.qty-input {
  width: 64px;
  text-align: center;
}
.discount-input {
  width: 78px;
  text-align: center;
}
.unit-col {
  width: 76px;
}
.qty-col {
  width: 84px;
}
.action-col {
  width: 48px;
  text-align: center;
}
.discount-col {
  width: 108px;
}
.money-col {
  width: 118px;
}
.position-remove-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  line-height: 1;
}
.order-totals {
  position: sticky;
  top: 82px;
  padding: 0.85rem 1rem;
  border: 1px solid #edf0f2;
  border-radius: 0.375rem;
  background: #f8f9fa;
}
.total-row {
  padding-top: 0.65rem;
  border-top: 1px solid #dee2e6;
  color: #2f455c;
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
@media (max-width: 992px) {
  .positions-layout {
    grid-template-columns: 1fr;
  }
  .order-totals {
    position: static;
    max-width: 360px;
    margin-left: auto;
  }
}
</style>
