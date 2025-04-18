from __future__ import unicode_literals

import random
import string
import datetime
import re
import os
from frappe.utils import get_url, get_url_to_form
import boto3
import frappe

from botocore.exceptions import ClientError
from frappe import _
import magic


class S3Operations(object):

    def __init__(self):
        """
        Function to initialise the aws settings from frappe S3 File attachment
        doctype.
        """
        self.s3_settings_doc = frappe.get_doc(
            'S3 File Attachment',
            'S3 File Attachment',
        )
        if (
            self.s3_settings_doc.aws_key and
            self.s3_settings_doc.aws_secret
        ):
            self.S3_CLIENT = boto3.client(
                's3',
                aws_access_key_id=self.s3_settings_doc.aws_key,
                aws_secret_access_key=self.s3_settings_doc.aws_secret,
                region_name=self.s3_settings_doc.region_name,
                endpoint_url="https://s3." + self.s3_settings_doc.region_name + ".amazonaws.com",
            )
        else:
            self.S3_CLIENT = boto3.client('s3')
        self.BUCKET = self.s3_settings_doc.bucket_name
        self.folder_name = self.s3_settings_doc.folder_name

    def strip_special_chars(self, file_name):
        """
        Strips file charachters which doesnt match the regex.
        """
        regex = re.compile('[^0-9a-zA-Z._-]')
        file_name = regex.sub('', file_name)
        return file_name

    def key_generator(self, file_name, parent_doctype, parent_name):
        """
        Generate keys for s3 objects uploaded with file name attached.
        """
        hook_cmd = frappe.get_hooks().get("s3_key_generator")
        if hook_cmd:
            try:
                k = frappe.get_attr(hook_cmd[0])(
                    file_name=file_name,
                    parent_doctype=parent_doctype,
                    parent_name=parent_name
                )
                if k:
                    return k.rstrip('/').lstrip('/')
            except:
                pass

        file_name = file_name.replace(' ', '_')
        file_name = self.strip_special_chars(file_name)
        key = ''.join(
            random.choice(
                string.ascii_uppercase + string.digits) for _ in range(8)
        )

        today = datetime.datetime.now()
        year = today.strftime("%Y")
        month = today.strftime("%m")
        day = today.strftime("%d")

        doc_path = None
        try:
            doc_path = frappe.db.get_value(
                parent_doctype,
                filters={'name': parent_name},
                fieldname=['s3_folder_path']
            )
            doc_path = doc_path.rstrip('/').lstrip('/')
        except Exception as e:
            print(e)

        if not doc_path:
            if self.folder_name:
                final_key = self.folder_name + "/" + year + "/" + month + \
                    "/" + day + "/" + parent_doctype + "/" + key + "_" + \
                    file_name
            else:
                final_key = year + "/" + month + "/" + day + "/" + \
                    parent_doctype + "/" + key + "_" + file_name
            return final_key
        else:
            final_key = doc_path + '/' + key + "_" + file_name
            return final_key

    def upload_files_to_s3_with_key(
            self, file_path, file_name, is_private, parent_doctype, parent_name
    ):
        """
        Uploads a new file to S3.
        Strips the file extension to set the content_type in metadata.
        """
        mime_type = magic.from_file(file_path, mime=True)
        file_name = file_name.encode('ascii', 'replace')
        file_name = file_name.decode("utf-8")
        key = self.key_generator(file_name, parent_doctype, parent_name)
        content_type = mime_type
        try:
            if is_private:
                self.S3_CLIENT.upload_file(
                    file_path, self.BUCKET, key,
                    ExtraArgs={
                        "ContentType": content_type,
                        "Metadata": {
                            "ContentType": content_type,
                            "file_name": file_name
                        }
                    }
                )
            else:
                self.S3_CLIENT.upload_file(
                    file_path, self.BUCKET, key,
                    ExtraArgs={
                        "ContentType": content_type,
                        "ACL": 'public-read',
                        "Metadata": {
                            "ContentType": content_type,

                        }
                    }
                )

        except boto3.exceptions.S3UploadFailedError:
            frappe.throw(frappe._("File Upload Failed. Please try again."))
        return key,file_name

    def copy_files_in_s3_with_key(
        self, destination_file_name, source_key, is_private, parent_doctype, parent_name
    ):
        """
                Copies a file within S3.
                Strips the file extension to set the content_type in metadata.
                """
        destination_key = self.key_generator(destination_file_name, parent_doctype, parent_name)
        # content_type = mime_type
        try:
            # Get metadata and content type of the original file
            response = self.S3_CLIENT.head_object(Bucket=self.BUCKET, Key=source_key)
            content_type = response.get("ContentType", "application/octet-stream")
            metadata = response.get("Metadata", {})

            copy_source = {
                "Bucket": self.BUCKET,
                "Key": source_key
            }

            # Build ExtraArgs for copy
            extra_args = {
                "ContentType": content_type,
                "Metadata": metadata,
                "MetadataDirective": "REPLACE"  # Necessary to apply new metadata
            }

            # Set ACL explicitly (ignore original file's ACL)
            if not is_private:
                extra_args["ACL"] = "public-read"

            self.S3_CLIENT.copy_object(
                CopySource=copy_source,
                Bucket=self.BUCKET,
                Key=destination_key,
                **extra_args
            )
        except self.S3_CLIENT.exceptions.NoSuchKey:
            frappe.throw(frappe._("Original file does not exist on S3."))
        except ClientError as e:
            frappe.log_error(frappe.get_traceback(), "S3 Copy Failed")
            frappe.throw(frappe._("Failed to copy file in S3. Please try again."))
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Unexpected S3 Error")
            frappe.throw(frappe._("Unexpected error occurred while copying file in S3."))

        return destination_key, destination_file_name

    def delete_from_s3(self, key):
        """Delete file from s3"""
        self.s3_settings_doc = frappe.get_doc(
            'S3 File Attachment',
            'S3 File Attachment',
        )

        if self.s3_settings_doc.delete_file_from_cloud:
            S3_CLIENT = boto3.client(
                's3',
                aws_access_key_id=self.s3_settings_doc.aws_key,
                aws_secret_access_key=self.s3_settings_doc.aws_secret,
                region_name=self.s3_settings_doc.region_name,
            )

            try:
                S3_CLIENT.delete_object(
                    Bucket=self.s3_settings_doc.bucket_name,
                    Key=key
                )
            except ClientError:
                frappe.throw(frappe._("Access denied: Could not delete file"))

    def read_file_from_s3(self, key):
        """
        Function to read file from a s3 file.
        """
        return self.S3_CLIENT.get_object(Bucket=self.BUCKET, Key=key)

    def get_url(self, key, file_name=None):
        """
        Return url.

        :param bucket: s3 bucket name
        :param key: s3 object key
        """
        if self.s3_settings_doc.signed_url_expiry_time:
            self.signed_url_expiry_time = self.s3_settings_doc.signed_url_expiry_time # noqa
        else:
            self.signed_url_expiry_time = 120
        params = {
                'Bucket': self.BUCKET,
                'Key': key,

        }
        if file_name:
            params['ResponseContentDisposition'] = 'filename={}'.format(file_name)

        url = self.S3_CLIENT.generate_presigned_url(
            'get_object',
            Params=params,
            ExpiresIn=self.signed_url_expiry_time,
        )

        return url


@frappe.whitelist()
def file_upload_to_s3(doc, method):
    """
    check and upload files to s3. the path check and
    """
    s3_upload = S3Operations()
    path = doc.file_url
    site_path = frappe.utils.get_site_path()
    # Folder cannot be uploaded to cloud. Ignore the folder
    if doc.is_folder:
        return

    if doc.doctype == "File" and not doc.attached_to_doctype:
        parent_doctype = doc.doctype
        parent_name = doc.name
    else:
        parent_doctype = doc.attached_to_doctype
        parent_name = doc.attached_to_name
    ignore_s3_upload_for_doctype = frappe.local.conf.get('ignore_s3_upload_for_doctype') or ['Data Import']
    if parent_doctype not in ignore_s3_upload_for_doctype:
        if not doc.is_private:
            file_path = site_path + '/public' + path
        else:
            file_path = site_path + path
        if not doc.uploaded_to_cloud:
            key,filename = s3_upload.upload_files_to_s3_with_key(
                file_path, doc.file_name,
                doc.is_private, parent_doctype,
                parent_name
            )
        else:
            key, filename = s3_upload.copy_files_in_s3_with_key(
                doc.file_name, doc.content_hash,
                doc.is_private, parent_doctype,
                parent_name
            )
        if doc.is_private:
            method = "frappe_s3_attachment.controller.generate_file"
            site_base_url = frappe.local.conf.site_base_url if frappe.local.conf.site_base_url else ""
            file_url = """{0}/api/method/{1}?key={2}&file_name={3}""".format(site_base_url, method, key, filename)
        else:
            file_url = '{}/{}/{}'.format(
                s3_upload.S3_CLIENT.meta.endpoint_url,
                s3_upload.BUCKET,
                key
            )
        frappe.db.sql("""UPDATE `tabFile` SET file_url=%s, folder=%s,
            old_parent=%s, content_hash=%s, uploaded_to_cloud=1 WHERE name=%s""", (
            file_url, 'Home/Attachments', doc.folder, key, doc.name))

        # From this PR, this code is unuseful
        # https://github.com/zerodha/frappe-attachments-s3/pull/39
        # if frappe.get_meta(parent_doctype).get('image_field'):
        #     frappe.db.set_value(parent_doctype, parent_name, frappe.get_meta(
        #         parent_doctype).get('image_field'), file_url)

        frappe.db.commit()
        doc.reload()
        # remove the file from local drive only if the original file (in case of copy) is not in the cloud
        os.remove(file_path) if not doc.uploaded_to_cloud else None


@frappe.whitelist()
def generate_file(key=None, file_name=None):
    """
    Function to stream file from s3.
    """
    if key:
        s3_upload = S3Operations()
        signed_url = s3_upload.get_url(key, file_name)
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = signed_url
    else:
        frappe.local.response['body'] = "Key not found."
    return

@frappe.whitelist()
def generate_signed_url(key=None, file_name=None):
    """
    Function to stream file from s3.
    """
    if key:
        s3_upload = S3Operations()
        signed_url = s3_upload.get_url(key, file_name)
        return signed_url
    else:
        frappe.throw(_("Key not found."))
    return


def upload_existing_files_s3(name, file_name):
    """
    Function to upload all existing files.
    """
    file_doc_name = frappe.db.get_value('File', {'name': name})
    if file_doc_name:
        doc = frappe.get_doc('File', name)
        s3_upload = S3Operations()
        path = doc.file_url
        site_path = frappe.utils.get_site_path()
        parent_doctype = doc.attached_to_doctype
        parent_name = doc.attached_to_name
        if not doc.is_private:
            file_path = site_path + '/public' + path
        else:
            file_path = site_path + path
        if os.path.isfile(file_path):
            key,filename = s3_upload.upload_files_to_s3_with_key(
                file_path, doc.file_name,
                doc.is_private, parent_doctype,
                parent_name
            )
        elif doc.uploaded_to_cloud or doc.uploaded_to_dropbox or doc.uploaded_to_google_drive:
            return
        else:
            # If file is missing on the local drive and not uploaded to cloud, then delete it
            doc.delete()
            return

        if doc.is_private:
            method = "frappe_s3_attachment.controller.generate_file"
            site_base_url = frappe.local.conf.site_base_url if frappe.local.conf.site_base_url else ""
            file_url = """{0}/api/method/{1}?key={2}""".format(site_base_url, method, key)
        else:
            file_url = '{}/{}/{}'.format(
                s3_upload.S3_CLIENT.meta.endpoint_url,
                s3_upload.BUCKET,
                key
            )
        os.remove(file_path)
        # Add Uploaded to Cloud as true; Set the right folder path from AWS
        doc = frappe.db.sql("""UPDATE `tabFile` SET file_url=%s, folder=%s,
            old_parent=%s, content_hash=%s, uploaded_to_cloud=1 WHERE name=%s""", (
            file_url, 'Home/Attachments', doc.folder, key, doc.name))
        frappe.db.commit()
    else:
        pass


def s3_file_regex_match(file_url):
    """
    Match the public file regex match.
    """
    return re.match(
        r'^(https:|/api/method/frappe_s3_attachment.controller.generate_file)',
        file_url
    )


@frappe.whitelist()
def migrate_existing_files():
    """
    Function to migrate the existing files to s3.
    """
    # get_all_files_from_public_folder_and_upload_to_s3
    files_list = frappe.get_all(
        'File',
        fields=['name', 'file_url', 'file_name']
    )
    for file in files_list:
        if file['file_url']:
            if not s3_file_regex_match(file['file_url']):
                upload_existing_files_s3(file['name'], file['file_name'])
    return True


def delete_from_cloud(doc, method):
    """Delete file from s3"""
    s3 = S3Operations()
    s3.delete_from_s3(doc.content_hash)


@frappe.whitelist()
def ping():
    """
    Test function to check if api function work.
    """
    return "pong"