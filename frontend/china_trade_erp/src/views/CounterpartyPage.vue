<template>
  <div class="container mt-4">
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
        <select v-model="filters.status" class="form-select" @change="onFiltersChanged">
          <option disabled selected hidden value="">Select status...</option>
          <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>
      <div class="col-md-2 d-flex align-items-end">
        <button class="btn btn-secondary w-100" @click="resetFilters">Reset</button>
      </div>
    </div>

    <!-- Add Button -->
    <button class="btn btn-primary mb-3 d-block mx-auto" @click="openModal">
      + Add Counterparty
    </button>

    <!-- Table -->
    <div class="table-responsive">
      <table class="table table-hover table-bordered align-middle">
        <thead class="table-light">
        <tr>
          <th>Name</th>
          <th>Region</th>
          <th>Roles</th>
          <th class="d-none d-md-table-cell">Phone</th>
          <th class="d-none d-md-table-cell">Email</th>
          <th class="d-none d-lg-table-cell">Source</th>
          <th>Code</th>
          <th class="d-none d-md-table-cell">Address</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
        </thead>
        <tbody>
        <tr
            v-for="item in counterparties"
            :key="item.id"
            @click="editCounterparty(item)"
            style="cursor: pointer;"
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
                  v-if="item.status && item.status.name"
                  class="badge rounded-pill"
                  :style="{ backgroundColor: item.status.color, color: '#fff' }"
              >
                {{ item.status.name }}
              </span>
            <span v-else class="text-muted">—</span>
          </td>
          <td @click.stop>
            <button
                v-if="item.qr_code_image"
                class="btn btn-sm btn-secondary me-1"
                @click="showQr(item.qr_code_image)"
            >QR
            </button>
            <button class="btn btn-sm btn-danger" @click="deleteCounterparty(item.id)">
              Delete
            </button>
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

    <div class="d-flex justify-content-between align-items-center mt-3" v-if="totalCount">
      <div class="text-muted small">
        Showing {{ pageStart }}-{{ pageEnd }} of {{ totalCount }}
      </div>
      <div class="btn-group">
        <button class="btn btn-outline-secondary btn-sm" :disabled="page <= 1 || isLoading" @click="changePage(page - 1)">
          Previous
        </button>
        <button class="btn btn-outline-secondary btn-sm disabled">
          Page {{ page }} / {{ totalPages }}
        </button>
        <button class="btn btn-outline-secondary btn-sm" :disabled="page >= totalPages || isLoading" @click="changePage(page + 1)">
          Next
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
                    <select v-model="counterpartyForm.status_id" class="form-select">
                      <option disabled value="">Select status...</option>
                      <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.name }}</option>
                    </select>
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
                    <input type="file" class="form-control" @change="handleQrUpload"/>
                    <div v-if="qrPreview" class="mt-2 text-center">
                      <img :src="qrPreview" class="img-fluid"/>
                    </div>
                  </div>
                </div>
              </form>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" @click="closeModal">Cancel</button>
              <button class="btn btn-primary" @click="saveCounterparty">
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
        class="modal fade"
        :class="{ show: !!qrModalUrl }"
        :style="qrModalUrl ? 'display: block;' : ''"
        tabindex="-1"
    >
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
    <div class="modal-backdrop fade" :class="{ show: !!qrModalUrl }"></div>
  </div>
</template>

<script>
import axios from '../axios';
import debounce from 'lodash/debounce';
import { clearCacheByPrefix, getCachedJson, getSavedState, paginatedResults, setCachedJson, setSavedState } from '../utils/pageCache';

const TABLE_STATE_KEY = 'counterparties-table-state';
const PAGE_SIZE = 50;

export default {
  name: 'CounterpartyView',
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
      searchQuery: '',
      filters: {type: '', role: '', status: ''},
      page: 1,
      pageSize: PAGE_SIZE,
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
    totalPages() {
      return Math.max(1, Math.ceil(this.totalCount / this.pageSize));
    },
    pageStart() {
      return this.totalCount ? ((this.page - 1) * this.pageSize) + 1 : 0;
    },
    pageEnd() {
      return Math.min(this.page * this.pageSize, this.totalCount);
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
      const cached = useCache ? getCachedJson(cacheKey) : null;
      if (cached) {
        this.applyCounterpartiesResponse(cached);
      }

      this.isLoading = !cached;
      try {
        const res = await axios.get('/api/counterparties/', {
          params: this.counterpartyQueryParams()
        });
        setCachedJson(cacheKey, res.data);
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
      return `counterparties:${JSON.stringify(this.counterpartyQueryParams())}`;
    },
    applyCounterpartiesResponse(data) {
      const page = paginatedResults(data);
      this.counterparties = page.results;
      this.totalCount = page.count;
    },
    saveTableState() {
      setSavedState(TABLE_STATE_KEY, {
        page: this.page,
        searchQuery: this.searchQuery,
        filters: this.filters,
      });
    },
    restoreTableState() {
      const state = getSavedState(TABLE_STATE_KEY, {
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
      if (page < 1 || page > this.totalPages || page === this.page) return;
      this.page = page;
      this.saveTableState();
      this.fetchCounterparties({ useCache: true });
    },
    openModal() {
      this.resetForm();
      this.isEdit = false;
      this.showModal = true;
      this.showEditContent = true;
      this.selectedId = null;
      this.qrPreview = null;
    },
    closeModal() {
      this.showModal = false;
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
        }
        clearCacheByPrefix('counterparties:');
        clearCacheByPrefix('counterparty-options');
        this.closeModal();
        this.fetchCounterparties();
      } catch (err) {
        console.error('Save error:', err.response?.data || err);
      }
    },
    async deleteCounterparty(id) {
      if (confirm('Delete this counterparty?')) {
        await axios.delete(`/api/counterparties/${id}/`);
        clearCacheByPrefix('counterparties:');
        clearCacheByPrefix('counterparty-options');
        this.counterparties = this.counterparties.filter(x => x.id !== id);
        this.totalCount = Math.max(0, this.totalCount - 1);
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
</style>
