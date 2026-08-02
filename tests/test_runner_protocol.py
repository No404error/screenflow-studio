"""Runner IPC line protocol."""

from screenflow.runner_protocol import (
    CMDS,
    decode_line,
    encode_message,
    event_exited,
    event_log,
    event_ready,
    event_status,
    is_command,
    is_event,
    cmd_ping,
    cmd_set_runtime,
    cmd_start,
    cmd_stop,
)


def test_encode_decode_roundtrip():
    msg = cmd_start()
    raw = encode_message(msg)
    assert raw.endswith(b"\n")
    assert decode_line(raw) == msg
    assert decode_line(raw.decode("utf-8")) == msg


def test_log_and_status_events():
    log = event_log("hello")
    assert is_event(log)
    assert decode_line(encode_message(log))["text"] == "hello"
    st = event_status({"mode": "running", "page_id": "p", "state": "a"})
    back = decode_line(encode_message(st))
    assert back["type"] == "status"
    assert back["mode"] == "running"


def test_commands_known():
    for fn in (cmd_start, cmd_stop, cmd_ping):
        m = fn()
        assert is_command(m)
        assert m["cmd"] in CMDS
    rt = cmd_set_runtime({"poll_interval": 0.4, "verbose_log": True})
    assert is_command(rt)
    assert rt["runtime"]["poll_interval"] == 0.4


def test_invalid_lines():
    assert decode_line("") is None
    assert decode_line("   ") is None
    assert decode_line("not-json") is None
    assert decode_line("[1,2]") is None
    assert decode_line(b"\xff\xfe") is None


def test_ready_exited():
    assert decode_line(encode_message(event_ready()))["type"] == "ready"
    ready = decode_line(encode_message(event_ready(12345)))
    assert ready["type"] == "ready"
    assert ready["pid"] == 12345
    assert decode_line(encode_message(event_exited(1)))["code"] == 1
