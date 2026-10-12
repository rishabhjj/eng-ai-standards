export function f(db: any, cp: any, user: string) {
  // ruleid: eng-ai.sec-004.js-sql-string
  db.query(`select * from t where u = '${user}'`);
  // ruleid: eng-ai.sec-004.js-sql-string
  db.query("select " + user);
  // ruleid: eng-ai.sec-004.js-sql-string
  db.$queryRawUnsafe("x");
  // ok: eng-ai.sec-004.js-sql-string
  db.query("select * from t where u = $1", [user]);
  // ruleid: eng-ai.sec-004.js-shell
  cp.exec(`ls ${user}`);
  // ok: eng-ai.sec-004.js-shell
  cp.execFile("ls", [user]);
}
