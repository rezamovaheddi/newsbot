from bot.utils import (
    canonical_url,
    clean_html,
    fa_digits,
    mask_phone,
    normalize_phone,
    split_plain_text,
)


def test_fa_digits():
    assert fa_digits("08:00") == "۰۸:۰۰"


def test_normalize_phone():
    assert normalize_phone("+98 912 345 6789") == "+989123456789"
    assert normalize_phone("09123456789") == "+989123456789"
    assert normalize_phone("00989123456789") == "+989123456789"
    assert normalize_phone("989123456789") == "+989123456789"


def test_mask_phone():
    assert mask_phone("+989123456789") == "+۹۸ **** **۸۹"


def test_split_plain_text():
    chunks = split_plain_text("a" * 9000, 3500)
    assert all(len(c) <= 3500 for c in chunks)
    assert "".join(chunks).replace("\n", "") == "a" * 9000


def test_clean_html():
    assert clean_html("<b>hi</b> there") == "hi there"
    assert clean_html("<script>x</script>ok") == "ok"


def test_canonical_url():
    assert canonical_url("https://x.com/a/?utm_source=foo&b=1#frag") == "https://x.com/a?b=1"
