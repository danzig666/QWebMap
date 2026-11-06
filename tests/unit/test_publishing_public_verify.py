"""public_verify: odd server answers are failed checks, not exceptions (the
release is already live when the pointer is checked; an exception there
reported "Publishing failed" and the profile was not saved)."""

import gzip
import json

from publishing import public_verify


class _Http:
    def __init__(self, status, head, body):
        self.answer = (status, head, body, False)

    def request(self, url, **_kwargs):  # pylint: disable=unused-argument
        return self.answer


def test_odd_pointer_answers_are_failed_checks():
    good = json.dumps({"releaseId": "r1"}).encode()
    assert public_verify.verify_pointer("https://x.org/m", "r1", _Http(200, {}, good)).ok
    for head, body in (({"content-encoding": "gzip"}, b"not gzip at all"),
                       ({}, b"[1, 2]"), ({}, b"<html>"),
                       ({"content-encoding": "gzip"}, gzip.compress(b"\"text\""))):
        check = public_verify.verify_pointer("https://x.org/m", "r1", _Http(200, head, body))
        assert not check.ok, (head, body)


def test_content_length_that_is_not_a_number():
    assert public_verify._length({"content-length": "12, 12"}) == -1  # pylint: disable=protected-access
    assert public_verify._length({"content-length": "12"}) == 12  # pylint: disable=protected-access
