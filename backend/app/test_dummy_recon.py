import asyncio
import os
import time
import uuid
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.admin_user import AdminUser
from app.models.course import Course
from app.models.batch import Batch
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission
from app.schemas.statement_import import ImportConfirmRequest, StatementColumnMapping, ColumnFieldMapping
from app.services.statement_import_service import StatementImportService
from app.services.reconciliation_service import ReconciliationService

async def test_reconciliation():
    async with async_session_factory() as db:
        ts_suffix = str(int(time.time()))[-4:]
        
        # 1. Fetch admin user
        admin_res = await db.execute(select(AdminUser).limit(1))
        admin = admin_res.scalars().first()

        # 2. Create test course and batch
        course = Course(name=f"Recon Test Course {ts_suffix}", description="Testing", status="ACTIVE")
        db.add(course)
        await db.flush()

        batch = Batch(course_id=course.id, name=f"Batch {ts_suffix}", amount_inr=2500, status="ACTIVE")
        db.add(batch)
        await db.flush()

        # Generate unique reference codes for this run
        ref_matched = f"REF_MATCH_{ts_suffix}"
        ref_pending = f"REF_PENDING_{ts_suffix}"
        ref_utr_mis = f"REF_UTR_MIS_{ts_suffix}"
        ref_amt_mis = f"REF_AMT_MIS_{ts_suffix}"
        ref_dup_tx  = f"REF_DUP_TX_{ts_suffix}"

        # Seed PaymentSession 1: MATCHED target
        ps1 = PaymentSession(
            full_name="Alice Smith", phone="9876543210", email="alice@example.com",
            course_id=course.id, batch_id=batch.id, course_name_snapshot=course.name, batch_name_snapshot=batch.name,
            amount_inr=2500, reference_id=ref_matched, upi_id_snapshot="samagra@ibl", payee_name_snapshot="Samagra",
            upi_uri=f"upi://pay?tr={ref_matched}", status="SUBMITTED"
        )
        db.add(ps1)
        await db.flush()
        sub1 = PaymentSubmission(payment_session_id=ps1.id, utr=f"1111{ts_suffix}", status="SUBMITTED", is_current=True)
        db.add(sub1)

        # Seed PaymentSession 2: PENDING target (no submission)
        ps2 = PaymentSession(
            full_name="Bob Jones", phone="9876543211", email="bob@example.com",
            course_id=course.id, batch_id=batch.id, course_name_snapshot=course.name, batch_name_snapshot=batch.name,
            amount_inr=2500, reference_id=ref_pending, upi_id_snapshot="samagra@ibl", payee_name_snapshot="Samagra",
            upi_uri=f"upi://pay?tr={ref_pending}", status="PENDING"
        )
        db.add(ps2)

        # Seed PaymentSession 3: UTR MISMATCH target
        ps3 = PaymentSession(
            full_name="Charlie Brown", phone="9876543212", email="charlie@example.com",
            course_id=course.id, batch_id=batch.id, course_name_snapshot=course.name, batch_name_snapshot=batch.name,
            amount_inr=2500, reference_id=ref_utr_mis, upi_id_snapshot="samagra@ibl", payee_name_snapshot="Samagra",
            upi_uri=f"upi://pay?tr={ref_utr_mis}", status="SUBMITTED"
        )
        db.add(ps3)
        await db.flush()
        sub3 = PaymentSubmission(payment_session_id=ps3.id, utr=f"3333{ts_suffix}", status="SUBMITTED", is_current=True)
        db.add(sub3)

        # Seed PaymentSession 4: AMOUNT MISMATCH target
        ps4 = PaymentSession(
            full_name="David Miller", phone="9876543213", email="david@example.com",
            course_id=course.id, batch_id=batch.id, course_name_snapshot=course.name, batch_name_snapshot=batch.name,
            amount_inr=2500, reference_id=ref_amt_mis, upi_id_snapshot="samagra@ibl", payee_name_snapshot="Samagra",
            upi_uri=f"upi://pay?tr={ref_amt_mis}", status="SUBMITTED"
        )
        db.add(ps4)
        await db.flush()
        sub4 = PaymentSubmission(payment_session_id=ps4.id, utr=f"4444{ts_suffix}", status="SUBMITTED", is_current=True)
        db.add(sub4)

        # Seed PaymentSession 5: DUPLICATE TRANSACTION target
        ps5 = PaymentSession(
            full_name="Eva Davis", phone="9876543214", email="eva@example.com",
            course_id=course.id, batch_id=batch.id, course_name_snapshot=course.name, batch_name_snapshot=batch.name,
            amount_inr=2500, reference_id=ref_dup_tx, upi_id_snapshot="samagra@ibl", payee_name_snapshot="Samagra",
            upi_uri=f"upi://pay?tr={ref_dup_tx}", status="SUBMITTED"
        )
        db.add(ps5)
        await db.flush()
        sub5 = PaymentSubmission(payment_session_id=ps5.id, utr=f"5555{ts_suffix}", status="SUBMITTED", is_current=True)
        db.add(sub5)

        await db.commit()

        # 3. Create fresh dummy CSV content
        csv_content = f"""Transaction Date,Transaction Type,Transaction Remarks,Credit Amount,UTR Number,Payer Name,Description
18/08/2026 01:22:00,CREDIT,{ref_matched},2500,1111{ts_suffix},Alice Smith,Exact Match Transaction
18/08/2026 01:25:00,CREDIT,{ref_pending},2500,9999{ts_suffix},Bob Jones,Pending Session Matched
18/08/2026 01:22:10,CREDIT,{ref_utr_mis},2500,999988887777,Charlie Brown,Differing Bank UTR
18/08/2026 01:21:00,CREDIT,{ref_amt_mis},2000,4444{ts_suffix},David Miller,Underpaid Bank Amount
18/08/2026 01:20:00,CREDIT,{ref_dup_tx},2500,5555{ts_suffix},Eva Davis,Duplicate Bank Credit 1
18/08/2026 01:20:05,CREDIT,{ref_dup_tx},2500,5555{ts_suffix},Eva Davis,Duplicate Bank Credit 2
18/08/2026 01:30:00,CREDIT,REF_UNKNOWN_99,5000,123456789,Stranger,Unknown Reference
18/08/2026 01:31:00,CREDIT,,1000,987654321,Anonymous,Missing Reference Code
18/08/2026 01:32:00,DEBIT,BANK_FEES,50,000000000,HDFC Bank,Debit Fee Charge
"""
        file_bytes = csv_content.encode("utf-8")
        import_filename = f"live_recon_demo_{ts_suffix}.csv"

        import_service = StatementImportService()
        preview = import_service.preview_import(
            file_bytes=file_bytes,
            filename=import_filename,
            admin_user_id=admin.id,
            header_row_index=1
        )

        mapping = StatementColumnMapping(
            transaction_at=ColumnFieldMapping(column_index=0, header="Transaction Date"),
            direction=ColumnFieldMapping(column_index=1, header="Transaction Type"),
            reference_id=ColumnFieldMapping(column_index=2, header="Transaction Remarks"),
            amount=ColumnFieldMapping(column_index=3, header="Credit Amount"),
            utr=ColumnFieldMapping(column_index=4, header="UTR Number"),
            counterparty_name=ColumnFieldMapping(column_index=5, header="Payer Name"),
            description=ColumnFieldMapping(column_index=6, header="Description")
        )

        payload = ImportConfirmRequest(
            preview_token=preview.preview_token,
            header_row_index=1,
            column_mapping=mapping,
        )

        statement_import_resp = await import_service.confirm_import(
            db=db,
            admin_user_id=admin.id,
            payload=payload,
        )
        print(f"\nStatement Import Created: {statement_import_resp.import_public_id} | Status: {statement_import_resp.status} | Total Rows: {statement_import_resp.total_rows}")

        recon_service = ReconciliationService()
        run_resp = await recon_service.run_reconciliation(
            db=db,
            statement_import_public_id=statement_import_resp.import_public_id,
            admin_user=admin
        )
        print("\n" + "="*80)
        print(f"RECONCILIATION RUN COMPLETED (Run ID: {run_resp.public_id})")
        print("="*80)
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
        print("-" * 120)
        print(f"{'REF CODE':<22} | {'STATUS':<21} | {'BANK AMT':<9} | {'EXPEC AMT':<9} | EXPLANATION")
        print("-" * 120)
        for r in results.items:
            ref = r.bank_reference_id or "(No Ref)"
            status = r.status
            bank_amt = f"₹{r.bank_amount_inr}" if r.bank_amount_inr is not None else "-"
            exp_amt = f"₹{r.expected_amount_inr}" if r.expected_amount_inr is not None else "-"
            print(f"{ref:<22} | {status:<21} | {bank_amt:<9} | {exp_amt:<9} | {r.explanation}")

if __name__ == "__main__":
    asyncio.run(test_reconciliation())
