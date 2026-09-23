app_name = "sepl_notifications"
app_title = "SEPL Notifications"
app_publisher = "Supreme Equipments Pvt Ltd"
app_description = "Item-wise Sales Order email notifications"
app_email = "arshpreet.singh@innosphereconsulting.in"
app_license = "mit"

doc_events = {
	"Sales Order": {
		"on_submit": "sepl_notifications.notifications.on_submit",
		"on_cancel": "sepl_notifications.notifications.on_cancel",
	}
}
