# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe


from frappe.model.document import Document
from frappe_s3_attachment.monkey_patches.document import s3Attachment_copy_attachments_from_amended_from

__version__ = "0.0.3"

old_get_hooks = frappe.get_hooks


def get_hooks(*args, **kwargs):
	if "frappe_s3_attachment" in frappe.get_installed_apps():
		import frappe_s3_attachment.monkey_patches

	return old_get_hooks(*args, **kwargs)


frappe.get_hooks = get_hooks

# override the copy_attachments_from_amended_from method in frappe.model.document
Document.copy_attachments_from_amended_from = s3Attachment_copy_attachments_from_amended_from