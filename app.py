from flask import Flask, session, request, jsonify, render_template_string, send_from_directory, redirect, url_for
from flask_session import Session
from datetime import datetime, timedelta
import re, secrets, os, boto3

app = Flask(__name__)
app.secret_key = os.urandom(24)

s3_client = boto3.client('s3')
S3_BUCKET = 'flask-assignment-server-bucket'

def generate_secure_token():
    return secrets.token_urlsafe()

def extract_number(text):
    numbers = re.findall(r'\d+', text)
    return numbers[0] if numbers else None

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
    #ext_user_username = "e073281" ########## Change this ##########
    if not ext_user_username:
        return jsonify({"error": "Username not provided"}), 400
    session['ext_user_username'] = ext_user_username
    
    filename = f'ASSIGNMENT_{hw_number}_{ext_user_username[1:]}.zip'
    session['filename'] = filename

    #download_url = url_for('download_file', token=token)

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
        if not token_sent or token_sent != token_session:
            raise ValueError("Token mismatch or expired")

        filename = session.get('filename')
        if not filename:
            raise ValueError("Filename not found in session")

        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': filename},
            ExpiresIn=3600
        )
        return redirect(response)
    except Exception as e:
        app.logger.error(f"Error downloading file: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

