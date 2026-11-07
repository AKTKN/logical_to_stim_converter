"""Decoder-neutral offline views, exact models and software record transforms."""

from .conditional import ConditionalReadoutModel, PauliFault, make_conditional_readout_model
from .errors import (
    DecoderViewError,
    DEMConstructionError,
    SourceMismatchError,
    UndefinedObservableError,
    UnsupportedProjectionError,
)
from .frames import CorrectionBatch, FrameBoundary, OfflineFrameBatch, OfflineFramePlan
from .records import GF2Map, RecordFlipMap, apply_record_flips
from .selectors import DetectorSelector
from .stages import (
    BoundaryRequest,
    ReadoutRequest,
    StageDecoder,
    StageInputs,
    StageRequests,
    StageResult,
    make_stage_requests,
)
from .views import (
    DecoderInputs,
    DecoderView,
    DEMOptions,
    IndexMap,
    SelectionAudit,
    make_decoder_view,
    observable_local_views,
    source_fingerprint,
)

__all__ = [
    "ConditionalReadoutModel",
    "PauliFault",
    "make_conditional_readout_model",
    "CorrectionBatch",
    "FrameBoundary",
    "OfflineFrameBatch",
    "OfflineFramePlan",
    "BoundaryRequest",
    "ReadoutRequest",
    "StageDecoder",
    "StageInputs",
    "StageResult",
    "StageRequests",
    "make_stage_requests",
    "DecoderView",
    "DecoderInputs",
    "IndexMap",
    "DEMOptions",
    "DetectorSelector",
    "SelectionAudit",
    "GF2Map",
    "RecordFlipMap",
    "apply_record_flips",
    "make_decoder_view",
    "observable_local_views",
    "source_fingerprint",
    "DecoderViewError",
    "DEMConstructionError",
    "SourceMismatchError",
    "UndefinedObservableError",
    "UnsupportedProjectionError",
]
