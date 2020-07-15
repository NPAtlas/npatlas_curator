import pytest
from app.checker.NameString import NameString


# Iterate over list of test name tuples
# tuple[0] = test case
# tuple[1] = expected result
TEST_NAME_TUPLES = (
    ("abc name", "Abc name"),
    ("Tricycline Methyl Ethyl Aglycon", "Tricycline methyl ethyl aglycon"),
    ("Methyl Ethyl Aglycon", "Methyl ethyl aglycon"),
    ("jacobius a1", "Jacobius A1"),
)


def test_regularize_name_unnamed():
    name = NameString("no name")
    name.regularize_name()
    assert name.get_name() == "Not named"


def test_regularize_unnamed1():
    name = NameString("not named")
    name._regularize_unnamed()
    assert name.get_name() == "Not named"


def test_regularize_unnamed_boundary():
    names = ("none", "unknown", "unkown", "non", "unnnamed")
    for name in names:
        name_obj = NameString(name)
        name_obj._regularize_unnamed()
        assert name_obj.get_name() == "Not named"


def test_capitalize_first():
    name = NameString("abc name")
    name._capitalize_first()
    assert name.get_name() == "Abc name"


def test_decapitalize_suffixes():
    name = NameString("Tricycline Methyl Ethyl Aglycon")
    name._decapitalize_suffixes()
    # Here get the
    assert name.get_name() == "Tricycline methyl ethyl aglycon"


def test_regularize_capital():
    for name in TEST_NAME_TUPLES:
        name_obj = NameString(name[0])
        name_obj._regularize_capital()
    assert name_obj.get_name() == name[1]


def test_regularize_name():
    for name in TEST_NAME_TUPLES:
        name_obj = NameString(name[0])
        name_obj.regularize_name()
    assert name_obj.get_name() == name[1]
