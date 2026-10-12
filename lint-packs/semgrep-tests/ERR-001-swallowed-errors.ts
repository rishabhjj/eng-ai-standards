export function f() {
  // ruleid: eng-ai.err-001.js-empty-catch
  try { run(); } catch (e) { }
  // ok: eng-ai.err-001.js-empty-catch
  try { run(); } catch (e) { console.error(e); throw e; }
}
