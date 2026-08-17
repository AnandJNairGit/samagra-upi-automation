"""Integration test suite for Statement Import API endpoints."""

import os
import uuid
import pytest
import httpx
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.hashing import hash_password
from app.auth.jwt import create_access_token
from app.core.database import get_db
from app.main import app
from app.models.admin_user import AdminUser

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
CSV_PATH = os.path.join(FIXTURES_DIR, "sample_statement.csv")
XLSX_PATH = os.path.join(FIXTURES_DIR, "sample_statement.xlsx")


@pytest.fixture(autouse=True)
def setup_test_environment(db_session: AsyncSession):
    """Bind test database session to FastAPI dependency."""
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides.clear()


async def get_test_admin_and_token(db_session: AsyncSession):
    """Helper to create an active test admin user and Bearer access token."""
    admin = AdminUser(
        public_id=uuid.uuid4(),
        email=f"import.admin.{uuid.uuid4().hex[:6]}@samagra.org",
        password_hash=hash_password("Password123!"),
        full_name="Import Admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()
    token = create_access_token(admin.public_id)
    return admin, token


@pytest.mark.asyncio
async def test_preview_csv_endpoint(db_session: AsyncSession):
    """Test previewing a CSV file (0 DB writes)."""
    admin, token = await get_test_admin_and_token(db_session)
    transport = ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with open(CSV_PATH, "rb") as f:
            response = await client.post(
                "/v1/admin/statement-imports/preview",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("sample_statement.csv", f, "text/csv")},
                data={"header_row_index": "1"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "preview_token" in data
        assert data["file_type"] == "csv"
        assert data["total_detected_rows"] == 4
        assert len(data["headers"]) == 7
        assert data["headers"][2]["header"] == "Transaction Remarks"


@pytest.mark.asyncio
async def test_preview_xlsx_multi_sheet_endpoint(db_session: AsyncSession):
    """Test previewing an XLSX file with sheet selection (0 DB writes)."""
    admin, token = await get_test_admin_and_token(db_session)
    transport = ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with open(XLSX_PATH, "rb") as f:
            response = await client.post(
                "/v1/admin/statement-imports/preview",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("sample_statement.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"sheet_name": "Transactions", "header_row_index": "2"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "xlsx"
        assert data["available_sheets"] == ["Summary", "Transactions", "Account Details"]
        assert data["selected_sheet_name"] == "Transactions"
        assert data["header_row_index"] == 2
        assert data["total_detected_rows"] == 4


@pytest.mark.asyncio
async def test_confirm_import_csv_workflow(db_session: AsyncSession):
    """Test two-step preview -> confirm workflow for CSV file."""
    admin, token = await get_test_admin_and_token(db_session)
    transport = ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with open(CSV_PATH, "rb") as f:
            prev_res = await client.post(
                "/v1/admin/statement-imports/preview",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("sample_statement.csv", f, "text/csv")},
                data={"header_row_index": "1"},
            )

        assert prev_res.status_code == 200
        prev_data = prev_res.json()
        preview_token = prev_data["preview_token"]

        confirm_payload = {
            "preview_token": preview_token,
            "header_row_index": 1,
            "column_mapping": {
                "reference_id": {"column_index": 2, "header": "Transaction Remarks"},
                "amount": {"column_index": 3, "header": "Credit Amount"},
                "transaction_at": {"column_index": 0, "header": "Transaction Date"},
                "direction": {"column_index": 1, "header": "Transaction Type"},
                "utr": {"column_index": 4, "header": "UTR Number"},
                "counterparty_name": {"column_index": 5, "header": "Payer Name"},
                "description": {"column_index": 6, "header": "Description"},
            },
        }

        conf_res = await client.post(
            "/v1/admin/statement-imports/confirm",
            headers={"Authorization": f"Bearer {token}"},
            json=confirm_payload,
        )

        assert conf_res.status_code == 200, f"Error detail: {conf_res.json()}"
        summary = conf_res.json()
        assert summary["already_imported"] is False
        assert summary["status"] == "COMPLETED"
        assert summary["total_rows"] == 4
        assert summary["valid_rows"] == 3
        assert summary["new_transactions"] == 3
        assert summary["rows_without_reference"] == 1

        # Verify single-use token invalidation: second confirm with same preview token should be rejected (400)
        second_conf = await client.post(
            "/v1/admin/statement-imports/confirm",
            headers={"Authorization": f"Bearer {token}"},
            json=confirm_payload,
        )
        assert second_conf.status_code == 400


@pytest.mark.asyncio
async def test_exact_duplicate_import_idempotency(db_session: AsyncSession):
    """Test that importing the exact same file + mapping twice returns an idempotent existing import response."""
    admin, token = await get_test_admin_and_token(db_session)
    transport = ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with open(CSV_PATH, "rb") as f:
            p1 = await client.post(
                "/v1/admin/statement-imports/preview",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("sample_statement.csv", f, "text/csv")},
                data={"header_row_index": "1"},
            )
        token1 = p1.json()["preview_token"]

        confirm_payload = {
            "preview_token": token1,
            "header_row_index": 1,
            "column_mapping": {
                "reference_id": {"column_index": 2, "header": "Transaction Remarks"},
                "amount": {"column_index": 3, "header": "Credit Amount"},
            },
        }

        res1 = await client.post(
            "/v1/admin/statement-imports/confirm",
            headers={"Authorization": f"Bearer {token}"},
            json=confirm_payload,
        )
        assert res1.status_code == 200
        sum1 = res1.json()
        assert sum1["already_imported"] is False
        import_id = sum1["import_public_id"]

        # Preview and confirm identical file & mapping again
        with open(CSV_PATH, "rb") as f:
            p2 = await client.post(
                "/v1/admin/statement-imports/preview",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("sample_statement.csv", f, "text/csv")},
                data={"header_row_index": "1"},
            )
        token2 = p2.json()["preview_token"]
        confirm_payload["preview_token"] = token2

        res2 = await client.post(
            "/v1/admin/statement-imports/confirm",
            headers={"Authorization": f"Bearer {token}"},
            json=confirm_payload,
        )
        assert res2.status_code == 200
        sum2 = res2.json()
        assert sum2["already_imported"] is True
        assert sum2["import_public_id"] == import_id
        assert "already been imported" in sum2["message"]


@pytest.mark.asyncio
async def test_list_and_detail_import_endpoints(db_session: AsyncSession):
    """Test fetching statement import history and detail views."""
    admin, token = await get_test_admin_and_token(db_session)
    transport = ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # First import a statement
        with open(CSV_PATH, "rb") as f:
            p = await client.post(
                "/v1/admin/statement-imports/preview",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("sample_statement.csv", f, "text/csv")},
                data={"header_row_index": "1"},
            )
        token1 = p.json()["preview_token"]

        await client.post(
            "/v1/admin/statement-imports/confirm",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "preview_token": token1,
                "header_row_index": 1,
                "column_mapping": {
                    "reference_id": {"column_index": 2, "header": "Transaction Remarks"},
                    "amount": {"column_index": 3, "header": "Credit Amount"},
                },
            },
        )

        # Fetch list
        list_res = await client.get(
            "/v1/admin/statement-imports",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_res.status_code == 200
        l_data = list_res.json()
        assert l_data["total"] >= 1
        import_public_id = l_data["items"][0]["public_id"]

        # Fetch detail
        detail_res = await client.get(
            f"/v1/admin/statement-imports/{import_public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail_res.status_code == 200
        d_data = detail_res.json()
        assert d_data["public_id"] == import_public_id
        assert "column_mapping" in d_data

        # Fetch transactions
        txns_res = await client.get(
            f"/v1/admin/statement-imports/{import_public_id}/transactions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert txns_res.status_code == 200
        t_data = txns_res.json()
        assert t_data["total"] >= 1
        assert "raw_row_data" not in t_data["items"][0]  # Omitted for privacy


@pytest.mark.asyncio
async def test_delete_statement_import_endpoint(db_session: AsyncSession):
    """Test deleting an imported statement and its bank transactions."""
    admin, token = await get_test_admin_and_token(db_session)
    transport = ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Preview and confirm import
        with open(CSV_PATH, "rb") as f:
            p = await client.post(
                "/v1/admin/statement-imports/preview",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("sample_statement.csv", f, "text/csv")},
                data={"header_row_index": "1"},
            )
        prev_token = p.json()["preview_token"]

        conf_res = await client.post(
            "/v1/admin/statement-imports/confirm",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "preview_token": prev_token,
                "header_row_index": 1,
                "column_mapping": {
                    "reference_id": {"column_index": 2, "header": "Transaction Remarks"},
                    "amount": {"column_index": 3, "header": "Credit Amount"},
                },
            },
        )
        import_public_id = conf_res.json()["import_public_id"]

        # 2. Delete statement import
        del_res = await client.delete(
            f"/v1/admin/statement-imports/{import_public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_res.status_code == 200
        assert del_res.json()["deleted_public_id"] == import_public_id

        # 3. Verify GET detail returns 404
        get_res = await client.get(
            f"/v1/admin/statement-imports/{import_public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_res.status_code == 404
