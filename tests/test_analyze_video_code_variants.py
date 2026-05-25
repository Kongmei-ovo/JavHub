import importlib.util
import sys
from pathlib import Path


def load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "analyze_video_code_variants.py"
    spec = importlib.util.spec_from_file_location("analyze_video_code_variants", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_normalize_censored_jp_variants_to_base_number():
    mod = load_module()

    assert mod.analyze_code("TKMIAA-784").base_display == "MIAA-784"
    assert mod.analyze_code("MIAA-784BOD").base_display == "MIAA-784"
    assert mod.analyze_code("miaa00784").base_display == "MIAA-784"
    assert mod.analyze_code("4MIAA784").base_display == "MIAA-784"


def test_variant_labels_capture_fanza_and_service_wrappers():
    mod = load_module()

    assert mod.analyze_code("TKMIAA-784").variants == ("fanza_limited_tk_prefix",)
    assert mod.analyze_code("MIAA-784BOD").variants == ("bod_suffix",)
    assert mod.analyze_code("4MIAA784").variants == ("rental_4_prefix",)
    assert mod.analyze_code("miaa00784").variants == ("dmm_padded_digits",)


def test_parse_regular_code_and_fc2_without_false_variant():
    mod = load_module()

    regular = mod.analyze_code("ABP-588")
    assert regular.base_display == "ABP-588"
    assert regular.variants == ()

    fc2 = mod.analyze_code("FC2-PPV-1234567")
    assert fc2.family == "fc2"
    assert fc2.base_display == "FC2-PPV-1234567"
    assert fc2.variants == ()


def test_row_variants_distinguish_content_id_padding_from_dvd_padding():
    mod = load_module()

    digital = {"content_id": "miaa00784", "dvd_id": None}
    assert mod.effective_row_variants(digital, mod.analyze_code("miaa00784")) == ("dmm_content_id_padded",)

    dvd = {"content_id": "000_024", "dvd_id": "DABA-0548"}
    assert mod.effective_row_variants(dvd, mod.analyze_code("DABA-0548")) == ("padded_digits_in_dvd_id",)
