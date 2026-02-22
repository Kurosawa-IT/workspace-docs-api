from __future__ import annotations

from typing import Final

ROLES: Final[set[str]] = {"owner", "admin", "member", "viewer"}

A_MEMBER_LIST: Final[str] = "member.list"
A_MEMBER_ADD: Final[str] = "member.add"
A_MEMBER_REMOVE: Final[str] = "member.remove"
A_MEMBER_CHANGE_ROLE: Final[str] = "member.change_role"

A_DOC_CREATE: Final[str] = "doc.create"
A_DOC_READ: Final[str] = "doc.read"
A_DOC_UPDATE: Final[str] = "doc.update"
A_DOC_DELETE: Final[str] = "doc.delete"
A_DOC_PUBLISH: Final[str] = "doc.publish"
A_DOC_ARCHIVE: Final[str] = "doc.archive"

A_AUDIT_READ: Final[str] = "audit.read"

A_EXPORT_CREATE: Final[str] = "export.create"
A_JOB_READ: Final[str] = "job.read"
A_EXPORT_DOWNLOAD: Final[str] = "export.download"

PERMISSIONS: Final[dict[str, set[str]]] = {
    "owner": {
        A_MEMBER_LIST,
        A_MEMBER_ADD,
        A_MEMBER_REMOVE,
        A_MEMBER_CHANGE_ROLE,
        A_DOC_CREATE,
        A_DOC_READ,
        A_DOC_UPDATE,
        A_DOC_DELETE,
        A_DOC_PUBLISH,
        A_DOC_ARCHIVE,
        A_AUDIT_READ,
        A_EXPORT_CREATE,
        A_JOB_READ,
        A_EXPORT_DOWNLOAD,
    },
    "admin": {
        A_MEMBER_LIST,
        A_MEMBER_ADD,
        A_MEMBER_REMOVE,
        A_DOC_CREATE,
        A_DOC_READ,
        A_DOC_UPDATE,
        A_DOC_DELETE,
        A_DOC_PUBLISH,
        A_DOC_ARCHIVE,
        A_AUDIT_READ,
        A_EXPORT_CREATE,
        A_JOB_READ,
        A_EXPORT_DOWNLOAD,
    },
    "member": {
        A_DOC_CREATE,
        A_DOC_READ,
        A_DOC_UPDATE,
        A_DOC_DELETE,
        A_DOC_PUBLISH,
        A_DOC_ARCHIVE,
        A_AUDIT_READ,
        A_EXPORT_CREATE,
        A_JOB_READ,
        A_EXPORT_DOWNLOAD,
    },
    "viewer": {
        A_DOC_READ,
    },
}


def can(role: str, action: str) -> bool:
    if role not in ROLES:
        return False
    return action in PERMISSIONS[role]
