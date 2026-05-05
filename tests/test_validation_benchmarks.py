from lob_engine.utils.performance import benchmark_event_throughput
from lob_engine.utils.validation import generate_validation_report, run_validation_suite


def test_validation_suite_passes():
    results = run_validation_suite(include_performance=False)
    assert results["passed"].all()


def test_benchmark_results_created(tmp_path):
    output = tmp_path / "benchmark_results.csv"
    results = benchmark_event_throughput(event_counts=(100,), output_path=output)
    assert output.exists()
    assert results["processed_events"].iloc[0] == 100
    assert results["events_per_second"].iloc[0] > 0


def test_validation_report_generation_runs(tmp_path):
    artifacts = generate_validation_report(output_dir=tmp_path, benchmark_event_counts=(100,))
    assert artifacts["validation_report"].exists()
    assert artifacts["benchmark_results"].exists()
    assert artifacts["validation"]["passed"].all()
