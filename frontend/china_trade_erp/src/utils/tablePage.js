import {
  getCachedJson,
  getSavedState,
  paginatedResults,
  setCachedJson,
  setSavedState,
} from './pageCache';

export const DEFAULT_PAGE_SIZE = 50;

export function pageMeta(page, totalCount, pageSize) {
  return {
    totalPages: Math.max(1, Math.ceil(totalCount / pageSize)),
    pageStart: totalCount ? ((page - 1) * pageSize) + 1 : 0,
    pageEnd: Math.min(page * pageSize, totalCount),
  };
}

export function makeTableCacheKey(prefix, params) {
  return `${prefix}:${JSON.stringify(params)}`;
}

export function getCachedTablePage(cacheKey, useCache = false) {
  return useCache ? getCachedJson(cacheKey) : null;
}

export function setCachedTablePage(cacheKey, data) {
  setCachedJson(cacheKey, data);
}

export function applyPaginatedData(target, data, rowsKey) {
  const page = paginatedResults(data);
  target[rowsKey] = page.results;
  target.totalCount = page.count;
}

export function saveTableStateSnapshot(key, target, extraKeys = []) {
  const state = {
    page: target.page,
    searchQuery: target.searchQuery,
    filters: target.filters,
  };
  extraKeys.forEach((extraKey) => {
    state[extraKey] = target[extraKey];
  });
  setSavedState(key, state);
}

export function restoreTableStateSnapshot(key, fallback, normalize = state => state) {
  return normalize(getSavedState(key, fallback));
}

export function changeTablePage(target, page, fetchMethodName) {
  const meta = pageMeta(target.page, target.totalCount, target.pageSize);
  if (page < 1 || page > meta.totalPages || page === target.page) return;
  target.page = page;
  target.saveTableState();
  target[fetchMethodName]({ useCache: true });
}
