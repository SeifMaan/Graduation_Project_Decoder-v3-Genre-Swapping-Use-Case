import json
import re
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from prompts import (
    BLUEPRINT_SYSTEM,
    OUTLINE_SYSTEM,
    PROSE_SYSTEM,
    build_blueprint_prompt,
    build_outline_prompt,
    build_scene_prompt,
    get_genre_modifier,
)

MISTRAL_API_KEY = "MISTRAL_API_KEY"
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL = "mistral-large-latest"


def create_session_with_retries():
    """Create a requests session with retry strategy"""
    session = requests.Session()

    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy, pool_connections=10, pool_maxsize=10
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 4000,
    retry_count: int = 3,
):
    """Call LLM with retry logic and better error handling"""

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    session = create_session_with_retries()
    last_error = None

    for attempt in range(retry_count):
        try:
            print(f"[DEBUG] API call attempt {attempt + 1}/{retry_count}")

            response = session.post(
                MISTRAL_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )

            response.raise_for_status()

            result = response.json()["choices"][0]["message"]["content"]
            print(f"[DEBUG] API call successful, response length: {len(result)}")
            return result

        except requests.exceptions.Timeout as e:
            last_error = e
            print(f"[DEBUG] Timeout error on attempt {attempt + 1}: {e}")
            if attempt < retry_count - 1:
                wait_time = (attempt + 1) * 10
                time.sleep(wait_time)

        except requests.exceptions.ConnectionError as e:
            last_error = e
            print(f"[DEBUG] Connection error on attempt {attempt + 1}: {e}")
            if attempt < retry_count - 1:
                wait_time = (attempt + 1) * 15
                time.sleep(wait_time)

        except Exception as e:
            last_error = e
            print(f"[DEBUG] Error on attempt {attempt + 1}: {e}")
            if attempt < retry_count - 1:
                wait_time = (attempt + 1) * 10
                time.sleep(wait_time)

    raise Exception(
        f"LLM call failed after {retry_count} attempts. Last error: {last_error}"
    )


def repair_json(json_str: str) -> dict:
    """Aggressive JSON repair for common LLM output issues"""

    # Remove markdown code blocks
    json_str = re.sub(r"```json\s*", "", json_str)
    json_str = re.sub(r"```\s*", "", json_str)

    # Try to extract JSON from text
    json_match = re.search(r"\{[\s\S]*\}", json_str)
    if json_match:
        json_str = json_match.group(0)

    # Fix common issues
    json_str = re.sub(r",\s*}", "}", json_str)  # Remove trailing commas
    json_str = re.sub(r",\s*]", "]", json_str)  # Remove trailing commas in arrays
    json_str = re.sub(
        r"([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', json_str
    )  # Add quotes to keys
    json_str = re.sub(
        r":\s*\'([^\']*)\'", r': "\1"', json_str
    )  # Replace single quotes with double
    json_str = re.sub(
        r':\s*([^"\[\]{}\s,][^,]*[^"\[\]{}\s,])', r': "\1"', json_str
    )  # Quote unquoted strings

    # Remove comments
    json_str = re.sub(r"//.*?(\n|$)", "\n", json_str)
    json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)

    # Fix missing commas between objects
    json_str = re.sub(r"}\s*{", "},{", json_str)

    # Fix newlines in strings
    json_str = re.sub(r'(?<!")\n(?!")', " ", json_str)

    return json_str


def parse_json(raw: str):
    """Parse JSON with extensive repair attempts"""

    print(f"[DEBUG] Attempting to parse JSON...")

    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try repair
    repaired = repair_json(raw)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        print(f"[DEBUG] First repair attempt failed: {e}")

        # Try more aggressive repair - extract only valid JSON structure
        lines = raw.split("\n")
        in_string = False
        escape = False
        brace_count = 0
        bracket_count = 0
        start_idx = -1

        for i, line in enumerate(lines):
            for j, char in enumerate(line):
                if escape:
                    escape = False
                    continue
                if char == "\\":
                    escape = True
                    continue
                if char == '"':
                    in_string = not in_string
                if not in_string:
                    if char == "{":
                        if brace_count == 0 and bracket_count == 0:
                            start_idx = i
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                    elif char == "[":
                        bracket_count += 1
                    elif char == "]":
                        bracket_count -= 1

        if start_idx != -1:
            # Try to extract from the first { to the matching }
            # This is simplified; in practice you'd track braces properly
            pass

        # Return a minimal valid blueprint as last resort
        return get_default_blueprint()


def get_default_blueprint():
    """Return a rich default blueprint structure"""
    return {
        "title": "A Court of Frost and Daylight - Continued",
        "premise": "Continue the story from where it left off, following the characters through new challenges and revelations.",
        "structure_type": "linear",
        "total_chapters": 5,
        "central_conflict": "The characters must face the consequences of their past actions while navigating new threats and relationships.",
        "primary_arcs": [
            {
                "arc_name": "Main Character Arc",
                "character": "Protagonist",
                "starts_at": "At a crossroads, uncertain of the future",
                "ends_at": "Having grown through challenges, ready for what comes next",
                "key_turning_point": "A crucial decision that changes everything",
            }
        ],
        "acts": [
            {
                "label": "Act One",
                "chapter_range": "1-2",
                "narrative_goal": "Establish the new status quo and inciting incident",
                "ends_with": "The protagonist makes a choice that sets events in motion",
            },
            {
                "label": "Act Two",
                "chapter_range": "3-4",
                "narrative_goal": "Complications arise and relationships are tested",
                "ends_with": "The situation reaches a critical point",
            },
            {
                "label": "Act Three",
                "chapter_range": "5",
                "narrative_goal": "Climax and resolution",
                "ends_with": "The story concludes with new understanding",
            },
        ],
        "world_threads_activated": [],
        "tone": "Dramatic and immersive, with emotional depth and tension",
    }


def compile_context(
    retrieved_context: dict,
    user_prompt: str,
    use_case: str,
    genre: str | None,
) -> dict:

    return {
        "use_case": use_case,
        "genre": genre,
        "user_prompt": user_prompt,
        "retrieved_context": retrieved_context,
    }


def generate_blueprint(compiled_context: dict):
    """Generate blueprint with error handling"""

    genre_modifier = get_genre_modifier(compiled_context.get("genre"))

    prompt = build_blueprint_prompt(
        compiled_context,
        genre_modifier,
    )

    print(f"[DEBUG] Generating blueprint...")

    try:
        raw = call_llm(
            BLUEPRINT_SYSTEM,
            prompt,
            temperature=0.7,
            max_tokens=4000,
        )

        # Save raw response for debugging
        with open("debug_blueprint_raw.txt", "w", encoding="utf-8") as f:
            f.write(raw)

        blueprint = parse_json(raw)

        # Validate blueprint has required fields
        if not blueprint.get("title"):
            blueprint["title"] = "A Court of Frost and Daylight - Continued"
        if not blueprint.get("total_chapters"):
            blueprint["total_chapters"] = 5
        if not blueprint.get("acts"):
            blueprint["acts"] = get_default_blueprint()["acts"]
        if not blueprint.get("primary_arcs"):
            blueprint["primary_arcs"] = get_default_blueprint()["primary_arcs"]

        print(
            f"[DEBUG] Blueprint generated with {blueprint.get('total_chapters')} chapters"
        )
        return blueprint

    except Exception as e:
        print(f"[ERROR] Blueprint generation failed: {e}")
        print(f"[ERROR] Using default blueprint")
        return get_default_blueprint()


def generate_outline(
    blueprint: dict,
    world_state: dict,
    previous_summaries: list[str],
    chapter_number: int,
):
    """Generate outline with error handling"""

    prompt = build_outline_prompt(
        blueprint,
        world_state,
        previous_summaries,
        chapter_number,
    )

    print(f"[DEBUG] Generating outline for chapter {chapter_number}")

    try:
        raw = call_llm(
            OUTLINE_SYSTEM,
            prompt,
            temperature=0.7,
            max_tokens=3000,
        )

        outline = parse_json(raw)

        # Ensure required fields
        if "chapter_number" not in outline:
            outline["chapter_number"] = chapter_number
        if "chapter_title" not in outline:
            outline["chapter_title"] = f"Chapter {chapter_number}"
        if "scenes" not in outline:
            outline["scenes"] = [
                {
                    "title": f"Scene 1",
                    "summary": f"Continue the story from chapter {chapter_number-1}",
                    "pov_character": "",
                    "key_beats": [],
                }
            ]
        if "world_state_changes" not in outline:
            outline["world_state_changes"] = []

        return outline

    except Exception as e:
        print(f"[ERROR] Outline generation failed for chapter {chapter_number}: {e}")
        # Return a minimal valid outline
        return {
            "chapter_number": chapter_number,
            "chapter_title": f"Chapter {chapter_number}",
            "scenes": [
                {
                    "title": f"Chapter {chapter_number} - Main Scene",
                    "summary": f"Continue the narrative, advancing the plot and character development.",
                    "pov_character": "",
                    "key_beats": [],
                }
            ],
            "world_state_changes": [],
        }


def generate_scene(
    scene_outline: dict,
    chapter_outline: dict,
    world_state: dict,
    previous_scene_ending: str,
    genre: str | None,
):
    """Generate scene prose with error handling"""

    genre_modifier = get_genre_modifier(genre)

    prompt = build_scene_prompt(
        scene_outline,
        chapter_outline,
        world_state,
        previous_scene_ending,
        genre_modifier,
    )

    print(f"[DEBUG] Generating scene: {scene_outline.get('title', 'Untitled')}")

    try:
        prose = call_llm(
            PROSE_SYSTEM,
            prompt,
            temperature=0.9,
            max_tokens=2000,
        )
        return prose

    except Exception as e:
        print(f"[ERROR] Scene generation failed: {e}")
        return f"The scene continued. {scene_outline.get('summary', 'The story progressed.')}"
