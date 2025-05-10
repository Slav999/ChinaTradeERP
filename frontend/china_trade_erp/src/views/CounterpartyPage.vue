<template>
  <div class="container mt-4">
    <h1 class="mb-4">Counterparties</h1>

    <!-- Search and filters -->
    <div class="row mb-3 g-2">
      <div class="col-md-4">
        <input
          type="text"
          class="form-control"
          placeholder="Search by name/code/email..."
          v-model="searchQuery"
          @input="filterCounterparties"
        />
      </div>
      <div class="col-md-3">
        <select class="form-select" v-model="filters.type" @change="filterCounterparties">
          <option disabled selected hidden value="">Select type...</option>
          <option value="china">Chinese</option>
          <option value="local">Local</option>
        </select>
      </div>
      <div class="col-md-3">
        <select class="form-select" v-model="filters.status" @change="filterCounterparties">
          <option disabled selected hidden value="">Select status...</option>
          <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>
      <div class="col-md-2 d-flex align-items-end">
        <button class="btn btn-secondary w-100" @click="resetFilters">Reset</button>
      </div>
    </div>

    <button
      class="btn btn-primary mb-3 d-block mx-auto"
      @click="openModal"
    >
      + Add Counterparty
    </button>

    <div class="table-responsive">
      <table class="table table-hover table-bordered align-middle">
        <thead class="table-light">
          <tr>
            <th>Name</th>
            <th>Type</th>
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
            v-for="item in filteredCounterparties"
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
            <td class="d-none d-md-table-cell">{{ item.phone || '—' }}</td>
            <td class="d-none d-md-table-cell">{{ item.email || '—' }}</td>
            <td class="d-none d-lg-table-cell">{{ item.source || '—' }}</td>
            <td>{{ item.unique_code }}</td>
            <td class="d-none d-md-table-cell">{{ item.address || '—' }}</td>
            <td>
              <span
                v-if="item.status && item.status.name && item.status.color"
                class="badge rounded-pill"
                :style="{ backgroundColor: item.status.color, color: 'white' }"
              >
                {{ item.status.name }}
              </span>
              <span v-else class="text-muted">—</span>
            </td>
            <td @click.stop>
              <button
                class="btn btn-sm btn-secondary me-1"
                v-if="item.qr_code_image"
                @click="showQr(item.qr_code_image)"
              >
                QR
              </button>
              <button class="btn btn-sm btn-danger" @click="deleteCounterparty(item.id)">Delete</button>
            </td>
          </tr>
          <tr v-if="filteredCounterparties.length === 0">
            <td colspan="9" class="text-center text-muted">No counterparties yet.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal for add/edit -->
    <div
      class="modal fade"
      :class="{ show: showModal }"
      :style="showModal ? 'display: block;' : ''"
      tabindex="-1"
      role="dialog"
      aria-modal="true"
    >
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ isEdit ? 'Edit' : 'Add' }} Counterparty</h5>
            <button type="button" class="btn-close" @click="closeModal"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="saveCounterparty">
              <div class="mb-3">
                <label class="form-label">Name</label>
                <input v-model="counterpartyForm.name" type="text" class="form-control" required />
              </div>
              <div class="mb-3">
                <label class="form-label">Type</label>
                <select v-model="counterpartyForm.type" class="form-select">
                  <option value="china">Chinese</option>
                  <option value="local">Local</option>
                </select>
              </div>
              <div class="mb-3">
                <label class="form-label">Unique Code</label>
                <input v-model="counterpartyForm.unique_code" type="text" class="form-control" />
              </div>
              <div class="mb-3">
                <label class="form-label">Address</label>
                <input v-model="counterpartyForm.address" type="text" class="form-control" />
              </div>
              <div class="mb-3">
                <label class="form-label">Phone</label>
                <input v-model="counterpartyForm.phone" type="text" class="form-control" />
              </div>
              <div class="mb-3">
                <label class="form-label">Email</label>
                <input v-model="counterpartyForm.email" type="email" class="form-control" />
              </div>
              <div class="mb-3">
                <label class="form-label">Source</label>
                <input v-model="counterpartyForm.source" type="text" class="form-control" />
              </div>
              <div class="mb-3">
                <label class="form-label">Status</label>
                <select v-model="counterpartyForm.status_id" class="form-select">
                  <option disabled value="">Select status...</option>
                  <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.name }}</option>
                </select>
              </div>
              <div class="mb-3">
                <label class="form-label">QR Code Image</label>
                <input type="file" class="form-control" @change="handleQrUpload" />
                <div v-if="qrPreview" class="mt-2 text-center">
                  <img :src="qrPreview" class="img-fluid" style="max-height: 400px;" />
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="closeModal">Cancel</button>
            <button class="btn btn-primary" @click="saveCounterparty">
              {{ isEdit ? 'Save changes' : 'Create' }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div
      class="modal-backdrop fade"
      :class="{ show: showModal }"
      v-if="showModal"
    ></div>

    <!-- Modal for QR preview -->
    <div
      class="modal fade"
      :class="{ show: !!qrModalUrl }"
      :style="qrModalUrl ? 'display: block;' : ''"
      tabindex="-1"
      role="dialog"
      aria-modal="true"
    >
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h6 class="modal-title">QR Code</h6>
            <button type="button" class="btn-close" @click="qrModalUrl = null"></button>
          </div>
          <div class="modal-body text-center">
            <img :src="qrModalUrl" class="img-fluid" style="max-height: 80vh;" alt="QR code" />
          </div>
        </div>
      </div>
    </div>
    <div
      class="modal-backdrop fade"
      :class="{ show: !!qrModalUrl }"
      v-if="qrModalUrl"
    ></div>
  </div>
</template>

<script>
import axios from '../axios';

export default {
  name: 'CounterpartyView',
  data() {
    return {
      counterparties: [],
      filteredCounterparties: [],
      statuses: [],
      showModal: false,
      isEdit: false,
      selectedId: null,
      qrPreview: null,
      qrModalUrl: null,
      searchQuery: '',
      filters: {
        type: '',
        status: ''
      },
      counterpartyForm: {
        name: '',
        type: 'china',
        unique_code: '',
        address: '',
        phone: '',
        email: '',
        source: '',
        status_id: null,
        qr_code_image: null
      }
    };
  },
  created() {
    this.fetchCounterparties();
    this.fetchStatuses();
  },
  methods: {
    async fetchCounterparties() {
      const res = await axios.get('/api/counterparties/');
      this.counterparties = res.data;
      this.filteredCounterparties = res.data;
    },
    async fetchStatuses() {
      const res = await axios.get('/api/counterparty-statuses/');
      this.statuses = res.data;
    },
    filterCounterparties() {
      const query = this.searchQuery.toLowerCase();
      this.filteredCounterparties = this.counterparties.filter(c => {
        const matchesQuery =
          c.name?.toLowerCase().includes(query) ||
          c.email?.toLowerCase().includes(query) ||
          c.unique_code?.toLowerCase().includes(query);

        const matchesType = this.filters.type ? c.type === this.filters.type : true;
        const matchesStatus = this.filters.status ? (c.status?.id === Number(this.filters.status)) : true;

        return matchesQuery && matchesType && matchesStatus;
      });
    },
    resetFilters() {
      this.searchQuery = '';
      this.filters.type = '';
      this.filters.status = '';
      this.filterCounterparties();
    },
    openModal() {
      this.showModal = true;
      this.isEdit = false;
      this.selectedId = null;
      this.qrPreview = null;
      this.counterpartyForm = {
        name: '',
        type: 'china',
        unique_code: '',
        address: '',
        phone: '',
        email: '',
        source: '',
        status_id: null,
        qr_code_image: null
      };
    },
    closeModal() {
      this.showModal = false;
    },
    editCounterparty(counterparty) {
      this.counterpartyForm = {
        ...counterparty,
        status_id: counterparty.status?.id || null,
        qr_code_image: null
      };
      this.qrPreview = counterparty.qr_code_image || null;
      this.selectedId = counterparty.id;
      this.isEdit = true;
      this.showModal = true;
    },
    showQr(url) {
      this.qrModalUrl = url;
    },
    handleQrUpload(event) {
      const file = event.target.files[0];
      if (file) {
        this.counterpartyForm.qr_code_image = file;
        this.qrPreview = URL.createObjectURL(file);
      }
    },
    async saveCounterparty() {
      try {
        const formData = new FormData();
        for (const key in this.counterpartyForm) {
          const value = this.counterpartyForm[key];
          if (value !== null && value !== undefined) {
            formData.append(key, value);
          }
        }

        const config = { headers: { 'Content-Type': 'multipart/form-data' } };
        let response;

        if (this.isEdit && this.selectedId) {
          response = await axios.put(`/api/counterparties/${this.selectedId}/`, formData, config);
          const index = this.counterparties.findIndex(item => item.id === this.selectedId);
          if (index !== -1) {
            this.counterparties.splice(index, 1, response.data);
          }
        } else {
          response = await axios.post('/api/counterparties/', formData, config);
          this.counterparties.unshift(response.data);
        }

        this.filterCounterparties();
        this.closeModal();
      } catch (error) {
        console.error('Ошибка при сохранении:', error.response?.data || error.message);
      }
    },
    async deleteCounterparty(id) {
      if (confirm('Are you sure you want to delete this counterparty?')) {
        await axios.delete(`/api/counterparties/${id}/`);
        this.counterparties = this.counterparties.filter(item => item.id !== id);
        this.filterCounterparties();
      }
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
</style>
