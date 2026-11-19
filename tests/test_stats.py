"""Tests for stats parsing."""

import os
import tempfile

from LocustLibrary.stats import parse_stats_csv


def test_parse_stats_csv(tmp_path):
    csv_content = (
        "Type,Name,Request Count,Failure Count,Median Response Time,Average Response Time,"
        "Min Response Time,Max Response Time,Average Content Size,Requests/s,Failures/s,"
        "50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%\n"
        "GET,/hello,10,2,3,5.0,1.0,123.0,460.0,2.0,0.5,3,4,4,4,5,16,120,120,120,120,120\n"
        ",Aggregated,10,2,3,5.0,1.0,123.0,460.0,2.0,0.5,3,4,4,4,5,16,120,120,120,120,120\n"
    )
    p = tmp_path / "stats.csv"
    p.write_text(csv_content)
    stats = parse_stats_csv(str(p))
    assert len(stats.rows) == 1
    assert stats.rows[0].name == "/hello"
    assert stats.rows[0].request_count == 10
    assert stats.rows[0].failure_count == 2
    assert stats.aggregated is not None
    assert stats.fail_ratio == 0.2
