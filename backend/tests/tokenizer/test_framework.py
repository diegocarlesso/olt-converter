from app.tokenizer.framework import Tokenizer


def test_tokenizer_classifies_lines():
    toks = Tokenizer().tokenize("! hi\ninterface gpon 1/1\n vlan 10\n")
    assert toks[0].kind == "comment"
    assert toks[1].kind == "block_start"
    assert toks[2].kind == "statement"
