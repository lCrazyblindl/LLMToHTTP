// LAP E1 — every operation should declare at least one 4xx/5xx error response,
// so success / empty / error are unambiguous. given: $.paths[*].

const METHODS = ['get', 'post', 'put', 'patch', 'delete'];

function hasErrorResponse(op) {
  const rs = op && op.responses;
  if (!rs || typeof rs !== 'object') return false;
  for (const code of Object.keys(rs)) if (/^[45]/.test(code)) return true;
  return false;
}

export default function lapErrorResponse(pathItem, _opts, context) {
  if (!pathItem || typeof pathItem !== 'object') return;
  const out = [];
  for (const m of METHODS) {
    const op = pathItem[m];
    if (op && typeof op === 'object' && !hasErrorResponse(op)) {
      out.push({
        message: 'E1: no 4xx/5xx error response declared - agents can\'t distinguish success/empty/error. [LAP E1]',
        path: [...context.path, m],
      });
    }
  }
  return out;
}
