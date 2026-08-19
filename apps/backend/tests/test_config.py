from app.config import resolve_worker_max_jobs


def test_worker_concurrency_auto_tracks_cpu_with_conservative_bounds():
    assert resolve_worker_max_jobs("auto", cpu_count=1) == 1
    assert resolve_worker_max_jobs("auto", cpu_count=4) == 4
    assert resolve_worker_max_jobs("auto", cpu_count=64) == 8


def test_worker_concurrency_explicit_value_wins():
    assert resolve_worker_max_jobs(12, cpu_count=2) == 12
