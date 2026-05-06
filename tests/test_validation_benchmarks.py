from lob_engine.utils.performance import benchmark_event_throughput
from lob_engine.utils.validation import generate_validation_report, run_validation_suite


def test_validation_suite_passes():
    results = run_validation_suite(include_performance=False)
    assert results["passed"].all()


def test_benchmark_results_created(tmp_path):
    output = tmp_path / "benchmark_results.csv"
    results = benchmark_event_throughput(event_counts=(100,), output_path=output)
    assert output.exists()
    assert (results["processed_events"] == 100).all()
    assert (results["events_per_second"] > 0).all()
    assert {"implementation_path", "benchmark_mode", "p95_latency_us", "peak_memory_mb"}.issubset(results.columns)


def test_optimised_core_benchmark_is_materially_faster():
    results = benchmark_event_throughput(event_counts=(1_000,))
    reference = results[
        (results["implementation_path"] == "reference") & (results["benchmark_mode"] == "core_matching")
    ]["events_per_second"].iloc[0]
    optimised = results[
        (results["implementation_path"] == "optimised") & (results["benchmark_mode"] == "core_matching")
    ]["events_per_second"].iloc[0]
    assert optimised > reference


def test_validation_report_generation_runs(tmp_path):
    artifacts = generate_validation_report(output_dir=tmp_path, benchmark_event_counts=(100,))
    assert artifacts["validation_report"].exists()
    assert artifacts["benchmark_results"].exists()
    assert artifacts["validation"]["passed"].all()
