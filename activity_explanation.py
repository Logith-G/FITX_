from __future__ import annotations


def _split_duration(total: int, weights: list[int]) -> list[int]:
    total = max(len(weights), int(total or 0))
    weight_sum = sum(weights)
    parts = [max(1, total * weight // weight_sum) for weight in weights]
    parts[-1] += total - sum(parts)
    return parts


def _step(name: str, minutes: int, instructions: list[str], repetitions: str = "") -> dict:
    return {
        "name": name,
        "minutes": minutes,
        "repetitions": repetitions,
        "instructions": instructions,
    }


def _single_activity(activity: str, duration: int) -> tuple[str, str, list[dict]]:
    duration = max(3, duration)
    if activity == "Walking":
        parts = _split_duration(duration, [2, 5, 3])
        return (
            "A simple walking session that builds comfortable movement and consistency.",
            "Keep a pace where you can still speak comfortably. Slow down whenever you need to.",
            [
                _step("Easy start", parts[0], ["Walk slowly and let your arms move naturally."]),
                _step("Comfortable walk", parts[1], ["Walk at a steady, relaxed pace.", "You should be able to speak in short sentences."]),
                _step("Slow down", parts[2], ["Gradually reduce your speed and finish with easy steps."]),
            ],
        )
    if activity == "Strength":
        parts = _split_duration(max(5, duration), [2, 2, 2, 1, 2])
        return (
            "Gentle muscle-strengthening movements using your own body or a stable support.",
            "Move slowly and stop before you feel pain. Bodyweight means using your own body instead of weights.",
            [
                _step("Sit-to-stand", parts[0], ["Sit on a stable chair.", "Stand up slowly, then sit down with control."], "Repeat at a comfortable pace."),
                _step("Wall push-ups", parts[1], ["Face a wall with your hands on it.", "Bend your elbows slowly, then push away gently."], "Repeat comfortably."),
                _step("Calf raises", parts[2], ["Hold a stable support if needed.", "Raise your heels slowly, then lower them."], "Repeat comfortably."),
                _step("Rest", parts[3], ["Pause, breathe normally, and relax your muscles."]),
                _step("Easy repeat", parts[4], ["Repeat one or two comfortable movements from above.", "Stop before you feel pain."]),
            ],
        )
    if activity == "Mobility":
        parts = _split_duration(duration, [1, 2, 2, 2, 2])
        return (
            "Controlled movements that help your joints move comfortably through their available range.",
            "Use a small, comfortable range of motion and never force a stretch.",
            [
                _step("Neck movement", parts[0], ["Slowly look left and right.", "Keep your shoulders relaxed."]),
                _step("Shoulder rolls", parts[1], ["Circle your shoulders slowly forward and backward."]),
                _step("Arm circles", parts[2], ["Make small controlled circles with your arms."]),
                _step("Hip movement", parts[3], ["Move your hips gently from side to side while standing tall."]),
                _step("Ankle circles", parts[4], ["Lift one foot slightly and circle the ankle slowly.", "Change sides halfway through."]),
            ],
        )
    if activity == "Yoga":
        parts = _split_duration(duration, [2, 2, 2, 2, 2, 1])
        return (
            "A gentle beginner yoga session combining simple positions, controlled movement, and breathing.",
            "Stay comfortable, breathe slowly, and use a chair or skip a position if it does not feel right.",
            [
                _step("Easy seated breathing", parts[0], ["Sit comfortably with your back relaxed and upright.", "Take slow breaths in and out."]),
                _step("Cat-cow movement", parts[1], ["On hands and knees, gently round your back, then relax it.", "Move slowly with your breathing."]),
                _step("Child's pose", parts[2], ["Lower your hips toward your heels or use a chair for support.", "Breathe comfortably."]),
                _step("Gentle standing stretch", parts[3], ["Stand tall and reach your arms comfortably overhead.", "Lower them slowly."]),
                _step("Seated forward stretch", parts[4], ["Sit comfortably and lean forward only as far as feels easy."]),
                _step("Easy relaxation", parts[5], ["Return to a comfortable position and take slow breaths."]),
            ],
        )
    if activity in {"Running", "Cycling", "Sports", "Dance", "Cardio"}:
        parts = _split_duration(duration, [2, 5, 2, 1])
        descriptions = {
            "Running": ("Easy jog", "Jog lightly or walk when needed."),
            "Cycling": ("Easy ride", "Cycle at a pace that lets you stay in control."),
            "Sports": ("Easy movement", "Practice relaxed movements from your chosen sport."),
            "Dance": ("Easy dance", "Move to a comfortable rhythm and keep enough space around you."),
            "Cardio": ("Continuous movement", "Use brisk walking or easy step movements."),
        }
        name, instruction = descriptions[activity]
        return (
            "Continuous movement that gently raises your heart rate and builds endurance.",
            "Choose an intensity where you can still speak. Reduce the pace if breathing becomes uncomfortable.",
            [
                _step("Warm-up", parts[0], ["Start with slow walking or very easy movement."]),
                _step(name, parts[1], [instruction, "Keep your movements smooth and controlled."]),
                _step("Easy movement", parts[2], ["Return to a lighter pace while staying gently active."]),
                _step("Cool-down", parts[3], ["Slow down until your breathing feels normal."]),
            ],
        )
    return (
        "A short general fitness session combining easy movement and body control.",
        "Work at a comfortable pace and take a brief pause whenever you need one.",
        [
            _step("Warm-up movement", max(1, duration // 5), ["Walk slowly and loosen your shoulders."]),
            _step("Main movement", max(1, duration * 3 // 5), ["Use comfortable whole-body movements such as walking and sit-to-stands."]),
            _step("Cool-down", max(1, duration - max(1, duration // 5) - max(1, duration * 3 // 5)), ["Slow down and breathe comfortably."]),
        ],
    )


def build_activity_breakdown(
    activity: str,
    duration: int,
    *,
    age_category: str = "Unspecified",
    activity_level: str = "Beginner",
    goal: str = "Consistency",
    reason: str = "This session matches your current FITX recommendation.",
    components: list[dict] | None = None,
) -> dict:
    """Turn an existing activity label into an actionable, beginner-friendly session."""
    if components:
        steps = []
        for component in components:
            _, _, component_steps = _single_activity(component["type"], component["minutes"])
            steps.extend(component_steps)
        what_is_it = "A personalized session made from several simple activity blocks."
        how_to_use = "Complete the blocks in order. Take a short pause between blocks if needed."
    else:
        what_is_it, how_to_use, steps = _single_activity(activity, duration)

    session_names = {
        "Walking": "Beginner Structured Walking",
        "Strength": "Beginner Bodyweight Strength",
        "Mobility": "Beginner Mobility Session",
        "Yoga": "Beginner Hatha Yoga",
        "Running": "Beginner Run-Walk Session",
        "Cycling": "Beginner Cycling Session",
        "Cardio": "Beginner Cardio Session",
        "Sports": "Beginner Sports Movement",
        "Dance": "Beginner Dance Movement",
    }
    session_name = "Personalized FITX Fitness Session" if components else session_names.get(activity, "Beginner General Fitness")

    return {
        "activity": activity,
        "title": f"{session_name} - {duration} minutes",
        "session_name": session_name,
        "duration": duration,
        "what_is_it": what_is_it,
        "why": reason,
        "how_to_use": how_to_use,
        "steps": steps,
        "profile": f"{age_category} - {activity_level} - {goal}",
        "note": "FITX provides general fitness guidance and is not a substitute for professional medical advice.",
    }