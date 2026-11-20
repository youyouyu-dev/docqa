import math

import pytest

import main
from check_v1 import hit_rate, stem


def _sd(*scores):
    return [(s, {"number": i}) for i, s in enumerate(scores, start=1)]


def test_split_words_stopwords_punct_case():
    assert main.split_words("The cat sat on the mat.") == ["cat", "sat", "mat"]
    assert main.split_words("Python, PYTHON! python?") == ["python", "python", "python"]


def test_split_words_empty_and_chinese():
    assert main.split_words("") == []
    assert main.split_words("观测接口和动作接口") == []


def test_has_chinese():
    assert main.has_chinese("六个组件是什么") is True
    assert main.has_chinese("six components") is False
    assert main.has_chinese("six 个 components") is True
    assert main.has_chinese("") is False


def test_get_real_file():
    chunks = main.get(main.text)
    assert len(chunks) == 44
    assert chunks[0]["number"] == 1
    assert all(c["chapter"] for c in chunks)
    assert all(c["text"].strip() for c in chunks)


def test_get_structure():
    text = "## A\nintro\n### A.1\nbody1\n## B\nbody2\n"
    chunks = main.get(text)
    assert len(chunks) == 3
    assert chunks[0]["chapter"] == "A"
    assert chunks[0]["section"] == ""
    assert chunks[1]["section"] == "A.1"
    assert chunks[2]["chapter"] == "B"


def test_score_section_boost():
    chunk = {"number": 1, "chapter": "ch", "section": "context", "text": "context"}
    N = 10
    df = {"context": 1}
    got = main.score("context", chunk, N, df)
    assert got == pytest.approx(4 * math.log(N))


def test_score_no_match():
    chunk = {"number": 1, "chapter": "ch", "section": "", "text": "alpha beta"}
    assert main.score("gamma", chunk, 10, {"gamma": 1}) == 0


@pytest.mark.parametrize(
    "scores, expected",
    [
        ((1.0, 0.8, 0.1, 0.05), 2),
        ((1.0, 0.9, 0.8, 0.05, 0.01), 3),
        ((1.0, 0.9, 0.8, 0.7, 0.05), 4),
        ((1.0, 0.9, 0.8, 0.7, 0.6, 0.05), 5),
        ((1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4), 6),
    ],
)
def test_pick_breakpoints(scores, expected):
    assert main.pick(_sd(*scores), skip_first=True) == expected


def test_pick_zero_tail():
    assert main.pick(_sd(1.0, 0.5, 0.0, 0.0), skip_first=True) == 2


def test_pick_min_k_floor():
    assert main.pick(_sd(1.0, 0.1, 0.05), skip_first=False) == 2


def test_stem():
    assert stem("studies") == "study"
    assert stem("components") == "component"
    assert stem("class") == "class"
    assert stem("running") == "runn"
    assert stem("") == ""


def test_hit_rate_phrase_and_plural():
    answer = "The components work in a closed loop."
    assert hit_rate(answer, ["component", "closed loop"]) == 1.0


def test_hit_rate_partial():
    assert hit_rate("only observation here", ["observation", "action"]) == 0.5
