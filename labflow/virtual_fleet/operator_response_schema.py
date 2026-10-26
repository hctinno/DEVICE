"""Exact operator schema profiles; no authority, I/O, provider or conversion."""
import hashlib

SCHEMA_BYTES = 3052
LEGACY_SCHEMA_SHA256 = 'aa321fa55e0d21af0c3992c5b6a91a78fd108d4a006e463a9bd3761ff21c0edb'
CURRENT_SCHEMA_SHA256 = 'e045c19a6fa5041780091f7a459e2b9f5a909d634cd6a7ccb6d82f16fafccf05'
_CURRENT = b'{\n  "additionalProperties": false,\n  "properties": {\n    "kind": {\n      "const": "virtual_operator_response"\n    },\n    "producer": {\n      "additionalProperties": false,\n      "properties": {\n        "kind": {\n          "const": "model"\n        },\n        "name": {\n          "const": "dgm-virtual-operator-v1"\n        }\n      },\n      "required": [\n        "kind",\n        "name"\n      ],\n      "type": "object"\n    },\n    "proposal": {\n      "anyOf": [\n        {\n          "additionalProperties": false,\n          "properties": {\n            "action": {\n              "const": "start"\n            },\n            "device_id": {\n              "const": "dut"\n            },\n            "kind": {\n              "const": "execute"\n            },\n            "parameters": {\n              "additionalProperties": false,\n              "properties": {},\n              "required": [],\n              "type": "object"\n            }\n          },\n          "required": [\n            "kind",\n            "device_id",\n            "action",\n            "parameters"\n          ],\n          "type": "object"\n        },\n        {\n          "additionalProperties": false,\n          "properties": {\n            "action": {\n              "enum": [\n                "acquire",\n                "read"\n              ]\n            },\n            "device_id": {\n              "const": "sensor"\n            },\n            "kind": {\n              "const": "execute"\n            },\n            "parameters": {\n              "additionalProperties": false,\n              "properties": {},\n              "required": [],\n              "type": "object"\n            }\n          },\n          "required": [\n            "kind",\n            "device_id",\n            "action",\n            "parameters"\n          ],\n          "type": "object"\n        },\n        {\n          "additionalProperties": false,\n          "properties": {\n            "kind": {\n              "const": "advance"\n            },\n            "ticks": {\n              "const": 1\n            }\n          },\n          "required": [\n            "kind",\n            "ticks"\n          ],\n          "type": "object"\n        },\n        {\n          "additionalProperties": false,\n          "properties": {\n            "claim": {\n              "enum": [\n                "completed",\n                "blocked",\n                "unsupported",\n                "failed"\n              ]\n            },\n            "kind": {\n              "const": "stop"\n            },\n            "reason": {\n              "maxLength": 4096,\n              "minLength": 1,\n              "type": "string"\n            }\n          },\n          "required": [\n            "kind",\n            "claim",\n            "reason"\n          ],\n          "type": "object"\n        }\n      ]\n    },\n    "request_sha256": {\n      "pattern": "^[0-9a-f]{64}$",\n      "type": "string"\n    },\n    "schema_version": {\n      "const": 1\n    }\n  },\n  "required": [\n    "schema_version",\n    "kind",\n    "request_sha256",\n    "producer",\n    "proposal"\n  ],\n  "type": "object"\n}\n'


def current_response_schema_bytes() -> bytes:
    """Return the fixed provider-compatible profile, without converting input."""
    return _CURRENT


def is_current_response_schema_bytes(value) -> bool:
    return (type(value) is bytes and len(value) == SCHEMA_BYTES
            and hashlib.sha256(value).hexdigest() == CURRENT_SCHEMA_SHA256)


def is_known_response_schema_bytes(value) -> bool:
    """Read-only recognition includes the historical provider-rejected profile."""
    return (type(value) is bytes and len(value) == SCHEMA_BYTES
            and hashlib.sha256(value).hexdigest() in {CURRENT_SCHEMA_SHA256, LEGACY_SCHEMA_SHA256})
