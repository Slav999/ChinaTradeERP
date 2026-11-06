<template>
  <div class="container mt-4">
    <ChatRecordPreview />
    <transition name="save-toast">
      <div v-if="saveToast" class="save-toast">
        {{ saveToast }}
      </div>
    </transition>

    <h1 class="mb-4">Counterparties</h1>

    <!-- Search & Filters -->
    <div class="row mb-3 g-2">
      <div class="col-md-4">
        <input
            v-model.trim="searchQuery"
            @input="onSearchInput"
            type="text"
            class="form-control"
            placeholder="Search by name/code/email..."
        />
      </div>
      <div class="col-md-2">
        <select v-model="filters.type" class="form-select" @change="onFiltersChanged">
          <option disabled selected hidden value="">Select region...</option>
          <option value="china">Chinese</option>
          <option value="local">Local</option>
        </select>
      </div>
      <div class="col-md-2">
        <select v-model="filters.role" class="form-select" @change="onFiltersChanged">
          <option disabled selected hidden value="">Select role...</option>
          <option value="supplier">Supplier</option>
          <option value="customer">Customer</option>
        </select>
      </div>
      <div class="col-md-2">
        <StatusSelect
            v-model="filters.status"
            :statuses="statuses"
            placeholder="Select status..."
            clearable
            @change="onFiltersChanged"
        />
      </div>
      <div class="col-md-2 d-flex align-items-end">
        <button class="btn btn-secondary w-100" @click="resetFilters">Reset</button>
      </div>
    </div>

    <!-- Add Button -->
    <button v-if="canManageCounterparties" class="btn btn-primary mb-3 d-block mx-auto" @click="openModal">
      + Add Counterparty
    </button>

    <!-- Table -->
    <div class="table-responsive">
      <table class="table table-hover table-bordered align-middle counterparties-table">
        <thead class="table-light">
        <tr>
          <th class="counterparty-name-col">Name</th>
          <th>Region</th>
          <th>Roles</th>
          <th class="d-none d-md-table-cell">Phone</th>
          <th class="d-none d-md-table-cell">Email</th>
          <th class="d-none d-lg-table-cell">Source</th>
          <th>Code</th>
          <th class="d-none d-md-table-cell">Address</th>
          <th>Status</th>
          <th class="actions-col">Actions</th>
        </tr>
        </thead>
        <tbody>
        <tr
            v-for="item in counterparties"
            :key="item.id"
            @click="canManageCounterparties && editCounterparty(item)"
            :style="canManageCounterparties ? 'cursor: pointer;' : ''"
        >
          <td>{{ item.name }}</td>
          <td>
              <span :class="['badge', item.type === 'china' ? 'bg-success' : 'bg-secondary']">
                {{ item.type === 'china' ? 'Chinese' : 'Local' }}
              </span>
          </td>
          <td>
            <span v-if="item.is_supplier" class="badge bg-primary me-1">Supplier</span>
            <span v-if="item.is_customer" class="badge bg-info text-dark">Customer</span>
            <span v-if="!item.is_supplier && !item.is_customer" class="text-muted">—</span>
          </td>
          <td class="d-none d-md-table-cell">{{ item.phone || '—' }}</td>
          <td class="d-none d-md-table-cell">{{ item.email || '—' }}</td>
          <td class="d-none d-lg-table-cell">{{ item.source || '—' }}</td>
          <td>{{ item.unique_code }}</td>
          <td class="d-none d-md-table-cell">{{ item.address || '—' }}</td>
          <td>
              <span
                  v-if="item.status && (item.status.display_name || item.status.name)"
                  class="badge rounded-pill"
                  :style="{ backgroundColor: item.status.color, color: '#fff' }"
              >
                {{ item.status.display_name || item.status.name }}
              </span>
            <span v-else class="text-muted">—</span>
          </td>
          <td class="actions-cell" @click.stop>
            <div class="actions-group">
              <ChatShareButton type="counterparty" :record-id="item.id" :title="item.name" compact />
              <button
                  v-if="item.qr_code_image"
                  class="btn btn-sm btn-secondary"
                  @click="showQr(item.qr_code_image)"
              >QR
              </button>
              <button v-if="canManageCounterparties" class="btn btn-sm btn-danger" @click="deleteCounterparty(item.id)">
                Delete
              </button>
            </div>
          </td>
        </tr>
        <tr v-if="isLoading">
          <td colspan="10" class="text-center text-muted">Loading...</td>
        </tr>
        <tr v-else-if="!counterparties.length">
          <td colspan="10" class="text-center text-muted">No counterparties yet.</td>
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
              <h5 class="modal-title">{{ isEdit ? 'Edit' : 'Add' }} Counterparty</h5>
              <button type="button" class="btn-close" @click="closeModal"></button>
            </div>
            <div class="modal-body">
              <!-- Audit Block -->
              <div
                  v-if="isEdit"
                  class="audit-info mt-3 mb-3 p-3 bg-light rounded border"
                  @click="openHistory"
                  style="cursor: pointer;"
              >
                <div class="row">
                  <div class="col text-muted small">
                    <strong>Created At:</strong> {{ formatDate(counterpartyForm.created_at) }}
                  </div>
                  <div class="col text-muted small">
                    <strong>Updated At:</strong> {{ formatDate(counterpartyForm.updated_at) }}
                  </div>
                </div>
                <div class="row mt-2">
                  <div class="col text-muted small">
                    <strong>Created By:</strong> {{ counterpartyForm.created_by || '—' }}
                  </div>
                  <div class="col text-muted small">
                    <strong>Updated By:</strong> {{ counterpartyForm.updated_by || '—' }}
                  </div>
                </div>
              </div>

              <form @submit.prevent="saveCounterparty">
                <div class="row gy-3">
                  <div class="col-md-6">
                    <label class="form-label">Name</label>
                    <input v-model="counterpartyForm.name" type="text" class="form-control" required/>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Region</label>
                    <select v-model="counterpartyForm.type" class="form-select">
                      <option value="china">Chinese</option>
                      <option value="local">Local</option>
                    </select>
                  </div>
                  <div class="col-12">
                    <label class="form-label">Roles</label>
                    <div class="d-flex flex-wrap gap-3">
                      <div class="form-check">
                        <input
                            id="counterpartyIsSupplier"
                            v-model="counterpartyForm.is_supplier"
                            class="form-check-input"
                            type="checkbox"
                        />
                        <label class="form-check-label" for="counterpartyIsSupplier">Supplier</label>
                      </div>
                      <div class="form-check">
                        <input
                            id="counterpartyIsCustomer"
                            v-model="counterpartyForm.is_customer"
                            class="form-check-input"
                            type="checkbox"
                        />
                        <label class="form-check-label" for="counterpartyIsCustomer">Customer</label>
                      </div>
                    </div>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Unique Code</label>
                    <input v-model="counterpartyForm.unique_code" class="form-control"/>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Status</label>
                    <StatusSelect v-model="counterpartyForm.status_id" :statuses="statuses" />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Phone</label>
                    <input v-model="counterpartyForm.phone" class="form-control"/>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Email</label>
                    <input type="email" v-model="counterpartyForm.email" class="form-control"/>
                  </div>
                  <div class="col-12">
                    <label class="form-label">Address</label>
                    <input v-model="counterpartyForm.address" class="form-control"/>
                  </div>
                  <div class="col-12">
                    <label class="form-label">Source</label>
                    <input v-model="counterpartyForm.source" class="form-control"/>
                  </div>
                  <div class="col-12">
                    <label class="form-label">QR Code Image</label>
                    <input ref="qrInput" type="file" class="form-control" @change="handleQrUpload"/>
                    <div
                        v-if="qrPreview"
                        class="qr-preview-box mt-2"
                        title="Open QR"
                        @click="showQr(qrPreview)"
                    >
                      <img :src="qrPreview" class="qr-preview-image" alt="QR preview"/>
                    </div>
                  </div>
                </div>
              </form>
            </div>
            <div class="modal-footer">
              <div v-if="isEdit && selectedId" class="me-auto d-flex flex-wrap gap-2">
                <ChatShareButton type="counterparty" :record-id="Number(selectedId)" :title="counterpartyForm.name" @shared="closeModal" />
                <RelatedChatsButton v-if="showModal" type="counterparty" :record-id="Number(selectedId)" :title="counterpartyForm.name" @opened="closeModal" />
              </div>
              <button class="btn btn-secondary" @click="closeModal">Cancel</button>
              <button v-if="canManageCounterparties" class="btn btn-primary" @click="saveCounterparty">
                {{ isEdit ? 'Save' : 'Create' }}
              </button>
            </div>
          </div>
        </transition>
      </div>
    </div>
    <div class="modal-backdrop fade edit-backdrop" :class="{ show: showModal }"></div>

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

    <!-- QR Preview Modal -->
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
  </div>
</template>

<script>
import axios from '../axios';
import ChatRecordPreview from '../components/ChatRecordPreview.vue';
import ChatShareButton from '../components/ChatShareButton.vue';
import RelatedChatsButton from '../components/RelatedChatsButton.vue';
import debounce from 'lodash/debounce';
import { clearCacheByPrefix, getCachedJson, setCachedJson } from '../utils/pageCache';
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
import { accessState, hasPermission, PERMISSIONS } from '../access';
import StatusSelect from '../components/StatusSelect.vue';

const TABLE_STATE_KEY = 'counterparties-table-state';

export default {
  name: 'CounterpartyView',
  components: { ChatShareButton, RelatedChatsButton, ChatRecordPreview, StatusSelect },
  data() {
    return {
      showEditContent: true,
      showHistoryContent: true,
      showQrContent: true,
      counterparties: [],
      statuses: [],
      showModal: false,
      isEdit: false,
      selectedId: null,
      qrPreview: null,
      qrModalUrl: null,
      historyLogs: [],
      showHistoryModal: false,
      saveToast: '',
      saveToastTimer: null,
      searchQuery: '',
      filters: {type: '', role: '', status: ''},
      page: 1,
      pageSize: DEFAULT_PAGE_SIZE,
      totalCount: 0,
      isLoading: false,
      defaultForm: {
        id: null,
        name: '',
        type: 'local',
        is_supplier: false,
        is_customer: true,
        unique_code: '',
        address: '',
        phone: '',
        email: '',
        source: '',
        status_id: null,
        qr_code_image: null,
        created_at: null,
        created_by: null,
        updated_at: null,
        updated_by: null
      },
      counterpartyForm: {}
    };
  },
  created() {
    this.resetForm();
    this.restoreTableState();
    this.fetchCounterparties({ useCache: true });
    this.fetchStatuses();
  },
  computed: {
    canManageCounterparties() {
      return hasPermission(PERMISSIONS.COUNTERPARTIES_MANAGE, accessState.user);
    },
    totalPages() {
      return pageMeta(this.page, this.totalCount, this.pageSize).totalPages;
    },
    pageStart() {
      return pageMeta(this.page, this.totalCount, this.pageSize).pageStart;
    },
    pageEnd() {
      return pageMeta(this.page, this.totalCount, this.pageSize).pageEnd;
    }
  },
  methods: {
    onSearchInput: debounce(function () {
      this.onFiltersChanged();
    }, 300),
    onFiltersChanged() {
      this.page = 1;
      this.saveTableState();
      this.fetchCounterparties();
    },
    resetFilters() {
      this.searchQuery = '';
      this.filters = {type: '', role: '', status: ''};
      this.page = 1;
      this.saveTableState();
      this.fetchCounterparties();
    },
    resetForm() {
      this.counterpartyForm = {...this.defaultForm};
    },
    async fetchCounterparties({ useCache = false } = {}) {
      const cacheKey = this.counterpartiesCacheKey();
      const cached = getCachedTablePage(cacheKey, useCache);
      if (cached) {
        this.applyCounterpartiesResponse(cached);
      }

      this.isLoading = !cached;
      try {
        const res = await axios.get('/api/counterparties/', {
          params: this.counterpartyQueryParams()
        });
        setCachedTablePage(cacheKey, res.data);
        this.applyCounterpartiesResponse(res.data);
        this.isLoading = false;
      } catch (e) {
        console.error(e);
        this.isLoading = false;
      }
    },
    async fetchStatuses() {
      const cached = getCachedJson('counterparty-statuses');
      if (cached) {
        this.statuses = cached;
        return;
      }

      const res = await axios.get('/api/counterparty-statuses/');
      this.statuses = res.data;
      setCachedJson('counterparty-statuses', this.statuses);
    },
    counterpartyQueryParams() {
      return {
        page: this.page,
        page_size: this.pageSize,
        search: this.searchQuery || undefined,
        type: this.filters.type || undefined,
        role: this.filters.role || undefined,
        status: this.filters.status || undefined,
      };
    },
    counterpartiesCacheKey() {
      return makeTableCacheKey('counterparties', this.counterpartyQueryParams());
    },
    applyCounterpartiesResponse(data) {
      applyPaginatedData(this, data, 'counterparties');
    },
    saveTableState() {
      saveTableStateSnapshot(TABLE_STATE_KEY, this);
    },
    restoreTableState() {
      const state = restoreTableStateSnapshot(TABLE_STATE_KEY, {
        page: 1,
        searchQuery: '',
        filters: {type: '', role: '', status: ''},
      });
      this.page = state.page;
      this.searchQuery = state.searchQuery;
      this.filters = {
        type: state.filters?.type || '',
        role: state.filters?.role || '',
        status: state.filters?.status || '',
      };
    },
    changePage(page) {
      changeTablePage(this, page, 'fetchCounterparties');
    },
    openModal() {
      this.resetForm();
      this.isEdit = false;
      this.showModal = true;
      this.showEditContent = true;
      this.selectedId = null;
      this.qrPreview = null;
      this.resetQrInput();
    },
    closeModal() {
      this.showModal = false;
      this.resetQrInput();
    },
    editCounterparty(item) {
      this.counterpartyForm = {
        ...this.defaultForm,
        ...item,
        status_id: item.status?.id || null,
        qr_code_image: null
      };
      this.isEdit = true;
      this.showModal = true;
      this.selectedId = item.id;
      this.qrPreview = item.qr_code_image || null;
      this.resetQrInput();
    },
    async saveCounterparty() {
      try {
        const formData = new FormData();
        Object.entries(this.counterpartyForm).forEach(([k, v]) => {
          if (v !== null && v !== undefined) formData.append(k, v);
        });
        const cfg = {headers: {'Content-Type': 'multipart/form-data'}};
        let res;
        if (this.isEdit && this.selectedId) {
          res = await axios.put(`/api/counterparties/${this.selectedId}/`, formData, cfg);
          const idx = this.counterparties.findIndex(x => x.id === this.selectedId);
          if (idx !== -1) this.counterparties.splice(idx, 1, res.data);
        } else {
          res = await axios.post('/api/counterparties/', formData, cfg);
          this.counterparties.unshift(res.data);
          this.isEdit = true;
          this.selectedId = res.data.id;
        }
        this.counterpartyForm = {
          ...this.defaultForm,
          ...res.data,
          status_id: res.data.status?.id || null,
          qr_code_image: null
        };
        this.qrPreview = res.data.qr_code_image || null;
        this.resetQrInput();
        clearCacheByPrefix('counterparties:');
        clearCacheByPrefix('counterparty-options');
        clearCacheByPrefix('supplier-orders:');
        clearCacheByPrefix('customer-orders:');
        this.fetchCounterparties();
        this.showSaveToast('Counterparty saved');
      } catch (err) {
        console.error('Save error:', err.response?.data || err);
      }
    },
    showSaveToast(message) {
      this.saveToast = message;
      clearTimeout(this.saveToastTimer);
      this.saveToastTimer = setTimeout(() => {
        this.saveToast = '';
      }, 1800);
    },
    async deleteCounterparty(id) {
      if (confirm('Delete this counterparty?')) {
        try {
          await axios.delete(`/api/counterparties/${id}/`);
          clearCacheByPrefix('counterparties:');
          clearCacheByPrefix('counterparty-options');
          this.counterparties = this.counterparties.filter(x => x.id !== id);
          this.totalCount = Math.max(0, this.totalCount - 1);
        } catch (error) {
          const detail = error.response?.data?.detail || 'Unable to delete counterparty.';
          alert(detail);
        }
      }
    },
    showQr(url) {
      this.showQrContent = true;
      this.qrModalUrl = url;
    },
    closeQr() {
      this.showQrContent = false;
      this.qrModalUrl = null;
    },
    handleQrUpload(ev) {
      const f = ev.target.files[0];
      if (f) {
        this.counterpartyForm.qr_code_image = f;
        this.qrPreview = URL.createObjectURL(f);
      }
    },
    resetQrInput() {
      this.counterpartyForm.qr_code_image = null;
      if (this.$refs.qrInput) {
        this.$refs.qrInput.value = '';
      }
    },
    openHistory() {
      if (!this.selectedId) return;
      this.showEditContent = false;    // прячем форму
      axios.get(`/api/counterparties/${this.selectedId}/history/`)
          .then(res => {
            this.historyLogs = res.data;
            this.showHistoryContent = true;
            this.showHistoryModal = true;  // открываем историю
          });
    },
    closeHistory() {
      this.showHistoryModal = false;
      this.showHistoryContent = false;
      if (this.isEdit) this.showEditContent = true;
    },
    fieldLabel(key) {
      const map = {
        name: 'Name',
        type: 'Region',
        is_supplier: 'Supplier role',
        is_customer: 'Customer role',
        address: 'Address',
        phone: 'Phone',
        email: 'Email',
        source: 'Source',
        status_id: 'Status',
        qr_code_image: 'QR Image'
      };
      return map[key] || key;
    },
    formatValue(field, val) {
      if (field === 'status_id') {
        const s = this.statuses.find(x => String(x.id) === String(val));
        return s ? s.name : '—';
      }
      if (field === 'qr_code_image') {
        return val ? val.split('/').pop() : '—';
      }
      return val || '—';
    },
    formatDate(value) {
      return value
          ? new Date(value).toLocaleString()
          : '—';
    }
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

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.modal-fade-enter-to,
.modal-fade-leave-from {
  opacity: 1;
  transform: translateY(0);
}

.history-modal-body {
  max-height: calc(100vh - 220px);
  overflow-y: auto;
}

.counterparties-table th,
.counterparties-table td {
  padding: 0.55rem 0.6rem;
}

.counterparties-table .badge {
  font-weight: 600;
}

.counterparty-name-col {
  min-width: 180px;
}

.actions-col {
  min-width: 145px;
}

.actions-cell {
  min-width: 145px;
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

.qr-preview-box,
.qr-modal-frame {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: auto;
  margin-right: auto;
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
  padding: 14px;
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
