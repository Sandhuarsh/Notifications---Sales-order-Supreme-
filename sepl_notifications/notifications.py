import frappe
from frappe.utils import formatdate, get_url, today

# ---------------------------------------------------------------------------
# TEST MODE: while True, every email is redirected to TEST_EMAIL_OVERRIDE
# instead of the real employee addresses. Set to False to go live.
# ---------------------------------------------------------------------------
TEST_MODE = True
TEST_EMAIL_OVERRIDE = "sandhuarshpreet123@gmail.com"

BANNER_COLOR_CREATED = "#16a34a"  # green
BANNER_COLOR_MODIFIED = "#d97706"  # amber
BANNER_COLOR_CANCELLED = "#dc2626"  # red


def format_qty_uom(qty, uom):
	uom = uom or ""
	if qty == 1 and uom.endswith("s"):
		uom = uom[:-1]
	qty_str = str(int(qty)) if qty == int(qty) else str(qty)
	return f"{qty_str} {uom}".strip()


def get_sales_person_name(sales_order_doc):
	if sales_order_doc.get("sales_team"):
		row = sales_order_doc.sales_team[0]
		return frappe.db.get_value("Sales Person", row.sales_person, "sales_person_name") or row.sales_person
	return "-"


def get_delivery_date(sales_order_doc):
	if sales_order_doc.get("delivery_date"):
		return formatdate(sales_order_doc.delivery_date, "dd/mm/yyyy")
	dates = [d.delivery_date for d in sales_order_doc.items if d.get("delivery_date")]
	if dates:
		return formatdate(min(dates), "dd/mm/yyyy")
	return "-"


def load_role_map():
	all_recip_rows = frappe.get_all(
		"Item Notification Recipient",
		filters={"parenttype": "Item Notification Role"},
		fields=["parent", "employee"],
	)
	role_to_employees = {}
	for rr in all_recip_rows:
		role_to_employees.setdefault(rr.parent, []).append(rr.employee)
	return role_to_employees


def get_item_roles(item_code):
	rows = frappe.get_all(
		"Item Notify Role",
		filters={"parenttype": "Item", "parent": item_code},
		fields=["role"],
	)
	return [r.role for r in rows]


def build_email(banner_title, banner_color, detail_rows, items, so_name, url):
	rows_html = "".join(
		f'<tr><td style="padding:6px 12px 6px 0;color:#6b7280;width:150px;vertical-align:top;font-size:13px;">{label}</td>'
		f'<td style="padding:6px 0;color:#111827;font-weight:600;font-size:13px;">{value}</td></tr>'
		for label, value in detail_rows
	)

	item_rows_html = "".join(
		f'<tr style="background:{"#ffffff" if pos % 2 == 0 else "#f9fafb"};">'
		f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:13px;">{i["idx"]}</td>'
		f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#111827;font-size:13px;">{i["item_code"]}</td>'
		f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#111827;font-size:13px;">{i["item_name"]}</td>'
		f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#111827;font-size:13px;text-align:right;">'
		f'{format_qty_uom(i["qty"], i["uom"])}</td></tr>'
		for pos, i in enumerate(items)
	)

	return f"""
	<div style="font-family:Arial,Helvetica,sans-serif;max-width:600px;margin:0 auto;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
		<div style="background:{banner_color};padding:18px 24px;">
			<span style="color:#ffffff;font-size:16px;font-weight:bold;letter-spacing:0.5px;">{banner_title}</span>
		</div>
		<div style="padding:20px 24px;background:#ffffff;">
			<table style="width:100%;border-collapse:collapse;">{rows_html}</table>
			<h3 style="margin:20px 0 8px 0;font-size:13px;color:#111827;text-transform:uppercase;letter-spacing:0.5px;">Item Details</h3>
			<table style="width:100%;border-collapse:collapse;">
				<tr style="background:#f3f4f6;text-align:left;">
					<th style="padding:8px;border-bottom:2px solid #e5e7eb;font-size:12px;color:#6b7280;">#</th>
					<th style="padding:8px;border-bottom:2px solid #e5e7eb;font-size:12px;color:#6b7280;">Item Code</th>
					<th style="padding:8px;border-bottom:2px solid #e5e7eb;font-size:12px;color:#6b7280;">Item Name</th>
					<th style="padding:8px;border-bottom:2px solid #e5e7eb;font-size:12px;color:#6b7280;text-align:right;">Qty</th>
				</tr>
				{item_rows_html}
			</table>
			<div style="text-align:center;margin-top:24px;">
				<a href="{url}/app/sales-order/{so_name}" style="background:#111827;color:#ffffff;padding:10px 22px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:600;display:inline-block;">Open Sales Order</a>
			</div>
		</div>
		<div style="background:#f9fafb;padding:10px 24px;font-size:11px;color:#9ca3af;text-align:center;border-top:1px solid #e5e7eb;">Automated notification &mdash; Supreme Equipments ERP</div>
	</div>
	"""


def notify(so, event_type):
	# Any failure here is logged and swallowed -- a notification bug must
	# never block the actual Sales Order submit/cancel transaction.
	try:
		if event_type == "Created":
			banner_title, banner_color = "SALES ORDER CREATED", BANNER_COLOR_CREATED
			date_label, by_label, subj_word = "Creation Date", "Created By", "CREATED"
		elif event_type == "Modified":
			banner_title, banner_color = "SALES ORDER MODIFIED", BANNER_COLOR_MODIFIED
			date_label, by_label, subj_word = "Modification Date", "Modified By", "Modified"
		else:
			banner_title, banner_color = "SALES ORDER CANCELLED", BANNER_COLOR_CANCELLED
			date_label, by_label, subj_word = "Cancellation Date", "Cancelled By", "Cancelled"

		performed_by = frappe.utils.get_fullname(so.modified_by)
		sales_person_name = get_sales_person_name(so)
		delivery_date = get_delivery_date(so)
		action_date = formatdate(today(), "dd/mm/yyyy")

		role_to_employees = load_role_map()

		recipients = {}
		for row in so.items:
			matched_roles = get_item_roles(row.item_code)
			if not matched_roles:
				continue
			emp_ids = set()
			for role_name in matched_roles:
				emp_ids.update(role_to_employees.get(role_name, []))
			for emp_id in emp_ids:
				emp = frappe.db.get_value("Employee", emp_id, ["employee_name", "user_id"], as_dict=True)
				if not emp or not emp.user_id:
					continue
				recipients.setdefault(emp.user_id, []).append({
					"idx": row.idx,
					"item_code": row.item_code,
					"item_name": row.item_name,
					"qty": row.qty,
					"uom": row.uom or row.stock_uom,
				})

		for email, items in recipients.items():
			items = sorted(items, key=lambda i: i["idx"])
			detail_rows = [
				("Sales Order No.", so.name),
				(date_label, action_date),
				(by_label, performed_by),
				("Sales Person", sales_person_name),
				("Customer", f"{so.customer} ({so.customer_name})"),
				("Delivery Date", delivery_date),
			]
			message = build_email(banner_title, banner_color, detail_rows, items, so.name, get_url())
			send_to = TEST_EMAIL_OVERRIDE if TEST_MODE else email
			frappe.sendmail(recipients=[send_to], subject=f"{so.name} {subj_word}", message=message)
	except Exception:
		frappe.log_error(title="SEPL Item Notification", message=frappe.get_traceback())


def on_submit(doc, method=None):
	event_type = "Modified" if doc.amended_from else "Created"
	notify(doc, event_type)


def on_cancel(doc, method=None):
	notify(doc, "Cancelled")
