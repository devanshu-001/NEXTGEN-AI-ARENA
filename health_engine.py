"""
Pulse AI — Advanced Health Metrics Engine
Pure calculation module, fully decoupled from any UI or framework.
"""

from dataclasses import dataclass, field
from typing import Tuple
import math


# ── Activity multipliers ──────────────────────────────────────────────────────
ACTIVITY_MULTIPLIERS = {
    "beginner":     1.2,
    "intermediate": 1.55,
    "advanced":     1.725,
}

# ── BMI category thresholds ───────────────────────────────────────────────────
BMI_CATEGORIES = [
    (0,    18.5, "Underweight"),
    (18.5, 25.0, "Normal"),
    (25.0, 30.0, "Overweight"),
    (30.0, 35.0, "Obese Class I"),
    (35.0, 40.0, "Obese Class II"),
    (40.0, math.inf, "Obese Class III"),
]


# ── Data models ───────────────────────────────────────────────────────────────
@dataclass
class UserInput:
    age: int
    gender: str          # "male" | "female" | "other"
    weight_kg: float
    height_cm: float
    activity_level: str  # "beginner" | "intermediate" | "advanced"

    def validate(self):
        errors = []
        if not (1 <= self.age <= 120):
            errors.append("Age must be between 1 and 120.")
        if self.weight_kg <= 0:
            errors.append("Weight must be positive.")
        if self.height_cm <= 0:
            errors.append("Height must be positive.")
        if self.activity_level.lower() not in ACTIVITY_MULTIPLIERS:
            errors.append(f"Activity level must be one of: {list(ACTIVITY_MULTIPLIERS.keys())}.")
        if errors:
            raise ValueError(" | ".join(errors))


@dataclass
class HealthMetrics:
    # Raw inputs (echoed back)
    age: int
    gender: str
    weight_kg: float
    height_cm: float
    activity_level: str

    # Calculated fields
    bmi: float = 0.0
    bmi_category: str = ""
    bmr: float = 0.0
    tdee: float = 0.0
    body_fat_pct: float = 0.0
    ideal_weight_min_kg: float = 0.0
    ideal_weight_max_kg: float = 0.0

    # Calorie targets
    calories_maintain: float = 0.0
    calories_lose_half_kg: float = 0.0
    calories_gain_half_kg: float = 0.0

    # Summary text
    ai_summary: str = ""


# ── Core engine ───────────────────────────────────────────────────────────────
class HealthEngine:
    """
    All calculations live here.  No Streamlit, no FastAPI — just Python.
    """

    @staticmethod
    def bmi(weight_kg: float, height_cm: float) -> Tuple[float, str]:
        height_m = height_cm / 100.0
        if height_m <= 0:
            raise ValueError("Height must be positive.")
        value = round(weight_kg / (height_m ** 2), 2)
        category = "Unknown"
        for lo, hi, cat in BMI_CATEGORIES:
            if lo <= value < hi:
                category = cat
                break
        return value, category

    @staticmethod
    def bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
        """Mifflin-St Jeor equation."""
        base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
        if gender.lower() == "male":
            return round(base + 5, 2)
        else:
            # female / other defaults to female formula (conservative)
            return round(base - 161, 2)

    @staticmethod
    def tdee(bmr: float, activity_level: str) -> float:
        multiplier = ACTIVITY_MULTIPLIERS.get(activity_level.lower(), 1.2)
        return round(bmr * multiplier, 2)

    @staticmethod
    def body_fat_pct(bmi: float, age: int, gender: str) -> float:
        """Deurenberg formula."""
        gender_int = 1 if gender.lower() == "male" else 0
        pct = (1.20 * bmi) + (0.23 * age) - (10.8 * gender_int) - 5.4
        return round(max(2.0, min(pct, 70.0)), 2)  # clamp to sensible range

    @staticmethod
    def ideal_weight_range(height_cm: float) -> Tuple[float, float]:
        """
        Derives the healthy BMI weight band (18.5 – 24.9) for a given height.
        """
        height_m = height_cm / 100.0
        w_min = round(18.5 * (height_m ** 2), 1)
        w_max = round(24.9 * (height_m ** 2), 1)
        return w_min, w_max

    @staticmethod
    def calorie_targets(tdee: float) -> Tuple[float, float, float]:
        """Returns (maintain, lose_0.5kg/week, gain_0.5kg/week)."""
        # 0.5 kg/week ≈ 550 kcal/day deficit or surplus
        return round(tdee, 0), round(tdee - 550, 0), round(tdee + 550, 0)

    @staticmethod
    def ai_summary(metrics: "HealthMetrics") -> str:
        lose = int(metrics.calories_lose_half_kg)
        maintain = int(metrics.calories_maintain)
        w_min = metrics.ideal_weight_min_kg
        w_max = metrics.ideal_weight_max_kg
        bf = metrics.body_fat_pct
        cat = metrics.bmi_category

        line1 = (
            f"Your BMI is classified as **{cat}** and your estimated body fat is **{bf}%**. "
            f"To maintain your current weight, target **{maintain} kcal/day**."
        )
        line2 = (
            f"To lose 0.5 kg per week, reduce to **{lose} kcal/day**. "
            f"Your ideal healthy weight range for your height is **{w_min}–{w_max} kg**."
        )
        return line1 + "  \n" + line2

    # ── Main entry point ──────────────────────────────────────────────────────
    @classmethod
    def calculate(cls, user: UserInput) -> HealthMetrics:
        user.validate()

        bmi_val, bmi_cat     = cls.bmi(user.weight_kg, user.height_cm)
        bmr_val              = cls.bmr(user.weight_kg, user.height_cm, user.age, user.gender)
        tdee_val             = cls.tdee(bmr_val, user.activity_level)
        bf_pct               = cls.body_fat_pct(bmi_val, user.age, user.gender)
        w_min, w_max         = cls.ideal_weight_range(user.height_cm)
        cal_m, cal_l, cal_g  = cls.calorie_targets(tdee_val)

        m = HealthMetrics(
            age=user.age,
            gender=user.gender,
            weight_kg=user.weight_kg,
            height_cm=user.height_cm,
            activity_level=user.activity_level,
            bmi=bmi_val,
            bmi_category=bmi_cat,
            bmr=bmr_val,
            tdee=tdee_val,
            body_fat_pct=bf_pct,
            ideal_weight_min_kg=w_min,
            ideal_weight_max_kg=w_max,
            calories_maintain=cal_m,
            calories_lose_half_kg=cal_l,
            calories_gain_half_kg=cal_g,
        )
        m.ai_summary = cls.ai_summary(m)
        return m
