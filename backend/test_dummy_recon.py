import asyncio
import os
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.admin_user import AdminUser
from app.services.statement_import_service import StatementImportService
from app.services.reconciliation_service import ReconciliationService

async def test_reconciliation():
    async with async_session_factory() as db:
        admin_res = await db.execute(select(AdminUser).limit(1))
        admin = admin_res.scalars().first()
        
        file_path = "demo_reconciliation_statement.csv"
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        import_service = StatementImportService()
        preview = import_service.preview_import(
            file_bytes=file_bytes,
            filename="demo_reconciliation_statement.csv",
            admin_user_id=admin.id,
            header_row_index=1
        )

        mapping = {
            "transaction_at": {"column_index": 0, "header": "Transaction Date"},
            "direction": {"column_index": 1, "header": "Transaction Type"},
            "reference_id": {"column_index": 2, "header": "Transaction Remarks"},
            "amount": {"column_index": 3, "header": "Credit Amount"},
            "utr": {"column_index": 4, "header": "UTR Number"},
            "counterparty_name": {"column_index": 5, "header": "Payer Name"},
            "description": {"column_index": 6, "header": "Description"}
        }

        statement_import_resp = await import_service.confirm_import(
            db=db,
            preview_token=preview.preview_token,
            header_row_index=1,
            column_mapping=mapping,
            admin_user=admin
        )
        print(f"Statement Import Created: {statement_import_resp.public_id} | Status: {statement_import_resp.status} | Total Rows: {statement_import_resp.total_rows}")

        recon_service = ReconciliationService()
        run_resp = await recon_service.run_reconciliation(
            db=db,
            statement_import_public_id=statement_import_resp.public_id,
            admin_user=admin
        )
        print("\n" + "="*70)
        print(f"RECONCILIATION RUN COMPLETED: {run_resp.public_id}")
        print("="*70)
        print(f"Total Transactions : {run_resp.total_transactions}")
        print(f"MATCHED            : {run_resp.matched_count}")
        print(f"AMOUNT_MISMATCH    : {run_resp.amount_mismatch_count}")
        print(f"UTR_MISMATCH       : {run_resp.utr_mismatch_count}")
        print(f"UNKNOWN_REFERENCE  : {run_resp.unknown_reference_count}")
        print(f"NO_REFERENCE       : {run_resp.no_reference_count}")
        print(f"DUPLICATE_TXN      : {run_resp.duplicate_transaction_count}")
        print(f"UNMATCHED (Debit)  : {run_resp.unmatched_count}")

        results = await recon_service.list_results_for_run_paginated(db=db, run_public_id=run_resp.public_id, page_size=50)
        print("\nDETAILED CLASSIFICATION RESULTS:")
        print("-" * 105)
        print(f"{'REF CODE':<24} | {'STATUS':<21} | {'BANK AMT':<8} | {'EXPEC AMT':<9} | EXPLANATION")
        print("-" * 105)
        for r in results.items:
            ref = r.bank_reference_id or "(No Ref)"
            status = r.status
            bank_amt = f"INR {r.bank_amount_inr}" if r.bank_amount_inr is not None else "-"
            exp_amt = f"INR {r.expected_amount_inr}" if r.expected_amount_inr is not None else "-"
            print(f"{ref:<24} | {status:<21} | {bank_amt:<8} | {exp_amt:<9} | {r.explanation}")

if __name__ == "__main__":
    asyncio.run(test_reconciliation())
