from backend.tools.product_recommender import recommend_product

queries = [
    "tomato blight treatment",
    "aphids on cabbage",
    "citrus root rot treatment",
    "What treats citrus canker?"
]

for q in queries:
    print("\n" + "=" * 60)
    print("Query:", q)
    print(recommend_product(q))