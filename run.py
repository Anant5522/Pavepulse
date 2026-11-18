import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')
    print(f"🚀 PavePulse starting on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
