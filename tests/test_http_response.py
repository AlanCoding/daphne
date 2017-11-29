# coding: utf8

from hypothesis import given, settings

import http_strategies
from http_base import DaphneTestCase


class TestHTTPResponse(DaphneTestCase):
    """
    Tests HTTP response handling.
    """

    def normalize_headers(self, headers):
        """
        Lowercases and sorts headers, and strips transfer-encoding ones.
        """
        return sorted([
            (name.lower(), value)
            for name, value in headers
            if name.lower() != "transfer-encoding"
        ])

    def test_minimal_response(self):
        """
        Smallest viable example. Mostly verifies that our response building works.
        """
        response = self.run_daphne_response([
            {
                "type": "http.response.start",
                "status": 200,
            },
            {
                "type": "http.response.content",
                "content": b"hello world",
            },
        ])
        self.assertEqual(response.status, 200)
        self.assertEqual(response.read(), b"hello world")

    def test_status_code_required(self):
        """
        Asserts that passing in the 'status' key is required.

        Previous versions of Daphne did not enforce this, so this test is here
        to make sure it stays required.
        """
        with self.assertRaises(ValueError):
            self.run_daphne_response([
                {
                    "type": "http.response.start",
                },
                {
                    "type": "http.response.content",
                    "content": b"hello world",
                },
            ])

    def test_custom_status_code(self):
        """
        Tries a non-default status code.
        """
        response = self.run_daphne_response([
            {
                "type": "http.response.start",
                "status": 201,
            },
            {
                "type": "http.response.content",
                "content": b"i made a thing!",
            },
        ])
        self.assertEqual(response.status, 201)
        self.assertEqual(response.read(), b"i made a thing!")

    def test_chunked_response(self):
        """
        Tries sending a response in multiple parts.
        """
        response = self.run_daphne_response([
            {
                "type": "http.response.start",
                "status": 201,
            },
            {
                "type": "http.response.content",
                "content": b"chunk 1 ",
                "more_content": True,
            },
            {
                "type": "http.response.content",
                "content": b"chunk 2",
            },
        ])
        self.assertEqual(response.status, 201)
        self.assertEqual(response.read(), b"chunk 1 chunk 2")

    def test_chunked_response_empty(self):
        """
        Tries sending a response in multiple parts and an empty end.
        """
        response = self.run_daphne_response([
            {
                "type": "http.response.start",
                "status": 201,
            },
            {
                "type": "http.response.content",
                "content": b"chunk 1 ",
                "more_content": True,
            },
            {
                "type": "http.response.content",
                "content": b"chunk 2",
                "more_content": True,
            },
            {
                "type": "http.response.content",
            },
        ])
        self.assertEqual(response.status, 201)
        self.assertEqual(response.read(), b"chunk 1 chunk 2")

    @given(body=http_strategies.http_body())
    @settings(max_examples=5, deadline=5000)
    def test_body(self, body):
        """
        Tries body variants.
        """
        response = self.run_daphne_response([
            {
                "type": "http.response.start",
                "status": 200,
            },
            {
                "type": "http.response.content",
                "content": body,
            },
        ])
        self.assertEqual(response.status, 200)
        self.assertEqual(response.read(), body)

    @given(headers=http_strategies.headers())
    @settings(max_examples=5, deadline=5000)
    def test_headers(self, headers):
        # The ASGI spec requires us to lowercase our header names
        response = self.run_daphne_response([
            {
                "type": "http.response.start",
                "status": 200,
                "headers": self.normalize_headers(headers),
            },
            {
                "type": "http.response.content",
            },
        ])
        # Check headers in a sensible way. Ignore transfer-encoding.
        self.assertEqual(
            self.normalize_headers(response.getheaders()),
            self.normalize_headers(headers),
        )