
import json

import pandas as pd

import config
from crawl_details import html_path
from parsers import parse_detail_page


def main():
    rows = [json.loads(l) for l in config.SEARCH_RESULTS_FILE.open(encoding="utf-8")]
    df = pd.DataFrame(rows)

    details = []
    for pid in df["property_id"].unique():
        p = html_path(pid)
        d = parse_detail_page(p.read_text(encoding="utf-8")) if p.exists() else {}
        d["property_id"] = pid
        details.append(d)
    df = df.merge(pd.DataFrame(details), on="property_id", how="left")

    # combinam sursele: card + pagina de detalii
    for col in ["bedrooms", "bathrooms", "beds"]:
        df[col] = df[f"{col}_card"].fillna(df.get(f"{col}_detail"))
    df["rating"] = df["rating"].fillna(df.get("rating_ld"))
    df["num_reviews"] = df["num_reviews"].fillna(df.get("num_reviews_ld"))
    if "has_breakfast" not in df.columns:
        df["has_breakfast"] = 0
    df["breakfast"] = (df["breakfast_included"].fillna(0).astype(int)
                       | df["has_breakfast"].fillna(0).astype(int))
    df = df.rename(columns={"query_city": "city", "price": "price_per_night"})

    # features
    main_cols = [
        "property_id", "name", "city", "property_type",
        "max_capacity", "bedrooms", "beds", "bathrooms",
        "rating", "num_reviews",
        "has_parking", "has_wifi", "has_air_conditioning", "breakfast",
        "has_balcony", "free_cancellation",
        "price_per_night",
    ]
    extra_cols = ["stars", "area_m2", "distance_from_centre", "latitude", "longitude",
                  "has_kitchen", "has_pool", "has_pets_allowed", "no_prepayment",
                  "num_facilities_listed", "unit_description", "address", "url",
                  "checkin", "adults", "scraped_at", "has_ski_storage", "has_ski_to_door", "has_sauna", "has_fireplace", "has_hot_tub"]
    cols = main_cols + [c for c in extra_cols if c in df.columns]
    for c in main_cols:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[cols]
    df = df[df["price_per_night"].notna()]

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.DATASET_FILE, index=False, encoding="utf-8")

    print(f"Dataset: {len(df)} randuri x {df.shape[1]} coloane -> {config.DATASET_FILE}")
    print("\nRanduri per oras:\n", df["city"].value_counts().to_string())
    print("\nRanduri per tip:\n", df["property_type"].value_counts().to_string())
    print("\n% valori lipsa (features principale):")
    print((df[main_cols].isna().mean() * 100).round(1).to_string())


if __name__ == "__main__":
    main()
