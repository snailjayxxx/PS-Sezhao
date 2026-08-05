from ps_sezhao.startup_guard import run_guarded


def _run_application(argv=None):
    from ps_sezhao.bootstrap import run_application

    return run_application(argv)


if __name__ == "__main__":
    raise SystemExit(run_guarded(_run_application))
