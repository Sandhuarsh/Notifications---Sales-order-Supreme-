# SEPL Notifications

Item-wise Sales Order email notifications for Supreme Equipments Pvt Ltd.

Sends a styled HTML email the instant a Sales Order is submitted, amended, or
cancelled, to whichever departments are flagged (via the `Item Notification
Role` / `Item Notification Recipient` doctypes already configured on the
site) for the items in that order.

Runs as a normal Frappe app hook (`doc_events` in `hooks.py`), not a Server
Script -- this avoids the Server Script sandbox, so notifications send
synchronously with no polling delay.

## Installation

```
bench get-app https://github.com/<your-org>/sepl_notifications
bench --site supremelive install-app sepl_notifications
```

## Configuration

Edit `sepl_notifications/notifications.py`:

- `TEST_MODE` -- while `True`, every notification is redirected to
  `TEST_EMAIL_OVERRIDE` instead of the real employee addresses. Set to
  `False` to go live.
