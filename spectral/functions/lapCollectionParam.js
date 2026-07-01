// LAP R1 / R2 / R3 — read-shaping on collection (array-returning) GETs.
// given: $.paths[*] (a path item). The `rule` option selects which check.
// Mirrors lap/lint.py so Spectral users get the same findings.

const PAGINATION = new Set([
  'limit', 'offset', 'page', 'page_size', 'pagesize', 'per_page', 'perpage',
  'cursor', 'top', 'skip', '$top', '$skip',
]);
const PROJECTION = new Set(['fields', 'field', 'select', '$select', 'include', 'expand', '$expand']);
const FILTER_HINTS = new Set(['filter', '$filter', 'q', 'query', 'where', 'search']);

function returnsArray(op) {
  const rs = op && op.responses;
  if (!rs || typeof rs !== 'object') return false;
  for (const code of ['200', '201', '202']) {
    const r = rs[code];
    if (!r || typeof r !== 'object') continue;
    if (r.content && typeof r.content === 'object') {
      for (const mt of Object.keys(r.content)) {
        const sch = r.content[mt] && r.content[mt].schema;
        if (sch && sch.type === 'array') return true;
      }
    }
    if (r.schema && r.schema.type === 'array') return true; // Swagger 2.0
  }
  return false;
}

function queryNames(pathItem, op) {
  const names = new Set();
  const collect = (params) => {
    if (!Array.isArray(params)) return;
    for (const p of params) {
      if (p && p.in === 'query' && typeof p.name === 'string') names.add(p.name.toLowerCase());
    }
  };
  collect(pathItem.parameters);
  collect(op.parameters);
  return names;
}

function intersects(set, names) {
  for (const n of names) if (set.has(n)) return true;
  return false;
}

export default function lapCollectionParam(pathItem, opts, context) {
  if (!pathItem || typeof pathItem !== 'object') return;
  const get = pathItem.get;
  if (!get || typeof get !== 'object' || !returnsArray(get)) return;

  const rule = (opts && opts.rule) || 'R3';
  const q = queryNames(pathItem, get);
  let missing = false;
  let message = '';

  if (rule === 'R3') {
    missing = !intersects(PAGINATION, q);
    message = 'R3: collection GET has no pagination (limit/offset/cursor) - agents pull the whole list (big result bucket). [LAP R3]';
  } else if (rule === 'R1') {
    missing = !intersects(PROJECTION, q);
    message = 'R1: collection GET has no field projection (fields/select) - every field is returned. [LAP R1]';
  } else if (rule === 'R2') {
    const others = [...q].filter((n) => !PAGINATION.has(n) && !PROJECTION.has(n));
    missing = !(intersects(FILTER_HINTS, q) || others.length > 0);
    message = 'R2: collection GET has no server-side filter params - agents fetch then filter in-context. [LAP R2]';
  }

  if (missing) return [{ message, path: [...context.path, 'get'] }];
  return [];
}
