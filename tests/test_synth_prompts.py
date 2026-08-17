import pytest

from ml.synth_prompts import BOT_STYLES, REGISTER_RULES, build_prompt


def test_every_style_has_required_keys():
    for style in BOT_STYLES:
        assert set(style) >= {"name", "instruction", "rubric", "words"}


def test_style_names_are_unique():
    names = [style["name"] for style in BOT_STYLES]
    assert len(names) == len(set(names))


def test_every_style_maps_to_a_rubric_signal():
    # Kelas bot harus mencerminkan sinyal yang dipakai anotator manusia
    # (context/11-annotation-rubric.md bagian 3), bukan ciri generator.
    for style in BOT_STYLES:
        assert style["rubric"].startswith("3.")


def test_word_targets_stay_near_real_review_length():
    # Median review asli 11 kata, bot berlabel tangan 9.5 kata. Target panjang
    # tiap gaya harus berada di sekitar itu, bukan 17+ kata seperti versi lama.
    for style in BOT_STYLES:
        low, high = style["words"]
        assert 3 <= low < high <= 22, style["name"]

    midpoints = sorted((low + high) / 2 for low, high in (s["words"] for s in BOT_STYLES))
    median_midpoint = midpoints[len(midpoints) // 2]
    assert 8 <= median_midpoint <= 14


def test_prompt_contains_style_instruction():
    style = BOT_STYLES[0]
    assert style["instruction"] in build_prompt(style, 10)


def test_prompt_contains_register_rules():
    # Tanpa aturan register, generator menulis Bahasa Indonesia baku dan model
    # cuma belajar "formal = bot".
    assert REGISTER_RULES in build_prompt(BOT_STYLES[0], 10)


def test_prompt_states_requested_count():
    assert "37" in build_prompt(BOT_STYLES[0], 37)


def test_prompt_states_word_budget():
    style = BOT_STYLES[0]
    low, high = style["words"]
    prompt = build_prompt(style, 5)
    assert str(low) in prompt and str(high) in prompt


def test_prompt_forbids_identifying_details():
    prompt = build_prompt(BOT_STYLES[0], 5)
    assert "nama toko" in prompt.lower()


def test_register_rules_demand_informal_markers():
    lowered = REGISTER_RULES.lower()
    assert "huruf kecil" in lowered
    assert "singkatan" in lowered


def test_build_prompt_rejects_nonpositive_count():
    with pytest.raises(ValueError):
        build_prompt(BOT_STYLES[0], 0)
