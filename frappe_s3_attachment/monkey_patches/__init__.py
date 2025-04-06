import os
import frappe
import frappe_s3_attachment.monkey_patches.importer

import frappe.core.doctype.file.file as file_module
from frappe.core.doctype.file.file import File

from frappe_s3_attachment.monkey_patches.file import s3Attachment_set_is_private, s3Attachment_is_safe_path

URL_PREFIXES = ("http://", "https://", "/api/")
# override url_prefix in file_module
file_module.URL_PREFIXES = URL_PREFIXES
file_module.is_safe_path = s3Attachment_is_safe_path
# override set_is_private in File Class
File.set_is_private = s3Attachment_set_is_private
