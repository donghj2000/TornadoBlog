# decorator.py
import jwt
from datetime import datetime,timedelta
from functools import wraps
from hashlib import sha256
import os
import random
import string
from slugify import slugify

import smtplib
from email.mime.text import MIMEText
from email.header import Header

import config

def jwt_payload(identity):
    iat = datetime.utcnow()
    exp = iat + timedelta(days=config.JWT_EXPIRATION_DAYS)
    return {'exp': exp, 'iat': iat, 'identity': identity }
    

def jwt_encode(identity):
    secret = config.JWT_SECRET_KEY
    algorithm = config.JWT_ALGORITHM
    required_claims = config.JWT_REQUIRED_CLAIMS

    payload = jwt_payload(identity)
    missing_claims = list(set(required_claims) - set(payload.keys()))

    if missing_claims:
        raise RuntimeError('Payload is missing required claims: %s' % ', '.join(missing_claims))

    return jwt.encode(payload, secret, algorithm=algorithm, headers=None)
    

def jwt_decode(token):
    secret = config.JWT_SECRET_KEY
    algorithm = config.JWT_ALGORITHM
    leeway = config.JWT_LEEWAY

    verify_claims = config.JWT_VERIFY_CLAIMS
    required_claims = config.JWT_REQUIRED_CLAIMS

    options = {
        'verify_' + claim: True
        for claim in verify_claims
    }
    options.update({
        'require_' + claim: True
        for claim in required_claims
    })

    return jwt.decode(token, secret, options=options, algorithms=[algorithm], leeway=leeway)
    

def encrypt(password):
    return sha256(password.encode("utf-8") + config.passwd_hash_key.encode("utf-8")).hexdigest()
    
def decrypt(hash, password):
    return ""

def get_sha256(str):
    m = sha256(str.encode('utf-8'))
    return m.hexdigest()
    
def send_mail(subject, message, recipient_list):
    msg = MIMEText(message, 'html', 'utf-8')
    msg['From'] = Header('Blog')  
    msg['Subject'] = Header(subject, 'utf-8')  

    try:
        smtpobj = smtplib.SMTP(config.MAIL_SERVER)
        smtpobj.connect(config.MAIL_SERVER, config.MAIL_PORT)    
        smtpobj.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)  
        smtpobj.sendmail(config.MAIL_USERNAME, recipient_list[0], msg.as_string()) 
    except smtplib.SMTPException:
        print("无法发送邮件")
    finally:
        # 关闭服务器
        smtpobj.quit()
    
def get_random_password():
    return ''.join(random.sample(string.ascii_letters+string.digits, 8))
    
def get_upload_file_path(path, upload_name):
    # Generate date based path to put uploaded file.
    date_path = datetime.now().strftime('%Y/%m/%d')

    # Complete upload path (upload_path + date_path).
    upload_path = os.path.join(config.UPLOAD_URL, path, date_path)
    full_path = os.path.join(config.BASE_DIR, upload_path)
 
    print(upload_path)
    print(full_path)
    make_sure_path_exist(full_path)
    file_name = slugify_filename(upload_name)
    return os.path.join(full_path, file_name).replace('\\', '/'), os.path.join('/', upload_path, file_name).replace('\\', '/')

def slugify_filename(filename):
    """ Slugify filename """
    name, ext = os.path.splitext(filename)
    slugified = get_slugified_name(name)
    return slugified + ext
    
def get_slugified_name(filename):
    slugified = slugify(filename)
    return slugified or get_random_string()

def get_random_string():
    return ''.join(random.sample(string.ascii_lowercase * 6, 6))

def make_sure_path_exist(path):
    if os.path.exists(path):
        return
    os.makedirs(path, exist_ok=True)