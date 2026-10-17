import pandas as pd
import pytest

from core.store import Store
from libs.data.eda import generate_eda_report, generate_heatmap


@pytest.fixture
def store(tmp_path):
    return Store(local_root=tmp_path / "data", locations=dict(analytics=None))


@pytest.fixture
def data():
    return pd.DataFrame(dict(price=[1.0, 2.0, 3.0, 4.0], rooms=[1, 2, 2, 3]))


def test_eda_report_through_the_store(store, data):
    path = store.save_artifact(
        "analytics",
        "eda/report.html",
        writer=lambda p: generate_eda_report(data, "EDA", p),
    )

    assert "<html" in path.read_text()[:1000].lower()


def test_heatmap_through_the_store(store, data):
    path = store.save_artifact(
        "analytics", "eda/heatmap.png", writer=lambda p: generate_heatmap(data, p)
    )

    assert path.read_bytes()[:4] == b"\x89PNG"
