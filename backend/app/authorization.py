from enum import StrEnum

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from .models import User, AuditEvent
from .security import current_user
from .trust_ledger import anchor_audit_event


class Permission(StrEnum):
    CASE_READ = "case:read"
    CASE_CREATE = "case:create"
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_VERSION_CREATE = "document:version:create"
    DOCUMENT_VERIFY = "document:verify"
    DOCUMENT_DOWNLOAD = "document:download"
    AUDIT_READ = "audit:read"
    TRUST_READ = "trust:read"
    SHARE_CREATE = "share:create"
    SHARE_READ = "share:read"
    SHARE_REVOKE = "share:revoke"
    SIGN = "document:sign"
    SIGNATURE_READ = "signature:read"
    GOVERNANCE_READ = "governance:read"
    GOVERNANCE_MANAGE = "governance:manage"
    INCIDENT_READ = "incident:read"
    INCIDENT_RESOLVE = "incident:resolve"
    CASE_MEMBER_MANAGE = "case:member:manage"


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "INVESTIGATING_OFFICER": frozenset({
        Permission.CASE_READ, Permission.CASE_CREATE,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_UPLOAD,
        Permission.DOCUMENT_VERSION_CREATE,
        Permission.DOCUMENT_VERIFY,
        Permission.DOCUMENT_DOWNLOAD,
        Permission.TRUST_READ, Permission.SHARE_CREATE, Permission.SHARE_READ, Permission.SHARE_REVOKE, Permission.SIGN, Permission.SIGNATURE_READ, Permission.GOVERNANCE_READ, Permission.GOVERNANCE_MANAGE, Permission.INCIDENT_READ, Permission.INCIDENT_RESOLVE, Permission.CASE_MEMBER_MANAGE,
    }),
    "FORENSIC_OFFICER": frozenset({
        Permission.CASE_READ, Permission.CASE_CREATE,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_UPLOAD,
        Permission.DOCUMENT_VERSION_CREATE,
        Permission.DOCUMENT_VERIFY,
        Permission.DOCUMENT_DOWNLOAD,
        Permission.TRUST_READ, Permission.SHARE_CREATE, Permission.SHARE_READ, Permission.SHARE_REVOKE, Permission.SIGN, Permission.SIGNATURE_READ, Permission.GOVERNANCE_READ, Permission.GOVERNANCE_MANAGE, Permission.INCIDENT_READ,
    }),
    "AUDITOR": frozenset({
        Permission.CASE_READ,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_VERIFY,
        Permission.AUDIT_READ, Permission.INCIDENT_READ,
        Permission.TRUST_READ, Permission.SHARE_READ, Permission.SIGNATURE_READ, Permission.GOVERNANCE_READ,
    }),
}


def has_permission(user: User, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.role, frozenset())


def _record_denial(db: Session, user: User, permission: Permission):
    event = AuditEvent(
        actor_id=user.id,
        action="AUTHORIZATION_DENIED",
        target_type="PERMISSION",
        target_id=permission.value,
        result="DENIED",
        details=(
            f"role={user.role}; required_permission={permission.value}; "
            "request blocked before protected handler execution"
        ),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    anchor_audit_event(db, event)


def require_permission(permission: Permission):
    """Server-side authorization boundary with an auditable denial event."""
    def dependency(
        db: Session = Depends(get_db),
        user: User = Depends(current_user),
    ) -> User:
        if not has_permission(user, permission):
            _record_denial(db, user, permission)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSION",
                    "message": "Your role is not authorized for this action.",
                    "required_permission": permission,
                    "role": user.role,
                },
            )
        return user

    return dependency
