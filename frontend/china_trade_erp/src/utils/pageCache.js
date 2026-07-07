const DEFAULT_TTL_MS = 5 * 60 * 1000;

export function getCachedJson(key, ttlMs = DEFAULT_TTL_MS) {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;

    const entry = JSON.parse(raw);
    if (!entry || Date.now() - entry.savedAt > ttlMs) {
      sessionStorage.removeItem(key);
      return null;
    }

    return entry.value;
  } catch {
    sessionStorage.removeItem(key);
    return null;
  }
}

export function setCachedJson(key, value) {
  sessionStorage.setItem(key, JSON.stringify({
    savedAt: Date.now(),
    value,
  }));
}

export function getSavedState(key, fallback) {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? { ...fallback, ...JSON.parse(raw) } : { ...fallback };
  } catch {
    return { ...fallback };
  }
}

export function setSavedState(key, state) {
  sessionStorage.setItem(key, JSON.stringify(state));
}

export function clearCacheByPrefix(prefix) {
  Object.keys(sessionStorage)
    .filter(key => key.startsWith(prefix))
    .forEach(key => sessionStorage.removeItem(key));
}

export function paginatedResults(data) {
  if (Array.isArray(data)) {
    return { count: data.length, results: data };
  }

  return {
    count: data?.count || 0,
    results: data?.results || [],
  };
}
