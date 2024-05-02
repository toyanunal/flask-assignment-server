from flask import Flask, session, request, jsonify, render_template_string, send_from_directory
from datetime import datetime, timedelta
import re, secrets, os

app = Flask(__name__)
app.secret_key = 'testing' ########## Change this ##########

def generate_secure_token():
    return secrets.token_urlsafe()

def extract_number(text):
    # Find all groups of digits in the text
    numbers = re.findall(r'\d+', text)
    if numbers:
        return numbers[0]  # Return the first number found
    return None

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

    directory = '/Users/toyanunal/Downloads/Docs/flask-assignment-server'
    session['directory'] = directory

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
    token_sent = request.args.get('token')
    token_session = session.get('download_token')
    token_uses = session.get('token_uses', 0)
    token_expiry = session.get('token_expiry', 0)

    # Check token expiry
    if datetime.now().timestamp() > token_expiry:
        return jsonify({"error": "Token expired"}), 403

    # Check token validity and uses
    if not token_sent or token_sent != token_session or token_uses >= 3:
        return jsonify({"error": "Unauthorized access"}), 403
    
    # Increment the use counter
    session['token_uses'] = token_uses + 1
    
    filename = session.get('filename', None)
    directory = session.get('directory', None)
    if not filename or not directory:
        return jsonify({"error": "File information not found"}), 400

    try:
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
    #port = int(os.environ.get("PORT", 5000))
    #app.run(host='0.0.0.0', port=port)

