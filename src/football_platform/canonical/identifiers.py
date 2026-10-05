"""Internal identifiers (decision D006).

Internal ids are UUIDv5 values derived from (provider, entity type, provider id).
They are deterministic, so re-running ingestion yields the same ids, and they do
not expose provider ids. The link back to the provider is kept in ExternalId.
"""

from __future__ import annotations

import uuid

from football_platform.canonical.enums import EntityType

# Fixed project namespace. Changing it would change every internal id.
PLATFORM_NAMESPACE = uuid.UUID("6f1c2b0e-4d3a-5b8e-9c71-2a4f8e0d5b13")


def internal_id(provider: str, entity_type: EntityType, provider_id: str | int) -> str:
    if not provider:
        raise ValueError("provider must not be empty")
    return str(uuid.uuid5(PLATFORM_NAMESPACE, f"{provider}|{entity_type.value}|{provider_id}"))
