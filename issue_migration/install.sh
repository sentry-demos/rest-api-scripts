set -e

if [ ! -d "./venv" ]; then
    python3.11 -m venv ./venv
fi

source venv/bin/activate
pip install -r requirements.txt