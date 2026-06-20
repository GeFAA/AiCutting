from threading import Event

from aicutting.core.progress import (
    CancellationToken,
    PipelineCancelledError,
    PipelinePhase,
    ProgressEvent,
    emit_progress,
)


def test_progress_event_defaults_to_phase_label() -> None:
    event = ProgressEvent(phase=PipelinePhase.CHECKING_INPUTS)

    assert event.message == "Checking inputs"
    assert event.step is None
    assert event.total is None


def test_emit_progress_calls_callback_with_event() -> None:
    events: list[ProgressEvent] = []

    emit_progress(
        events.append,
        PipelinePhase.RENDERING_FINAL_VIDEO,
        "Rendering final video",
        step=6,
        total=7,
    )

    assert events == [
        ProgressEvent(
            phase=PipelinePhase.RENDERING_FINAL_VIDEO,
            message="Rendering final video",
            step=6,
            total=7,
        )
    ]


def test_cancelled_token_raises_pipeline_cancelled_error() -> None:
    token = CancellationToken()
    token.cancel()

    try:
        token.raise_if_cancelled()
    except PipelineCancelledError as exc:
        assert str(exc) == "Cut was cancelled by the user."
    else:
        raise AssertionError("Expected PipelineCancelledError")


def test_cancellation_token_uses_thread_safe_event() -> None:
    token = CancellationToken()

    assert isinstance(token._cancelled, Event)
    assert token.cancelled is False

    token.cancel()

    assert token.cancelled is True
