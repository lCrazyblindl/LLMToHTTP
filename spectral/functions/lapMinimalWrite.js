// LAP W1 — writes (POST/PUT/PATCH) should default to a minimal response
// (status + server-generated fields), not a full representation.
// given: $.paths[*].

const WRITES = ['post', 'put', 'patch'];

function returnsBody(op) {
  const rs = op && op.responses;
  if (!rs || typeof rs !== 'object') return false;
  for (const code of ['200', '201']) {
    const r = rs[code];
    if (!r || typeof r !== 'object') continue;
    if (r.content && typeof r.content === 'object') {
      for (const mt of Object.keys(r.content)) {
        if (r.content[mt] && r.content[mt].schema) return true;
      }
    }
    if (r.schema) return true; // Swagger 2.0
  }
  return false;
}

export default function lapMinimalWrite(pathItem, _opts, context) {
  if (!pathItem || typeof pathItem !== 'object') return;
  const out = [];
  for (const m of WRITES) {
    const op = pathItem[m];
    if (op && typeof op === 'object' && returnsBody(op)) {
      out.push({
        message: `W1: ${m.toUpperCase()} returns a full representation by default - consider Prefer: return=minimal (server-generated fields only). [LAP W1]`,
        path: [...context.path, m],
      });
    }
  }
  return out;
}
