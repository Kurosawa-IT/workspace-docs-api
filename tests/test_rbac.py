from app.core import rbac


def test_owner_can_do_everything_important():
    assert rbac.can("owner", rbac.A_MEMBER_CHANGE_ROLE) is True
    assert rbac.can("owner", rbac.A_DOC_DELETE) is True
    assert rbac.can("owner", rbac.A_EXPORT_CREATE) is True


def test_admin_cannot_change_role_but_can_manage_members():
    assert rbac.can("admin", rbac.A_MEMBER_LIST) is True
    assert rbac.can("admin", rbac.A_MEMBER_ADD) is True
    assert rbac.can("admin", rbac.A_MEMBER_REMOVE) is True
    assert rbac.can("admin", rbac.A_MEMBER_CHANGE_ROLE) is False


def test_member_can_edit_docs_but_cannot_manage_members():
    assert rbac.can("member", rbac.A_DOC_CREATE) is True
    assert rbac.can("member", rbac.A_DOC_UPDATE) is True
    assert rbac.can("member", rbac.A_MEMBER_ADD) is False
    assert rbac.can("member", rbac.A_MEMBER_LIST) is False


def test_viewer_is_read_only():
    assert rbac.can("viewer", rbac.A_DOC_READ) is True
    assert rbac.can("viewer", rbac.A_DOC_UPDATE) is False
    assert rbac.can("viewer", rbac.A_EXPORT_CREATE) is False


def test_unknown_role_is_denied():
    assert rbac.can("hacker", rbac.A_DOC_READ) is False
