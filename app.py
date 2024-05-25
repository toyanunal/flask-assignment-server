import zipfile, os, random, hashlib, re, secrets, boto3, logging, io
from lxml import etree
from flask import Flask, session, request, jsonify, render_template_string, redirect
from flask_session import Session
from datetime import datetime, timedelta

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

def copy_file_in_s3(bucket, src_key, dst_key):
    copy_source = {'Bucket': bucket, 'Key': src_key}
    app.logger.info(f"Copying {src_key} to {dst_key} in bucket {bucket}")
    s3_client.copy(copy_source, bucket, dst_key)
    app.logger.info(f"Copied {src_key} to {dst_key} in bucket {bucket}")

def upload_file_to_s3(bucket, key, file_path):
    app.logger.info(f"Uploading {file_path} to S3 bucket {bucket} at {key}")
    s3_client.upload_file(file_path, bucket, key)
    app.logger.info(f"Uploaded {file_path} to {key} in S3 bucket {bucket}")

def delete_s3_folder(bucket, prefix):
    app.logger.info(f"Deleting files in S3 bucket {bucket} with prefix {prefix}")
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket)
    bucket.objects.filter(Prefix=prefix).delete()
    app.logger.info(f"Deleted files with prefix {prefix} in S3 bucket {bucket}")

def generate_secure_token():
    return secrets.token_urlsafe()

def extract_number(text):
    numbers = re.findall(r'\d+', text)
    return numbers[0] if numbers else None

def generate_random_number(ext_user_username, max_number):
    seed = int(ext_user_username[1:])
    random.seed(seed)
    return random.randint(1, max_number)

def embed_hidden_info_docx(docx_key, ext_user_username, new_docx_key):
    app.logger.info(f"Embedding hidden info in DOCX file {docx_key}")

    # Download the DOCX file to an in-memory file
    docx_obj = io.BytesIO()
    s3_client.download_fileobj(S3_BUCKET, docx_key, docx_obj)
    docx_obj.seek(0)

    # Extract the contents of the DOCX file to an in-memory zip
    with zipfile.ZipFile(docx_obj, 'r') as zip_ref:
        temp_dir = {name: zip_ref.read(name) for name in zip_ref.namelist()}

    # Modify the custom XML part in-memory
    hash_object = hashlib.sha256(ext_user_username[1:].encode())
    hex_dig = hash_object.hexdigest()
    root = etree.Element('root')
    hidden_info = etree.SubElement(root, 'hiddenInfo')
    hidden_info.text = hex_dig
    tree = etree.ElementTree(root)
    custom_xml_obj = io.BytesIO()
    tree.write(custom_xml_obj, xml_declaration=True, encoding='UTF-8')
    custom_xml_obj.seek(0)
    temp_dir['customXml/item1.xml'] = custom_xml_obj.read()

    # Create a new DOCX file in-memory
    new_docx_obj = io.BytesIO()
    with zipfile.ZipFile(new_docx_obj, 'w') as zip_ref:
        for name, data in temp_dir.items():
            zip_ref.writestr(name, data)
    new_docx_obj.seek(0)

    # Upload the modified DOCX file to S3
    s3_client.upload_fileobj(new_docx_obj, S3_BUCKET, new_docx_key)
    app.logger.info(f"Uploaded modified DOCX to {new_docx_key}")

    return new_docx_key

def embed_hidden_info_xlsx(xlsx_key, ext_user_username, new_xlsx_key):
    app.logger.info(f"Embedding hidden info in XLSX file {xlsx_key}")

    # Download the XLSX file to an in-memory file
    xlsx_obj = io.BytesIO()
    s3_client.download_fileobj(S3_BUCKET, xlsx_key, xlsx_obj)
    xlsx_obj.seek(0)

    # Extract the contents of the XLSX file to an in-memory zip
    with zipfile.ZipFile(xlsx_obj, 'r') as zip_ref:
        temp_dir = {name: zip_ref.read(name) for name in zip_ref.namelist()}

    # Modify the workbook XML part in-memory
    workbook_xml_obj = io.BytesIO(temp_dir['xl/workbook.xml'])
    tree = etree.parse(workbook_xml_obj)
    root = tree.getroot()
    hash_object = hashlib.sha256(ext_user_username[1:].encode())
    hex_dig = hash_object.hexdigest()
    hidden_info = etree.Element('hiddenInfo')
    hidden_info.text = hex_dig
    root.append(hidden_info)
    workbook_xml_obj = io.BytesIO()
    tree.write(workbook_xml_obj, xml_declaration=True, encoding='UTF-8')
    workbook_xml_obj.seek(0)
    temp_dir['xl/workbook.xml'] = workbook_xml_obj.read()

    # Create a new XLSX file in-memory
    new_xlsx_obj = io.BytesIO()
    with zipfile.ZipFile(new_xlsx_obj, 'w') as zip_ref:
        for name, data in temp_dir.items():
            zip_ref.writestr(name, data)
    new_xlsx_obj.seek(0)

    # Upload the modified XLSX file to S3
    s3_client.upload_fileobj(new_xlsx_obj, S3_BUCKET, new_xlsx_key)
    app.logger.info(f"Uploaded modified XLSX to {new_xlsx_key}")

    return new_xlsx_key

def create_zip(ext_user_username, hw_number):
    temp_dir = 'temp/'
    output_dir = 'output/'
    s3_src_dir = f'assignment{hw_number}_files/'

    app.logger.info("Cleaning up temp and output directories in S3")
    delete_s3_folder(S3_BUCKET, temp_dir)
    delete_s3_folder(S3_BUCKET, output_dir)

    if hw_number == '1':
        random_number = generate_random_number(ext_user_username, 9)
        app.logger.info(f"Random number generated: {random_number}")

        doc_key = f'{s3_src_dir}IS100_Assignment{hw_number}_Type{random_number}_Text.docx'
        pdf_key = f'{s3_src_dir}IS100_Assignment{hw_number}_Type{random_number}_Question.pdf'
        app.logger.info(f"Selected DOCX key: {doc_key}, PDF key: {pdf_key}")

        doc_dst_key = f'{temp_dir}IS100_Assignment{hw_number}_Type{random_number}_Text.docx'
        pdf_dst_key = f'{temp_dir}IS100_Assignment{hw_number}_Type{random_number}_Question.pdf'
        copy_file_in_s3(S3_BUCKET, doc_key, doc_dst_key)
        copy_file_in_s3(S3_BUCKET, pdf_key, pdf_dst_key)

        new_docx_key = f'{output_dir}IS100_Assignment{hw_number}_{ext_user_username[1:]}.docx'
        modified_docx_key = embed_hidden_info_docx(doc_dst_key, ext_user_username, new_docx_key)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zipf:
            with io.BytesIO() as doc_data:
                s3_client.download_fileobj(S3_BUCKET, modified_docx_key, doc_data)
                doc_data.seek(0)
                zipf.writestr(f'IS100_Assignment{hw_number}_{ext_user_username[1:]}.docx', doc_data.read())

            with io.BytesIO() as pdf_data:
                s3_client.download_fileobj(S3_BUCKET, pdf_dst_key, pdf_data)
                pdf_data.seek(0)
                zipf.writestr(f'IS100_Assignment{hw_number}_Question.pdf', pdf_data.read())

            app.logger.info(f"Created ZIP file with {modified_docx_key} and {pdf_dst_key}")
        zip_buffer.seek(0)

    elif hw_number == '2':
        random_number = generate_random_number(ext_user_username, 2)
        app.logger.info(f"Random number generated: {random_number}")
    
        xlsx_key = f'{s3_src_dir}IS100_Assignment{hw_number}_Type{random_number}_Question.xlsx'
        txt_key = f'{s3_src_dir}IS100_Assignment{hw_number}_Type{random_number}_Data.txt'
        app.logger.info(f"Selected XLSX key: {xlsx_key}, TXT key: {txt_key}")

        xlsx_dst_key = f'{temp_dir}IS100_Assignment{hw_number}_Type{random_number}_Question.xlsx'
        txt_dst_key = f'{temp_dir}IS100_Assignment{hw_number}_Type{random_number}_Data.txt'
        copy_file_in_s3(S3_BUCKET, xlsx_key, xlsx_dst_key)
        copy_file_in_s3(S3_BUCKET, txt_key, txt_dst_key)

        new_xlsx_key = f'{output_dir}IS100_Assignment{hw_number}_{ext_user_username[1:]}.xlsx'
        modified_xlsx_key = embed_hidden_info_xlsx(xlsx_dst_key, ext_user_username, new_xlsx_key)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zipf:
            with io.BytesIO() as xlsx_data:
                s3_client.download_fileobj(S3_BUCKET, modified_xlsx_key, xlsx_data)
                xlsx_data.seek(0)
                zipf.writestr(f'IS100_Assignment{hw_number}_{ext_user_username[1:]}.xlsx', xlsx_data.read())

            with io.BytesIO() as txt_data:
                s3_client.download_fileobj(S3_BUCKET, txt_dst_key, txt_data)
                txt_data.seek(0)
                zipf.writestr(f'IS100_Assignment{hw_number}_Data.txt', txt_data.read())

            app.logger.info(f"Created ZIP file with {modified_xlsx_key} and {txt_dst_key}")
        zip_buffer.seek(0)

    s3_output_key = f'output/ASSIGNMENT_{hw_number}_{ext_user_username[1:]}.zip'
    app.logger.info(f"Uploading ZIP file to S3 at {s3_output_key}")
    s3_client.upload_fileobj(zip_buffer, S3_BUCKET, s3_output_key)

    return s3_output_key

@app.route('/initiate-download', methods=['POST'])
def initiate_download():
    token = generate_secure_token()
    session['download_token'] = token
    session['token_expiry'] = (datetime.now() + timedelta(minutes=1)).timestamp()
    session['token_uses'] = 0

    # Print the form data for debugging
    app.logger.info(f"Form Data: {request.form}")

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

    app.logger.info(f"Token generated and stored in session: {token}")
    
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
    token_sent = request.args.get('token')
    token_session = session.get('download_token')
    token_uses = session.get('token_uses', 0)

    app.logger.info(f"Token sent: {token_sent}, Token in session: {token_session}, Token uses: {token_uses}")

    if not token_sent or token_sent != token_session:
        app.logger.error("Token validation failed.")
        raise ValueError("Unauthorized access or too many downloads")

    if token_uses >= 3:
        app.logger.error("Too many downloads.")
        raise ValueError("Unauthorized access or too many downloads")
    
    session['token_uses'] = token_uses + 1

    s3_output_key = session.get('filename')
    if not s3_output_key:
        app.logger.error("Filename not found in session")
        raise ValueError("Filename not found in session")

    response = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET, 'Key': s3_output_key},
        ExpiresIn=3600
    )

    app.logger.info(f"Cleaning up temp directory in S3")
    delete_s3_folder(S3_BUCKET, 'temp/')
    
    app.logger.info(f"Presigned URL generated for {s3_output_key}")
    return redirect(response)