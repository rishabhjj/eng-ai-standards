class Err001 {
  void f() {
    // ruleid: eng-ai.err-001.java-empty-catch
    try { run(); } catch (Exception e) { }
    // ok: eng-ai.err-001.java-empty-catch
    try { run(); } catch (Exception e) { throw new RuntimeException(e); }
  }
}
