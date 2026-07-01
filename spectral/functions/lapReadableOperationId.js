// LAP D3 — operationId should be a readable name, not opaque/numeric/too short.
// given: $.paths[*]. Only judged when operationId is present (Spectral can't see
// lap's synthesized names).

const METHODS = ['get', 'post', 'put', 'patch', 'delete'];

export default function lapReadableOperationId(pathItem, _opts, context) {
  if (!pathItem || typeof pathItem !== 'object') return;
  const out = [];
  for (const m of METHODS) {
    const op = pathItem[m];
    if (!op || typeof op !== 'object') continue;
    const id = op.operationId;
    if (typeof id !== 'string' || id.length === 0) continue;
    const opaque = id.length < 3 || /^\d+$/.test(id) || !/[A-Za-z]/.test(id);
    if (opaque) {
      out.push({
        message: `D3: opaque operationId "${id}" - LLMs ground on readable names. [LAP D3]`,
        path: [...context.path, m, 'operationId'],
      });
    }
  }
  return out;
}
