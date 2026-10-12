class Sec004 {
  void f(java.sql.Statement s, javax.persistence.EntityManager em, String u) throws Exception {
    // ruleid: eng-ai.sec-004.java-sql-string
    s.executeQuery("select " + u);
    // ruleid: eng-ai.sec-004.java-sql-string
    s.executeUpdate("update " + u);
    // ruleid: eng-ai.sec-004.java-sql-string
    em.createQuery("from T where x = " + u);
    // ok: eng-ai.sec-004.java-sql-string
    s.executeQuery("select 1");
  }
}
