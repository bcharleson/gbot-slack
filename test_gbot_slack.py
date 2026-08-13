#!/usr/bin/env python3
"""Unit tests for gbot-slack human-event filtering (stdlib unittest)."""

from __future__ import annotations

import importlib.util
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


def _load_cli():
    path = Path(__file__).resolve().parent / "gbot-slack"
    loader = SourceFileLoader("gbot_slack", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


cli = _load_cli()


def _events_api(event: dict, **envelope_extra) -> dict:
    return {
        "type": "events_api",
        "envelope_id": "E1",
        "payload": {"event": event},
        **envelope_extra,
    }


class HumanEventFilterTests(unittest.TestCase):
    SELF = "U_BOT"
    BOT_ID = "B_BOT"

    def summarize(self, envelope, **kwargs):
        return cli._human_event_summary(
            envelope,
            self_user_id=kwargs.pop("self_user_id", self.SELF),
            self_bot_id=kwargs.pop("self_bot_id", self.BOT_ID),
            **kwargs,
        )

    def test_human_message_passes(self):
        summary = self.summarize(
            _events_api(
                {
                    "type": "message",
                    "user": "U_HUMAN",
                    "channel": "D1",
                    "ts": "1.0",
                    "text": "hello",
                }
            )
        )
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary["user"], "U_HUMAN")
        self.assertEqual(summary["type"], "message")
        self.assertEqual(summary["event_type"], "message")

    def test_self_echo_ignored(self):
        summary = self.summarize(
            _events_api(
                {
                    "type": "message",
                    "user": self.SELF,
                    "channel": "D1",
                    "ts": "1.0",
                    "text": "bot reply",
                }
            )
        )
        self.assertIsNone(summary)

    def test_bot_id_ignored(self):
        summary = self.summarize(
            _events_api(
                {
                    "type": "message",
                    "bot_id": "B_OTHER",
                    "channel": "D1",
                    "ts": "1.0",
                    "text": "other bot",
                }
            )
        )
        self.assertIsNone(summary)

    def test_message_subtype_ignored(self):
        summary = self.summarize(
            _events_api(
                {
                    "type": "message",
                    "subtype": "message_changed",
                    "user": "U_HUMAN",
                    "channel": "D1",
                    "ts": "1.0",
                    "text": "edited",
                }
            )
        )
        self.assertIsNone(summary)

    def test_thread_reply_in_dm_counts(self):
        summary = self.summarize(
            _events_api(
                {
                    "type": "message",
                    "user": "U_HUMAN",
                    "channel": "D1",
                    "ts": "2.0",
                    "thread_ts": "1.0",
                    "text": "thread reply",
                }
            )
        )
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary["thread_ts"], "1.0")
        self.assertEqual(summary["text"], "thread reply")

    def test_allow_from_filters(self):
        envelope = _events_api(
            {
                "type": "message",
                "user": "U_OTHER",
                "channel": "D1",
                "ts": "1.0",
                "text": "nope",
            }
        )
        self.assertIsNone(self.summarize(envelope, allow_from=["U_ALLOWED"]))
        allowed = _events_api(
            {
                "type": "message",
                "user": "U_ALLOWED",
                "channel": "D1",
                "ts": "1.0",
                "text": "yes",
            }
        )
        summary = self.summarize(allowed, allow_from=["U_ALLOWED"])
        self.assertIsNotNone(summary)

    def test_app_mention_passes(self):
        summary = self.summarize(
            _events_api(
                {
                    "type": "app_mention",
                    "user": "U_HUMAN",
                    "channel": "C1",
                    "ts": "1.0",
                    "text": "<@U_BOT> hi",
                }
            )
        )
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary["type"], "app_mention")

    def test_assistant_thread_started_with_user(self):
        summary = self.summarize(
            _events_api(
                {
                    "type": "assistant_thread_started",
                    "assistant_thread": {
                        "user_id": "U_HUMAN",
                        "channel_id": "D1",
                        "thread_ts": "9.0",
                    },
                }
            )
        )
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary["user"], "U_HUMAN")
        self.assertEqual(summary["channel"], "D1")
        self.assertEqual(summary["thread_ts"], "9.0")

    def test_assistant_thread_started_without_user_ignored(self):
        summary = self.summarize(
            _events_api({"type": "assistant_thread_started", "assistant_thread": {}})
        )
        self.assertIsNone(summary)

    def test_unknown_type_calls_hook_and_ignores(self):
        seen = []
        summary = self.summarize(
            _events_api({"type": "totally_new_event", "user": "U_HUMAN"}),
            on_unknown=seen.append,
        )
        self.assertIsNone(summary)
        self.assertEqual(seen, ["totally_new_event"])

    def test_retry_envelope_ignored(self):
        summary = self.summarize(
            _events_api(
                {
                    "type": "message",
                    "user": "U_HUMAN",
                    "channel": "D1",
                    "ts": "1.0",
                    "text": "hi",
                },
                retry_attempt=1,
                retry_reason="http_error",
            )
        )
        self.assertIsNone(summary)


if __name__ == "__main__":
    unittest.main()
