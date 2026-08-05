from ps_sezhao.bootstrap import run_application
from ps_sezhao.startup_guard import run_guarded


if __name__ == "__main__":
    raise SystemExit(run_guarded(run_application))
