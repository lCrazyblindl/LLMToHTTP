// LAP A1 — the API should offer at least one aggregate/count endpoint, so
// "how many ..." questions don't force pulling the whole list. given: $ (root).

const METHODS = ['get', 'post', 'put', 'patch', 'delete'];
const AGG = /count|aggregate|stats|summary/i;

export default function lapAggregateEndpoint(root, _opts, _context) {
  if (!root || typeof root !== 'object' || !root.paths || typeof root.paths !== 'object') return;
  for (const p of Object.keys(root.paths)) {
    if (AGG.test(p)) return []; // a path mentions count/aggregate/stats/summary
    const item = root.paths[p];
    if (!item || typeof item !== 'object') continue;
    for (const m of METHODS) {
      const op = item[m];
      if (op && typeof op.operationId === 'string' && AGG.test(op.operationId)) return [];
    }
  }
  return [{
    message: 'A1: no aggregate/count endpoint - "how many ..." questions force pulling the full list. [LAP A1]',
    path: ['paths'],
  }];
}
