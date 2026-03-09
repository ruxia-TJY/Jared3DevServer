import os
import config
from app import create_app

app = create_app()

if __name__ == '__main__':
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.DATA_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=False)
