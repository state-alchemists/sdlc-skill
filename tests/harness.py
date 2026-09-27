"""Shared runner for the framework-free test scripts in this directory."""


def run_cases(namespace):
    """Run every `case_*` function in `namespace`, in definition order.

    Prints one line per case and returns an exit code: 0 when all pass.
    """
    cases = [
        value
        for name, value in namespace.items()
        if name.startswith("case_") and callable(value)
    ]
    failures = 0
    for case in cases:
        try:
            case()
            print("PASS  %s" % case.__name__)
        except Exception as error:  # a crash is a failed case, not a lost run
            failures += 1
            print("FAIL  %s — %s: %s" % (case.__name__, type(error).__name__, error))
    print("\n%d case(s), %d failed" % (len(cases), failures))
    return 1 if failures else 0
