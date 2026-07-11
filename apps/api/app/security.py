"""Operator authentication for control-plane mutations (AOS-AUTH-BOUNDARY-001).

The node registry, authority envelope, and connector registry are enforcement
boundaries only if the routes that GRANT or CHANGE authority are themselves
authenticated. Before this package, node enrollment and authority approve/reject
had no auth dependency at all — an anonymous client could enroll a node with
``write_access`` or approve any pending action.

``require_operator`` is the single reusable operator gate. Its policy:

- ``operator_token`` set  → require a matching ``X-Operator-Token`` (constant-time).
- ``operator_token`` empty + ``auth_dev_mode`` True → allow, but LOG a warning so an
  open operator plane is never silent (the local/tailnet single-operator default).
- ``operator_token`` empty + ``auth_dev_mode`` False → **fail closed** (503): a
  deployed profile with no operator secret refuses operator actions rather than
  leaving them open. The shipped docker-compose sets ``AUTH_DEV_MODE=false``.

The returned value is the operator principal (``X-Operator-Id`` if supplied, else
``"operator"``), recorded as the actor on every authorization/policy change.
"""

from __future__ import annotations

import logging
import secrets

from fastapi import Header, HTTPException

from aos_core.config import get_settings

logger = logging.getLogger("archetypeos.security")

settings = get_settings()

_dev_mode_warned = False


def require_operator(
    x_operator_token: str | None = Header(default=None),
    x_operator_id: str | None = Header(default=None),
) -> str:
    """Authenticate an operator for a control-plane mutation; return the principal.

    Raises 401 on a missing/wrong token when one is configured, or 503 when no
    token is configured AND dev-mode is off (fail-closed deployed profile).
    """
    token = settings.operator_token
    if token:
        if not x_operator_token or not secrets.compare_digest(x_operator_token, token):
            raise HTTPException(status_code=401, detail="Invalid or missing operator token")
        return (x_operator_id or "operator").strip() or "operator"

    if settings.auth_dev_mode:
        global _dev_mode_warned
        if not _dev_mode_warned:
            logger.warning(
                "operator routes are OPEN: no operator_token set and auth_dev_mode=True "
                "(local/tailnet dev). Set OPERATOR_TOKEN + AUTH_DEV_MODE=false to lock down."
            )
            _dev_mode_warned = True
        return (x_operator_id or "operator").strip() or "operator"

    # No token configured and dev-mode explicitly disabled → fail closed.
    raise HTTPException(
        status_code=503,
        detail="operator authentication is not configured (set OPERATOR_TOKEN or enable AUTH_DEV_MODE)",
    )


__all__ = ["require_operator"]
