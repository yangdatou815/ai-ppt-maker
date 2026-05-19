from app.outline.fallback import rule_based


def test_chinese_paragraphs():
    text = (
        "我们今年发布了新一代产品 X。它解决了三大痛点。\n\n第一是性能。第二是成本。第三是可维护性。"
    )
    o = rule_based(text)
    assert o.language == "zh"
    assert o.sections
    assert all(s.bullets for s in o.sections)
    assert o.subtitle and "LLM" in o.subtitle


def test_markdown_headings():
    text = "# Vision\nWe build amazing things.\n\n## Market\nHuge TAM.\n\n## Product\nFast, cheap, reliable."
    o = rule_based(text)
    assert o.language == "en"
    headings = [s.heading for s in o.sections]
    assert "Vision" in headings
    assert "Market" in headings


def test_bullet_list():
    text = "## Features\n- Fast\n- Cheap\n- Reliable\n- Secure\n- Scalable\n- Bonus"
    o = rule_based(text)
    feat = next(s for s in o.sections if s.heading == "Features")
    assert len(feat.bullets) == 5  # capped


def test_empty_input_safe():
    o = rule_based("")
    assert o.sections
    assert o.title
