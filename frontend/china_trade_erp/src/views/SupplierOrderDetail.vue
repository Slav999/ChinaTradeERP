<template>
  <div class="container mt-4">
    <!-- Заголовок + «Назад» -->
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h1>{{ $t(isSamples ? (isEdit ? 'Edit sample order' : 'New sample order') : (isEdit ? 'Edit Order' : 'New Order')) }}</h1>
      <div class="order-actions">
        <ChatShareButton v-if="selectedId" type="supplier_order" :record-id="Number(selectedId)" :title="`Заказ поставщику №${orderForm.order_number || selectedId}`" />
        <RelatedChatsButton v-if="selectedId" type="supplier_order" :record-id="Number(selectedId)" :title="`Заказ поставщику №${orderForm.order_number || selectedId}`" />
        <div v-if="canManageOrders" class="send-action">
        <button
            class="btn btn-primary"
            :disabled="isSending || !isEdit || !orderItems.length || hasUnsavedChanges"
            :title="$t(!orderItems.length ? 'Add at least one position before sending the order.' : (hasUnsavedChanges ? 'Save changes before sending the order.' : ''))"
            @click="sendToSupplier"
        >
          {{ isSending ? 'Sending...' : 'Send to Supplier' }}
        </button>
          <div v-if="orderForm.sent_at" class="sent-note">
            Sent {{ formatDate(orderForm.sent_at) }}
          </div>
        </div>
        <button v-if="canManageOrders" type="button" class="btn btn-success" :disabled="isSaving" @click="saveOrder">
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
        >Order
        </button>
      </li>
      <li class="nav-item">
        <button
            class="nav-link"
            :class="{ active: activeTab==='positions' }"
            @click="activeTab = 'positions'"
        >Positions <span class="badge bg-secondary ms-1">{{ orderItems.length }}</span>
        </button>
      </li>
      <li v-if="!isSamples" class="nav-item">
        <button
            class="nav-link"
            :class="{ active: activeTab==='docs' }"
            @click="activeTab = 'docs'"
        >Related documents <span class="badge bg-secondary ms-1">{{ relatedDocsCount }}</span>
        </button>
      </li>
      <li class="nav-item">
        <button
            class="nav-link"
            :class="{ active: activeTab==='files' }"
            @click="activeTab = 'files'"
        >Files <span class="badge bg-secondary ms-1">{{ filesCount }}</span>
        </button>
      </li>
    </ul>

    <!-- Форма (показывается, пока не открыта история) -->
    <transition name="fade">
      <div v-if="activeTab==='order'">
        <!-- ▼ AUDIT-BLOCK (клик — открываем историю) ▼ -->
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
        <!-- ▲ AUDIT-BLOCK ▲ -->

        <!-- ▼ ФОРМА ЗАКАЗА (полностью из исходного файла) ▼ -->
        <form @submit.prevent="saveOrder">
          <fieldset :disabled="!canManageOrders" class="p-0 m-0 border-0">
          <div class="row gx-2 gy-2 order-form-grid" :class="{ 'sample-form': isSamples }">
            <div class="row gx-2 gy-2">
              <div class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Order Number</label>
                <input v-model="orderForm.order_number" class="form-control form-control-sm" readonly/>
              </div>
              <div class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Status</label>
                <StatusSelect v-model="orderForm.status_id" :statuses="statuses" size="sm" />
              </div>
              <div class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Supplier</label>
                <div class="input-group input-group-sm">
                  <SearchableCounterpartySelect
                      v-model="orderForm.supplier_id"
                      :options="suppliers"
                      placeholder="Select supplier..."
                      size="sm"
                  />
                  <IconButton
                      icon="plus-lg"
                      variant="outline-secondary"
                      size="sm"
                      :title="$t('Create supplier')"
                      @click="openCounterpartyModal('supplier')"
                  />
                </div>
              </div>
              <div v-if="!isSamples" class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Customer</label>
                <div class="input-group input-group-sm">
                  <SearchableCounterpartySelect
                      v-model="orderForm.customer_id"
                      :options="customers"
                      placeholder="Select customer..."
                      size="sm"
                  />
                  <IconButton
                      icon="plus-lg"
                      variant="outline-secondary"
                      size="sm"
                      :title="$t('Create customer')"
                      @click="openCounterpartyModal('customer')"
                  />
                </div>
              </div>
              <div v-if="isSamples" class="col-12">
                <label for="sample-trip" class="form-label small">{{ $t('Trip / exhibition / meeting') }}</label>
                <input id="sample-trip" v-model.trim="orderForm.trip_name" maxlength="255" class="form-control form-control-sm"
                    :placeholder="$t('For example: Guangzhou exhibition')" />
              </div>
              <div v-if="!isSamples" class="col-md-4">
                <label class="form-label small">Plan Receipt</label>
                <input v-model="orderForm.planned_receipt_date" type="date" class="form-control form-control-sm"/>
              </div>
              <div v-if="!isSamples" class="col-md-4">
                <label class="form-label small">Shipment</label>
                <input v-model="orderForm.shipment_date" type="date" class="form-control form-control-sm"/>
              </div>
              <div class="col-md-4">
                <label class="form-label small">Delivery</label>
                <input v-model="orderForm.delivery_date" type="date" class="form-control form-control-sm"/>
              </div>
              <div v-if="!isSamples" class="col-12 compact-text-field">
                <label class="form-label small">Shipping Address</label>
                <textarea v-model="orderForm.shipping_address" class="form-control form-control-sm" rows="2"></textarea>
              </div>
              <div v-if="!isSamples" class="col-12 compact-text-field">
                <label class="form-label small">Supplier Comment</label>
                <textarea v-model="orderForm.supplier_comment" class="form-control form-control-sm" rows="2"></textarea>
              </div>
              <div class="col-12 compact-text-field sample-comment">
                <label class="form-label small">{{ $t('Comment') }}</label>
                <textarea v-model="orderForm.internal_comment" class="form-control form-control-sm" :rows="isSamples ? 2 : 3"></textarea>
              </div>
              <div v-if="canViewPurchasePrice" class="col-md-4">
                <label class="form-label small">Amount CNY</label>
                <input v-model="orderForm.amount_cny" type="number" step="0.01" class="form-control form-control-sm"/>
              </div>
              <div class="col-md-4">
                <label class="form-label small">Track Number</label>
                <input v-model="orderForm.track_number" class="form-control form-control-sm"/>
              </div>
              <div v-if="!isSamples" class="col-md-4">
                <label class="form-label small">China Exit Date</label>
                <input v-model="orderForm.china_exit_date" type="date" class="form-control form-control-sm"/>
              </div>
              <div v-if="!isSamples" class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Logistic Invoice#</label>
                <input v-model="orderForm.logistic_invoice_no" class="form-control form-control-sm"/>
              </div>
              <div v-if="!isSamples" class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Production Due</label>
                <input v-model="orderForm.production_due_date" type="date" class="form-control form-control-sm"/>
              </div>
              <div class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Payment Date</label>
                <input v-model="orderForm.payment_date" type="date" class="form-control form-control-sm"/>
              </div>

              <div v-if="!isSamples" class="col-6 col-md-4 col-lg-3 mb-2">
                <label class="form-label small">Shipping Code</label>
                <input v-model="orderForm.shipping_code" class="form-control form-control-sm"/>
              </div>

              <div v-if="!isSamples || orderForm.payment_details_qr || qrPreview" class="col-6 payment-qr-col">
                <label class="form-label small">Payment QR</label>
                <div
                    v-if="orderForm.payment_details_qr || qrPreview"
                    class="qr-preview-box mt-2"
                    title="Open QR"
                    @click="showQr(qrPreview || orderForm.payment_details_qr)"
                >
                  <img
                      :src="qrPreview || orderForm.payment_details_qr"
                      class="qr-preview-image"
                      alt="Payment QR"
                  />
                </div>
                <div v-else class="text-muted">—</div>
              </div>
            </div>
          </div>
          </fieldset>
        </form>
        <!-- ▲ ФОРМА ▲ -->
      </div>
    </transition>
    <transition>
      <div v-if="!isSamples && activeTab==='docs'">
        <RelatedDocumentsTree
            v-if="relatedRoot"
            :root="relatedRoot"
            :children="relatedDocs"
            :highlight-id="selectedId"
            empty-text="No related supplier orders."
        />
        <div v-else class="text-muted py-3">
          Parent customer order is not linked.
        </div>
      </div>
    </transition>
    <transition>
      <div v-if="activeTab==='files'">
        <div class="compact-files-block">
          <label class="form-label small">Attachments</label>
          <input
              v-if="canManageOrders"
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
                {{ attachmentName(att) }}
              </a>
              <IconButton
                  v-if="canManageOrders"
                  icon="trash"
                  variant="outline-danger"
                  size="sm"
                  class="ms-2"
                  @click="deleteAttachment(att.id)"
                  :title="$t('Delete attachment')"
              />
            </li>
          </ul>
        </div>
      </div>
    </transition>
    <transition>
      <div v-if="activeTab==='positions'">
        <!-- 1) поиск -->
        <div v-if="canManageOrders" class="position-search position-relative compact-position-search mb-3">
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
              + Create new product: "{{ positionSearch }}"
            </li>
          </ul>
        </div>

        <!-- 2) существующие позиции -->
        <div class="positions-table-wrap">
          <table class="table table-sm align-middle mb-2 positions-table supplier-positions-table">
            <thead v-if="orderItems.length">
            <tr>
              <th class="product-col">{{ $t('Product') }}</th>
              <th class="qty-col">{{ $t('Qty') }}</th>
              <th class="qty-col">{{ $t('Defect qty') }}</th>
              <th class="unit-col">{{ $t('Unit') }}</th>
              <th v-if="canViewPurchasePrice" class="money-col text-end">{{ $t('Purchase price') }}</th>
              <th v-if="canManageOrders" class="action-col"></th>
            </tr>
            </thead>
            <tbody>
            <tr v-for="item in orderItems" :key="item.id">
              <td class="product-col product-link" @click="openProductModalForEdit(item.product)">{{ item.product.name }}
              </td>
              <td class="qty-col">
                <input
                    type="number"
                    step="0.01"
                    class="form-control form-control-sm qty-input"
                    :disabled="!canManageOrders"
                    v-model.number="item.quantity"
                    @change="updatePosition(item)"
                />
              </td>
              <td class="qty-col">
                <input
                    v-model.number="item.defective_quantity"
                    type="number"
                    min="0"
                    :max="item.quantity"
                    step="0.01"
                    class="form-control form-control-sm qty-input"
                    :disabled="!canManageOrders"
                    @change="updatePosition(item)"
                />
              </td>
              <td class="unit-col">{{ item.product.unit?.name || '—' }}</td>
              <td v-if="canViewPurchasePrice" class="money-col">
                <div class="input-group input-group-sm">
                  <input
                      v-model.number="item.unit_price_cny"
                      type="number"
                      min="0"
                      step="0.01"
                      class="form-control text-end"
                      :disabled="!canEditPurchasePrice"
                      @change="updatePosition(item)"
                  />
                  <IconButton
                      v-if="canEditPurchasePrice"
                      icon="arrow-counterclockwise"
                      variant="outline-secondary"
                      size="sm"
                      :title="$t('Restore product purchase price')"
                      @click="resetPurchasePrice(item)"
                  />
                </div>
              </td>
              <td v-if="canManageOrders" class="action-col">
                <IconButton icon="trash" variant="outline-danger" size="sm" :title="$t('Remove position')" @click="removeItem(item.id)" />
              </td>
            </tr>
            <tr v-if="!orderItems.length">
              <td :colspan="supplierPositionColumnCount" class="text-center text-muted">{{ $t('No positions yet.') }}</td>
            </tr>
            </tbody>
          </table>
        </div>
      </div>
    </transition>

    <!-- ▼ HISTORY-MODAL (не тронут) ▼ -->
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

    <div class="modal-backdrop fade history-backdrop" :class="{ show: showHistoryModal }"></div>

    <ProductAddEditModal
        :visible="showProductModal"
        :initial-product="editingProduct"
        :categories="categories"
        :units="units"
        :suppliers="suppliers"
        :read-only="!canManageProducts"
        :can-view-purchase-price="canViewPurchasePrice"
        :can-edit-purchase-price="canEditPurchasePrice"
        :can-view-cost-price="canViewCostPrice"
        :can-view-cost-breakdown="canViewCostBreakdown"
        :can-view-sale-price="canViewSalePrice"
        :can-edit-sale-price="canEditCatalogSalePrice"
        @saved="onProductSaved"
        @reference-created="onReferenceCreated"
        @open-history="openProductHistory"
        @close="showProductModal = false"
    />

    <CounterpartyQuickAddModal
        :visible="showCounterpartyModal"
        :role="counterpartyModalRole"
        :title="counterpartyModalTitle"
        @saved="onCounterpartySaved"
        @close="showCounterpartyModal = false"
    />

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
              <div v-else class="text-center text-muted py-4">
                No changes found.
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" @click="closeProductHistory">Close</button>
            </div>
          </div>
        </transition>
      </div>
    </div>
    <div class="modal-backdrop fade history-backdrop" :class="{ show: showProductHistoryModal }"></div>

    <!-- ▼ QR-MODAL ▼ -->
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
              <button type="button" class="btn-close" @click="qrModalUrl = null"></button>
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
    <!-- ▲ QR-MODAL ▲ -->
  </div>
</template>


<script>
import axios from '../axios';
import ChatShareButton from '../components/ChatShareButton.vue';
import RelatedChatsButton from '../components/RelatedChatsButton.vue';
import CounterpartyQuickAddModal from "../components/CounterpartyQuickAddModal.vue";
import ProductAddEditModal from "../components/ProductAddEditModal.vue";
import RelatedDocumentsTree from "../components/RelatedDocumentsTree.vue";
import SearchableCounterpartySelect from "../components/SearchableCounterpartySelect.vue";
import StatusSelect from "../components/StatusSelect.vue";
import IconButton from "../components/IconButton.vue";
import { clearCacheByPrefix } from "../utils/pageCache";
import { accessState, hasPermission, PERMISSIONS } from '../access';

export default {
  name: 'SupplierOrderDetail',
  components: {RelatedChatsButton, ChatShareButton, CounterpartyQuickAddModal, ProductAddEditModal, RelatedDocumentsTree, SearchableCounterpartySelect, StatusSelect, IconButton},
  data() {
    return {
      isSending: false,
      activeTab: 'order',
      suppressLeaveGuard: false,
      showProductModal: false,
      showCounterpartyModal: false,
      counterpartyModalRole: 'supplier',
      editingProduct: null,
      addProductToOrderAfterSave: false,
      orderItems: [],
      relatedRoot: null,
      relatedDocs: [],
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
      defaultSupplierShippingAddress: '',

      /* форма */
      defaultForm: {
        trip_name: '', order_number: '', status_id: '', supplier_id: '', customer_id: '',
        planned_receipt_date: '', shipment_date: '', delivery_date: '',
        china_exit_date: '', shipping_address: '', shipping_code: '',
        supplier_comment: '', internal_comment: '', amount_cny: '', track_number: '',
        logistic_invoice_no: '', production_due_date: '',
        payment_date: '', payment_details_qr: null, sent_at: null
      },
      orderForm: {},

      /* UI-состояния */
      isSaving: false,
      saveToast: '',
      saveToastTimer: null,
      qrPreview: null,           /* превью только что загруженного QR */
      qrModalUrl: null,
      showQrContent: true,
      historyLogs: [],
      showHistoryModal: false,
      showHistoryContent: false,
      productHistoryLogs: [],
      showProductHistoryModal: false,
      showEditContent: true,

      /* текущее id */
      selectedId: null,
      savedSnapshot: '',
      savedItemIds: [],
    };
  },

  computed: {
    isSamples() { return !!this.$route.meta.samples || !!this.orderForm.is_sample; },
    sectionPath() { return this.isSamples ? '/samples-trips' : '/supplier-orders'; },
    canManageOrders() {
      return hasPermission(PERMISSIONS.SUPPLIER_ORDERS_MANAGE, accessState.user);
    },
    canManageProducts() {
      return hasPermission(PERMISSIONS.PRODUCTS_MANAGE, accessState.user);
    },
    canViewPurchasePrice() {
      return hasPermission(PERMISSIONS.PURCHASE_PRICE_VIEW, accessState.user);
    },
    canEditPurchasePrice() {
      return this.canManageOrders && hasPermission(PERMISSIONS.PURCHASE_PRICE_MANAGE, accessState.user);
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
    supplierPositionColumnCount() {
      return 4 + (this.canViewPurchasePrice ? 1 : 0) + (this.canManageOrders ? 1 : 0);
    },
    isEdit() {
      return !!this.selectedId;
    },
    filesCount() {
      return this.existingAttachments.length + this.attachments.length;
    },
    relatedDocsCount() {
      return this.relatedRoot ? this.relatedDocs.length : 0;
    },
    hasUnsavedChanges() {
      return this.canManageOrders && this.savedSnapshot !== this.currentSnapshot();
    },
    counterpartyModalTitle() {
      return this.counterpartyModalRole === 'supplier' ? 'Add Supplier' : 'Add Customer';
    }
  },

  created() {
    this.selectedId = this.$route.params.id ? +this.$route.params.id : null;
    this.resetForm();
    this.fetchAux().then(async () => {
      if (this.isEdit) {
        await Promise.all([
          this.fetchOrder(),
          this.fetchOrderItems(),
          this.fetchRelatedDocuments(),
        ]);
      }
      this.updateSavedSnapshot();
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
        ]).then(() => this.updateSavedSnapshot());
      } else {
        this.updateSavedSnapshot();
      }
    }
  },

  beforeRouteLeave(to, from, next) {
    if (this.suppressLeaveGuard) {
      next();
      return;
    }
    this.confirmUnsavedChanges({skipRedirect: true})
      .then(canLeave => next(canLeave))
      .catch(() => next(false));
  },

  methods: {
    async sendToSupplier() {
      if (!this.isEdit || !this.orderItems.length || this.hasUnsavedChanges) return;
    if (!confirm('Send order to supplier?')) return;
    this.isSending = true;
    try {
      const { data } = await axios.post(`/api/supplier-order/${this.selectedId}/send/`);
      this.orderForm.sent_at = data.sent_at || new Date().toISOString();
      clearCacheByPrefix('supplier-orders:');
      this.updateSavedSnapshot();
      this.showSaveToast('Order sent');
    } catch (e) {
      console.error(e);
      alert('Unable to send order.');
    } finally {
      this.isSending = false;
    }
  },
    openProductModalForEdit(product) {
      this.editingProduct = product;
      this.addProductToOrderAfterSave = false;
      this.showProductModal = true;
    },
    openProductModalWithName() {
      this.editingProduct = {name: this.positionSearch};
      this.addProductToOrderAfterSave = true;
      this.showProductModal = true;
    },
    openCounterpartyModal(role) {
      this.counterpartyModalRole = role;
      this.showCounterpartyModal = true;
    },
    onCounterpartySaved(counterparty) {
      if (counterparty.is_supplier && !this.suppliers.some(item => item.id === counterparty.id)) {
        this.suppliers.push(counterparty);
      }
      if (counterparty.is_customer && !this.customers.some(item => item.id === counterparty.id)) {
        this.customers.push(counterparty);
      }
      if (this.counterpartyModalRole === 'supplier' && counterparty.is_supplier) {
        this.orderForm.supplier_id = counterparty.id;
      }
      if (this.counterpartyModalRole === 'customer' && counterparty.is_customer) {
        this.orderForm.customer_id = counterparty.id;
      }
      this.showCounterpartyModal = false;
    },
    // 1) подсказки
    async fetchProductSuggestions() {
      if (this.positionSearch.length < 1) {
        this.productSuggestions = []
        return
      }
      const {data} = await axios.get('/api/products/', {
        params: {search: this.positionSearch}
      })
      this.productSuggestions = Array.isArray(data) ? data : (data.results || [])
    },

    // 2) добавить позицию
    async addPosition(product) {
      if (!this.orderForm.supplier_id && product.supplier?.id) {
        this.orderForm.supplier_id = product.supplier.id;
      }
      this.orderItems.push({
        id: `tmp-${Date.now()}-${product.id}`,
        product,
        quantity: 1,
        defective_quantity: 0,
        unit_price_cny: this.numberOrZero(product.purchase_price),
        comment: '',
      });
      this.positionSearch = ''
      this.productSuggestions = []
    },

    // 3) удалить
    async removeItem(itemId) {
      this.orderItems = this.orderItems.filter(item => item.id !== itemId);
    },

    // 4) загрузить список
    async fetchOrderItems() {
      if (!this.selectedId) return;
      const {data} = await axios.get('/api/supplier-order-items/', {
        params: {order: this.selectedId}
      })
      this.orderItems = data.map(this.normalizeOrderItem)
    },

    async fetchRelatedDocuments() {
      if (this.isSamples) return;
      if (!this.selectedId) return;
      const {data} = await axios.get(`/api/supplier-order/${this.selectedId}/related-documents/`);
      this.relatedRoot = data.root;
      this.relatedDocs = data.children || [];
    },

    // 5) менять количество «на лету»
    async unusedEnsureOrderSaved(product = null) {
      if (this.selectedId) return true;

      if (!this.orderForm.supplier_id && product?.supplier?.id) {
        this.orderForm.supplier_id = product.supplier.id;
      }
      if (!this.orderForm.supplier_id) {
        alert('Select supplier before adding positions.');
        return false;
      }

      const fd = new FormData();
        if (!this.isEdit) fd.append('is_sample', this.isSamples ? 'true' : 'false');
      const allowed = [
        'trip_name', 'status_id', 'supplier_id', 'customer_id',
        'planned_receipt_date', 'shipment_date', 'china_exit_date', 'delivery_date',
        'shipping_address', 'shipping_code', 'supplier_comment', 'internal_comment', 'amount_cny',
        'track_number', 'logistic_invoice_no', 'production_due_date', 'payment_date', 'order_number',
      ];
      allowed.forEach(k => {
        const v = this.orderForm[k];
        if (v != null && v !== '') fd.append(k, v);
      });
      this.attachments.forEach(f => fd.append('attachments', f));

      try {
        const {data} = await axios.post('/api/supplier-order/', fd, {
          headers: {'Content-Type': 'multipart/form-data'},
        });
        this.selectedId = data.id;
        this.orderForm = {
          ...this.defaultForm,
          ...data,
          status_id: data.status?.id,
          supplier_id: data.supplier?.id,
          customer_id: data.customer?.id,
        };
        this.attachments = [];
        await this.$router.replace(`${this.sectionPath}/${data.id}`);
        return true;
      } catch (e) {
        console.error('Save error', e.response?.data || e);
        alert('Unable to save order before adding positions.');
        return false;
      }
    },

    async updatePosition(item) {
      item.quantity = this.formatQuantityInput(item.quantity);
      item.defective_quantity = this.formatQuantityInput(item.defective_quantity);
      item.unit_price_cny = this.formatQuantityInput(item.unit_price_cny);
      if (item.defective_quantity > item.quantity) {
        item.defective_quantity = item.quantity;
      }
    },
    resetPurchasePrice(item) {
      item.unit_price_cny = this.numberOrZero(item.product?.purchase_price);
    },
    async onProductSaved(product) {
      this.showProductModal = false;
      this.positionSearch = '';
      this.productSuggestions = [];
      if (!this.addProductToOrderAfterSave) {
        this.orderItems = this.orderItems.map(item =>
          item.product?.id === product.id ? {...item, product} : item
        );
        this.addProductToOrderAfterSave = false;
        return;
      }
      this.addProductToOrderAfterSave = false;
      if (!this.selectedId) {
        if (!this.orderForm.supplier_id && product.supplier?.id) {
          this.orderForm.supplier_id = product.supplier.id;
        }
        this.orderItems.push({
          id: `tmp-${Date.now()}-${product.id}`,
          product,
          quantity: 1,
          defective_quantity: 0,
          unit_price_cny: this.numberOrZero(product.purchase_price),
          comment: '',
        });
        return;
      }
      if (!this.orderForm.supplier_id && product.supplier?.id) {
        this.orderForm.supplier_id = product.supplier.id;
      }
      this.orderItems.push({
        id: `tmp-${Date.now()}-${product.id}`,
        product,
        quantity: 1,
        defective_quantity: 0,
        unit_price_cny: this.numberOrZero(product.purchase_price),
        comment: '',
      });
    },
    onReferenceCreated({type, item}) {
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
    /* --- навигация --- */
    goBack() {
      this.leaveToOrders();
    },
    async leaveToOrders() {
      const query = this.selectedId ? {highlight: this.selectedId} : {};
      this.$router.push({path: this.sectionPath, query});
    },
    async confirmUnsavedChanges(saveOptions = {}) {
      if (!this.hasUnsavedChanges) return true;
      if (confirm('Save changes before leaving?')) {
        const saved = await this.saveOrder({silent: true, ...saveOptions});
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

    /* --- util --- */
    resetForm() {
      this.orderForm = {...this.defaultForm};
      this.orderItems = [];
      this.relatedRoot = null;
      this.relatedDocs = [];
    },
    currentSnapshot() {
      return JSON.stringify({
        order: {
          trip_name: this.orderForm.trip_name || '',
          status_id: this.orderForm.status_id || '',
          supplier_id: this.orderForm.supplier_id || '',
          customer_id: this.orderForm.customer_id || '',
          planned_receipt_date: this.orderForm.planned_receipt_date || '',
          shipment_date: this.orderForm.shipment_date || '',
          china_exit_date: this.orderForm.china_exit_date || '',
          delivery_date: this.orderForm.delivery_date || '',
          shipping_address: this.orderForm.shipping_address || '',
          shipping_code: this.orderForm.shipping_code || '',
          supplier_comment: this.orderForm.supplier_comment || '',
          internal_comment: this.orderForm.internal_comment || '',
          amount_cny: this.orderForm.amount_cny || '',
          track_number: this.orderForm.track_number || '',
          logistic_invoice_no: this.orderForm.logistic_invoice_no || '',
          production_due_date: this.orderForm.production_due_date || '',
          payment_date: this.orderForm.payment_date || '',
        },
        items: this.orderItems.map(item => ({
          id: item.id,
          product_id: item.product?.id,
          quantity: this.numberOrZero(item.quantity),
          defective_quantity: this.numberOrZero(item.defective_quantity),
          unit_price_cny: this.numberOrZero(item.unit_price_cny),
          comment: item.comment || '',
        })),
        attachments: this.attachments.map(file => file.name),
      });
    },
    updateSavedSnapshot() {
      this.savedSnapshot = this.currentSnapshot();
      this.savedItemIds = this.orderItems
        .filter(item => !String(item.id).startsWith('tmp-'))
        .map(item => item.id);
    },
    numberOrZero(value) {
      const numberValue = Number(String(value ?? 0).replace(',', '.'));
      return Number.isFinite(numberValue) ? numberValue : 0;
    },
    formatQuantityInput(value) {
      return this.numberOrZero(value);
    },
    formatPrice(value) {
      const numberValue = this.numberOrZero(value);
      return numberValue ? numberValue.toLocaleString('ru-RU', { maximumFractionDigits: 2 }) : '—';
    },
    normalizeOrderItem(item) {
      return {
        ...item,
        quantity: this.formatQuantityInput(item.quantity),
        defective_quantity: this.formatQuantityInput(item.defective_quantity),
        unit_price_cny: this.numberOrZero(item.unit_price_cny ?? item.product?.purchase_price),
      };
    },
    formatDate(v) {
      return v ? new Date(v).toLocaleString() : '—';
    },

    /* --- справочники --- */
    async fetchAux() {
      try {
        const [
          supplierRes,
          customerRes,
          stRes,
          catRes,
          unitRes
        ] = await Promise.all([
          axios.get('/api/counterparties/options/', { params: { role: 'supplier' } }),
          axios.get('/api/counterparties/options/', { params: { role: 'customer' } }),
          axios.get('/api/supplier-order-statuses/'),
          axios.get('/api/product-category/'),
          axios.get('/api/units/'),
        ]);

        this.suppliers = supplierRes.data;
        this.customers = customerRes.data;
        this.statuses = stRes.data;
        this.categories = catRes.data;
        this.units = unitRes.data;
        await this.fetchDefaultSupplierShippingAddress();
        if (!this.isEdit && !this.orderForm.shipping_address && this.defaultSupplierShippingAddress) {
          this.orderForm.shipping_address = this.defaultSupplierShippingAddress;
        }
      } catch (e) {
        console.error(e);
        alert('Unable to load reference data.');
      }
    },

    async fetchDefaultSupplierShippingAddress() {
      const {data} = await axios.get('/api/settings/');
      const settings = Array.isArray(data) ? data[0] : data;
      this.defaultSupplierShippingAddress = settings?.company_china_warehouse_address || '';
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
        alert('Unable to load order.');
      }
    },

    async saveOrder(options = {}) {
      const silent = options?.silent === true;
      const skipRedirect = options?.skipRedirect === true;
      if (this.isEdit && !this.hasUnsavedChanges) {
        if (!silent) this.showSaveToast('No changes to save');
        return this.orderForm;
      }
      this.isSaving = true;
      const pendingItems = this.selectedId ? [] : [...this.orderItems];
      try {
        /* 1. собираем form-data */
        const fd = new FormData();
        if (!this.isEdit) fd.append('is_sample', this.isSamples ? 'true' : 'false');
        const allowed = [
          'trip_name', 'status_id', 'supplier_id', 'customer_id',
          'planned_receipt_date', 'shipment_date', 'china_exit_date', 'delivery_date',
          'shipping_address', 'shipping_code', 'supplier_comment', 'internal_comment', 'amount_cny',
          'track_number', 'logistic_invoice_no', 'production_due_date', 'payment_date', 'order_number',
        ];
        allowed.forEach(k => {
          const v = this.orderForm[k];
          if (v != null && (v !== '' || ['trip_name', 'shipping_address', 'supplier_comment', 'internal_comment'].includes(k))) fd.append(k, v);
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
          const currentExistingIds = this.orderItems
            .filter(item => !String(item.id).startsWith('tmp-'))
            .map(item => item.id);
          const removedIds = this.savedItemIds.filter(id => !currentExistingIds.includes(id));
          for (const itemId of removedIds) {
            await axios.delete(`/api/supplier-order-items/${itemId}/`);
          }
          for (const item of this.orderItems) {
            if (String(item.id).startsWith('tmp-')) {
              await axios.post('/api/supplier-order-items/', {
                order: this.selectedId,
                product_id: item.product.id,
                quantity: item.quantity,
                defective_quantity: item.defective_quantity || 0,
                unit_price_cny: item.unit_price_cny,
                comment: item.comment || '',
              });
            } else {
              await axios.patch(`/api/supplier-order-items/${item.id}/`, {
                quantity: item.quantity,
                defective_quantity: item.defective_quantity || 0,
                unit_price_cny: item.unit_price_cny,
                comment: item.comment || '',
              });
            }
          }
          await this.fetchOrderItems();
          this.orderForm = {...this.orderForm, ...res.data};
          if (!silent) this.showSaveToast('Order saved');
        } else {
          /* POST → переводим страницу в режим редактирования созданного заказа */
          res = await axios.post('/api/supplier-order/', fd, cfg);
          const newOrderId = res.data.id;
          for (const item of pendingItems) {
            await axios.post('/api/supplier-order-items/', {
              order: newOrderId,
              product_id: item.product.id,
              quantity: item.quantity,
              defective_quantity: item.defective_quantity || 0,
              unit_price_cny: item.unit_price_cny,
              comment: item.comment || '',
            });
          }
          this.selectedId = newOrderId;
          this.orderForm = {
            ...this.defaultForm,
            ...res.data,
            status_id: res.data.status?.id,
            supplier_id: res.data.supplier?.id,
            customer_id: res.data.customer?.id,
          };
          if (!silent) this.showSaveToast('Order created');
          if (!skipRedirect) {
            this.suppressLeaveGuard = true;
            await this.$router.replace(`${this.sectionPath}/${res.data.id}`);
            this.suppressLeaveGuard = false;
          }
          await this.fetchOrderItems();
          this.attachments = [];
        clearCacheByPrefix('supplier-orders:');
        this.updateSavedSnapshot();
          return res.data;
          return;                /* компонент перезагрузится watcher-ом */
        }

        /* очищаем буферы */
        this.attachments = [];
        clearCacheByPrefix('supplier-orders:');
        this.updateSavedSnapshot();
        return res.data;

      } catch (e) {
        console.error('Save error', e.response?.data || e);
        alert('Unable to save order. Please check the fields.');
      } finally {
        this.isSaving = false;
      }
    },

    /* --- вложения --- */
    async deleteAttachment(id) {
      if (!confirm('Delete this file?')) return;
      try {
        await axios.delete(`/api/supplier-order/${this.selectedId}/attachments/${id}/`);
        this.existingAttachments = this.existingAttachments.filter(a => a.id !== id);
      } catch (e) {
        console.error(e);
        alert('Unable to delete file.');
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

    fieldLabel(k) {
      const m = {
        trip_name: 'Trip / exhibition / meeting', is_sample: 'Samples and trips', order_number: 'Order#', supplier_id: 'Supplier', customer_id: 'Customer',
        planned_receipt_date: 'Plan Receipt', shipment_date: 'Shipment',
        delivery_date: 'Delivery', amount_cny: 'Amount CNY', track_number: 'Track#',
        item_unit_price_cny: 'Item purchase price, CNY',
        logistic_invoice_no: 'Logistic Invoice#', china_exit_date: 'China Exit',
        production_due_date: 'Production Due', payment_date: 'Payment Date',
        payment_details_qr: 'Payment QR', shipping_address: 'Address',
        shipping_code: 'Code', supplier_comment: 'Supplier Comment',
        internal_comment: 'Comment', status_id: 'Status'
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
    attachmentName(att) {
      if (att.file_name) return att.file_name;
      const rawName = att.file ? att.file.split('/').pop() : '';
      try {
        return decodeURIComponent(rawName);
      } catch {
        return rawName;
      }
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

.order-actions {
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.send-action {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
}

.sent-note {
  margin-top: 0.25rem;
  color: #557066;
  font-size: 0.76rem;
  line-height: 1.1;
  white-space: nowrap;
}

.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity .3s, transform .3s;
}

.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.history-modal-body {
  max-height: calc(100vh - 220px);
  overflow-y: auto;
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
.sample-form > .row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem;
  margin: 0;
  max-width: 900px;
}
.order-form-grid.sample-form > .row > div[class*="col-"] {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0;
}
.sample-form > .row > .col-12 {
  grid-column: 1 / -1;
}
.sample-form .sample-comment { order: 1; }
.sample-form .payment-qr-col { order: 2; }
.sample-form .qr-preview-box { width: 120px; height: 120px; padding: 8px; }
@media (max-width: 575.98px) {
  .sample-form > .row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

.compact-text-field {
  max-width: 760px;
}
.compact-files-block {
  max-width: 520px;
}
.quick-add-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  padding-right: 0;
  padding-left: 0;
  font-weight: 600;
  line-height: 1;
}
.order-form-grid [class*="col-"]:not(.col-12):not(.col-6) {
  flex: 0 0 auto;
  width: min(100%, 250px);
}
.order-form-grid .col-6:not(.payment-qr-col) {
  flex: 0 0 auto;
  width: min(100%, 250px);
}
.order-form-grid .col-12 textarea {
  width: 100%;
}
.qr-preview-box,
.qr-modal-frame {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #d8e0e7;
  border-radius: 8px;
  background: #fff;
}
.qr-preview-box {
  width: 220px;
  height: 220px;
  padding: 12px;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}
.qr-preview-box:hover {
  border-color: #7f95a8;
  box-shadow: 0 8px 22px rgba(47, 63, 80, 0.12);
  transform: translateY(-1px);
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
.qr-preview-image,
.qr-modal-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.qr-modal-frame {
  width: min(360px, calc(100vw - 4rem));
  height: min(360px, calc(100vw - 4rem));
  margin: 0 auto;
  padding: 14px;
}
.product-link {
  color: #0d6efd;
  cursor: pointer;
}
.product-link:hover {
  color: #0a58ca;
  text-decoration: underline;
}
.positions-table-wrap {
  max-width: 760px;
  overflow-x: auto;
}
.positions-table {
  table-layout: fixed;
  min-width: 560px;
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
.supplier-positions-table {
  width: auto;
}
.unit-col {
  width: 78px;
}
.qty-col {
  width: 86px;
}
.qty-input {
  width: 64px;
  text-align: center;
}
.money-col {
  width: 120px;
}
.action-col {
  width: 48px;
  text-align: center;
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
