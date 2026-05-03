from __future__ import annotations
from typing import Annotated
from agents import function_tool, RunContextWrapper
from agent.context import AppContext
from database import get_connection


@function_tool
async def submit_refund_request(
    wrapper: RunContextWrapper[AppContext],
    order_id: Annotated[str, "The order ID the user wants to refund."],
    reason: Annotated[str, "The reason the user is requesting a refund."],
) -> str:
    """
    Submit a refund request for a specific order on behalf of the current user.

    Use this tool when the user explicitly asks to initiate a refund or return
    and has provided their order ID. Do NOT submit without a clear order ID.

    Returns a confirmation with the assigned request ID and next steps.
    """
    user_id = wrapper.context.user_id

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO refund_requests (user_id, order_id, reason)
            VALUES (%s, %s, %s)
            """,
            (user_id, order_id, reason),
        )
        request_id = cursor.lastrowid
        cursor.close()

    return (
        f"Refund request submitted successfully.\n"
        f"  Request ID : {request_id}\n"
        f"  Order ID   : {order_id}\n"
        f"  Reason     : {reason}\n"
        f"  Status     : pending\n\n"
        f"You will receive an email confirmation shortly. "
        f"Refunds are processed within 5–7 business days after the returned item is received. "
        f"Premium members receive instant approval with no restocking fee."
    )


@function_tool
async def check_refund_status(
    wrapper: RunContextWrapper[AppContext],
    order_id: Annotated[str, "The order ID to check refund status for."],
) -> str:
    """
    Check the status of an existing refund request for a specific order.

    Use this tool when the user asks about the progress of a refund they already
    submitted. Requires the order ID.

    Returns the current status, reason, refund amount (if determined), and timestamps.
    """
    user_id = wrapper.context.user_id

    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, order_id, reason, status, amount, requested_at, updated_at
            FROM refund_requests
            WHERE user_id = %s AND order_id = %s
            ORDER BY requested_at DESC
            LIMIT 1
            """,
            (user_id, order_id),
        )
        row = cursor.fetchone()
        cursor.close()

    if row is None:
        return (
            f"No refund request found for order '{order_id}' under your account. "
            f"If you believe this is an error, please double-check your order ID "
            f"or contact our support team directly."
        )

    amount_str = f"${row['amount']:.2f}" if row["amount"] is not None else "pending review"
    return (
        f"Refund request for order '{order_id}':\n"
        f"  Request ID   : {row['id']}\n"
        f"  Status       : {row['status']}\n"
        f"  Reason       : {row['reason']}\n"
        f"  Refund amount: {amount_str}\n"
        f"  Requested    : {row['requested_at']}\n"
        f"  Last updated : {row['updated_at']}"
    )
