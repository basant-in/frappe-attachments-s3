import frappe

from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def execute():
    """
    Insert uploaded_to_cloud custom field in the File doctype
    """
    _fieldname = "uploaded_to_cloud"

    df = {
        "fieldname": _fieldname,
        "module": "Frappe S3 Attachment",
        "label": "Uploaded to Cloud (AWS S3)",
        "insert_after": "uploaded_to_google_drive",
        "fieldtype": "Check",
        "read_only": 1,
    }
    try:
        create_custom_field("File", df, ignore_validate=True, is_system_generated=False)
        frappe.clear_cache(doctype="File")
    except Exception:
        pass