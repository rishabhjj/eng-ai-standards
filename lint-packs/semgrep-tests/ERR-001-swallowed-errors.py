def f(x):
    # ruleid: eng-ai.err-001.python-swallowed
    try:
        run()
    except:
        pass
    # ruleid: eng-ai.err-001.python-swallowed
    try:
        run()
    except ValueError:
        pass
    # ruleid: eng-ai.err-001.python-swallowed
    try:
        run()
    except ValueError as e:
        pass
    # ok: eng-ai.err-001.python-swallowed
    try:
        run()
    except ValueError as e:
        raise RuntimeError("bad") from e
