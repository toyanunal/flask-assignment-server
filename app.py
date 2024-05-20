import boto3
import os
import zipfile
import shutil
import tempfile
from lxml import etree

# Initialize the S3 client
s3_client = boto3.client('s3')
S3_BUCKET = 'flask-assignment-server-bucket'

def download_file_from_s3(bucket, key, download_path):
    s3_client.download_file(bucket, key, download_path)
    print(f"Downloaded {key} to {download_path}")

def upload_file_to_s3(file_path, bucket, key):
    s3_client.upload_file(file_path, bucket, key)
    print(f"Uploaded {file_path} to {key}")

def embed_hidden_info_docx(docx_path, ext_user_username):
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()

    # Extract the contents of the docx file to the temporary directory
    with zipfile.ZipFile(docx_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # Path to the custom XML part
    custom_xml_path = os.path.join(temp_dir, 'customXml/item1.xml')

    # Create a SHA-256 hash of the username
    hash_object = hashlib.sha256(ext_user_username.encode())
    hex_dig = hash_object.hexdigest()

    # Create XML elements and set the hashed username as hidden info
    root = etree.Element('root')
    hidden_info = etree.SubElement(root, 'hiddenInfo')
    hidden_info.text = hex_dig
    tree = etree.ElementTree(root)

    # Ensure the directory for custom XML exists
    custom_xml_dir = os.path.dirname(custom_xml_path)
    if not os.path.exists(custom_xml_dir):
        os.makedirs(custom_xml_dir)

    # Write the hidden info to the custom XML file
    with open(custom_xml_path, 'wb') as xml_file:
        tree.write(xml_file, xml_declaration=True, encoding='UTF-8')

    # Create a new docx file with the modified contents
    new_docx_path = os.path.join(tempfile.gettempdir(), 'modified.docx')
    with zipfile.ZipFile(new_docx_path, 'w') as zip_ref:
        for folder_name, subfolders, filenames in os.walk(temp_dir):
            for filename in filenames:
                file_path = os.path.join(folder_name, filename)
                arcname = os.path.relpath(file_path, temp_dir)
                zip_ref.write(file_path, arcname)

    # Clean up intermediate files
    shutil.rmtree(temp_dir)

    return new_docx_path

def main():
    # Example variables
    hw_number = '1'
    ext_user_username = 'e269694'
    random_number = '4'
    doc_key = f'assignment{hw_number}_files/IS100_Assignment{hw_number}_Type{random_number}_Text.docx'
    download_path = f'/tmp/IS100_Assignment{hw_number}_Type{random_number}_Text.docx'
    upload_key = f'output/IS100_Assignment{hw_number}_{ext_user_username[1:]}.docx'

    # Step 1: Download the file from S3
    download_file_from_s3(S3_BUCKET, doc_key, download_path)

    # Step 2: Process the file
    modified_docx_path = embed_hidden_info_docx(download_path, ext_user_username)

    # Step 3: Upload the processed file back to S3
    upload_file_to_s3(modified_docx_path, S3_BUCKET, upload_key)

if __name__ == '__main__':
    main()