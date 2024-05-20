import zipfile
import os
import shutil
import random
import hashlib
from lxml import etree
from flask import Flask, session, request, jsonify, render_template_string, redirect, url_for
from flask_session import Session
from datetime import datetime, timedelta
import re, secrets, boto3, logging
import tempfile

app = Flask(__name__)

# Configure session to use filesystem (not default, which uses signed cookies)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
app.config['SECRET_KEY'] = os.urandom(24)  # Use a secure random key

# Initialize Session
Session(app)

# Configure S3 client
s3_client = boto3.client('s3')
S3_BUCKET = 'flask-assignment-server-bucket'

# Configure logging
logging.basicConfig(level=logging.INFO)
app.logger.addHandler(logging.StreamHandler())

def generate_secure_token():
    return secrets.token_urlsafe()

def extract_number(text):
    numbers = re.findall(r'\d+', text)
    return numbers[0] if numbers else None

def embed_hidden_info_docx(docx_path, ext_user_username, temp_dir, new_docx_path):
    # Clean up and create a temporary directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    # Extract the contents of the docx file to the temporary directory
    with zipfile.ZipFile(docx_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # Path to the custom XML part
    custom_xml_path = os.path.join(temp_dir, 'customXml/item1.xml')

    # Create a SHA-256 hash of the username
    hash_object = hashlib.sha256(ext_user_username[1:].encode())
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
    with zipfile.ZipFile(new_docx_path, 'w') as zip_ref:
        for folder_name, subfolders, filenames in os.walk(temp_dir):
            for filename in filenames:
                file_path = os.path.join(folder_name, filename)
                arcname = os.path.relpath(file_path, temp_dir)
                zip_ref.write(file_path, arcname)

    # Clean up intermediate files
    shutil.rmtree(temp_dir)

    return new_docx_path

def embed_hidden_info_xlsx(xlsx_path, ext_user_username, temp_dir, new_xlsx_path):
    # Clean up and create a temporary directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    # Extract the contents of the xlsx file to the temporary directory
    with zipfile.ZipFile(xlsx_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # Path to the workbook XML part
    workbook_xml_path = os.path.join(temp_dir, 'xl/workbook.xml')

    # Parse the workbook XML
    tree = etree.parse(workbook_xml_path)
    root = tree.getroot()

    # Create a SHA-256 hash of the username
    hash_object = hashlib.sha256(ext_user_username[1:].encode())
    hex_dig = hash_object.hexdigest()

    # Create XML elements and set the hashed username as hidden info
    hidden_info = etree.Element('hiddenInfo')
    hidden_info.text = hex_dig
    root.append(hidden_info)

    # Write the hidden info to the workbook XML
    tree.write(workbook_xml_path, xml_declaration=True, encoding='UTF-8')

    # Create a new xlsx file with the modified contents
    with zipfile.ZipFile(new_xlsx_path, 'w') as zip_ref:
        for folder_name, subfolders, filenames in os.walk(temp_dir):
            for filename in filenames:
                file_path = os.path.join(folder_name, filename)
                arcname = os.path.relpath(file_path, temp_dir)
                zip_ref.write(file_path, arcname)

    # Clean up intermediate files
    shutil.rmtree(temp_dir)

    return new_xlsx_path

def create_zip(ext_user_username, hw_number):
    temp_dir = tempfile.mkdtemp()
    output_dir = tempfile.mkdtemp()
    
    try:
        # Determine source directory on S3 based on hw_number
        s3_src_dir = f'assignment{hw_number}_files/'
        
        # Determine the specific files to download and process
        if hw_number == '1':
            random_number = random.randint(1, 9)
            doc_key = os.path.join(s3_src_dir, f'IS100_Assignment{hw_number}_Type{random_number}_Text.docx')
            pdf_key = os.path.join(s3_src_dir, f'IS100_Assignment{hw_number}_Type{random_number}_Question.pdf')
        elif hw_number == '2':
            random_number = random.randint(1, 2)
            xlsx_key = os.path.join(s3_src_dir, f'IS100_Assignment{hw_number}_Type{random_number}_Question.xlsx')
            txt_key = os.path.join(s3_src_dir, f'IS100_Assignment{hw_number}_Type{random_number}_Data.txt')
        else:
            return None

        # Download only the determined files from S3
        if hw_number == '1':
            doc_src_path = os.path.join(temp_dir, f'IS100_Assignment{hw_number}_Type{random_number}_Text.docx')
            pdf_src_path = os.path.join(temp_dir, f'IS100_Assignment{hw_number}_Type{random_number}_Question.pdf')
            s3_client.download_file(S3_BUCKET, doc_key, doc_src_path)
            s3_client.download_file(S3_BUCKET, pdf_key, pdf_src_path)
        elif hw_number == '2':
            xlsx_src_path = os.path.join(temp_dir, f'IS100_Assignment{hw_number}_Type{random_number}_Question.xlsx')
            txt_src_path = os.path.join(temp_dir, f'IS100_Assignment{hw_number}_Type{random_number}_Data.txt')
            s3_client.download_file(S3_BUCKET, xlsx_key, xlsx_src_path)
            s3_client.download_file(S3_BUCKET, txt_key, txt_src_path)

        # Process files (embed hidden info)
        if hw_number == '1':
            doc_dst = f'IS100_Assignment{hw_number}_{ext_user_username[1:]}.docx'
            pdf_dst = f'IS100_Assignment{hw_number}_Question.pdf'
            new_docx_path = os.path.join(output_dir, f'IS100_Assignment{hw_number}_{ext_user_username[1:]}.docx')

            modified_docx_path = embed_hidden_info_docx(doc_src_path, ext_user_username, temp_dir, new_docx_path)

            with zipfile.ZipFile(os.path.join(output_dir, 'output.zip'), 'w') as zipf:
                zipf.write(modified_docx_path, doc_dst)
                zipf.write(pdf_src_path, pdf_dst)

            os.remove(modified_docx_path)

        elif hw_number == '2':
            xlsx_dst = f'IS100_Assignment{hw_number}_{ext_user_username[1:]}.xlsx'
            txt_dst = f'IS100_Assignment{hw_number}_Data.txt'
            new_xlsx_path = os.path.join(output_dir, f'IS100_Assignment{hw_number}_{ext_user_username[1:]}.xlsx')

            modified_xlsx_path = embed_hidden_info_xlsx(xlsx_src_path, ext_user_username, temp_dir, new_xlsx_path)

            with zipfile.ZipFile(os.path.join(output_dir, 'output.zip'), 'w') as zipf:
                zipf.write(modified_xlsx_path, xlsx_dst)
                zipf.write(txt_src_path, txt_dst)

            os.remove(modified_xlsx_path)

        # Upload the ZIP file to S3 output directory
        zip_filepath = os.path.join(output_dir, 'output.zip')
        s3_output_key = f'output/ASSIGNMENT_{hw_number}_{ext_user_username[1:]}.zip'
        s3_client.upload_file(zip_filepath, S3_BUCKET, s3_output_key)

        return s3_output_key

    finally:
        shutil.rmtree(temp_dir)
        shutil.rmtree(output_dir)

@app.route('/initiate-download', methods=['POST'])
def initiate_download():
    token = generate_secure_token()
    session['download_token'] = token
    session['token_expiry'] = (datetime.now() + timedelta(minutes=1)).timestamp()
    session['token_uses'] = 0

    custom_hw = request.form.get('custom_hw')
    resource_link_title = request.form.get('resource_link_title')
    hw_number = extract_number(custom_hw) if custom_hw else extract_number(resource_link_title)
    
    if not hw_number:
        return jsonify({"error": "Assignment number not correctly provided"}), 400
    
    ext_user_username = request.form.get('ext_user_username')

    if not ext_user_username:
        return jsonify({"error": "Username not provided"}), 400
    session['ext_user_username'] = ext_user_username

    if not re.match(r'^e\d+$', ext_user_username):
        return jsonify({"error": "Invalid username format"}), 400

    try:
        s3_output_key = create_zip(ext_user_username, hw_number)
        if s3_output_key:
            session['filename'] = s3_output_key
        else:
            return jsonify({"error": "Failed to create zip file"}), 500
    except Exception as e:
        app.logger.error(f"Error creating zip file: {str(e)}")
        return jsonify({"error": str(e)}), 500

    token = generate_secure_token()
    html_content = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>IS100 - Download Assignment</title>
    </head>
    <body>
        <script>
            function initiateDownload() {{
                var downloadUrl = "/download-file?token={token}";
                window.location.href = downloadUrl;
                
                setTimeout(function() {{
                    if (window.history.length > 1) {{
                        window.history.back();
                    }} else {{
                        window.location.href = "https://odtuclass.metu.edu.tr/";
                    }}
                }}, 5000);
            }}
            window.onload = initiateDownload;
        </script>
        <p>You will be redirected back in 5 seconds.</p>
        <p>If your download does not start, <a href="/download-file?token={token}">click here</a>.</p>
        <p>To return to the previous page, <a href="javascript:history.back()">click here</a>.</p>
        <p>To return to the ODTUClass, <a href="https://odtuclass.metu.edu.tr/">click here</a>.</p>
    </body>
    </html>
    '''
    return render_template_string(html_content)

@app.route('/download-file', methods=['GET'])
def download_file():
    try:
        token_sent = request.args.get('token')
        token_session = session.get('download_token')
        token_uses = session.get('token_uses', 0)
        if not token_sent or token_sent != token_session or token_uses >= 3:
            raise ValueError("Unauthorized access or too many downloads")
        
        session['token_uses'] = token_uses + 1

        s3_output_key = session.get('filename')
        if not s3_output_key:
            raise ValueError("Filename not found in session")

        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_output_key},
            ExpiresIn=3600
        )
        return redirect(response)
    except ValueError as ve:
        app.logger.error(f"Access error: {str(ve)}")
        return jsonify({"error": str(ve)}), 403
    except Exception as e:
        app.logger.error(f"Error downloading file: {str(e)}")
        return jsonify({"error": str(e)}), 500