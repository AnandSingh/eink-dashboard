from app import theme


def test_identity_at_factor_1():
    lut = theme.eink_lut(1.0)
    assert len(lut) == 256
    assert list(lut) == list(range(256))  # no-op


def test_endpoints_preserved():
    lut = theme.eink_lut(1.35)
    assert lut[0] == 0      # black stays black
    assert lut[255] == 255  # paper stays paper


def test_all_values_in_range():
    for f in (1.0, 1.35, 2.0, 3.0):
        lut = theme.eink_lut(f)
        assert all(0 <= v <= 255 for v in lut)
        assert len(lut) == 256


def test_monotonic_non_decreasing():
    lut = theme.eink_lut(1.35)
    assert all(lut[i] <= lut[i + 1] for i in range(255))


def test_contrast_pushes_darks_down_lights_up():
    lut = theme.eink_lut(1.35)
    # darks get darker, lights get lighter (separation increases)
    assert lut[40] < 40     # headings toward near-black
    assert lut[110] < 110   # secondary text slightly darker
    assert lut[180] > 180   # faint hints recede toward paper
    assert lut[128] == 128  # mid-grey is the fixed point


def test_stronger_factor_more_extreme():
    weak = theme.eink_lut(1.2)
    strong = theme.eink_lut(2.0)
    assert strong[40] <= weak[40]     # darks darker under stronger contrast
    assert strong[200] >= weak[200]   # lights lighter
