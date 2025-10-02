from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Cấu hình
SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_ID = '1ANjL1BaCNnlQZf9eozQTiHltQxPtoaDZ'  # Thư mục bạn đã chia sẻ

# Xác thực
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

drive_service = build('drive', 'v3', credentials=credentials)

# Upload file vào thư mục chia sẻ
file_metadata = {
    'name': 'demo.txt',
    'parents': [FOLDER_ID]
}
media = MediaFileUpload('demo.txt', mimetype='text/plain')

file = drive_service.files().create(
    body=file_metadata,
    media_body=media,
    fields='id'
).execute()

print('✅ File uploaded to shared folder. File ID:', file.get('id'))
