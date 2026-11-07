"""Noiseless final-sector MWPM only; this is not a circuit-level decoder."""

import numpy as np
import pymatching


def preparation_corrections(compiled, raw):
    records = {m.key: m.index for m in compiled.measurements}
    result = {}
    for prep in compiled.preparations:
        hx, hz = (prep.check_matrix(basis) for basis in "XZ")
        sx, sz = (raw[:, [records[c.measurements[-1]] for c in prep.checks if c.basis == basis]]
                  for basis in "XZ")
        # Rows are semantic check identities; columns are stable physical data
        # IDs. PyMatching 2.3.1 returns one correction bit per matrix column.
        xs = pymatching.Matching.from_check_matrix(hz).decode_batch(sz).astype(np.uint8)
        zs = pymatching.Matching.from_check_matrix(hx).decode_batch(sx).astype(np.uint8)
        assert xs.shape == zs.shape == (len(raw), len(prep.data_ids))
        assert np.array_equal(xs @ hz.T % 2, sz)
        assert np.array_equal(zs @ hx.T % 2, sx)
        result[prep.module_id] = tuple(prep.resolve(x, z) for x, z in zip(xs, zs, strict=True))
    return result
