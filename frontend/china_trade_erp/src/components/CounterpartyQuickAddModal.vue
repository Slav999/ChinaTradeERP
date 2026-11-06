<template>
  <div
      class="modal fade counterparty-quick-modal"
      :class="{ show: visible }"
      :style="visible ? 'display: block;' : ''"
      tabindex="-1"
  >
    <div class="modal-dialog modal-dialog-centered modal-lg">
      <transition name="modal-fade">
        <div class="modal-content" v-if="visible">
          <div class="modal-header">
            <h5 class="modal-title">{{ title }}</h5>
            <button type="button" class="btn-close" @click="$emit('close')"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="save">
              <div class="row gy-3">
                <div class="col-md-6">
                  <label class="form-label">Name</label>
                  <input v-model.trim="form.name" type="text" class="form-control" required/>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Region</label>
                  <select v-model="form.type" class="form-select">
                    <option value="china">Chinese</option>
                    <option value="local">Local</option>
                  </select>
                </div>
                <div class="col-12">
                  <label class="form-label">Roles</label>
                  <div class="d-flex flex-wrap gap-3">
                    <div class="form-check">
                      <input :id="`${uid}-supplier`" v-model="form.is_supplier" class="form-check-input" type="checkbox"/>
                      <label class="form-check-label" :for="`${uid}-supplier`">Supplier</label>
                    </div>
                    <div class="form-check">
                      <input :id="`${uid}-customer`" v-model="form.is_customer" class="form-check-input" type="checkbox"/>
                      <label class="form-check-label" :for="`${uid}-customer`">Customer</label>
                    </div>
                  </div>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Unique Code</label>
                  <input v-model.trim="form.unique_code" class="form-control"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Status</label>
                  <select v-model="form.status_id" class="form-select">
                    <option value="">No status</option>
                    <option v-for="status in statuses" :key="status.id" :value="status.id">
                      {{ status.display_name || status.name }}
                    </option>
                  </select>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Phone</label>
                  <input v-model.trim="form.phone" class="form-control"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Email</label>
                  <input v-model.trim="form.email" type="email" class="form-control"/>
                </div>
                <div class="col-12">
                  <label class="form-label">Address</label>
                  <input v-model.trim="form.address" class="form-control"/>
                </div>
                <div class="col-12">
                  <label class="form-label">Source</label>
                  <input v-model.trim="form.source" class="form-control"/>
                </div>
                <div class="col-12">
                  <label class="form-label">QR Code Image</label>
                  <input type="file" class="form-control" accept="image/*" @change="handleQrUpload"/>
                  <div v-if="qrPreview" class="qr-preview-box mt-2">
                    <img :src="qrPreview" class="qr-preview-image" alt="QR preview"/>
                  </div>
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="$emit('close')">Cancel</button>
            <button class="btn btn-primary" :disabled="isSaving" @click="save">
              {{ isSaving ? 'Creating...' : 'Create' }}
            </button>
          </div>
        </div>
      </transition>
    </div>
  </div>
  <div v-if="visible" class="modal-backdrop quick-counterparty-backdrop"></div>
</template>

<script>
import axios from '../axios';

const emptyForm = role => ({
  name: '',
  type: role === 'supplier' ? 'china' : 'local',
  is_supplier: role === 'supplier',
  is_customer: role === 'customer',
  unique_code: '',
  status_id: '',
  phone: '',
  email: '',
  address: '',
  source: '',
  qr_code_image: null,
});

export default {
  name: 'CounterpartyQuickAddModal',
  props: {
    visible: {type: Boolean, default: false},
    role: {type: String, default: 'supplier'},
    title: {type: String, default: 'Add Counterparty'},
  },
  emits: ['close', 'saved'],
  data() {
    return {
      form: emptyForm(this.role),
      statuses: [],
      qrPreview: null,
      isSaving: false,
      uid: `counterparty-${Math.random().toString(36).slice(2, 9)}`,
    };
  },
  watch: {
    visible(value) {
      if (!value) return;
      this.form = emptyForm(this.role);
      this.qrPreview = null;
      this.fetchStatuses();
    },
    role(value) {
      if (this.visible) {
        this.form = emptyForm(value);
        this.qrPreview = null;
      }
    },
  },
  methods: {
    async fetchStatuses() {
      if (this.statuses.length) return;
      try {
        const {data} = await axios.get('/api/counterparty-statuses/');
        this.statuses = Array.isArray(data) ? data : data.results || [];
      } catch (error) {
        console.error(error);
      }
    },
    handleQrUpload(event) {
      const file = event.target.files[0];
      if (!file) return;
      this.form.qr_code_image = file;
      this.qrPreview = URL.createObjectURL(file);
    },
    async save() {
      if (!this.form.name.trim()) {
        alert('Please enter counterparty name');
        return;
      }
      if (!this.form.is_supplier && !this.form.is_customer) {
        alert('Select at least one role: supplier or customer.');
        return;
      }

      const payload = new FormData();
      Object.entries(this.form).forEach(([key, value]) => {
        if (value === null || value === undefined || value === '') return;
        payload.append(key, value);
      });

      this.isSaving = true;
      try {
        const {data} = await axios.post('/api/counterparties/', payload, {
          headers: {'Content-Type': 'multipart/form-data'},
        });
        this.$emit('saved', data);
      } catch (error) {
        alert(this.formatApiError(error));
      } finally {
        this.isSaving = false;
      }
    },
    formatApiError(error) {
      const data = error.response?.data;
      if (!data) return 'Unable to create counterparty';
      if (typeof data === 'string') return data;
      if (data.detail || data.error) return data.detail || data.error;
      return Object.entries(data)
          .map(([field, messages]) => {
            const text = Array.isArray(messages) ? messages.join(' ') : messages;
            return `${field}: ${text}`;
          })
          .join('\n');
    },
  },
};
</script>

<style scoped>
.counterparty-quick-modal {
  z-index: 1070;
}

.quick-counterparty-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1065;
  background-color: #000;
  opacity: 0.35;
}

.qr-preview-box {
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

.qr-preview-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>
