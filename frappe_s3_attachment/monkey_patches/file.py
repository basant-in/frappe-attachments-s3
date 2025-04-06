# Copyright (c) 2025, Basant Choudhary. and Contributors
# MIT License. See license.txt

from frappe.utils import cint

# override set_is_private from frappe.core.doctype.file.file
def s3Attachment_set_is_private(self):
    if self.file_url:
        self.is_private = cint(self.file_url.startswith("/private") or self.file_url.startswith("/api/method/frappe_s3_attachment.controller.generate_file"))


# override is_safe_path from frappe.utils.file_manager
def s3Attachment_is_safe_path(path: str) -> bool:
    URL_PREFIXES = ("http://", "https://", "/api/")
    if path.startswith(URL_PREFIXES):
        return True

    basedir = frappe.get_site_path()
    # ref: https://docs.python.org/3/library/os.path.html#os.path.commonpath
    matchpath = os.path.abspath(path)
    basedir = os.path.abspath(basedir)

    return basedir == os.path.commonpath((basedir, matchpath))