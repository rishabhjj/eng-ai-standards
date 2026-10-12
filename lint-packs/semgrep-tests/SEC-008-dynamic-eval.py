import json
import pickle

import yaml


def f(user):
    # ruleid: eng-ai.sec-008.python-dynamic-eval
    eval(user)
    # ruleid: eng-ai.sec-008.python-dynamic-eval
    exec(user)
    # ruleid: eng-ai.sec-008.python-dynamic-eval
    pickle.loads(user)
    # ok: eng-ai.sec-008.python-dynamic-eval
    json.loads(user)
    # ruleid: eng-ai.sec-008.python-unsafe-yaml
    yaml.load(user)
    # ok: eng-ai.sec-008.python-unsafe-yaml
    yaml.load(user, Loader=yaml.SafeLoader)
    # ok: eng-ai.sec-008.python-unsafe-yaml
    yaml.load(user, yaml.SafeLoader)
    # ok: eng-ai.sec-008.python-unsafe-yaml
    yaml.load(user, Loader=yaml.CSafeLoader)
    # ok: eng-ai.sec-008.python-unsafe-yaml
    yaml.load(user, yaml.CSafeLoader)
    # ok: eng-ai.sec-008.python-unsafe-yaml
    yaml.safe_load(user)
