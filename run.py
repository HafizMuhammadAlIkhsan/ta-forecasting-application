import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.cli import cli_bp

app = create_app()
app.register_blueprint(cli_bp)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
