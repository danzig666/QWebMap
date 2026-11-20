from fidelity.html_labels import MAX_SECTIONS, SUB_SUP_SCALE, format_expression, html_sections


def test_sub_and_mismatched_close_as_qt():
    """Szerkezeti változás területtel: '<sub>..</small>' — the closing tag
    ends the innermost size change, like Qt."""
    assert html_sections("1ő→1ő\n<sub>4.35 ha</small>") == [
        ("1ő→1ő\n", 1.0), ("4.35 ha", round(SUB_SUP_SCALE, 4))]


def test_breaks_entities_and_unknown_tags():
    assert html_sections("a<br>b &amp; <b>c</b>") == [("a\nb & c", 1.0)]
    assert html_sections(None) == [] and html_sections("x") == [("x", 1.0)]


def test_sections_are_capped_and_format_lists_them_all():
    text = "".join(f"n{i}<sub>s{i}</sub>" for i in range(10))
    sections = html_sections(text)
    assert len(sections) == MAX_SECTIONS
    assert "".join(t for t, _ in sections) == "".join(f"n{i}s{i}" for i in range(10))
    expression = format_expression()
    assert expression[0] == "format" and len(expression) == 1 + 2 * MAX_SECTIONS


def test_runs_keep_colours_weights_slants_families_and_point_sizes():
    """QGIS draws a run's colour, bold, italic, family and pt size: each
    becomes a run of its own (nested formatting combines, a close ends its tag)."""
    from fidelity.html_labels import Run, html_runs
    text = ('A <b>B <i>C</i></b> <span style="color:#ff0000">D</span> '
            '<font color="blue" face="Courier New, monospace">E</font> '
            '<span style="font-size:20pt; font-weight:600">F</span>'
            '<span style="font-style:italic;font-weight:normal">G</span>')
    assert html_runs(text, base_points=10) == [
        Run("A "), Run("B ", font="|1|"), Run("C", font="|1|1"), Run(" "),
        Run("D", color="#ff0000"), Run(" "), Run("E", color="blue", font="Courier New||"), Run(" "),
        Run("F", scale=2.0, font="|1|"), Run("G", font="|0|1")]
    # A pt size needs the label's size; without it the run keeps scale 1.
    assert html_runs('<span style="font-size:20pt">x</span>')[0].scale == 1.0
    # px as Qt reads them (0.75 pt), within a <sub>: both scales.
    assert html_runs('<sub><span style="font-size:16px">x</span></sub>', 12)[0].scale == \
        round(SUB_SUP_SCALE, 4)


def test_qt_hex_alpha_colours_backgrounds_and_the_flags():
    from fidelity.html_labels import (FLAG_BACKGROUND, FLAG_TRUNCATED, css_color, html_flags,
                                      html_runs, section_color, section_font, section_scale,
                                      section_text)
    assert css_color("#80ff0000") == "rgba(255, 0, 0, 0.502)"   # Qt: #AARRGGBB
    assert css_color(" Red ") == "red"
    text = 'x <span style="background-color: yellow">bg</span>'
    assert html_flags(text) == FLAG_BACKGROUND and html_runs(text)[1].background
    assert html_flags('<span style="background-color:transparent">t</span>') == 0
    many = "".join(f'<span style="color:#{i:06x}">{i}</span>' for i in range(MAX_SECTIONS + 3))
    assert html_flags(many) == FLAG_TRUNCATED
    # The field functions: NULL where nothing is set (nothing written into the tiles).
    assert section_text("a<b>b</b>", 1) == "b" and section_text("a", 3) is None
    assert section_font("a<b>b</b>", 0) is None and section_font("a<b>b</b>", 1) == "|1|"
    assert section_color('<font color="#00ff00">g</font>', 0) == "#00ff00"
    assert section_scale("a", 0) is None and section_scale("<sub>a</sub>", 0) == round(SUB_SUP_SCALE, 4)


def test_format_lists_colours_and_fonts_per_section():
    expression = format_expression("#333333", ["|1|", ["literal", ["Arial Bold"]], ["literal", ["Arial Regular"]]])
    options = expression[2]
    assert options["text-color"] == ["to-color", ["get", "q2vt_label_c0"], "#333333"]
    assert options["text-font"] == ["match", ["coalesce", ["get", "q2vt_label_f0"], ""],
                                    "|1|", ["literal", ["Arial Bold"]], ["literal", ["Arial Regular"]]]
    assert "text-color" not in format_expression()[2]


def test_size_only_span_fields_come_from_one_parse():
    """An absolute font-size alone starts a run only with the base size: the
    text, colour and font fields use it like the scale field (pairs by index)."""
    from fidelity.html_labels import (html_runs, section_color, section_font, section_scale,
                                      section_text)
    text = '<span style="font-size:20pt">Big</span> small'
    assert len(html_runs(text, 10)) == 2
    assert [section_text(text, i, 10) for i in range(3)] == ["Big", " small", None]
    assert [section_scale(text, i, 10) for i in range(2)] == [2.0, None]
    assert section_color(text, 1, 10) is None and section_font(text, 1, 10) is None
