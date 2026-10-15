import pandas as pd

from libs.data.transforms import apply_aggregations


def test_custom_aggregations_keep_their_own_values():
    data = pd.DataFrame(dict(g=[1, 1, 2], a=["x", "y", "z"], b=["p", "q", "r"]))
    config = dict(
        groupby=["g"],
        date_columns=[],
        custom_functions=[
            dict(name="has_x", condition="x", true_value=1, false_value=0),
            dict(name="has_q", condition="q", true_value=10, false_value=-10),
        ],
        aggregations=[
            dict(column="a", name="a_has_x", aggfunc="has_x"),
            dict(column="b", name="b_has_q", aggfunc="has_q"),
        ],
    )

    result = apply_aggregations(data, config)

    assert result["a_has_x"].tolist() == [1, 0]
    assert result["b_has_q"].tolist() == [10, -10]
    assert config["groupby"] == ["g"]
