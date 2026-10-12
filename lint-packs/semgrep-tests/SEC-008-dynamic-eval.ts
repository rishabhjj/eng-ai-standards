export function f(user: string) {
  // ruleid: eng-ai.sec-008.js-dynamic-eval
  eval(user);
  // ruleid: eng-ai.sec-008.js-dynamic-eval
  const g = new Function(user);
  // ok: eng-ai.sec-008.js-dynamic-eval
  JSON.parse(user);
}
