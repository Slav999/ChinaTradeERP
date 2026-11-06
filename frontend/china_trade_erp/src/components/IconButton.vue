<template>
  <button
    type="button"
    class="btn app-icon-button"
    :class="[`btn-${variant}`, size ? `btn-${size}` : '']"
    :title="title"
    :aria-label="title"
    :disabled="disabled"
  >
    <i class="bi" :class="`bi-${icon}`" aria-hidden="true"></i>
  </button>
</template>

<script>
export default {
  name: 'IconButton',
  props: {
    icon: { type: String, required: true },
    title: { type: String, required: true },
    variant: { type: String, default: 'outline-secondary' },
    size: { type: String, default: '' },
    disabled: { type: Boolean, default: false },
  },
};
</script>

<style scoped>
.app-icon-button {
  align-items: center;
  display: inline-flex;
  flex: 0 0 auto;
  justify-content: center;
  line-height: 1;
  min-height: 38px;
  padding: 0;
  width: 42px;
}

.app-icon-button.btn-sm {
  min-height: 31px;
  width: 34px;
}

.app-icon-button .bi {
  display: block;
  font-size: 1rem;
  line-height: 1;
}
</style>
