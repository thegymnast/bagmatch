import math


def _value(record, name):
    try:
        return record[name]
    except (KeyError, TypeError):
        return getattr(record, name)


def rank_bags(query, bags, limit=10, flight=None):
    candidates = []
    for bag in bags:
        if flight and _value(bag, "flight") and _value(bag, "flight").upper() != flight.upper():
            continue
        weight_difference = abs(float(_value(bag, "weight_kg")) - float(query["weight_kg"]))
        bag_dimensions = sorted(
            float(_value(bag, field))
            for field in ("length_cm", "width_cm", "height_cm")
        )
        query_dimensions = sorted(
            float(query.get(field, _value(bag, field)))
            for field in ("length_cm", "width_cm", "height_cm")
        )
        dimension_differences = [
            abs(bag_dimension - query_dimension)
            / max(bag_dimension, query_dimension, 1.0)
            for bag_dimension, query_dimension in zip(bag_dimensions, query_dimensions)
        ]
        if weight_difference > 2.0 or any(value > 0.15 for value in dimension_differences):
            continue

        colour_difference = math.sqrt(
            sum(
                (float(_value(bag, field)) - float(query[field])) ** 2
                for field in ("L", "a", "b_lab")
            )
        )
        dimension_score = sum(dimension_differences) / len(dimension_differences)
        score = (
            0.55 * min(colour_difference / 100.0, 1.0)
            + 0.30 * dimension_score
            + 0.15 * min(weight_difference / 2.0, 1.0)
        )
        reasons = [
            "Colour: {:.1f} ΔE".format(colour_difference),
            "Dimensions: {:.1f}% average difference".format(dimension_score * 100),
            "Weight: {:.2f} kg difference".format(weight_difference),
        ]
        candidates.append(
            {
                "bag": bag,
                "score": score,
                "colour_distance": colour_difference,
                "dimension_difference": dimension_score,
                "weight_difference": weight_difference,
                "reasons": reasons,
            }
        )
    candidates.sort(key=lambda result: result["score"])
    return candidates[:limit]
