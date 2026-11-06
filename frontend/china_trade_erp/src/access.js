import { reactive } from 'vue';
import axios, { AUTH_SESSION_KEY } from './axios';

export const PERMISSIONS = Object.freeze({
  SUPPLIER_ORDERS_VIEW: 'orders.supplier.view',
  SUPPLIER_ORDERS_MANAGE: 'orders.supplier.manage',
  CUSTOMER_ORDERS_VIEW: 'orders.customer.view',
  CUSTOMER_ORDERS_MANAGE: 'orders.customer.manage',
  COUNTERPARTIES_VIEW: 'counterparties.view',
  COUNTERPARTIES_MANAGE: 'counterparties.manage',
  PRODUCTS_VIEW: 'products.view',
  PRODUCTS_MANAGE: 'products.manage',
  WAREHOUSE_VIEW: 'warehouse.view',
  WAREHOUSE_MANAGE: 'warehouse.manage',
  COMPANY_USERS_MANAGE: 'company.users.manage',
  COMPANY_SETTINGS_MANAGE: 'company.settings.manage',
  PURCHASE_PRICE_VIEW: 'pricing.purchase.view',
  PURCHASE_PRICE_MANAGE: 'pricing.purchase.manage',
  COST_PRICE_VIEW: 'pricing.cost.view',
  SALE_PRICE_VIEW: 'pricing.sale.view',
  ORDER_SALE_PRICE_MANAGE: 'pricing.sale.order.manage',
  CATALOG_SALE_PRICE_MANAGE: 'pricing.sale.catalog.manage',
  FINANCIAL_REPORTS_VIEW: 'reports.financial.view',
});

function readCachedUser() {
  try {
    return JSON.parse(localStorage.getItem('current_user_profile')) || null;
  } catch {
    return null;
  }
}

export const accessState = reactive({
  user: readCachedUser(),
  loaded: false,
  loading: false,
});

let loadPromise = null;

export function setCurrentUser(user) {
  const previous = accessState.user;
  const signature = value => JSON.stringify([value?.id, value?.company_id, value?.is_company_admin, [...(value?.permissions || [])].sort()]);
  if (signature(previous) !== signature(user)) {
    sessionStorage.clear();
  }
  accessState.user = user || null;
  accessState.loaded = true;
  if (user) {
    localStorage.setItem('current_user_profile', JSON.stringify(user));
  } else {
    localStorage.removeItem('current_user_profile');
  }
}

export function permissionCodes(user = accessState.user) {
  if (!user) return [];
  const raw = user.permissions || user.access_permissions || user.capabilities || [];
  return Array.isArray(raw) ? raw : [];
}

export function hasPermission(permission, user = accessState.user) {
  if (!permission || !user) return false;
  if (user.is_superuser || user.is_company_admin) return true;
  return permissionCodes(user).includes(permission);
}

export function hasAnyPermission(permissions, user = accessState.user) {
  return permissions.some(permission => hasPermission(permission, user));
}

export async function loadCurrentUser({ force = false } = {}) {
  if (!localStorage.getItem(AUTH_SESSION_KEY)) {
    setCurrentUser(null);
    return null;
  }
  if (!force && accessState.loaded) return accessState.user;
  if (loadPromise) return loadPromise;

  accessState.loading = true;
  loadPromise = axios.get('/api/auth/me/')
    .then(({ data }) => {
      setCurrentUser(data);
      return data;
    })
    .finally(() => {
      accessState.loading = false;
      loadPromise = null;
    });
  return loadPromise;
}

export function firstAllowedRoute(user = accessState.user) {
  if (hasPermission(PERMISSIONS.SUPPLIER_ORDERS_VIEW, user)) return '/supplier-orders';
  if (hasPermission(PERMISSIONS.CUSTOMER_ORDERS_VIEW, user)) return '/customer-orders';
  if (hasPermission(PERMISSIONS.PRODUCTS_VIEW, user)) return '/products';
  if (hasPermission(PERMISSIONS.WAREHOUSE_VIEW, user)) return '/warehouse';
  if (hasPermission(PERMISSIONS.COUNTERPARTIES_VIEW, user)) return '/counterparty';
  return '/profile';
}
