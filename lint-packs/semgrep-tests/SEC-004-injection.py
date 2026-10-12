import os
import subprocess


def f(cur, user):
    # ruleid: eng-ai.sec-004.python-sql-string
    cur.execute(f"select * from t where u = '{user}'")
    # ruleid: eng-ai.sec-004.python-sql-string
    cur.execute("select " + user)
    # ruleid: eng-ai.sec-004.python-sql-string
    cur.execute("select %s" % user)
    # ruleid: eng-ai.sec-004.python-sql-string
    cur.execute("select {}".format(user))
    # ok: eng-ai.sec-004.python-sql-string
    cur.execute("select * from t where u = %s", (user,))
    # ruleid: eng-ai.sec-004.python-shell
    subprocess.run("ls " + user, shell=True)
    # ruleid: eng-ai.sec-004.python-shell
    os.system("x")
    # ok: eng-ai.sec-004.python-shell
    subprocess.run(["ls", user], check=True)
