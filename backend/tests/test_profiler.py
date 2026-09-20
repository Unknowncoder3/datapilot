import pandas as pd
from app.services.profiler import profile_dataframe

def test_profile_dataframe():
    df=pd.DataFrame({"name":["A","B","B"],"revenue":[10,None,20]})
    p=profile_dataframe(df)
    assert p["row_count"]==3
    assert p["missing_cells"]==1
    assert p["duplicate_rows"]==1
    assert p["columns"][1]["semantic_type"]=="numeric"
