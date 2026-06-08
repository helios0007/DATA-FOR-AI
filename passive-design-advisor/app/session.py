"""
In-memory session store.
Maps session_id → { ifc_path, building, report }
Suitable for local single-user use. Replace with Redis for multi-user deployment.
"""

session_store: dict = {}
