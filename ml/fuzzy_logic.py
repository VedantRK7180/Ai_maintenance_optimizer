# ============================================================
# FUZZY LOGIC — MAINTENANCE URGENCY
# ============================================================

# 1. TRIANGULAR AND SHOULDER MEMBERSHIP FUNCTIONS

def triangular_membership(x, a, b, c):
    """
    Calculates the membership degree of x between 0 and 1.

    Normal triangular function:
        a < b < c

    Left-shoulder function:
        a = b

    Right-shoulder function:
        b = c
    """

    # Left-shoulder function: membership is highest at the left end
    if a == b:
        if x <= b:
            return 1.0
        elif x >= c:
            return 0.0
        else:
            return (c - x) / (c - b)

    # Right-shoulder function: membership is highest at the right end
    if b == c:
        if x >= b:
            return 1.0
        elif x <= a:
            return 0.0
        else:
            return (x - a) / (b - a)

    # Normal triangular function
    if x <= a or x >= c:
        return 0.0

    if x == b:
        return 1.0

    if x < b:
        return (x - a) / (b - a)

    return (c - x) / (c - b)


# 2. FAILURE RISK MEMBERSHIP

def risk_membership(risk):
    low = triangular_membership(risk, 0, 0, 40)
    medium = triangular_membership(risk, 20, 50, 80)
    high = triangular_membership(risk, 60, 100, 100)

    return {
        "low": low,
        "medium": medium,
        "high": high
    }


# 3. OPERATING HOURS MEMBERSHIP

def hours_membership(hours):
    low = triangular_membership(hours, 0, 0, 4000)
    medium = triangular_membership(hours, 2500, 5000, 7500)
    high = triangular_membership(hours, 6000, 10000, 10000)

    return {
        "low": low,
        "medium": medium,
        "high": high
    }


# 4. CRITICALITY MEMBERSHIP

def criticality_membership(criticality):
    low = triangular_membership(criticality, 0, 0, 40)
    medium = triangular_membership(criticality, 20, 50, 80)
    high = triangular_membership(criticality, 60, 100, 100)

    return {
        "low": low,
        "medium": medium,
        "high": high
    }


# 5. CONVERT CRITICALITY TEXT TO NUMBER

def criticality_to_number(criticality):
    mapping = {
        "Low": 20,
        "Medium": 50,
        "High": 80,
        "Critical": 100
    }

    return mapping.get(criticality, 50)


# 6. FUZZY INFERENCE ENGINE

def calculate_urgency(failure_risk, operating_hours, criticality):

    # Calculate membership degrees
    risk = risk_membership(failure_risk)
    hours = hours_membership(operating_hours)

    criticality_value = criticality_to_number(criticality)
    criticality_fuzzy = criticality_membership(criticality_value)

    # Rule 1: Low risk + low criticality -> Low urgency
    rule1 = min(
        risk["low"],
        criticality_fuzzy["low"]
    )

    # Rule 2: Medium risk -> Medium urgency
    rule2 = risk["medium"]

    # Rule 3: High risk -> High urgency
    rule3 = risk["high"]

    # Rule 4: Low risk + high criticality -> Medium urgency
    rule4 = min(
        risk["low"],
        criticality_fuzzy["high"]
    )

    # Rule 5: Medium risk + high criticality -> High urgency
    rule5 = min(
        risk["medium"],
        criticality_fuzzy["high"]
    )

    # Rule 6: High operating hours + high criticality -> High urgency
    rule6 = min(
        hours["high"],
        criticality_fuzzy["high"]
    )

    # Rule 7: High operating hours + medium risk -> High urgency
    rule7 = min(
        hours["high"],
        risk["medium"]
    )

    # Aggregate the rule outputs
    low_urgency = rule1

    medium_urgency = max(
        rule2,
        rule4
    )

    high_urgency = max(
        rule3,
        rule5,
        rule6,
        rule7
    )

    # Defuzzification using a weighted average
    numerator = (
        low_urgency * 20
        + medium_urgency * 50
        + high_urgency * 80
    )

    denominator = (
        low_urgency
        + medium_urgency
        + high_urgency
    )

    if denominator == 0:
        urgency_score = 0.0
    else:
        urgency_score = numerator / denominator

    # Convert the score into an urgency category
    if urgency_score < 40:
        urgency_level = "LOW"
    elif urgency_score < 65:
        urgency_level = "MEDIUM"
    else:
        urgency_level = "HIGH"

    return urgency_score, urgency_level


# 7. TEST THE FUZZY LOGIC INDEPENDENTLY

if __name__ == "__main__":

    print("\n========== FUZZY LOGIC TEST ==========\n")

    failure_risk = 43.0
    operating_hours = 7240
    criticality = "High"

    print("Input:")
    print(f"Failure Risk     : {failure_risk}%")
    print(f"Operating Hours  : {operating_hours}")
    print(f"Criticality      : {criticality}")

    urgency_score, urgency_level = calculate_urgency(
        failure_risk,
        operating_hours,
        criticality
    )

    print("\nFuzzy Logic Result:")
    print(f"Urgency Score    : {urgency_score:.2f}")
    print(f"Urgency Level    : {urgency_level}")

    print("\n========== BOUNDARY TESTS ==========\n")

    print("Risk 0% membership:", risk_membership(0))
    print("Risk 100% membership:", risk_membership(100))

    print("Hours 0 membership:", hours_membership(0))
    print("Hours 10000 membership:", hours_membership(10000))

    print("\n====================================\n")