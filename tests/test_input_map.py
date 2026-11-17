def test_labels_and_groups_present(tables):
    for row in tables.rows("tblInputMap"):
        assert row.Label.strip() and row.Group.strip()


def test_spouse_and_salt_labels(tables):
    labels = {r.Field: r.Label for r in tables.rows("tblInputMap")}
    assert labels["spouse_dob"].startswith("Spouse")
    assert "state, local" in labels["schedule_a_salt"]
