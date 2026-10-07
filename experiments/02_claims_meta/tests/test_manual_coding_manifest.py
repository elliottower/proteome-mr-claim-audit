import hashlib

import manual_coding_manifest as manifest


def test_a_folder_hash_changes_with_a_byte_or_a_name_and_not_with_the_order_written(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for folder, names in ((a, ("x.txt", "sub/y.txt")), (b, ("sub/y.txt", "x.txt"))):
        for name in names:
            (folder / name).parent.mkdir(parents=True, exist_ok=True)
            (folder / name).write_text(name)
    first = manifest.tree(a)
    assert first["files"] == 2 and first["sha256"] == manifest.tree(b)["sha256"]
    lines = "".join(f"{hashlib.sha256(n.encode()).hexdigest()}  {n}\n"
                    for n in ("sub/y.txt", "x.txt"))
    assert first["sha256"] == hashlib.sha256(lines.encode()).hexdigest()
    (b / "x.txt").write_text("x.txT")
    assert manifest.tree(b)["sha256"] != first["sha256"]
    (a / "x.txt").rename(a / "z.txt")
    assert manifest.tree(a)["sha256"] != first["sha256"]
