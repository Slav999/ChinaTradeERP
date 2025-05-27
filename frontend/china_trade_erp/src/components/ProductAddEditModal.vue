<template>
  <!-- Add/Edit Product Modal -->
  <div
      class="modal fade edit-modal"
      :class="{ show: visible }"
      :style="visible ? 'display: block;' : ''"
      tabindex="-1"
  >
    <div class="modal-dialog modal-dialog-centered modal-lg">
      <transition name="modal-fade">
        <div class="modal-content" v-if="visible">
          <div class="modal-header">
            <h5 class="modal-title">{{ isEdit ? 'Edit Product' : 'Add Product' }}</h5>
            <button type="button" class="btn-close" @click="$emit('close')"></button>
          </div>
          <div class="modal-body">
            <div v-if="isEdit" class="audit-info mb-3 p-3 bg-light rounded border" style="cursor: pointer;"
                 @click="$emit('open-history')">
              <div class="row">
                <div class="col text-muted small">
                  <strong>Created At:</strong> {{ formatDate(form.created_at) }}
                </div>
                <div class="col text-muted small">
                  <strong>Updated At:</strong> {{ formatDate(form.updated_at) }}
                </div>
              </div>
              <div class="row mt-2">
                <div class="col text-muted small"><strong>Created By:</strong> {{ form.created_by || '—' }}</div>
                <div class="col text-muted small"><strong>Updated By:</strong> {{ form.updated_by || '—' }}</div>
              </div>
            </div>

            <form @submit.prevent="save">
              <div class="row gy-3">
                <div class="col-md-6">
                  <label class="form-label">Name</label>
                  <input v-model="form.name" type="text" class="form-control" required/>
                </div>
                <div class="col-md-6">
                  <label class="form-label">SKU</label>
                  <input v-model="form.sku" type="text" class="form-control" required/>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Category</label>
                  <select v-model="form.category_id" class="form-select">
                    <option disabled value="">Select category...</option>
                    <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                  </select>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Unit</label>
                  <select v-model="form.unit_id" class="form-select">
                    <option disabled value="">Select unit...</option>
                    <option v-for="u in units" :key="u.id" :value="u.id">{{ u.name }}</option>
                  </select>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Supplier</label>
                  <select v-model="form.supplier_id" class="form-select">
                    <option disabled value="">Select supplier...</option>
                    <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
                  </select>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Quantity</label>
                  <input v-model.number="form.quantity" type="number" min="0" class="form-control"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Purchase Price</label>
                  <input v-model.number="form.purchase_price" type="number" step="0.01" class="form-control"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Sale Price</label>
                  <input v-model.number="form.sale_price" type="number" step="0.01" class="form-control"/>
                </div>
                <div class="col-12">
                  <label class="form-label">Image</label>
                  <input type="file" class="form-control" @change="handleImageUpload"/>
                  <div v-if="imagePreview" class="mt-2 text-center">
                    <img :src="imagePreview" class="img-fluid" style="max-height: 200px;"/>
                  </div>
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer justify-content-end">
            <button class="btn btn-secondary" @click="$emit('close')">Cancel</button>
            <button v-if="isEdit" class="btn btn-warning me-auto" @click="$emit('open-calc')">Calculate Price</button>
            <button class="btn btn-primary" @click="save">{{ isEdit ? 'Save' : 'Create' }}</button>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script>
import axios from '../axios';

export default {
  name: 'ProductAddEditModal',
  props: {
    visible: {type: Boolean, default: false},
    initialProduct: {type: Object, default: null},
    categories: Array,
    units: Array,
    suppliers: Array,
  },
  data() {
    return {
      form: this.initialProduct
          ? {...this.initialProduct, image: null}
          : {
            name: '', sku: '', category_id: null, unit_id: null,
            supplier_id: null, quantity: 0,
            purchase_price: 0, sale_price: 0,
            image: null,
            created_at: null, created_by: null,
            updated_at: null, updated_by: null,
          },
      imagePreview: this.initialProduct?.image || null,
    };
  },
  methods: {
    async save() {
      const fd = new FormData();
      Object.entries(this.form).forEach(([k, v]) => {
        if (v !== null && v !== undefined) fd.append(k, v);
      });
      try {
        let res;
        const cfg = {headers: {'Content-Type': 'multipart/form-data'}};
        if (this.isEdit && this.form.id) {
          res = await axios.put(`/api/products/${this.form.id}/`, fd, cfg);
        } else {
          res = await axios.post('/api/products/', fd, cfg);
        }
        this.$emit('saved', res.data);
      } catch (e) {
        console.error(e);
      }
    },
    handleImageUpload(e) {
      const file = e.target.files[0];
      if (file) {
        this.form.image = file;
        this.imagePreview = URL.createObjectURL(file);
      }
    },
    formatDate(val) {
      return val ? new Date(val).toLocaleString() : '—';
    },
  },
  computed: {
    isEdit() {
      return Boolean(this.initialProduct && this.initialProduct.id);
    }
  },
  watch: {
    initialProduct(prod) {
      // reset form when prop changes
      this.form = prod ? {...prod, image: null} : {
        name: '', sku: '', category_id: null, unit_id: null,
        supplier_id: null, quantity: 0,
        purchase_price: 0, sale_price: 0,
        image: null,
        created_at: null, created_by: null,
        updated_at: null, updated_by: null,
      };
      this.imagePreview = prod?.image || null;
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