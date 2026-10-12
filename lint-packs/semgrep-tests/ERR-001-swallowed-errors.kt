fun f() {
    // ruleid: eng-ai.err-001.kotlin-empty-catch
    try { run() } catch (e: Exception) { }
    // ok: eng-ai.err-001.kotlin-empty-catch
    try { run() } catch (e: Exception) { throw RuntimeException(e) }
}
