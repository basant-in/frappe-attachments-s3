# Copyright (c) 2025, Basant Choudhary. and Contributors
# MIT License. See license.txt

import frappe

# Override copy_attachments_from_amended_from function from Document Class
def s3Attachment_copy_attachments_from_amended_from(self):
    """Copy attachments from `amended_from`"""

    # loop through attachments
    for attach_item in s3Attachment_get_attachments(self.doctype, self.amended_from):
        # save attachments to new doc
        _file = frappe.get_doc(
            {
                "doctype": "File",
                "file_url": attach_item.file_url,
                "file_name": attach_item.file_name,
                "file_type": attach_item.file_type,
                "attached_to_name": self.name,
                "attached_to_doctype": self.doctype,
                # "folder": "Home/Attachments",
                "is_private": attach_item.is_private,
                "content_hash": attach_item.content_hash,
                "uploaded_to_cloud": attach_item.uploaded_to_cloud,
            }
        )
        _file.save()

def s3Attachment_get_attachments(dt, dn):
    return frappe.get_all(
        "File",
        fields=["name", "file_name", "file_url", "is_private", "file_type", "content_hash", "uploaded_to_cloud"],
        filters={"attached_to_name": dn, "attached_to_doctype": dt},
    )