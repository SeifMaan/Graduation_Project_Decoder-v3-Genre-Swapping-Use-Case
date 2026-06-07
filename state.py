def initialize_world_state(compiled_context: dict):

    context = compiled_context["retrieved_context"]

    return {
        "characters": context.get("character_states", []),
        "relationships": context.get("relationship_summary", []),
        "events": [],
        "chapter_memory": [],
    }


def update_world_state(
    world_state: dict,
    outline: dict,
):

    changes = outline.get(
        "world_state_changes",
        [],
    )

    world_state["events"].extend(changes)

    summary = summarize_chapter(outline)

    world_state["chapter_memory"].append(summary)

    world_state["chapter_memory"] = world_state["chapter_memory"][-5:]

    return world_state


def summarize_chapter(outline: dict):
    """Safely summarize chapter even if chapter_number is missing"""

    # Safe access with defaults
    chapter_num = outline.get("chapter_number", "?")
    chapter_title = outline.get("chapter_title", "Untitled Chapter")

    scene_text = " ".join(
        scene.get("summary", "") for scene in outline.get("scenes", [])
    )

    return (
        f"Chapter {chapter_num} - "
        f"{chapter_title}: "
        f"{scene_text[:500]}"  # Limit length
    )


def validate_scene(
    prose: str,
    world_state: dict,
    outline: dict,
    genre: str | None,
):

    warnings = []

    pov = outline.get("pov_character", "")

    if pov and pov.lower() not in prose.lower():
        warnings.append(f"POV character '{pov}' missing from prose.")

    known_names = [
        character.get("name", "").lower()
        for character in world_state.get("characters", [])
    ]

    # Check for unknown character names (capitalized words not in known names)
    words = prose.split()
    for word in words:
        clean_word = word.strip(".,!?\"'").lower()
        if clean_word.istitle() and len(clean_word) > 3:
            if clean_word not in known_names:
                # This is just a soft warning, don't add for now
                pass

    if genre == "psychological_thriller":
        thriller_words = ["fear", "secret", "suspicion", "paranoia", "dark", "twist"]
        if not any(word in prose.lower() for word in thriller_words):
            warnings.append(
                "Thriller tone appears weak. Consider adding more suspenseful elements."
            )

    return warnings
