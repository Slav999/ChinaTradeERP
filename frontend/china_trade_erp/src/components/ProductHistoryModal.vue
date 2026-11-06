<template>
  <Teleport to="body">
    <div
      class="modal fade history-modal"
      :class="{ show: visible }"
      :style="visible ? 'display: block;' : ''"
      tabindex="-1"
    >
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <transition name="modal-fade">
          <div v-if="visible" class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ $t('Change History') }}</h5>
            <button type="button" class="btn-close" :aria-label="$t('Close')" @click="$emit('close')"></button>
          </div>
          <div class="modal-body history-modal-body">
            <div v-if="loading" class="text-center text-muted py-4">{{ $t('Loading...') }}</div>
            <table v-else-if="logs.length" class="table table-striped">
              <thead>
                <tr>
                  <th>{{ $t('Date') }}</th>
                  <th>{{ $t('User') }}</th>
                  <th>{{ $t('Field') }}</th>
                  <th>{{ $t('From') }}</th>
                  <th>{{ $t('To') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(log, idx) in logs" :key="idx">
                  <td>{{ log.changed_at }}</td>
                  <td>{{ log.changed_by }}</td>
                  <td>{{ fieldLabel(log) }}</td>
                  <td>{{ oldValue(log) }}</td>
                  <td>{{ newValue(log) }}</td>
                </tr>
              </tbody>
            </table>
            <div v-else class="text-center text-muted py-4">{{ $t('No changes found.') }}</div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="$emit('close')">{{ $t('Close') }}</button>
          </div>
          </div>
        </transition>
      </div>
    </div>
    <div v-if="visible" class="modal-backdrop fade show history-backdrop"></div>
  </Teleport>
</template>

<script>
import axios from '../axios';

export default {
  name: 'ProductHistoryModal',
  props: {
    visible: { type: Boolean, default: false },
    productId: { type: [Number, String], default: null },
    categories: { type: Array, default: () => [] },
    units: { type: Array, default: () => [] },
    suppliers: { type: Array, default: () => [] },
  },
  emits: ['close'],
  data() {
    return { logs: [], loading: false, requestId: 0 };
  },
  watch: {
    visible(value) {
      if (value) this.loadHistory();
    },
    productId() {
      if (this.visible) this.loadHistory();
    },
  },
  methods: {
    async loadHistory() {
      if (!this.productId) {
        this.logs = [];
        return;
      }
      const requestId = ++this.requestId;
      this.loading = true;
      try {
        const { data } = await axios.get(`/api/products/${this.productId}/history/`);
        if (requestId === this.requestId) this.logs = data;
      } catch {
        if (requestId === this.requestId) this.logs = [];
      } finally {
        if (requestId === this.requestId) this.loading = false;
      }
    },
    isArchiveLog(log) {
      return log.field_name === 'is_archived';
    },
    fieldLabel(log) {
      if (this.isArchiveLog(log)) return this.$t(log.new_value === 'True' ? 'Archived' : 'Restored');
      const labels = {
        name: 'Name', sku: 'SKU', description: 'Description', category_id: 'Category',
        unit_id: 'Unit', supplier_id: 'Supplier', purchase_price: 'Purchase Price',
        sale_price: 'Sale Price', image: 'Image', is_stock_item: 'Warehouse item',
        minimum_stock: 'Minimum stock', average_monthly_consumption: 'Average monthly consumption',
      };
      return this.$t(labels[log.field_name] || log.field_name);
    },
    oldValue(log) {
      return this.isArchiveLog(log) ? '—' : this.formatValue(log.field_name, log.old_value);
    },
    newValue(log) {
      return this.isArchiveLog(log) ? '—' : this.formatValue(log.field_name, log.new_value);
    },
    formatValue(field, value) {
      const collections = { category_id: this.categories, unit_id: this.units, supplier_id: this.suppliers };
      if (collections[field]) {
        return collections[field].find(item => String(item.id) === String(value))?.name || '—';
      }
      if (field === 'image') return value ? value.split('/').pop() : '—';
      return value != null && value !== '' ? value : '—';
    },
  },
};
</script>

<style scoped>
.history-modal { padding-left: 0 !important; padding-right: 0 !important; z-index: 1070; }
.history-modal .modal-dialog { margin-left: auto; margin-right: auto; width: calc(100% - 1rem); }
.history-backdrop { z-index: 1065; }
.history-modal-body { max-height: calc(100vh - 220px); overflow-y: auto; }
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity .3s ease, transform .3s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; transform: translateY(-10px); }
.modal-fade-enter-to, .modal-fade-leave-from { opacity: 1; transform: translateY(0); }
@media (max-width: 575.98px) {
  .history-modal .modal-dialog { margin-bottom: .5rem; margin-top: .5rem; }
  .history-modal-body { max-height: calc(100vh - 150px); overflow-x: auto; }
}
</style>
