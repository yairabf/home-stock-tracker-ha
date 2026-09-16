"""Tests for Home Assistant service metadata."""

from pathlib import Path

import yaml


def test_inventory_service_metadata_matches_declared_contract() -> None:
    """Developer Tools metadata retains the approved inventory-write boundary."""
    services_path = (
        Path(__file__).parents[1]
        / "custom_components"
        / "home_stock_tracker"
        / "services.yaml"
    )
    services = yaml.safe_load(services_path.read_text(encoding="utf-8"))

    assert set(services) == {
        "complete_grocery_purchase",
        "adjust_inventory_stock",
    }

    purchase_fields = services["complete_grocery_purchase"]["fields"]
    assert purchase_fields["confirm"]["required"] is True
    assert purchase_fields["product_id"]["required"] is True
    assert purchase_fields["grocery_item_ids"]["required"] is True
    assert purchase_fields["quantity"]["selector"]["number"]["min"] == 0

    adjustment_fields = services["adjust_inventory_stock"]["fields"]
    assert adjustment_fields["confirm"]["required"] is True
    assert adjustment_fields["product_id"]["required"] is True
    assert adjustment_fields["operation"]["required"] is True
    assert adjustment_fields["operation"]["selector"]["select"]["options"] == [
        "set",
        "decrement",
        "mark_out",
    ]
    assert "required" not in adjustment_fields["quantity"]
    assert "required" not in adjustment_fields["unit"]
