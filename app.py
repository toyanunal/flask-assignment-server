from flask import Flask, session, request, jsonify, render_template_string, redirect, url_for
from flask_session import Session # Import Session for server-side sessions
from datetime import datetime, timedelta
import re, secrets, os, boto3, logging,  tempfile, zipfile, shutil, hashlib, random
from lxml import etree

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
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    with zipfile.ZipFile(docx_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    custom_xml_path = os.path.join(temp_dir, 'customXml/item1.xml')
    hash_object = hashlib.sha256(ext_user_username[1:].encode())
    hex_dig = hash_object.hexdigest()

    root = etree.Element('root')
    hidden_info = etree.SubElement(root, 'hiddenInfo')
    hidden_info.text = hex_dig
    tree = etree.ElementTree(root)

    custom_xml_dir = os.path.dirname(custom_xml_path)
    if not os.path.exists(custom_xml_dir):
        os.makedirs(custom_xml_dir)

    with open(custom_xml_path, 'wb') as xml_file:
        tree.write(xml_file, xml_declaration=True, encoding='UTF-8')

    with zipfile.ZipFile(new_docx_path, 'w') as zip_ref:
        for folder_name, subfolders, filenames in os.walk(temp_dir):
            for filename in filenames:
                file_path = os.path.join(folder_name, filename)
                arcname = os.path.relpath(file_path, temp_dir)
                zip_ref.write(file_path, arcname)

    shutil.rmtree(temp_dir)
    return new_docx_path

def embed_hidden_info_xlsx(xlsx_path, ext_user_username, temp_dir, new_xlsx_path):
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    with zipfile.ZipFile(xlsx_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    workbook_xml_path = os.path.join(temp_dir, 'xl/workbook.xml')
    tree = etree.parse(workbook_xml_path)
    root = tree.getroot()

    hash_object = hashlib.sha256(ext_user_username[1:].encode())
    hex_dig = hash_object.hexdigest()
    hidden_info = etree.Element('hiddenInfo')
    hidden_info.text = hex_dig
    root.append(hidden_info)

    tree.write(workbook_xml_path, xml_declaration=True, encoding='UTF-8')

    with zipfile.ZipFile(new_xlsx_path, 'w') as zip_ref:
        for folder_name, subfolders, filenames in os.walk(temp_dir):
            for filename in filenames:
                file_path = os.path.join(folder_name, filename)
                arcname = os.path.relpath(file_path, temp_dir)
                zip_ref.write(file_path, arcname)

    shutil.rmtree(temp_dir)
    return new_xlsx_path

def create_zip(ext_user_username, hw_number, temp_dir):
    output_dir = tempfile.mkdtemp(dir=temp_dir)

    zip_filename = f'ASSIGNMENT_{hw_number}_{ext_user_username[1:]}.zip'
    zip_filepath = os.path.join(output_dir, zip_filename)

    if hw_number == '1':
        random_number = random.randint(1, 9)
        doc_src = download_from_s3(f'IS100_Assignment{hw_number}_Type{random_number}_Text.docx', temp_dir)
        pdf_src = download_from_s3(f'IS100_Assignment{hw_number}_Type{random_number}_Question.pdf', temp_dir)
        doc_dst = f'IS100_Assignment{hw_number}_{ext_user_username[1:]}.docx'
        pdf_dst = f'IS100_Assignment{hw_number}_Question.pdf'
        new_docx_path = os.path.join(output_dir, f'IS100_Assignment{hw_number}_{ext_user_username[1:]}.docx')

        modified_docx_path = embed_hidden_info_docx(doc_src, ext_user_username, temp_dir, new_docx_path)

        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            zipf.write(modified_docx_path, doc_dst)
            zipf.write(pdf_src, pdf_dst)

        os.remove(modified_docx_path)

    elif hw_number == '2':
        random_number = random.randint(1, 2)
        xlsx_src = download_from_s3(f'IS100_Assignment{hw_number}_Type{random_number}_Question.xlsx', temp_dir)
        txt_src = download_from_s3(f'IS100_Assignment{hw_number}_Type{random_number}_Data.txt', temp_dir)
        xlsx_dst = f'IS100_Assignment{hw_number}_{ext_user_username[1:]}.xlsx'
        txt_dst = f'IS100_Assignment{hw_number}_Data.txt'
        new_xlsx_path = os.path.join(output_dir, f'IS100_Assignment{hw_number}_{ext_user_username[1:]}.xlsx')

        modified_xlsx_path = embed_hidden_info_xlsx(xlsx_src, ext_user_username, temp_dir, new_xlsx_path)

        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            zipf.write(modified_xlsx_path, xlsx_dst)
            zipf.write(txt_src, txt_dst)

        os.remove(modified_xlsx_path)

    else:
        print("Invalid hw_number. Please provide either '1' or '2'.")
        return
    
    upload_to_s3(zip_filepath, f'ASSIGNMENT_{hw_number}_{ext_user_username[1:]}.zip')
    shutil.rmtree(output_dir)

def download_from_s3(key, temp_dir):
    file_path = os.path.join(temp_dir, key)
    s3_client.download_file(S3_BUCKET, key, file_path)
    return file_path

def upload_to_s3(file_path, key):
    s3_client.upload_file(file_path, S3_BUCKET, key)

@app.route('/initiate-download', methods=['POST'])
def initiate_download():
    #return request.form
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
    # ext_user_username = "e269694"  # Use for debugging purposes
    
    if not ext_user_username:
        return jsonify({"error": "Username not provided"}), 400
    session['ext_user_username'] = ext_user_username

    # check if first character is 'e' and the rest are digits
    if not re.match(r'^e\d+$', ext_user_username):
        return jsonify({"error": "Invalid username format"}), 400
    
    temp_dir = tempfile.mkdtemp()
    try:
        create_zip(ext_user_username, hw_number, temp_dir)
    finally:
        shutil.rmtree(temp_dir)

    filename = f'ASSIGNMENT_{hw_number}_{ext_user_username[1:]}.zip'
    session['filename'] = filename

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
                }}, 5000);  // Redirect back after 5 seconds
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

        filename = session.get('filename')
        if not filename:
            raise ValueError("Filename not found in session")

        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': filename},
            ExpiresIn=3600
        )
        return redirect(response)
    except ValueError as ve:
        app.logger.error(f"Access error: {str(ve)}")
        return jsonify({"error": str(ve)}), 403
    except Exception as e:
        app.logger.error(f"Error downloading file: {str(e)}")
        return jsonify({"error": str(e)}), 500

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', debug=True)